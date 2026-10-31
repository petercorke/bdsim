"""Core block base class and concrete block-type subclasses."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, Literal, cast
import numbers
import warnings

import numpy as np

import spatialmath.base as smb

from bdsim.exceptions import BlockApiError, BlockRuntimeError
from bdsim.components import Clock, _fixname, oodebug
from bdsim.connect import Plug, Port, Wire
from bdsim.signature import Signature, maybe_asarray

if TYPE_CHECKING:
    from bdsim.blockdiagram import BlockDiagram
    from bdsim.components import SimulationState

Vector1D = int | float | tuple[float, ...] | list[float] | np.ndarray


class PortValueSlot:
    """
    The signal on one wire.

    The slot of an output port is shared with every input port wired to it, so
    ``value`` and ``signature`` are the producer's and every consumer's view of
    the same wire.  ``signature`` is ``None`` until compile() has observed the
    wire.
    """

    __slots__ = ("value", "signature")

    def __init__(self) -> None:
        self.value: Any = None
        self.signature: Signature | None = None


def _collapse_size_one_vector(value: Any) -> Any:
    """A 1-D ndarray of size 1 is presented as a scalar of the same NumPy type.

    Only ``ndarray`` is affected, and only if it is 1-D: a ``(1, 1)`` matrix
    stays a matrix.
    """
    if isinstance(value, np.ndarray) and value.ndim == 1 and value.size == 1:
        return value[0]
    return value


_MISSING = object()


class Parameter:
    """
    A parameter of a block, see :meth:`Block.add_param`.

    :param name: the name, which is the ``__init__`` argument of the block
    :param when: ``"anytime"``, ``"setup"`` or ``"never"``
    :param validate: optional check of a new value, which raises if it is not acceptable
    :param coerce: check the new value against the type of the current one
    :param forward: ``(block, name)``, the parameter of another block that this one
        stands for, see :meth:`Block.add_param`
    :param unavailable: why the parameter cannot be used, for a block that was built
        without the part it belongs to
    """

    __slots__ = ("name", "when", "validate", "coerce", "forward", "unavailable")

    def __init__(
        self,
        name: str,
        when: Literal["anytime", "setup", "never"] = "anytime",
        validate: Callable[[Any], None] | None = None,
        coerce: bool = True,
        forward: tuple[Block, str] | None = None,
        unavailable: str | None = None,
    ) -> None:
        if when not in ("anytime", "setup", "never"):
            raise ValueError(
                f"when must be 'anytime', 'setup' or 'never', not {when!r}"
            )
        self.name = name
        self.when = when
        self.validate = validate
        self.coerce = coerce
        self.forward = forward
        self.unavailable = unavailable


def _coerce_parameter(block: Block, name: str, old: Any, new: Any) -> Any:
    """
    The new value of a parameter in the type of the old one, or an error.

    The current value says what is acceptable, so no type has to be declared:

    * an ``ndarray`` keeps its shape and dtype; a list of numbers becomes an array,
      and an array that can be cast safely to the dtype is cast (an integer array
      into a float one)
      A one-element array also accepts a number.
    * a ``bool`` stays a bool
    * a number may be any other number, and is widened (an integer parameter can
      become a float, a float parameter stays a float), never narrowed
    * a callable stays callable
    * anything else must be the same type
    * if the current value is ``None`` or does not exist there is nothing to compare
      with, and the new value is accepted
    """
    where = f"block {block.name}: parameter '{name}'"
    if old is _MISSING or old is None:
        return maybe_asarray(new)

    if isinstance(old, np.ndarray):
        if (
            old.size == 1
            and isinstance(new, numbers.Number)
            and not isinstance(new, (bool, np.bool_))
        ):
            new = np.full(old.shape, new)  # a number for a one-element array
        new = maybe_asarray(new)
        if not isinstance(new, np.ndarray):
            raise TypeError(f"{where} is {Signature.of(old)}, not {Signature.of(new)}")
        if new.shape != old.shape:
            raise ValueError(f"{where} has shape {old.shape}, not {new.shape}")
        if new.dtype != old.dtype:
            if not np.can_cast(new.dtype, old.dtype, "same_kind"):
                raise ValueError(
                    f"{where} has dtype {old.dtype}, it cannot be set to {new.dtype}"
                )
            new = new.astype(old.dtype)
        return new

    if isinstance(old, (bool, np.bool_)):
        if not isinstance(new, (bool, np.bool_)):
            raise TypeError(f"{where} is a bool, not {Signature.of(new)}")
        return new

    if isinstance(old, numbers.Number):
        if isinstance(new, (bool, np.bool_)) or not isinstance(new, numbers.Number):
            raise TypeError(
                f"{where} is a number ({Signature.of(old)}), not {Signature.of(new)}"
            )
        return type(old + new)(new)  # widen, never narrow

    if callable(old):
        if not callable(new):
            raise TypeError(f"{where} is a function, not {Signature.of(new)}")
        return new

    if type(new) is not type(old):
        raise TypeError(f"{where} is {Signature.of(old)}, not {Signature.of(new)}")
    return new


class Block(ABC, Port):
    """_summary_

    :param ABC: _description_
    :type ABC: _type_
    :return: _description_
    :rtype: _type_

    Block is the superclass of all blocks in the simulation environment.  It defines the common properties of all blocks:

    - ``nin`` the number of input ports
    - ``nout`` the number of output ports
    - ``nstates`` the number of continuous-time state variables
    - ``ndstates`` the number of discrete-time state variables
    - ``name`` the unique name of the block
    - ``blockclass`` a string indicating the block class, eg. 'sink', 'source', 'function', 'transfer', 'subsystem', 'clocked', etc.
    - ``type`` a string indicating the block type, eg. 'gain', 'sum', 'integrator', etc.

    The simulation engine uses these methods:

        - ``getstate0()``: returns the initial state of the block as a NumPy array
        - ``setstate(x)``: sets the state of the block to the given state ``x`` and returns any remaining state for the next block in the clock sequence
        - ``next(t, u, x)``: computes the next state of the block given the current time ``t``, input values ``inputs``, and current state ``x``
        - ``output(t, u, x)``: returns the output value of the block at output port ``i`` given the current state and inputs. The outputs are cached and
          can be accessed by ``block.output_value(i)``
        - ``deriv(t, u, x)``: returns the derivative of the state variables for continuous-time blocks
        - ``reset()``: restores the block's own initial state, once per run
        - ``configure()``: prepares the block for a run using the signatures of its wires, once per run, after ``reset()`` and before ``start()``
        - ``done()``: performs any cleanup at end of the simulation
        - ``add_param(name, when=, validate=, coerce=)``: registers a parameter, one call per ``__init__`` argument, with when it can be set (``anytime``, ``setup`` or ``never``)
        - ``set_param(name, value)``: sets a registered parameter, checking that the value is of the same kind as the current one, and returns the old value
        - ``parameters()``: the parameters that can be set, with their current values
        - ``info()``: displays information about the block for debugging purposes

    Ports can be accessed by index, eg. ``block.input_value(i)`` or ``block.output_value(i)``, or by name, eg. ``block.inport("in1")`` or ``block.outport("out1")`` if the block has named ports.

        - ``input_value(i)``: returns the value of the input port at index ``i``
        - ``output_value(i)``: returns the value of the output port at index ``i``
        - ``inport_name(i)``: returns the name of the input port at index ``i``
        - ``outport_name(i)``: returns the name of the output port at index ``i``

    """

    # ========================================================================
    # ARCHITECTURE: Port-Slot Runtime Values
    # ========================================================================
    # Runtime signal transport is via one mutable slot per output port.
    #
    # Publish path:
    #   block.output(...) -> Block._publish_output_values(values)
    #   -> a 1-D ndarray of size 1 is collapsed to a scalar (once, here)
    #   -> cache in block._output_values
    #   -> write each output-port value once to self._outport_slots[port]
    #
    # Read path:
    #   block.inport_values / block.inport_value(i)
    #   -> read directly from pre-bound self._inport_slots[i]
    #
    # Wiring model:
    #   Wires remain the topology model. During compile(), after subsystem
    #   flattening and wire hookup, each destination input port is bound to
    #   the source output slot for fast runtime access.
    # ========================================================================

    # Subclasses may define port counts and labels as plain class variables.
    nin: int = 0
    nout: int = 0
    inlabels: list[str] | tuple[str, ...] | None = None
    outlabels: list[str] | tuple[str, ...] | None = None

    # block class, eg. 'sink', 'source', 'function', 'transfer', 'subsystem', 'clocked', etc.
    _blockclass: str = "?"
    _type: str = "?"

    _name: str | None
    _name_tex: str | None

    # graphical hints
    _pos: tuple[float, float] | None  # position on canvas, eg. (x,y)
    _shape: str | None  # passed to graphviz, eg. 'box', 'ellipse', 'diamond'

    _initd: bool = False
    _bd: BlockDiagram | None = None

    _output_values: list | None = None  # access by block.output_value(i)

    _x_view: np.ndarray | None

    _inport_names: list[str] | None
    _outport_names: list[str] | None
    _state_names: list[str] | None

    _clocked: bool = False
    _clock: Clock | None

    _graphics: bool = False
    _parameters: dict[str, Parameter]
    _running: bool = False  # between start() and done(), see set_param()

    # these lists are used to record the wires connected to the block, set by connect()
    # used to build inter-block references at compile time
    _input_wires: list[Wire | None]  # incoming wires
    _output_wires: list[list[Wire]]  # outgoing wires
    _inport_slots: list[PortValueSlot | None]
    _outport_slots: list[PortValueSlot]

    # used at compile time to determine the order of block execution
    _sequence: int | None
    _parents: list[Plug | None]  # blocks that feed into this block, set at compile time

    __array_ufunc__ = None  # allow block operators with NumPy operands

    def __init__(
        self,
        name: str | None = None,
        nin: int | None = None,
        nout: int | None = None,
        nstates: int = 0,
        ndstates: int = 0,
        x0: Vector1D | None = None,
        inputs: Block | tuple[Block | Plug, ...] | list[Block | Plug] | None = None,
        inames: list[str] | None = None,
        onames: list[str] | None = None,
        snames: list[str] | None = None,
        clock: Clock | None = None,
        pos: tuple[float, float] | None = None,
        bd: BlockDiagram | None = None,
        type: str | None = None,
        blockclass: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Construct a new block object.

        :param name: Name of the block, defaults to None
        :type name: str, optional
        :param nin: Number of inputs, defaults to None
        :type nin: int, optional
        :param nout: Number of outputs, defaults to None
        :type nout: int, optional
        :param inputs: Optional incoming connections
        :type inputs: Block, Plug or list of Block or Plug
        :param inames: Names of input ports, defaults to None
        :type inames: list of str, optional
        :param onames: Names of output ports, defaults to None
        :type onames: list of str, optional
        :param snames: Names of states, defaults to None
        :type snames: list of str, optional
        :param pos: Position of block on the canvas, defaults to None
        :type pos: 2-element tuple or list, optional
        :param bd: Parent block diagram, defaults to None
        :type bd: BlockDiagram, optional
        :param kwargs: Unused arguments
        :type kwargs: dict
        :return: A Block superclass
        :rtype: Block

        A block object is the superclass of all blocks in the simulation environment.

        This is the top-level initializer, and handles most options passed to
        the superclass initializer for each block in the library.

        """

        if kwargs:
            raise ValueError(
                f"unexpected keyword arguments {list(kwargs.keys())} in block {name}"
            )

        # print('Block constructor, bd = ', bd)

        def normalized_port_names(
            names: list[str] | tuple[str, ...] | str,
        ) -> list[str]:
            if isinstance(names, str):
                candidates: list[str] = [names]
            else:
                candidates = list(names)
            fixed_names = _fixname(candidates)
            if isinstance(fixed_names, str):
                return [fixed_names]
            return [str(name) for name in fixed_names]

        # set basic block parameters

        # nin and nout can be set by the constructor, or by class variables in the subclass, or default to 0.
        explicit_nin = nin is not None or "nin" in self.__class__.__dict__
        explicit_nout = nout is not None or "nout" in self.__class__.__dict__
        self.nin = nin if nin is not None else int(self.__class__.nin)
        self.nout = nout if nout is not None else int(self.__class__.nout)

        self.name = name

        # set the block type and block class
        self._type = type or self.__class__.__name__.lower()

        if blockclass is not None:
            self._blockclass = blockclass
        if self._blockclass is None:
            raise ValueError(f"blockclass must be specified for block {self.name}")

        # key simulation variables
        self._x_view: np.ndarray | None = (
            None  # view into engine state vector, bound at simulation start
        )
        self._output_values = None  # cached block output values, set by output() method, accessed by outport_value()

        # set by add_block() when block is added to a block diagram
        self._bd: BlockDiagram | None = bd  # owning block diagram
        self._id: int | None = None  # index in block diagram's blocklist

        # deprecated options for graphical display
        if isinstance(pos, list):
            if len(pos) != 2:
                raise ValueError("block position must have exactly two elements")
            self._pos = (pos[0], pos[1])
        else:
            self._pos = pos
        self._shape = "block"  # for box

        self._initd = True
        self._clocked = False
        self._clock = clock
        self._graphics = False
        self._parameters = {}

        self._depth = 0  # block depth in subsystem hierarchy, set at compile time

        if bd is not None:
            bd.add_block(self)

        # ports can have names as well as indices, for access by name.
        #  names are set by:
        #  - inames and onames options, or by
        #  - inlabels and outlabels class variables, or
        #  - default to None.
        #
        # _portnames is the list of all port names, used for access by name in __setattr__ and __getattr__
        def checknames(names: list[str]) -> None:
            for name in names:
                if name in self.__dict__:
                    raise ValueError(f"port name {name} conflicts with block attribute")

        if inames is None:
            inames = getattr(self.__class__, "inlabels", None)
        if inames is not None:
            if explicit_nin:
                if len(inames) != self.nin:
                    raise ValueError(
                        "number of input port names must match number of inputs"
                    )
            else:
                self.nin = len(inames)
            inames = normalized_port_names(inames)
            if len(set(inames)) != len(inames):
                raise ValueError("input port names must be unique")
            checknames(inames)
        self._inport_names = inames

        if onames is None:
            onames = getattr(self.__class__, "outlabels", None)
        if onames is not None:
            if explicit_nout:
                if len(onames) != self.nout:
                    raise ValueError(
                        "number of output port names must match number of outputs"
                    )
            else:
                self.nout = len(onames)
            onames = normalized_port_names(onames)
            if len(set(onames)) != len(onames):
                raise ValueError("output port names must be unique")
            checknames(onames)
        self._outport_names = onames

        if snames is not None:
            if nstates is not None:
                if len(snames) != nstates:
                    raise ValueError(
                        "number of state names must match number of states"
                    )
            else:
                nstates = len(snames)
        self._state_names = snames

        # block inputs can be specified in the constructor for convenience, and are connected here.
        if isinstance(inputs, Block):
            inputs = (inputs,)
        if inputs is not None and len(inputs) > 0:
            # assert len(inputs) == self.nin, 'Number of input connections must match number of inputs'
            if self.bd is None:
                raise RuntimeError(
                    "inputs provided but block is not in a block diagram"
                )  # pragma: no cover
            for i, input in enumerate(inputs):
                self.bd.connect(input, Plug(self, port=i))

        self._nstates = nstates
        self._ndstates = ndstates

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Initialize a subclass of Block.

        :param cls: The subclass being initialized
        :type cls: class type
        :param kwargs: keyword args passed to subclass definition
        :type kwargs: dict

        This method is called when a new subclass of Block is defined, not when it is
        instantiated. Here we check that the subclass does not define methods that are
        inconsistent with its block class, and raise an error if it does.  This is a
        sanity check to prevent blocks from being defined with methods that will never
        be called by the simulation engine, which would indicate a misunderstanding of
        the block API.

        """
        super().__init_subclass__(**kwargs)

        # Auto-derive _blockclass from class name for typed base classes (e.g.
        # ContinuousBlock → "continuous") unless an explicit override is present.
        if cls.__name__.endswith("Block") and "_blockclass" not in cls.__dict__:
            cls._blockclass = cls.__name__.lower().replace("block", "")

        # check that the subclass does not have methods inconsistent with its class
        disallowed = {
            "SourceBlock": ["deriv", "step", "next"],
            "SinkBlock": ["deriv", "output", "next"],
            "FunctionBlock": ["deriv", "next", "step"],
            "ContinuousBlock": ["next", "step"],
            "TransferBlock": ["next", "step"],  # deprecated alias for ContinuousBlock
            "GraphicsBlock": ["deriv", "next", "output"],
            "SampledBlock": ["deriv", "step"],
            "ClockedBlock": ["deriv", "step"],  # deprecated alias for SampledBlock
            "SubsystemBlock": ["deriv", "output", "next", "step"],
        }
        blockclass = cls.__mro__[1].__name__
        if blockclass in disallowed:
            # raise ValueError(
            #     f"unknown block class {blockclass} for class {cls.__name__}"
            # )
            # # check that the subclass does not have methods inconsistent with its class
            for method in disallowed[blockclass]:
                if hasattr(cls, method):
                    raise BlockApiError(
                        f"method {method} not allowed for block {cls.__name__} in class {blockclass} -- owning module will not be included in block library",
                        traceback=False,
                    )

    # def __str__(self) -> str:
    #     if hasattr(self, "name") and self.name is not None:
    #         return self.name
    #     else:
    #         return self.blockclass + ".??"

    def __repr__(self) -> str:
        s = f"Block.{self._blockclass}('{self.name}', type={self._type}"
        if hasattr(self, "_clock") and self._clock is not None:
            s += f", clock={self._clock.name}"
        if self.nin > 0:
            s += f", nin={self.nin}"
        if self.nout > 0:
            s += f", nout={self.nout}"
        if self._nstates > 0:
            s += f", nstates={self.nstates}"
        if self._ndstates > 0:
            s += f", ndstates={self.ndstates}"
        if self._inport_names is not None:
            s += f", inames={self._inport_names}"
        if self._outport_names is not None:
            s += f", onames={self._outport_names}"
        if self._state_names is not None:
            s += f", snames={self._state_names}"
        return s + ")"

    @property
    def info(self) -> None:
        """
        Interactive display of block properties.

        Displays all attributes of the block for debugging purposes.

        """
        print("block: " + type(self).__name__)
        items = sorted(self.__dict__.items())
        for k, v in [i for i in items if i[0].startswith("_")] + [
            i for i in items if not i[0].startswith("_")
        ]:
            print("  {:11s}{:s}".format(k + ":", str(v)))

    def add_param(
        self,
        name: str,
        *,
        when: Literal["anytime", "setup", "never"] = "anytime",
        validate: Callable[[Any], None] | None = None,
        coerce: bool = True,
        forward: tuple[Block, str] | None = None,
        unavailable: str | None = None,
    ) -> None:
        """
        Register a parameter of the block, one per call.

        :param name: the name of the parameter, which is the name of the ``__init__``
            argument.  The block's current value is ``getattr(self, name)``, so it is a
            plain attribute or a Python ``property``
        :type name: str
        :param when: when the parameter can be set, one of

            * ``"anytime"``: at any time, between evaluations (default)
            * ``"setup"``: before the run starts, including from ``--set``, but not
              while it runs, because :meth:`start` has used the value to build something
              such as an event or a figure
            * ``"never"``: not after the block is created, for structure such as
              ``nin`` or ``clock``

        :type when: str, optional
        :param validate: a function of the new value that raises ``ValueError`` or
            ``TypeError`` if it is not acceptable, for example a bound method of the
            block, called after the type has been checked.  If it returns a value that
            is not ``None`` that replaces the new value, which lets a check that has to
            keep two parameters consistent promote them together
        :type validate: callable, optional
        :param coerce: check the new value against the type of the current one,
            see :meth:`set_param`, defaults to True.  Give ``False`` for a parameter
            that legitimately takes several forms or changes shape, such as a
            polynomial that may be given as coefficients or as factors, and let the
            ``property`` setter or ``validate`` deal with the value
        :type coerce: bool, optional
        :param forward: for a block made of other blocks, such as a subsystem: the
            parameter of an inner block that this one stands for, as ``(block, name)``.
            The value lives in the inner block, which does all the checking, so
            ``set_param`` and the current value are simply passed on.  The inner
            parameter can itself be forwarded, so subsystems nest.  The block is given
            as an object, which stays the right one when the subsystem is flattened into
            its parent diagram and its blocks are renamed.
        :type forward: tuple(Block, str), optional
        :param unavailable: for a parameter that belongs to a part the block was built
            without, such as the integral term of a PID block with ``I=0``: the reason,
            which is the message if someone tries to set it
        :type unavailable: str, optional

        Every ``__init__`` argument of a block is registered, each with a decision
        about when it can be set.  A parameter whose value is not kept under its own
        name, because the block built other blocks or derived state from it, is a
        ``property`` of the class: the getter finds the value and the setter applies it.

        :seealso: :meth:`set_param` :meth:`parameters`
        """
        if forward is not None:
            target, target_name = forward
            inner = target._parameters.get(target_name)
            if inner is None or inner.when == "never":
                raise ValueError(
                    f"{name} cannot stand for {target.name}:{target_name}, which is not "
                    "a parameter that can be set"
                )
        self.__dict__["_parameters"][name] = Parameter(
            name, when, validate, coerce, forward, unavailable
        )

    def _param_when(self, param: Parameter) -> str:
        """When a parameter can be set; that of the inner parameter if it is forwarded."""
        if param.unavailable is not None:
            return "never"
        if param.forward is not None:
            target, name = param.forward
            return target._param_when(target._parameters[name])
        return param.when

    def _param_value(self, name: str) -> Any:
        """The current value of a parameter, from the inner block if it is forwarded."""
        param = self._parameters.get(name)
        if param is not None and param.forward is not None:
            target, target_name = param.forward
            return target._param_value(target_name)
        return getattr(self, name, None)

    def remove_param(self, name: str) -> None:
        """
        Remove a registered parameter, for a subclass whose parent registers one that
        does not apply to it.

        :param name: the name of the parameter
        :type name: str
        """
        self.__dict__["_parameters"].pop(name, None)

    def _lookup_param(self, name: str) -> Parameter:
        """The registered parameter, or a ValueError that says what can be set."""
        param = self._parameters.get(name)
        if param is None:
            settable = ", ".join(self.parameters()) or "none"
            raise ValueError(
                f"block {self.name} ({self.type}) has no settable parameter '{name}'; "
                f"settable parameters: {settable}"
            )
        if param.unavailable is not None:
            raise ValueError(
                f"block {self.name}: parameter '{name}' cannot be set, {param.unavailable}"
            )
        if self._param_when(param) == "never":
            raise ValueError(
                f"block {self.name}: parameter '{name}' is fixed when the block is "
                "created and cannot be set"
            )
        return param

    def set_param(self, name: str, newvalue: Any) -> Any:
        """
        Set a registered parameter of the block.

        :param name: the name of the parameter
        :type name: str
        :param newvalue: the new value
        :return: the old value
        :raises ValueError: no such parameter, it is fixed, it cannot be set while the
            run is going, or the value is not acceptable
        :raises TypeError: the value is of the wrong type

        The new value must be of the same kind as the current one, see
        :func:`_coerce_parameter`: an array keeps its shape and dtype, a number can widen
        from integer to float but not narrow, and so on.  A list of numbers is
        converted to an array if the parameter is an array.

        :seealso: :meth:`add_param` :meth:`parameters`
        """
        param = self._lookup_param(name)
        if param.forward is not None:
            target, target_name = param.forward
            return target.set_param(target_name, newvalue)
        if param.when == "setup" and self._running:
            raise ValueError(
                f"block {self.name}: parameter '{name}' can only be set before the "
                "run starts, not while it is running"
            )

        old = getattr(self, name, _MISSING)
        new = _coerce_parameter(self, name, old, newvalue) if param.coerce else newvalue
        if param.validate is not None:
            checked = param.validate(new)
            if checked is not None:  # the check may normalise the value
                new = checked
        setattr(self, name, new)
        return None if old is _MISSING else old

    def parameters(self) -> dict[str, Any]:
        """
        The parameters that can be set, with their current values.

        :return: ``{name: value}`` for every registered parameter that is not fixed
        :rtype: dict

        :seealso: :meth:`add_param` :meth:`set_param`
        """
        return {
            name: self._param_value(name)
            for name, param in self._parameters.items()
            if self._param_when(param) != "never"
        }

    @property
    def id(self) -> int | None:
        return self._id

    @id.setter
    def id(self, v: int | None) -> None:
        self._id = v

    @property
    def type(self) -> str:
        return self._type

    @type.setter
    def type(self, v: str) -> None:
        self._type = v

    @property
    def nstates(self) -> int:
        return self._nstates

    @nstates.setter
    def nstates(self, v: int) -> None:
        self._nstates = v

    @property
    def ndstates(self) -> int:
        return self._ndstates

    @ndstates.setter
    def ndstates(self, v: int) -> None:
        self._ndstates = v

    @property
    def blockclass(self) -> str:
        return self._blockclass

    @blockclass.setter
    def blockclass(self, v: str) -> None:
        self._blockclass = v

    @property
    def name(self) -> str | None:
        return self._name

    @name.setter
    def name(self, name: str | None) -> None:
        if name is not None:
            self._name_tex = name
            fixed_name = _fixname(name)
            if not isinstance(fixed_name, str):
                raise TypeError("block name must resolve to a string")
            self._name = fixed_name
        else:
            self._name_tex = None
            self._name = None

    @property
    def name_tex(self) -> str | None:
        return self._name_tex

    def state_names(self, names: list[str]) -> None:
        self._state_names = names

    def inport_names(self, names: list[str] | tuple[str, ...] | str) -> None:
        """Set input port names (legacy method for backward compatibility)."""
        if isinstance(names, str):
            names = [names]
        else:
            names = list(names)
        names = [str(n) for n in _fixname(names)]
        self._inport_names = names

    def outport_names(self, names: list[str] | tuple[str, ...] | str) -> None:
        """Set output port names (legacy method for backward compatibility)."""
        if isinstance(names, str):
            names = [names]
        else:
            names = list(names)
        names = [str(n) for n in _fixname(names)]
        self._outport_names = names

    @property
    def fullname(self) -> str:
        return self.blockclass + "." + str(self)

    @property
    def hasstate(self) -> bool:
        """True if the block owns continuous or discrete state."""
        return self.nstates > 0 or self.ndstates > 0

    # ---------------------------------------------------------------------- #

    @property
    def isclocked(self) -> bool:
        """
        Test if block is clocked

        :return: True if block is clocked
        :rtype: bool

        True if block is clocked, False if it is continuous time.
        """
        return self._clocked

    @property
    def isgraphics(self) -> bool:
        """
        Test if block does graphics

        :return: True if block does graphics
        :rtype: bool
        """
        return self._graphics

    @property
    def pos(self) -> tuple[float, float] | None:
        return self._pos

    @property
    def shape(self) -> str | None:
        return self._shape

    @property
    def initd(self) -> bool:
        return self._initd

    @property
    def bd(self) -> BlockDiagram:
        if self._bd is None:
            raise RuntimeError("block is not in a block diagram")  # pragma: no cover
        return self._bd

    @bd.setter
    def bd(self, bd: BlockDiagram | None) -> None:
        self._bd = bd

    # ---------------------------------------------------------------------- #
    # inputs to the block

    @property
    def sources(self) -> list[Block]:
        """
        List of source blocks feeding into this block.

        :return: List of source blocks
        :rtype: list of Block, of length ``nin``

        Returns the list of source blocks, those that feed input signals into this block.

        This is determined at compile time by the connections in the block diagram.  It
        is used to determine the order of block execution.

        :seealso: :meth:`Block.inports` :meth:`Block.inputs` :meth:`Block.source_name`
        """
        sources: list[Block] = []
        for wire in self._input_wires:
            if wire is None:
                raise ValueError(f"block {self.name} has an unconnected input")
            sources.append(wire.start.block)
        return sources

    @property
    def inports(self) -> list[Plug]:
        """
        List of output plugs feeding into this block.

        :return: List of source plugs
        :rtype: list of Plug, of length ``nin``

        Returns the list of plugs that describe the outout ports (block and port) that
        feed into this block.

        This is determined at compile time by the connections in the block diagram.  It
        is used to determine the order of block execution.

        :seealso: :meth:`Block.sources` :meth:`Block.inputs`
        """
        inports: list[Plug] = []
        for wire in self._input_wires:
            if wire is None:
                raise ValueError(f"block {self.name} has an unconnected input")
            inports.append(wire.start)
        return inports

    @property
    def inport_values(self) -> list[Any]:
        """
        Get inport values as a list

        :return: list of input to block
        :rtype: list of length ``nin``

        Returns a list of values corresponding to the input ports of the block.  The types of the
        elements are dictated by the blocks connected to the input ports.

        .. note:: Values are read from pre-bound input slots.
            For compatibility with direct unit tests (without compile), if an
            input slot is not bound yet the value is read from the predecessor block.

        :seealso: :meth:`inport_value`
        """
        values = []
        slots = getattr(self, "_inport_slots", None)
        if slots is None:
            raise RuntimeError(
                f"block {self.name} input slots not initialised"
            )  # pragma: no cover
        for i, slot in enumerate(slots):
            if slot is not None:
                values.append(slot.value)
                continue
        return values

    def inport_value(self, i: int) -> Any:
        """
        Get the value applied to specified input port.

        :param i: Input port index
        :type i: int
        :return: Input port value
        :rtype: Any

        Get the value of the signal applied to port ``i``.

        .. note:: The value is read from a pre-bound input slot.
            For compatibility with direct unit tests (without compile), it
            falls back to predecessor block output lookup.

        :seealso: :meth:`inport_values`
        """
        slots = getattr(self, "_inport_slots", None)
        if slots is None:
            raise RuntimeError(
                f"block {self.name} input slots not initialised"
            )  # pragma: no cover

        if slots is not None:
            slot = slots[i]
            if slot is not None:
                return slot.value
        raise ValueError(f"block {self.name} input port {i} not connected")

        # wire = self._input_wires[i]
        # assert wire is not None, f"block {self.name} input port {i} not connected"
        # source = wire.start
        # return source.block.outport_value(source.port)

    def inport_name(self, i: int) -> str:
        """
        Get the name of an input port.

        :param i: Input port index
        :type i: int

        Get the name of an input port by index.  By default the name is the port number
        in square brackets, but if the block has named ports then the name is taken from
        the list of input port names.

        :seealso: :meth:`outport_name` :meth:`source_name`
        """
        if i >= self.nin:
            raise IndexError(f"block {self.name} input port index {i} out of range")
        if self._inport_names is None:
            return f"[{i}]"
        else:
            return self._inport_names[i]

    def source_name(self, port: int) -> str:
        """
        Get the name of output port driving this input port.

        :param port: Input port
        :type port: int
        :return: Port name
        :rtype: str

        Get the name of the output port that drives the specified input port.  By default
        the name is the port number in square brackets, but if the block has named ports
        then the name is taken from the list of input port names.

        :seealso: :meth:`outport_name` :meth:`inport_name`
        """

        wire = self._input_wires[port]
        if wire is None:
            raise ValueError(f"block {self.name} input port {port} not connected")
        if wire.name is not None:
            return wire.name
        b = wire.start.block
        return f"{b.name}{b.outport_name(wire.start.port)}"  # type: ignore[arg-type]

    # ---------------------------------------------------------------------- #
    # outputs of a block

    def outport_value(self, i: int) -> Any:
        """
        Get the value of an output port.

        :param i: Output port index
        :type i: int
        :return: Output port value
        :rtype: Any

        Get the value of the signal at output port ``i``.

        .. note:: The value is obtained from the block's output values
            which are stored in the attribute ``_output_values`` -- a list of length
            ``nout``. These values are set when the block's ``output``
            method is evaluated.

        :seealso: :meth:`inport_value`
        """
        if self._output_values is None:
            raise RuntimeError(
                f"block {self.name} output values not initialised"
            )  # pragma: no cover
        if self._output_values[i] is None:
            raise RuntimeError(
                f"block {self.name} output value {i} not set"
            )  # pragma: no cover
        return self._output_values[i]

    def _publish_output_values(self, out: list[Any] | tuple[Any, ...]) -> None:
        """Cache block outputs and publish each port value once to its slot."""
        self._output_values = [_collapse_size_one_vector(value) for value in out]
        for port, value in enumerate(self._output_values):
            self._outport_slots[port].value = value

    @property
    def outsig(self) -> list[Signature | None]:
        """
        Signatures of the output ports.

        An entry is ``None`` until :meth:`BlockDiagram.compile` has observed
        the wire.

        :seealso: :class:`~bdsim.signature.Signature` :attr:`insig`
        """
        slots = self.__dict__.get("_outport_slots")  # created by compile()
        if slots is None:
            return [None] * self.nout
        return [slot.signature for slot in slots]

    @property
    def insig(self) -> list[Signature | None]:
        """
        Signatures of the input ports.

        The input port is bound to the slot of the output port that drives it,
        so this is that producer's :attr:`outsig`.  An entry is ``None`` if the
        port is unconnected or the wire has not yet been observed.

        :seealso: :class:`~bdsim.signature.Signature` :attr:`outsig`
        """
        slots = self.__dict__.get("_inport_slots")  # created by compile()
        if slots is None:
            return [None] * self.nin
        return [None if slot is None else slot.signature for slot in slots]

    def outport_slot(self, i: int) -> PortValueSlot:
        if i >= self.nout:
            raise IndexError(f"block {self.name} output port index {i} out of range")
        return self._outport_slots[i]

    def bind_input_slot(self, i: int, slot: PortValueSlot) -> None:
        if i >= self.nin:
            raise IndexError(f"block {self.name} input port index {i} out of range")
        self._inport_slots[i] = slot

    def outport_name(self, i: int) -> str:
        """
        Get the name of an output port.

        :param i: Output port index
        :type i: int

        Get the name of an output port by index.  By default the name is the port number
        in square brackets, but if the block has named ports then the name is taken from
        the list of output port names.

        :seealso: :meth:`inport_name` :meth:`source_name`
        """
        if i >= self.nout:
            raise IndexError(f"block {self.name} output port index {i} out of range")
        if self._outport_names is None:
            return f"[{i}]"
        else:
            return self._outport_names[i]

    def _raise_runtime_error(
        self,
        operation: str,
        err: Exception,
        *,
        t: float | None = None,
        inputs: Any = None,
        state: Any = None,
    ) -> None:
        raise BlockRuntimeError(
            operation=operation,
            block=self,
            cause=err,
            t=t,
            inputs=inputs,
            state=state,
        ) from err

    def output_safe(self, t: Any, u: Any, x: Any) -> Any:
        try:
            return self.output(t, u, x)
        except Exception as err:
            self._raise_runtime_error("output", err, t=t, inputs=u, state=x)

    def deriv_safe(self, t: Any, u: Any, x: Any) -> Any:
        try:
            return self.deriv(t, u, x)
        except Exception as err:
            self._raise_runtime_error("deriv", err, t=t, inputs=u, state=x)

    def step_safe(self, t: Any, u: Any) -> None:
        try:
            self.step(t, u)
        except Exception as err:
            self._raise_runtime_error("step", err, t=t, inputs=u)

    def record(self, t: float, u: list[Any]) -> None:
        """Record one accepted sample, independent of graphics/animation throttling.

        Default is a no-op. Sink blocks that log signal data (e.g. ``Scope``)
        override this to append at full simulation resolution, since ``step``
        itself may be called only periodically for display-refresh purposes.

        :param t: simulation time
        :type t: float
        :param u: block input port values
        :type u: list
        """

    def record_safe(self, t: Any, u: Any) -> None:
        try:
            self.record(t, u)
        except Exception as err:
            self._raise_runtime_error("record", err, t=t, inputs=u)

    def next_safe(self, t: Any, u: Any, x: Any) -> Any:
        try:
            return self.next(t, u, x)
        except Exception as err:
            self._raise_runtime_error("next", err, t=t, inputs=u, state=x)

    def check_safe(self) -> None:
        try:
            self.check()
        except Exception as err:
            self._raise_runtime_error("check", err)

    def getstate0_safe(self) -> Any:
        try:
            return self.getstate0()
        except Exception as err:
            self._raise_runtime_error("getstate0", err)

    def reset_safe(self) -> None:
        try:
            self.reset()
        except Exception as err:
            self._raise_runtime_error("reset", err)

    def configure_safe(self) -> None:
        try:
            self.configure()
        except Exception as err:
            self._raise_runtime_error("configure", err)

    def start_safe(self, simstate: Any) -> None:
        try:
            self.start(simstate)
        except Exception as err:
            self._raise_runtime_error("start", err)
        self._running = True

    def validate_start_safe(self) -> None:
        try:
            self.validate_start()
        except Exception as err:
            self._raise_runtime_error("start", err)

    def done_safe(self, **kwargs: Any) -> None:
        try:
            self.done(**kwargs)
        except Exception as err:
            self._raise_runtime_error("done", err)
        finally:
            self._running = False

    # ---------------------------------------------------------------------- #
    # methods used for unit testing

    #  test_MMMMM is a wrapper around the normal block method MMMMM, which checks the inputs and outputs for
    #  consistency with the block definition, and is used for concise unit tests.

    def test_output(
        self, *inputs: Any, t: float = 0.0, x: np.ndarray | None = None
    ) -> list[Any]:
        """
        Evaluate a block for unit testing.

        :param inputs: Input port values
        :param t: Simulation time, defaults to 0.0
        :type t: float, optional
        :param x: state vector
        :type x: ndarray
        :return: Block output port values
        :rtype: list

        The output ports of the block are evaluated for a given simulation time
        and set of input port values. Input ports are assigned to consecutive inputs,
        output port values are a list.

        Mostly used for making concise unit tests.
        """
        # check inputs and assign to attribute
        if len(inputs) != self.nin:
            raise ValueError("wrong number of inputs provided")

        # evaluate the block
        out = self.output(t, inputs, x)

        # sanity check the output
        if not isinstance(out, list):
            raise TypeError("result must be a list")
        if len(out) != self.nout:
            raise ValueError("result list is wrong length")
        return out

    def test_deriv(
        self, *inputs: Any, t: float = 0.0, x: np.ndarray | None = None
    ) -> np.ndarray:
        """
        Evaluate a block for unit testing.

        :param inputs: input port values
        :type inputs: list
        :param t: Simulation time, defaults to 0.0
        :type t: float, optional
        :param x: state vector
        :type x: ndarray
        :return: Block derivative value
        :rtype: ndarray

        The derivative of the block is evaluated for a given set of input port
        values. Input port values are treated as lists.

        Mostly used for making concise unit tests.
        """

        # check inputs and assign to attribute
        if len(inputs) != self.nin:
            raise ValueError("wrong number of inputs provided")

        if x is not None and len(x) != self.nstates:
            raise ValueError("passed state is wrong length")

        # evaluate the block
        out = self.deriv(t, inputs, x)

        # sanity check the output
        if not isinstance(out, np.ndarray):
            raise TypeError("result must be an ndarray")
        if out.shape != (self.nstates,):
            raise ValueError("result array is wrong length")
        return out

    def test_next(
        self, *inputs: Any, t: float = 0.0, x: np.ndarray | None = None
    ) -> np.ndarray:
        """
        Evaluate a block for unit testing.

        :param inputs: input port values
        :type inputs: list
        :param t: Simulation time, defaults to 0.0
        :type t: float, optional
        :param x: state vector
        :type x: ndarray
        :return: Block next state value
        :rtype: ndarray

        The next value of a discrete time block is evaluated for a given set of input port
        values. Input port values are treated as lists.

        Mostly used for making concise unit tests.

        """

        # check inputs and assign to attribute
        if len(inputs) != self.nin:
            raise ValueError("wrong number of inputs provided")

        if x is not None and len(x) != self.ndstates:
            raise ValueError("passed state is wrong length")

        # evaluate the block
        if not hasattr(self, "next"):
            raise AttributeError("block does not have a next method")
        out = self.next(t, inputs, x)

        # sanity check the output
        if not isinstance(out, np.ndarray):
            raise TypeError("next state must be an ndarray")
        if out.shape != (self.ndstates,):
            raise ValueError("next state array is wrong length")
        return out

    def test_step(self, *inputs: Any, t: float = 0.0) -> None:
        """
        Step a block for unit testing.

        :param inputs: input port values
        :type inputs: list
        :param t: Simulation time, defaults to 0.0
        :type t: float, optional

        Step the block for a given set of input port
        values. Input port values are treated as lists.

        Mostly used for making concise unit tests.

        """

        # check inputs and assign to attribute
        if len(inputs) != self.nin:
            raise ValueError("wrong number of inputs provided")

        # step the block
        self.step(t, inputs)

    def test_start(self, simstate: SimulationState | None = None) -> SimulationState:
        from bdsim.run_sim import BDSimState, Options

        if simstate is None:

            class RunTime:
                options: Options

                def DEBUG(self, *args: Any) -> None:
                    pass

            class BlockDiagram:
                runtime: RunTime

            runtime = RunTime()
            runtime.options = Options()
            blockdiagram = BlockDiagram()
            blockdiagram.runtime = runtime
            self._bd = cast("BlockDiagram", blockdiagram)  # type: ignore[assignment]
            simstate = BDSimState()
            simstate.options = runtime.options
            simstate.t = 0.0

        # step the block
        self.start(simstate)
        return simstate

    # ---------------------------------------------------------------------- #
    #  set/get items and attributes

    def __getitem__(self, port: int | slice) -> Plug:
        """
        Convert a RHS block slice reference to a Plug.

        :param port: Port number
        :type port: int
        :return: A port plug
        :rtype: Plug

        Invoked whenever a block is referenced as a slice, for example::

            c = bd.CONSTANT(1)

            bd.connect(x, c[0])
            bd.connect(c[0], x)

        In both cases ``c[0]`` is converted to a ``Plug`` by this method.
        """
        # block[i] is a plug object
        # print('getitem called', self, port)
        return Plug(self, port)

    def __setitem__(self, port: int, src: Block | Plug) -> None:
        """
        Convert a LHS block slice reference to a wire.

        :param port: Port number
        :type port: int
        :param src: the RHS
        :type src: Block or Plug

        Used to create a wired connection by assignment, for example::

            X[0] = Y

        where ``X`` and ``Y`` are blocks. This method is implicitly invoked and
        creates a wire from ``Y`` to input port 0 of ``X``.

        .. note:: The square brackets on the left-hand-side is critical, and
            ``X = Y`` will simply overwrite the reference to ``X``.
        """
        # b[port] = src
        # src --> b[port]
        # print('connecting', src, self, port)
        return self.bd.connect(src, self[port])

    def __getattr__(self, name: str) -> Any:
        """
        Convert a RHS block name reference to a Plug.

        :param name: Port name
        :type port: str
        :return: Block or plug for specified block port name
        :rtype: ``Port``

        Used to create a wired connection by assignment, for example::

            c = bd.CONSTANT(1, onames=['v'])

            y = c.v

                ┌───┐               ┌───┐
                │ c ├ v ──────────▶ │ y │
                └───┘               └───┘

        Also used for assignments using ``connect``, for example::

            bd.connect(x, c.v)  # connect output of x to input port v of block c
            bd.connect(c.v, x)  # connect output port v of block c to input of x

        .. warning:: to avoid infinite recursion, this method must use
            ``super().__getattribute__`` to access attributes of the block, and only
            create a Plug if the name is in the list of port names.
        """

        # come here only if the attribute is not found in the normal way, so we know
        # it's not a regular attribute of the block

        # we have to use self.__dict__.get() to avoid infinite recursion, since the port
        # names are stored in attributes of the block

        # is it an output port name?
        outport_names = self.__dict__.get("_outport_names")
        if outport_names is not None and name in outport_names:
            port = outport_names.index(name)
            return Plug(self, port)

        # is it an input port name?
        inport_names = self.__dict__.get("_inport_names")
        if inport_names is not None and name in inport_names:
            port = inport_names.index(name)
            return Plug(self, port)

        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Convert a LHS block name reference to a wire.

        :param name: Port name
        :type port: str
        :param value: the RHS
        :type value: ``Port``

        Used to create a wired connection by assignment, for example::

            c = bd.CONSTANT(1, inames=['u'])

            c.u = x

        Ths method is invoked to create a wire from ``x`` to port 'u' of
        the constant block ``c``.

                +---+              +---+
                | x | --------> u- | c |
                +---+              +---+

        Notes:

            - this overloaded method handles all instances of ``setattr`` and
              implements normal functionality as well, only creating a wire
              if ``name`` is a known port name.
        """

        # b[port] = src
        # src --> b[port]
        # gets called for regular attribute settings, as well as for wiring

        # on the LHS the ports must be input ports

        inport_names = self.__dict__.get("_inport_names")
        if inport_names is not None and name in (inport_names or []):
            # we're doing wiring
            port = inport_names.index(name)
            self.bd.connect(value, Plug(self, port=port))
        else:
            # regular case, add attribute
            super().__setattr__(name, value)

    # ---------------------------------------------------------------------- #
    # methods used at compile time to build inter-block references

    def compile(self) -> None:
        """
        Compile the block for execution.

        This method is called at compile time to initialize the attributes required for
        compilation.

        :seealso: :meth:`BlockDiagram.compile`
        """
        # initialize lists of input and output ports
        #  these are set when blocks are connected, used to build inter-block references at compile time
        self._output_wires: list[list[Wire]] = [[] for _ in range(self.nout)]
        self._input_wires: list[Wire | None] = [None] * self.nin  # type: ignore[list-item]
        self._outport_slots: list[PortValueSlot] = [
            PortValueSlot() for _ in range(self.nout)
        ]
        self._inport_slots: list[PortValueSlot | None] = [None] * self.nin

        # used to build execution plan at compile time, set by compile() method
        self._sequence = None
        self._depth = 0
        self._parents: list[Plug | None] = [None] * self.nin  # type: ignore[list-item]

    def add_output_wire(self, w: Wire) -> None:
        port = w.start.port
        if not isinstance(port, int):
            raise TypeError("output wire port must be an int")
        if port >= len(self._output_wires):
            raise IndexError("port number too big")
        self._output_wires[port].append(w)

    def add_input_wire(self, w: Wire) -> None:
        port = w.end.port
        if not isinstance(port, int):
            raise TypeError("input wire port must be an int")
        if self._input_wires[port] is not None:
            raise ValueError("attempting to connect second wire to an input")
        self._input_wires[port] = w
        self._parents[port] = w.start

    # ---------------------------------------------------------------------- #
    # operator overloads for implicit wiring

    @oodebug
    def __rshift__(left: Block, right: Block | Plug) -> Block | Plug:
        """
        Operator for implicit wiring.

        :param left: A block to be wired from
        :type left: Block
        :param right: A block or plugto be wired to
        :type right: Block or Plug
        :return: ``right``
        :rtype: Block or Plug

        Implements implicit wiring, for example::

            a = bd.CONSTANT(1) >> bd.GAIN(2)

        will connect the output of the CONSTANT block to the input of the
        GAIN block.  The result will be GAIN block, whose output in this case
        will be assigned to ``a``.

        Note that::

           a = bd.CONSTANT(1) >> func[1]

        will connect port 0 of CONSTANT to port 1 of ``func``, and port 1 of ``func``
        will be assigned to ``a``.  To specify a different outport port on ``func``
        we need to use parentheses::

            a = (bd.CONSTANT(1) >> func[1])[0]

        which will connect port 0 of CONSTANT ` to port 1 of ``func``, and port 0 of ``func``
        will be assigned to ``a``.

        :seealso: Plug.__rshift__

        """
        # called for the cases:
        # block * block
        # block * plug
        s = left.bd
        if s is None:
            raise RuntimeError(  # pragma: no cover
                "left operand of >> operator must be a block connected to a block diagram"
            )
        s.connect(left, right)
        return right

        # make connection, return a plug

    def _autoconstant(self, value: int | float | str | np.ndarray) -> Block:
        if self.bd is None:
            raise RuntimeError(  # pragma: no cover
                "block must be connected to a block diagram to create an automatic constant"
            )

        if isinstance(value, (int, float)):
            name = "_const.{:d}({:.3g})".format(next(self.bd.n_auto_const), value)
        elif isinstance(value, str):
            name = "_const.{:d}({})".format(next(self.bd.n_auto_const), value)
        else:
            name = "_const.{:d}<{}>".format(
                next(self.bd.n_auto_const), type(value).__name__
            )
        return self.bd.CONSTANT(value, name=name)

    def _autogain(self, value: int | float | np.ndarray, **kwargs: Any) -> Block:
        if self.bd is None:
            raise RuntimeError(  # pragma: no cover
                "block must be connected to a block diagram to create an automatic gain"
            )

        if isinstance(value, (int, float)):
            name = "_gain.{:d}({:.3g})".format(next(self.bd.n_auto_gain), value)
        elif isinstance(value, np.ndarray):
            name = "_gain.{:d}({})".format(next(self.bd.n_auto_gain), value)
        else:
            raise TypeError(
                f"automatic gain value must be int, float, or ndarray, got {type(value).__name__}"
            )
        return self.bd.GAIN(value, name=name, **kwargs)

    def _autopow(self, value: int | float, **kwargs: Any) -> Block:
        if self.bd is None:
            raise RuntimeError(  # pragma: no cover
                "block must be connected to a block diagram to create an automatic power block"
            )

        name = "_pow.{:d}({:.3g})".format(next(self.bd.n_auto_pow), value)
        return self.bd.POW(value, name=name, **kwargs)

    @oodebug
    def __add__(self, other):
        """
        Overloaded + operator for implicit block creation.

        :param self: A signal (block) to be added
        :type self: Block
        :param other: A signal (block or plug) to be added
        :type other: Block or Plug
        :return: SUM block
        :rtype: Block subclass

        This method is implicitly invoked by the + operator
        when the right operand is a ``Block``
        and the left operand is a ``Plug``, ``Block`` or constant::

            result = X + Y
            result = X + Y[j]
            result = X + C

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        Creates a ``SUM("++") block named ``_sum.N`` whose inputs are the
        left and right operands.  For the third case, a new ``CONSTANT(C)`` block
        named ``_const.N`` is also created.

        .. note::
            * The inputs to the summing junction are reversed: right then left operand.
            * The ``mode`` is None, regular addition

        :seealso: :meth:`Block.__radd__` :meth:`Plug.__add__`
        """
        # value + value, create a SUM block
        from bdsim.blocks import Sum

        if self.bd is None:
            raise RuntimeError(  # pragma: no cover
                "block must be connected to a block diagram to create an automatic sum block"
            )
        name = "_sum.{:d}".format(next(self.bd.n_auto_sum))
        if isinstance(other, (int, float, np.ndarray)):
            # block + constant, create a CONSTANT block
            other = self._autoconstant(other)
        return Sum("++", inputs=(self, other), name=name, bd=self.bd)

    @oodebug
    def __radd__(self, other: Block | Plug | int | float | np.ndarray) -> Block:
        """
        Overloaded + operator for implicit block creation.

        :param self: A signal (block) to be added
        :type self: Block
        :param other: A signal (block or plug) to be added
        :type other: Block or Plug
        :return: SUM block
        :rtype: Block subclass

        This method is implicitly invoked by the + operator
        when the right operand is a ``Block``
        and the left operand is a ``Plug``, ``Block`` or constant::

            result = X + Y[j]
            result = X[i] + Y[j]
            result = C + Y[j]

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        Creates a ``SUM("++") block named ``_sum.N`` whose inputs are the
        left and right operands.  For the third case, a new ``CONSTANT(C)`` block
        named ``_const.N`` is also created.

        .. note::
            * The inputs to the summing junction are reversed: right then left operand.
            * The ``mode`` is None, regular addition

        :seealso: :meth:`Block.__add__` :meth:`Plug.__radd__`
        """
        # value + value, create a SUM block
        from bdsim.blocks import Sum

        if self.bd is None:
            raise RuntimeError(  # pragma: no cover
                "block must be connected to a block diagram to create an automatic sum block"
            )
        name = "_sum.{:d}".format(next(self.bd.n_auto_sum))
        if isinstance(other, (int, float, np.ndarray)):
            # constant + block, create a CONSTANT block
            other = self._autoconstant(other)
        return Sum("++", inputs=(other, self), name=name, bd=self.bd)

    @oodebug
    def __sub__(self, other: Block | Plug | int | float | np.ndarray) -> Block:
        """
        Overloaded - operator for implicit block creation.

        :param self: A signal (block) to be added (minuend)
        :type self: Block
        :param other: A signal (block or plug) to be subtracted (subtrahend)
        :type other: Block or Plug
        :return: SUM block
        :rtype: Block subclass

        This method is implicitly invoked by the - operator when the left operand is a ``Block``
        and the right operand is a ``Plug``, ``Block`` or constant::

            result = X - Y
            result = X - Y[j]
            result = X - C

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        Creates a ``SUM("+-")`` block named ``_sum.N`` whose inputs are the
        left and right operands.  For the third case, a new ``CONSTANT(C)`` block
        named ``_const.N`` is also created.

        :seealso: :meth:`Block.__rsub__` :meth:`Plug.__sub__`
        """
        # value - value, create a SUM block
        from bdsim.blocks import Sum

        if self.bd is None:
            raise RuntimeError(  # pragma: no cover
                "block must be connected to a block diagram to create an automatic sum block"
            )
        name = "_sum.{:d}".format(next(self.bd.n_auto_sum))
        if isinstance(other, (int, float, np.ndarray)):
            # block - constant, create a CONSTANT block
            other = self._autoconstant(other)
        return Sum("+-", inputs=(self, other), name=name, bd=self.bd)

    @oodebug
    def __rsub__(self, other: Block | Plug | int | float | np.ndarray) -> Block:
        """
        Overloaded - operator for implicit block creation.

        :param self: A signal (block) to be added (minuend)
        :type self: Block
        :param other: A signal (block or plug) to be subtracted (subtrahend)
        :type other: Block or Plug
        :return: SUM block
        :rtype: Block subclass

        This method is implicitly invoked by the - operator when the left operand is a ``Block``
        and the right operand is a ``Plug``, ``Block`` or constant::

            result = X - Y
            result = X[i] - Y
            result = C - Y

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        Creates a ``SUM("+-")`` block named ``_sum.N`` whose inputs are the
        left and right operands.  For the third case, a new ``CONSTANT(C)`` block
        named ``_const.N`` is also created.

        .. note::
            * The inputs to the summing junction are reversed: right then left operand.
            * The ``mode`` is None, regular addition

        :seealso: :meth:`Block.__sub__` :meth:`Plug.__rsub__`
        """
        # value - value, create a SUM block
        from bdsim.blocks import Sum

        if self.bd is None:
            raise RuntimeError(  # pragma: no cover
                "block must be connected to a block diagram to create an automatic sum block"
            )

        name = "_sum.{:d}".format(next(self.bd.n_auto_sum))
        if isinstance(other, (int, float, np.ndarray)):
            # constant - block, create a CONSTANT block
            other = self._autoconstant(other)
        return Sum("+-", inputs=(other, self), name=name, bd=self.bd)

    @oodebug
    def __neg__(self):
        """
        Overloaded unary minus operator for implicit block creation.

        :param self: A signal (block) to be negated
        :type self: Block
        :return: GAIN block
        :rtype: Block subclass

        This method is implicitly invoked by the - operator for unary minus when the operand is a ``Block``::

            result = -X

        where ``X`` is a block.

        Creates a ``GAIN(-1)`` block named ``_gain.N`` whose input is the
        operand.

        :seealso: :meth:`Plug.__neg__`
        """
        return self._autogain(-1.0, inputs=[self])

    @oodebug
    def __pow__(self, p):
        """
        Overloaded unary power operator for implicit block creation.

        :param self: A signal (block) to be negated
        :type self: Block
        :return: POW block
        :rtype: Block subclass

        This method is implicitly invoked by the ** operator for unary power when the operand is a ``Block``::

            result = X**3

        where ``X`` is a block.

        Creates a ``POW(3)`` block named ``_pow.N`` whose input is the
        operand.

        :seealso: :meth:`Plug.__pow__`
        """
        return self._autopow(p, inputs=[self])

    @oodebug
    def __mul__(self, other: Block | Plug | int | float | np.ndarray) -> Block:
        """
        Overloaded * operator for implicit block creation.

        :param self: A signal (block) to be multiplied
        :type self: Block
        :param other: A signal (block or plug) to be multiplied
        :type other: Block or Plug
        :return: PROD or GAIN block
        :rtype: Block subclass

        This method is implicitly invoked by the * operator when the left operand is a ``Block``
        and the right operand is a ``Plug``, ``Block`` or constant::

            result = X * Y
            result = X * Y[j]
            result = X * C

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        Create a ``PROD("**")`` block named ``_prod.N`` whose inputs are the
        left and right operands.

        For the third case, create a ``GAIN(C)`` block named ``_gain.N``.

        .. note:: ``C'' can be a scalar or ndarray.


        :seealso: :meth:`Block.__rmul__` :meth:`Plug.__mul__`
        """
        from bdsim.blocks import Prod

        if self.bd is None:
            raise RuntimeError(  # pragma: no cover
                "block must be connected to a block diagram to create an automatic product block"
            )

        if isinstance(other, (int, float, np.ndarray)):
            # block * constant, create a GAIN block
            return self._autogain(other, premul=False, inputs=[self])
        else:
            # value * value, create a PROD block
            name = "_prod.{:d}".format(next(self.bd.n_auto_prod))
            return Prod("**", inputs=[self, other], name=name, bd=self.bd)

    @oodebug
    def __rmul__(self, other: Block | Plug | int | float | np.ndarray) -> Block | None:
        """
        Overloaded * operator for implicit block creation.

        :param self: A signal (block) to be multiplied
        :type self: Block
        :param other: A signal (block or plug) to be multiplied
        :type other: Block or Plug
        :return: PROD or GAIN block
        :rtype: Block subclass

        This method is implicitly invoked by the * operator when the right operand is a ``Block``
        and the left operand is a ``Plug``, ``Block`` or constant::

            result = X * Y
            result = X[i] * Y
            result = C * Y

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        For the first two cases, a ``PROD("**")`` block named ``_prod.N`` whose inputs are the
        left and right operands.

        For the third case, create a ``GAIN(C)`` block named ``_gain.N``.

        .. note:: ``C'' can be a scalar or ndarray.


        :seealso: :meth:`Block.__mul__` :meth:`Plug.__rmul__`
        """
        if isinstance(other, (int, float, np.ndarray)):
            # constant * block, create a GAIN block
            return self._autogain(other, premul=True, inputs=[self])
        return None

    @oodebug
    def __truediv__(self, other: Block | Plug | int | float | np.ndarray) -> Block:
        """
        Overloaded / operator for implicit block creation.

        :param self: A signal (block) to be multiplied (dividend)
        :type self: Block
        :param other: A signal (block or plug) to be divided (divisor)
        :type other: Block or Plug
        :return: PROD or GAIN block
        :rtype: Block subclass

        This method is implicitly invoked by the / operator when the left operand is a ``Block``
        and the right operand is a ``Plug``, ``Block`` or constant::

            result = X / Y
            result = X / Y[j]
            result = X / C

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        Create a ``PROD("**")`` block named ``_prod.N`` whose inputs are the
        left and right operands.

        For the third case, create a ``GAIN(1/C)`` block named ``_gain.N``.

        .. note:: ``C'' can be a scalar or ndarray.

        :seealso: :meth:`Block.__rtruediv__` :meth:`Plug.__truediv__`
        """
        # value / value, create a PROD block
        from bdsim.blocks import Prod

        if self.bd is None:
            raise RuntimeError(  # pragma: no cover
                "block must be connected to a block diagram to create an automatic product block"
            )

        name = "_prod.{:d}".format(next(self.bd.n_auto_prod))
        if isinstance(other, (int, float, np.ndarray)):
            # block / constant, create a GAIN block
            if isinstance(other, np.ndarray):
                inverse = np.linalg.inv(other)
            else:
                inverse = 1.0 / other
            return self._autogain(inverse, premul=False, inputs=[self])
        else:
            # value * value, create a PROD block
            name = "_prod.{:d}".format(next(self.bd.n_auto_prod))
            return Prod("*/", inputs=[self, other], name=name, bd=self.bd)

    @oodebug
    def __rtruediv__(self, other: Block | Plug | int | float | np.ndarray) -> Block:
        """
        Overloaded / operator for implicit block creation.

        :param self: A signal (block) to be multiplied (dividend)
        :type self: Block
        :param other: A signal (block or plug) to be divided (divisor)
        :type other: Block or Plug
        :return: PROD block
        :rtype: Block subclass

        This method is implicitly invoked by the / operator when the right operand is a ``Block``
        and the left operand is a ``Plug``, ``Block`` or constant::

            result = X / Y
            result = X[i] / Y
            result = C / Y

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        For the first two cases, a ``PROD("*/")`` block named ``_prod.N`` whose inputs are the
        left and right operands.  For the third case, a new CONSTANT block
        named ``_const.N`` is also created.

        .. note:: ``C'' can be a scalar or ndarray.


        :seealso: :meth:`Block.__truediv__` :meth:`Plug.__rtruediv__`
        """
        # value / value, create a PROD block
        from bdsim.blocks import Prod

        if self.bd is None:
            raise RuntimeError(  # pragma: no cover
                "block must be connected to a block diagram to create an automatic product block"
            )

        name = "_prod.{:d}".format(next(self.bd.n_auto_prod))
        if isinstance(other, (int, float, np.ndarray)):
            # constant / block, create a CONSTANT block
            other = self._autoconstant(other)
        return Prod("*/", inputs=(other, self), name=name, bd=self.bd)

    # ---------------------------------------------------------------------- #

    def reset(self) -> None:
        """
        Restore the block's initial internal state.

        Called once per run, before :meth:`start`, so that nothing the
        compile-time trial evaluation or a previous run did to the block is
        visible to the run about to start.  A block that keeps state of its own
        in Python, for example a random number generator or a mode flag, must
        override this and restore it.  Continuous and discrete state vectors
        are not part of this: they are restored from :meth:`getstate0`.

        The values on the block's ports are not touched.
        """
        pass

    def configure(self) -> None:
        """
        Prepare the block for a run, using what compile() learned about its wires.

        Called once per run, after :meth:`reset` and before :meth:`start`.  This
        is the place to read :attr:`insig` and :attr:`outsig`, for example to
        size per-element detectors or allocate buffers.  The signatures are those
        observed by the trial evaluation in ``compile()``.  They are ``None`` if
        the diagram was compiled with ``evaluate=False``, in which case the block
        should not assume anything about its wires.

        The default does nothing.  :meth:`start` keeps its meaning: acquire
        resources and register with the simulation.
        """
        pass

    def start(self, simstate: SimulationState) -> None:  # begin a simulation
        pass

    def validate_start(self) -> None:
        """Validate block initialization completed after ``start``."""
        pass

    def check(self) -> None:  # check validity of block parameters at start
        if not hasattr(self, "nin"):
            raise AttributeError(f"block {self.name} has no nin specified")
        if not hasattr(self, "nout"):
            raise AttributeError(f"block {self.name} has no nout specified")

        if not isinstance(self.nin, int):
            raise TypeError(f"block {self.name} nin must be an int")
        if not isinstance(self.nout, int):
            raise TypeError(f"block {self.name} nout must be an int")
        if self.nin < 0:
            raise ValueError(f"block {self.name} nin must be non-negative")
        if self.nout < 0:
            raise ValueError(f"block {self.name} nout must be non-negative")

        if self._inport_names is not None and len(self._inport_names) != self.nin:
            raise ValueError("number of input port names must match number of inputs")

        if self._outport_names is not None and len(self._outport_names) != self.nout:
            raise ValueError("number of output port names must match number of outputs")

        if not (self.nin > 0 or self.nout > 0):
            raise ValueError(f"block {self.name} no inputs or outputs specified")
        if not (hasattr(self, "_initd") and self._initd):
            raise RuntimeError(  # pragma: no cover
                "Block superclass not initalized. was super().__init__ called?"
            )

    def done(self, **kwargs: Any) -> None:  # end of simulation
        pass

    def savefig(self, *pos: Any, **kwargs: Any) -> None:
        pass


class SourceBlock(Block):
    """
    A SourceBlock is a subclass of Block that represents a block that has outputs
    but no inputs.  Its output is a function of parameters and time.
    """

    def __init__(self, **blockargs: Any) -> None:
        """
        Create a source block.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: source block base class
        :rtype: SourceBlock

        This is the parent class of all source blocks.
        """
        super().__init__(nin=0, nstates=0, ndstates=0, **blockargs)

    @abstractmethod
    def output(self, t: float, u: list[Any], x: np.ndarray) -> list[Any]:
        raise NotImplementedError


class SinkBlock(Block):
    """
    A SinkBlock is a subclass of Block that represents a block that has inputs
    but no outputs. Typically used to save data to a variable, file or
    graphics.
    """

    def __init__(self, **blockargs: Any) -> None:
        """
        Create a sink block.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: sink block base class
        :rtype: SinkBlock

        This is the parent class of all sink blocks.
        """
        super().__init__(nout=0, nstates=0, ndstates=0, **blockargs)

    @abstractmethod
    def step(self, t: float, u: list[Any]) -> None:
        raise NotImplementedError


class FunctionBlock(Block):
    """
    A FunctionBlock is a subclass of Block that represents a block that has inputs
    and outputs but no state variables.  Typically used to describe operations
    such as gain, summation or various mappings.
    """

    def __init__(self, **blockargs: Any) -> None:
        """
        Create a function block.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: function block base class
        :rtype: FunctionBlock

        This is the parent class of all function blocks.
        """
        super().__init__(nstates=0, ndstates=0, **blockargs)

    @abstractmethod
    def output(self, t: float, u: list[Any], x: np.ndarray) -> list[Any]:
        raise NotImplementedError


def _initial_state(block: Any, value: Any) -> np.ndarray:
    """An initial state vector for the block, as a float array with one element per state."""
    x0 = smb.getvector(value, dtype=float)
    n = len(block._x0)
    if x0.shape != (n,):
        raise ValueError(
            f"x0 must have {n} element{'s' if n != 1 else ''}, one per state, not {len(x0)}"
        )
    return x0


class ContinuousBlock(Block):
    """
    A ContinuousBlock is a subclass of Block that represents a block with inputs,
    outputs and states. Typically used to describe a continuous-time dynamic
    system, either linear or nonlinear.
    """

    def __init__(
        self,
        nstates: int = 0,
        x0: Vector1D | None = None,
        feedthrough: bool = False,
        **blockargs: Any,
    ) -> None:
        """
        Create a continuous-time block.

        :param nstates: number of continuous-time states
        :type nstates: int
        :param x0: initial state vector, defaults to None
        :type x0: Vector1D, optional
        :param feedthrough: whether the block has direct feedthrough from input to output, defaults to False
        :type feedthrough: bool, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: continuous-time block base class
        :rtype: ContinuousBlock

        This is the parent class of all continuous-time dynamic blocks.
        """
        if x0 is None:
            # use the old protocol, initial state vector is _x0 attribute
            x0 = self._x0 if hasattr(self, "_x0") else None

        if x0 is not None:
            self._x0 = smb.getvector(x0, dtype=float)
            nstates = len(self._x0)
        elif nstates > 0:
            # set initial state vector to zero if not specified
            self._x0 = np.zeros(nstates)
        else:
            # raise ValueError(
            #     "must specify initial state vector or number of discrete states"
            # )
            pass
        self._feedthrough = feedthrough
        super().__init__(nstates=nstates, ndstates=0, **blockargs)

    def setstate(self, x: np.ndarray) -> np.ndarray:
        self._x_view = x[: self.nstates]
        return x[self.nstates :]

    @property
    def x0(self) -> np.ndarray:
        """Initial state vector.  It can be set until the run starts."""
        return self._x0  # type: ignore[no-any-return]

    @x0.setter
    def x0(self, value: Any) -> None:
        self._x0 = _initial_state(self, value)

    def getstate0(self) -> np.ndarray:
        return self._x0

    def check(self) -> None:
        super().check()
        if len(self._x0) != self.nstates:
            raise ValueError("incorrect length for initial state")
        if not (self.nin > 0 or self.nout > 0):
            raise ValueError("no inputs or outputs specified")

    @abstractmethod
    def deriv(self, t: float, u: list[Any], x: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    @abstractmethod
    def output(self, t: float, u: list[Any], x: np.ndarray) -> list[Any]:
        raise NotImplementedError


class SampledBlock(Block):
    """
    A SampledBlock is a subclass of Block that represents a block with inputs,
    outputs and discrete states. Typically used to describe a sampled-time dynamic
    system, either linear or nonlinear.
    """

    def __init__(
        self,
        clock: Clock,
        *,
        ndstates: int | None = None,
        x0: Vector1D | None = None,
        feedthrough: bool = False,
        **blockargs: Any,
    ) -> None:
        """
        Create a clocked block.

            :param clock: the clock that governs the block's discrete time updates
        :type clock: Clock
        :param ndstates: number of discrete-time states
        :type ndstates: int, optional
        :param x0: initial state vector, defaults to None
        :type x0: Vector1D, optional
        :param feedthrough: whether the block has direct feedthrough from input to output, defaults to False
        :type feedthrough: bool, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: clocked block base class
        :rtype: SampledBlock

        This is the parent class of all sampled-time blocks.
        """
        if x0 is not None:
            self._x0 = smb.getvector(x0, dtype=float)
            ndstates = len(self._x0)
        elif ndstates is not None:
            self._x0 = np.zeros(ndstates)
        else:
            raise ValueError(
                "must specify initial state vector or number of discrete states"
            )

        super().__init__(nstates=0, ndstates=ndstates, **blockargs)
        self._clocked = True
        self._clock = clock
        self.T = clock.T
        self._feedthrough = feedthrough
        clock.add_block(self)

    def setstate(self, x: np.ndarray) -> np.ndarray:
        self._x_view = x[: self.ndstates]
        return x[self.ndstates :]

    @property
    def x0(self) -> np.ndarray:
        """Initial state vector.  It can be set until the run starts."""
        return self._x0  # type: ignore[no-any-return]

    @x0.setter
    def x0(self, value: Any) -> None:
        self._x0 = _initial_state(self, value)

    def getstate0(self) -> np.ndarray:
        return self._x0

    def check(self) -> None:
        if not (self.ndstates > 0 and self._x0 is not None):
            raise ValueError(
                "sampled block must have discrete states and initial state "
                f"vector, ndstates={self.ndstates}, x0={self._x0}"
            )
        if len(self._x0) != self.ndstates:
            raise ValueError(
                f"incorrect length for initial state: got {len(self._x0)}, "
                f"expected {self.ndstates}"
            )
        if not (self.nin > 0 or self.nout > 0):
            raise ValueError("block has no inputs or outputs")


class SubsystemBlock(Block):
    """
    A SubSystem is a subclass of Block that represents a block that has inputs
    and outputs but no state variables.  Typically used to describe operations
    such as gain, summation or various mappings.
    """

    def __init__(self, subsystem: BlockDiagram, **blockargs: Any) -> None:
        """
        Create a subsystem block.

        :param subsystem: the subsystem to wrap
        :type subsystem: BlockDiagram
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: subsystem block base class
        :rtype: SubsystemBlock

        This is the parent class of all subsystem blocks.
        """
        super().__init__(nstates=0, ndstates=0, **blockargs)

        # each subsystem must have exactly one INPORT and one OUTPORT block
        inports = [b for b in subsystem.blocklist if b.type == "inport"]
        outports = [b for b in subsystem.blocklist if b.type == "outport"]

        if len(inports) == 0:
            raise ValueError(f"Subsystem({self.name}) has no INPORT blocks")
        if len(inports) > 1:
            raise ValueError(f"Subsystem({self.name}) has more than 1 INPORT blocks")
        if len(outports) == 0:
            raise ValueError(f"Subsystem({self.name}) has no OUTPORT blocks")
        if len(outports) > 1:
            raise ValueError(f"Subsystem({self.name}) has more than 1 OUTPORT blocks")

        # the block inherits its number of inputs and outputs from the subsystem's INPORT and OUTPORT blocks
        self.nin = inports[0].nout
        self.nout = outports[0].nin

        self.subsystem = subsystem
        self.inport = inports[0]
        self.outport = outports[0]

        # set when the diagram is compiled and the INPORT and OUTPORT blocks are replaced
        # by wires, see BlockDiagram._elide_subsystem_ports
        self._ports_elided = False
        self._source_inports: list[Plug | None] = []
        self._source_outports: list[Plug | None] = []

    @property
    def inports(self) -> list[Plug]:
        """
        The output ports that feed the inputs of the subsystem.

        :return: one plug per input, the block and port that drives it
        :rtype: list of Plug

        Like :attr:`Block.inports`, but the subsystem block is not part of the compiled
        network.  Available after the diagram has been compiled.
        """
        return self._source_inports  # type: ignore[return-value]

    @property
    def outports(self) -> list[Plug]:
        """
        The output ports that generate the outputs of the subsystem.

        :return: one plug per output, the block and port inside the subsystem whose value
            is the output.  Nested subsystems are looked through.
        :rtype: list of Plug

        This is how the output of a subsystem is watched: ``watch=[pid]`` or
        ``watch=[pid[0]]`` watch the plug found here.  Available after the diagram has
        been compiled.
        """
        return self._source_outports  # type: ignore[return-value]


class EventSource:
    pass


# GraphicsBlock and is_notebook_backend live in bdsim.graphics_block
# (kept separate so the core block hierarchy does not depend on matplotlib).


# ----------------------- deprecated classes for backward compatibility ----------------------- #


def deprecated_block(new_name: str) -> Callable[[type], type]:
    """Class decorator that marks a block as deprecated.

    Wraps ``__init__`` to emit a ``FutureWarning`` on instantiation.
    The AST-based block loader detects the ``@deprecated_block`` decorator by
    name and skips the class from menus, so no extra attribute is needed in
    the class body.

    Usage::

        @deprecated_block("NewName")
        class OldName(NewName):
            ...
    """

    def decorator(cls: type) -> type:
        orig_init = cls.__init__

        def __init__(self: Any, *args: Any, **kwargs: Any) -> None:
            warnings.warn(
                f"{cls.__name__} is deprecated; use {new_name} instead.",
                FutureWarning,
                stacklevel=2,
            )
            orig_init(self, *args, **kwargs)

        cls.__init__ = __init__
        return cls

    return decorator


@deprecated_block("ContinuousBlock")
class TransferBlock(ContinuousBlock):
    """Deprecated alias for ContinuousBlock. Will be removed in v3.0.0."""

    _blockclass = "continuous"  # name 'transfer' != 'continuous', must be explicit

    def __init_subclass__(cls, **kwargs: Any) -> None:
        warnings.warn(
            f"{cls.__name__} subclasses TransferBlock which is deprecated since v2.0.0 "
            "and will be removed in v3.0.0. Subclass ContinuousBlock instead.",
            FutureWarning,
            stacklevel=2,
        )
        super().__init_subclass__(**kwargs)


@deprecated_block("SampledBlock")
class ClockedBlock(SampledBlock):
    """Deprecated alias for SampledBlock. Will be removed in v3.0.0."""

    _blockclass = "sampled"  # name 'clocked' != 'sampled', must be explicit

    def __init_subclass__(cls, **kwargs: Any) -> None:
        warnings.warn(
            f"{cls.__name__} subclasses ClockedBlock which is deprecated since v2.0.0 "
            "and will be removed in v3.0.0. Subclass SampledBlock instead.",
            FutureWarning,
            stacklevel=2,
        )
        super().__init_subclass__(**kwargs)


if __name__ == "__main__":
    try:
        from ._selftest import run_module_test
    except ImportError:
        from bdsim._selftest import run_module_test

    raise SystemExit(run_module_test(__file__))
