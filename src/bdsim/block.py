"""Core block base class and concrete block-type subclasses."""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, cast

import matplotlib
import matplotlib.figure
import numpy as np
from matplotlib import animation

import matplotlib.pyplot as plt

from bdsim.exceptions import BlockApiError, BlockRuntimeError


from bdsim.components import Clock, _fixname, oodebug
from bdsim.connect import Plug, Port, Wire

if TYPE_CHECKING:
    from bdsim.blockdiagram import BlockDiagram


class PortValueSlot:
    __slots__ = ("value",)

    def __init__(self) -> None:
        self.value: Any = None


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
        - ``reset()``: resets the block to its initial state
        - ``done()``: performs any cleanup at end of the simulation
        - ``info()``: displays information about the block for debugging purposes

    Ports can be accessed by index, eg. ``block.input_value(i)`` or ``block.output_value(i)``, or by name, eg. ``block.inport("in1")`` or ``block.outport("out1")`` if the block has named ports.

        - ``input_value(i)``: returns the value of the input port at index ``i``
        - ``output_value(i)``: returns the value of the output port at index ``i``
        - ``inport_name(i)``: returns the name of the input port at index ``i``
        - ``outport_name(i)``: returns the name of the output port at index ``i``

    """

    # ========================================================================
    # ARCHITECTURE: Wire-Centric Signal Values
    # ========================================================================
    # Runtime signal transport is via one mutable slot per output port.
    #
    # Publish path:
    #   block.output(...) -> Block._publish_output_values(values)
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

    _x: np.ndarray[tuple[Any, ...], np.dtype[Any]] | None

    _inport_names: list[str] | None
    _outport_names: list[str] | None
    _state_names: list[str] | None

    _clocked: bool = False
    _clock: Clock | None

    _graphics: bool = False
    _parameters: dict[str, Any]

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

    # def __new__(cls, *args, bd=None, **kwargs) -> Self:
    #     """
    #     Construct a new Block object.

    #     :param cls: The class to construct
    #     :type cls: class type
    #     :param *args: positional args passed to constructor
    #     :type *args: list
    #     :param **kwargs: keyword args passed to constructor
    #     :type **kwargs: dict
    #     :return: new Block instance
    #     :rtype: Block instance
    #     """
    #     # print('Block __new__', args,bd, kwargs)
    #     block: Self = super(Block, cls).__new__(cls)  # create a new instance

    #     # we overload setattr, so need to know whether it is being passed a port
    #     # name.  Add this attribute now to allow proper operation.
    #     # block.__dict__["_portnames"] = []  # must be first, see __setattr__
    #     # block._portnames = []  # must be first, see __setattr__
    #     return block

    def __init_subclass__(cls, **kwargs) -> None:
        """
        Initialize a subclass of Block.

        :param cls: The subclass being initialized
        :type cls: class type
        :param **kwargs: keyword args passed to subclass definition
        :type **kwargs: dict

        This method is called when a new subclass of Block is defined, not when it is
        instantiated. Subclasses can define class variables such as ``nin``, ``nout``,
        ``inlabels``, ``outlabels``, etc.  For example::

            class MyBlock(Block):
                nin = 1
                nout = 1
                inlabels = ['in']
                outlabels = ['out']

        """
        super().__init_subclass__(**kwargs)

        # check that the subclass does not have methods inconsistent with its class
        disallowed = {
            "SourceBlock": ["deriv", "step", "next"],
            "SinkBlock": ["deriv", "output", "next"],
            "FunctionBlock": ["deriv", "next", "step"],
            "TransferBlock": ["next", "step"],
            "GraphicsBlock": ["deriv", "next", "output"],
            "ClockedBlock": ["deriv", "step"],
            "SubsystemBlock": ["deriv", "output", "next", "step"],
        }
        blockclass = cls.__mro__[1].__name__
        x = ":".join([c.__name__ for c in cls.__mro__])
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

    def __init__(
        self,
        name: str | None = None,
        nin: int | None = None,
        nout: int | None = None,
        nstates: int = 0,
        ndstates: int = 0,
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

        if blockclass is None:
            for cls in self.__class__.__bases__:
                if cls.__name__.endswith("Block"):
                    self._blockclass = cls.__name__[:-5].lower()
                    break
        else:
            self._blockclass = blockclass
        assert (
            self._blockclass is not None
        ), f"blockclass must be specified for block {self.name}"

        # key simulation variables
        self._x = None  # state vector
        self._output_values = None  # cached block output values, set by output() method, accessed by outport_value()

        # set by add_block() when block is added to a block diagram
        self._bd: BlockDiagram | None = bd  # owning block diagram
        self._id = None  # index in block diagram's blocklist

        # deprecated options for graphical display
        if isinstance(pos, list):
            assert len(pos) == 2, "block position must have exactly two elements"
            self._pos = (pos[0], pos[1])
        else:
            self._pos = pos
        self._shape = "block"  # for box

        self._initd = True
        self._clocked = False
        self._clock = clock
        self._graphics = False
        self._parameters = {}

        if bd is not None:
            bd.add_block(self)

        # ports can have names as well as indices, for access by name.
        #  names are set by:
        #  - inames and onames options, or by
        #  - inlabels and outlabels class variables, or
        #  - default to None.
        #
        # _portnames is the list of all port names, used for access by name in __setattr__ and __getattr__
        def checknames(names):
            for name in names:
                if name in self.__dict__:
                    raise ValueError(f"port name {name} conflicts with block attribute")

        if inames is None:
            inames = getattr(self.__class__, "inlabels", None)
        if inames is not None:
            if explicit_nin:
                assert (
                    len(inames) == self.nin
                ), "number of input port names must match number of inputs"
            else:
                self.nin = len(inames)
            inames = normalized_port_names(inames)
            assert len(set(inames)) == len(inames), "input port names must be unique"
            checknames(inames)
        self._inport_names = inames

        if onames is None:
            onames = getattr(self.__class__, "outlabels", None)
        if onames is not None:
            if explicit_nout:
                assert (
                    len(onames) == self.nout
                ), "number of output port names must match number of outputs"
            else:
                self.nout = len(onames)
            onames = normalized_port_names(onames)
            assert len(set(onames)) == len(onames), "output port names must be unique"
            checknames(onames)
        self._outport_names = onames

        if snames is not None:
            if nstates is not None:
                assert (
                    len(snames) == nstates
                ), "number of state names must match number of states"
            else:
                nstates = len(snames)
        self._state_names = snames

        # block inputs can be specified in the constructor for convenience, and are connected here.
        if isinstance(inputs, Block):
            inputs = (inputs,)
        if inputs is not None and len(inputs) > 0:
            # assert len(inputs) == self.nin, 'Number of input connections must match number of inputs'
            assert (
                self.bd is not None
            ), "inputs provided but block is not in a block diagram"
            for i, input in enumerate(inputs):
                self.bd.connect(input, Plug(self, port=i))

        self._nstates = nstates
        self._ndstates = ndstates

    def __init_subclass__(cls, **kwargs) -> None:
        """
        Initialize a subclass of Block.

        :param cls: The subclass being initialized
        :type cls: class type
        :param **kwargs: keyword args passed to subclass definition
        :type **kwargs: dict

        This method is called when a new subclass of Block is defined, not when it is
        instantiated. Here we check that the subclass does not define methods that are
        inconsistent with its block class, and raise an error if it does.  This is a
        sanity check to prevent blocks from being defined with methods that will never
        be called by the simulation engine, which would indicate a misunderstanding of
        the block API.

        """
        super().__init_subclass__(**kwargs)
        # check that the subclass does not have methods inconsistent with its class
        disallowed = {
            "SourceBlock": ["deriv", "step", "next"],
            "SinkBlock": ["deriv", "output", "next"],
            "FunctionBlock": ["deriv", "next", "step"],
            "TransferBlock": ["next", "step"],
            "GraphicsBlock": ["deriv", "next", "output"],
            "ClockedBlock": ["deriv", "step"],
            "SubsystemBlock": ["deriv", "output", "next", "step"],
        }
        blockclass = cls.__mro__[1].__name__
        x = ":".join([c.__name__ for c in cls.__mro__])
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

    def __repr__(self):
        s = f"Block(name={self._name}, type={self._type}, blockclass={self._blockclass}"
        if self.nin > 0:
            s += f", nin={self.nin}"
        if self.nout > 0:
            s += f", nout={self.nout}"
        if self._nstates > 0:
            s += f", nstates={self.nstates}"
        if self._ndstates > 0:
            s += f", ndstates={self.ndstates}"
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

    def add_param(self, param, handler=None) -> None:
        if handler is None:

            def default_handler(self, name, newvalue) -> None:
                setattr(self, name, newvalue)

            handler = default_handler

        self.__dict__["_parameters"][param] = handler

    def set_param(self, name, newvalue) -> None:
        print(f"setting parameter {name} of block {self.name} to {newvalue}")
        self._parameters[name](self, name, newvalue)

    @property
    def id(self) -> int | None:
        return self._id

    @id.setter
    def id(self, v) -> None:
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
            assert isinstance(fixed_name, str), "block name must resolve to a string"
            self._name = fixed_name
        else:
            self._name_tex = None
            self._name = None

    @property
    def name_tex(self) -> str | None:
        return self._name_tex

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

    def __str__(self) -> str:
        if hasattr(self, "name") and self.name is not None:
            return self.name
        else:
            return self.blockclass + ".??"

    def __repr__(self):
        s = f"Block(name={self._name}, type={self._type}, blockclass={self._blockclass})"
        if self.nin > 0:
            s += f", nin={self.nin}"
        if self.nout > 0:
            s += f", nout={self.nout}"
        if self._nstates > 0:
            s += f", nstates={self.nstates}"
        if self._ndstates > 0:
            s += f", ndstates={self.ndstates}"
        return s + ")"

    def state_names(self, names) -> None:
        self._state_names = names

    @property
    def fullname(self) -> str:
        return self.blockclass + "." + str(self)

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
        assert self._bd is not None, "block is not in a block diagram"
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
            assert wire is not None, f"block {self.name} has an unconnected input"
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
            assert wire is not None, f"block {self.name} has an unconnected input"
            inports.append(wire.start)
        return inports

    @property
    def inport_values(self):
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
        if slots is not None:
            for i, slot in enumerate(slots):
                if slot is not None:
                    values.append(slot.value)
                    continue

                # Compatibility fallback for tests using uncompiled/manual wiring.
                wire = self._input_wires[i]
                assert wire is not None, f"block {self.name} has an unconnected input"
                plug = wire.start
                values.append(plug.block.outport_value(plug.port))
            return values

        # Compatibility path if called before compile() initialized slots.
        for wire in self._input_wires:
            assert wire is not None, f"block {self.name} has an unconnected input"
            plug = wire.start
            values.append(plug.block.outport_value(plug.port))
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
        if slots is not None:
            slot = slots[i]
            if slot is not None:
                return slot.value

        wire = self._input_wires[i]
        assert wire is not None, f"block {self.name} input port {i} not connected"
        source = wire.start
        return source.block.outport_value(source.port)

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
        assert i < self.nin, f"block {self.name} input port index {i} out of range"
        if self._inport_names is None:
            return f"[{i}]"
        else:
            return self._inport_names[i]

    def source_name(self, port):
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
        if wire.name is not None:
            return wire.name
        b = wire.start.block
        return f"{b.name}{b.outport_name(wire.start.port)}"

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
        assert (
            self._output_values is not None
        ), f"block {self.name} output values not initialised"
        assert (
            self._output_values[i] is not None
        ), f"block {self.name} output value {i} not set"
        return self._output_values[i]

    def _publish_output_values(self, out: list[Any] | tuple[Any, ...]) -> None:
        """Cache block outputs and publish each port value once to its slot."""
        self._output_values = list(out)
        for port, value in enumerate(self._output_values):
            self._outport_slots[port].value = value

    def outport_slot(self, i: int) -> PortValueSlot:
        assert i < self.nout, f"block {self.name} output port index {i} out of range"
        return self._outport_slots[i]

    def bind_input_slot(self, i: int, slot: PortValueSlot) -> None:
        assert i < self.nin, f"block {self.name} input port index {i} out of range"
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
        assert i < self.nout, f"block {self.name} output port index {i} out of range"
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

    def start_safe(self, simstate: Any) -> None:
        try:
            self.start(simstate)
        except Exception as err:
            self._raise_runtime_error("start", err)

    def done_safe(self, **kwargs: Any) -> None:
        try:
            self.done(**kwargs)
        except Exception as err:
            self._raise_runtime_error("done", err)

    # ---------------------------------------------------------------------- #
    # methods used for unit testing

    #  test_MMMMM is a wrapper around the normal block method MMMMM, which checks the inputs and outputs for
    #  consistency with the block definition, and is used for concise unit tests.

    def test_output(self, *inputs, t=0.0, x=None):
        """
        Evaluate a block for unit testing.

        :param *inputs: Input port values
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
        assert len(inputs) == self.nin, "wrong number of inputs provided"

        # evaluate the block
        out = self.output(t, inputs, x)

        # sanity check the output
        assert isinstance(out, list), "result must be a list"
        assert len(out) == self.nout, "result list is wrong length"
        return out

    def test_deriv(self, *inputs, t=0.0, x=None):
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
        assert len(inputs) == self.nin, "wrong number of inputs provided"

        if x is not None:
            assert len(x) == self.nstates, "passed state is wrong length"

        # evaluate the block
        out = self.deriv(t, inputs, x)

        # sanity check the output
        assert isinstance(out, np.ndarray), "result must be an ndarray"
        assert out.shape == (self.nstates,), "result array is wrong length"
        return out

    def test_next(self, *inputs, t=0.0, x=None):
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
        assert len(inputs) == self.nin, "wrong number of inputs provided"

        if x is not None:
            assert len(x) == self.ndstates, "passed state is wrong length"

        # evaluate the block
        assert hasattr(self, "next"), "block does not have a next method"
        out = self.next(t, inputs, x)

        # sanity check the output
        assert isinstance(out, np.ndarray), "next state must be an ndarray"
        assert out.shape == (self.ndstates,), "next state array is wrong length"
        return out

    def test_step(self, *inputs, t=0.0) -> None:
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
        assert len(inputs) == self.nin, "wrong number of inputs provided"

        # step the block
        self.step(t, inputs)

    def test_start(self, simstate=None):

        from bdsim.run_sim import BDSimState, Options

        if simstate is None:

            class RunTime:
                options: Options

                def DEBUG(self, *args) -> None:
                    pass

            class BlockDiagram:
                runtime: RunTime

            runtime = RunTime()
            runtime.options = Options()
            blockdiagram = BlockDiagram()
            blockdiagram.runtime = runtime
            self._bd = cast("BlockDiagram", blockdiagram)
            simstate = BDSimState()
            simstate.options = runtime.options
            simstate.t = 0.0

        # step the block
        self.start(simstate)
        return simstate

    # ---------------------------------------------------------------------- #
    #  set/get items and attributes

    def __getitem__(self, port) -> Plug:
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

    def __setitem__(self, port, src) -> None:
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

    def __getattr__(self, name) -> Any:
        """
        Convert a RHS block name reference to a Plug.

        :param name: Port name
        :type port: str
        :return: Block or plug for specified block port name
        :rtype: ``Port``

        Used to create a wired connection by assignment, for example::

            c = bd.CONSTANT(1, onames=['v'])

            y = c.v

                +---+               +---+
                | c | -v ---------> | y |
                +---+               +---+

        .. note::  this overloaded method handles all instances of ``setattr`` and
              implements normal functionality as well, only creating a wire
              if ``name`` is a known port name.

        .. warning:: to avoid infinite recursion, this method must use
            ``super().__getattribute__`` to access attributes of the block, and only
            create a Plug if the name is in the list of port names.
        """

        # come here only if the attribute is not found in the normal way, so we know
        # it's not a regular attribute of the block

        # we have to use self.__dict__.get() to avoid infinite recursion, since the port
        # names are stored in attributes of the block

        # on the RHS the ports must be output ports
        outport_names = self.__dict__.get("_outport_names")

        if outport_names is not None and name in outport_names:
            port = outport_names.index(name)
            return Plug(self, port)
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def __setattr__(self, name, value) -> None:
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
            self.bd.connect(value, Plug(value, port=0))
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
        self._parents: list[Plug | None] = [None] * self.nin  # type: ignore[list-item]

    def add_output_wire(self, w) -> None:
        port = w.start.port
        assert port < len(self._output_wires), "port number too big"
        self._output_wires[port].append(w)

    def add_input_wire(self, w) -> None:
        port = w.end.port
        assert (
            self._input_wires[port] is None
        ), "attempting to connect second wire to an input"
        self._input_wires[port] = w
        self._parents[port] = w.start

    # ---------------------------------------------------------------------- #
    # operator overloads for implicit wiring

    @oodebug
    def __rshift__(left, right):
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
        assert (
            s is not None
        ), "left operand of >> operator must be a block connected to a block diagram"
        # assert isinstance(right, Block), 'arguments to * must be blocks not ports (for now)'
        w = s.connect(left, right)  # add a wire
        # print('block * ' + str(w))
        return right

        # make connection, return a plug

    def _autoconstant(self, value):
        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic constant"

        if isinstance(value, (int, float, str)):
            name = "_const.{:d}({})".format(next(self.bd.n_auto_const), value)
        else:
            name = "_const.{:d}<{}>".format(
                next(self.bd.n_auto_const), type(value).__name__
            )
        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic constant"
        return self.bd.CONSTANT(value, name=name)

    def _autogain(self, value, **kwargs):
        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic gain"

        if isinstance(value, (int, float, np.ndarray)):
            name = "_gain.{:d}({})".format(next(self.bd.n_auto_gain), value)
        else:
            raise TypeError(
                f"automatic gain value must be int, float, or ndarray, got {type(value).__name__}"
            )
        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic gain"
        return self.bd.GAIN(value, name=name, **kwargs)

    def _autopow(self, value, **kwargs):
        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic power block"

        name = "_pow.{:d}({})".format(next(self.bd.n_auto_pow), value)
        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic power block"
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

        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic sum block"
        name = "_sum.{:d}".format(next(self.bd.n_auto_sum))
        if isinstance(other, (int, float, np.ndarray)):
            # block + constant, create a CONSTANT block
            other = self._autoconstant(other)
        return Sum("++", inputs=(self, other), name=name, bd=self.bd)

    @oodebug
    def __radd__(self, other):
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

        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic sum block"
        name = "_sum.{:d}".format(next(self.bd.n_auto_sum))
        if isinstance(other, (int, float, np.ndarray)):
            # constant + block, create a CONSTANT block
            other = self._autoconstant(other)
        return Sum("++", inputs=(other, self), name=name, bd=self.bd)

    @oodebug
    def __sub__(self, other):
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

        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic sum block"
        name = "_sum.{:d}".format(next(self.bd.n_auto_sum))
        if isinstance(other, (int, float, np.ndarray)):
            # block - constant, create a CONSTANT block
            other = self._autoconstant(other)
        return Sum("+-", inputs=(self, other), name=name, bd=self.bd)

    @oodebug
    def __rsub__(self, other):
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

        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic sum block"

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
    def __mul__(self, other):
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

        .. note:: Signals are assumed to be scalars, but if ``C`` is a NumPy
            array then the option ``matrix`` is set to True.

        :seealso: :meth:`Block.__rmul__` :meth:`Plug.__mul__`
        """
        from bdsim.blocks import Prod

        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic product block"

        matrix = False
        if isinstance(other, (int, float, np.ndarray)):
            # block * constant, create a GAIN block
            matrix: bool = isinstance(other, np.ndarray)
            return self._autogain(other, premul=matrix, matrix=matrix, inputs=[self])
        else:
            # value * value, create a PROD block
            name = "_prod.{:d}".format(next(self.bd.n_auto_prod))
            return Prod(
                "**", inputs=[self, other], matrix=matrix, name=name, bd=self.bd
            )

    @oodebug
    def __rmul__(self, other):
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

        .. note:: Signals are assumed to be scalars, but if ``C`` is a NumPy
            array then the option ``matrix`` is set to True.

        :seealso: :meth:`Block.__mul__` :meth:`Plug.__rmul__`
        """
        matrix = False
        if isinstance(other, (int, float, np.ndarray)):
            # constant * block, create a GAIN block
            matrix: bool = isinstance(other, np.ndarray)
            return self._autogain(other, premul=matrix, inputs=[self])

    @oodebug
    def __truediv__(self, other):
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

        .. note:: Signals are assumed to be scalars, but if ``C`` is a NumPy
            array then the option ``matrix`` is set to True.

        :seealso: :meth:`Block.__rtruediv__` :meth:`Plug.__truediv__`
        """
        # value / value, create a PROD block
        from bdsim.blocks import Prod

        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic product block"

        name = "_prod.{:d}".format(next(self.bd.n_auto_prod))
        matrix = False
        if isinstance(other, (int, float, np.ndarray)):
            # block / constant, create a CONSTANT block
            other = self._autoconstant(other)
            matrix: bool = isinstance(other, np.ndarray)
        return Prod("*/", inputs=(self, other), matrix=matrix, name=name, bd=self.bd)

    @oodebug
    def __rtruediv__(self, other):
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

        .. note:: Signals are assumed to be scalars, but if ``C`` is a NumPy
            array then the option ``matrix`` is set to True.

        :seealso: :meth:`Block.__truediv__` :meth:`Plug.__rtruediv__`
        """
        # value / value, create a PROD block
        from bdsim.blocks import Prod

        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic product block"

        name = "_prod.{:d}".format(next(self.bd.n_auto_prod))
        matrix = False
        if isinstance(other, (int, float, np.ndarray)):
            # constant / block, create a CONSTANT block
            other = self._autoconstant(other)
            matrix: bool = isinstance(other, np.ndarray)
        return Prod("*/", inputs=(other, self), matrix=matrix, name=name, bd=self.bd)

    # TODO arithmetic with a constant, add a gain block or a constant block

    # ---------------------------------------------------------------------- #

    def reset(self) -> None:
        self._updated = False
        self._output_values = [None] * self.nout
        for slot in getattr(self, "_outport_slots", []):
            slot.value = None

    def start(self, simstate) -> None:  # begin a simulation
        pass

    def check(self) -> None:  # check validity of block parameters at start
        assert hasattr(self, "nin"), f"block {self.name} has no nin specified"
        assert hasattr(self, "nout"), f"block {self.name} has no nout specified"

        assert isinstance(self.nin, int), f"block {self.name} nin must be an int"
        assert isinstance(self.nout, int), f"block {self.name} nout must be an int"
        assert self.nin >= 0, f"block {self.name} nin must be non-negative"
        assert self.nout >= 0, f"block {self.name} nout must be non-negative"

        if self._inport_names is not None:
            assert (
                len(self._inport_names) == self.nin
            ), "number of input port names must match number of inputs"

        if self._outport_names is not None:
            assert (
                len(self._outport_names) == self.nout
            ), "number of output port names must match number of outputs"

        assert (
            self.nin > 0 or self.nout > 0
        ), f"block {self.name} no inputs or outputs specified"
        assert (
            hasattr(self, "_initd") and self._initd
        ), "Block superclass not initalized. was super().__init__ called?"

    def done(self, **kwargs) -> None:  # end of simulation
        pass

    def savefig(self, *pos, **kwargs) -> None:
        pass


class SinkBlock(Block):
    """
    A SinkBlock is a subclass of Block that represents a block that has inputs
    but no outputs. Typically used to save data to a variable, file or
    graphics.
    """

    _blockclass = "sink"

    def __init__(self, **blockargs) -> None:
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


class SourceBlock(Block):
    """
    A SourceBlock is a subclass of Block that represents a block that has outputs
    but no inputs.  Its output is a function of parameters and time.
    """

    _blockclass = "source"

    def __init__(self, **blockargs) -> None:
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


class TransferBlock(Block):
    """
    A TransferBlock is a subclass of Block that represents a block with inputs
    outputs and states. Typically used to describe a continuous time dynamic
    system, either linear or nonlinear.
    """

    _blockclass = "transfer"

    def __init__(self, nstates, **blockargs) -> None:
        """
        Create a transfer function block.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: transfer function block base class
        :rtype: TransferBlock

        This is the parent class of all transfer function blocks.
        """
        super().__init__(nstates=nstates, ndstates=0, **blockargs)

    def reset(self) -> None:
        super().reset()
        self._x = self._x0

    def setstate(self, x):
        x = np.array(x)
        self._x = x[: self.nstates]  # take as much state vector as we need
        return x[self.nstates :]  # return the rest

    def getstate0(self):
        return self._x0

    def check(self) -> None:
        super().check()
        assert len(self._x0) == self.nstates, "incorrect length for initial state"
        assert self.nin > 0 or self.nout > 0, "no inputs or outputs specified"

    @abstractmethod
    def deriv(self, t: float, u: list[Any], x: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    @abstractmethod
    def output(self, t: float, u: list[Any], x: np.ndarray) -> list[Any]:
        raise NotImplementedError


class FunctionBlock(Block):
    """
    A FunctionBlock is a subclass of Block that represents a block that has inputs
    and outputs but no state variables.  Typically used to describe operations
    such as gain, summation or various mappings.
    """

    _blockclass = "function"

    def __init__(self, **blockargs) -> None:
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


class SubsystemBlock(Block):
    """
    A SubSystem is a subclass of Block that represents a block that has inputs
    and outputs but no state variables.  Typically used to describe operations
    such as gain, summation or various mappings.
    """

    _blockclass = "subsystem"

    def __init__(self, **blockargs) -> None:
        """
        Create a subsystem block.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: subsystem block base class
        :rtype: SubsystemBlock

        This is the parent class of all subsystem blocks.
        """
        super().__init__(nstates=0, ndstates=0, **blockargs)


class ClockedBlock(Block):
    """
    A ClockedBlock is a subclass of Block that represents a block with inputs
    outputs and discrete states. Typically used to describe a discrete time dynamic
    system, either linear or nonlinear.
    """

    _blockclass = "clocked"

    def __init__(self, *, ndstates: int, clock: Clock, **blockargs) -> None:
        """
        Create a clocked block.

        :param ndstates: number of discrete-time states
        :type ndstates: int
        :param clock: the clock that governs the block's discrete time updates
        :type clock: Clock
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: clocked block base class
        :rtype: ClockedBlock

        This is the parent class of all clocked blocks.
        """
        super().__init__(nstates=0, ndstates=ndstates, **blockargs)
        assert clock is not None, "clocked block must have a clock"
        self._clocked = True
        self._clock = clock
        clock.add_block(self)

    def reset(self) -> None:
        super().reset()

    def setstate(self, x):
        self._x = x[: self.ndstates]  # take as much state vector as we need
        return x[self.ndstates :]  # return the rest

    def getstate0(self):
        return self._x0

    def check(self) -> None:
        assert len(self._x0) == self.ndstates, "incorrect length for initial state"
        assert self.nin > 0 or self.nout > 0, "no inputs or outputs specified"
        self._x = self._x0


class EventSource:
    pass


def is_notebook_backend(backend: str) -> bool:
    """Return True if *backend* names a Jupyter/inline rendering backend.

    Matplotlib exposes notebook backends under two different name forms:
    - Full module path: ``module://matplotlib_inline.backend_inline``,
      ``module://ipympl.backend_nbagg``, etc.
    - Short alias registered by the magic: ``inline``, ``widget``, ``nbagg``.

    Recognising both forms prevents bdsim from overriding a notebook backend
    with a desktop GUI backend (e.g. QtAgg) when running inside Jupyter.
    """
    if backend.startswith("module://"):
        return True
    return backend.lower() in ("inline", "widget", "nbagg")


class GraphicsBlock(SinkBlock):
    """
    A GraphicsBlock is a subclass of SinkBlock that represents a block that has inputs
    but no outputs and creates/updates a graphical display.
    """

    _blockclass = "graphics"

    def __init__(self, movie=None, **blockargs) -> None:
        """
        Create a graphical display block.

        :param movie: Save animation in this file in MP4 format, defaults to None
        :type movie: str, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: transfer function block base class
        :rtype: TransferBlock

        This is the parent class of all graphic display blocks.
        """
        super().__init__(**blockargs)
        self._graphics = True
        self._fig: matplotlib.figure.Figure | None = None
        self._movie = movie

    @property
    def fig(self) -> matplotlib.figure.Figure | None:
        return self._fig

    @fig.setter
    def fig(self, v: matplotlib.figure.Figure | None) -> None:
        self._fig = v

    @property
    def movie(self) -> str | None:
        return self._movie

    @movie.setter
    def movie(self, v: str | None) -> None:
        self._movie = v

    @property
    def writer(self):
        return self._writer

    @writer.setter
    def writer(self, v) -> None:
        self._writer = v

    def start(self, simstate) -> None:

        # plt.draw()
        # plt.show(block=False)
        self._simstate = simstate
        self._enabled = simstate.options.graphics

        if self._movie is not None and not simstate.options.animation:
            print(
                "enabling global animation option to allow movie option on block", self
            )
            if not simstate.options.animation:
                print("must enable animation to render a movie")
        if self._movie is not None:
            try:
                self._writer = animation.FFMpegWriter(
                    fps=10, extra_args=["-vcodec", "libx264"]
                )
                self._writer.setup(fig=self._fig, outfile=self._movie)  # type: ignore[union-attr]
                print("movie block", self, " --> ", self._movie)
            except FileNotFoundError:
                self.fatal("cannot save movie, please install ffmpeg")  # type: ignore[union-attr]

    def step(self, t, inports) -> None:
        # super().step(t, inports)  # type: ignore[safe-super]

        # bring the figure up to date in a backend-specific way
        if self._simstate.options.animation:
            if self._simstate.backend == "TkAgg":
                self._fig.canvas.flush_events()  # type: ignore[union-attr]
                plt.show(block=False)
                plt.show(block=False)
            elif self._simstate.backend == "Qt5Agg":
                self._fig.canvas.flush_events()  # type: ignore[union-attr]
                self._fig.canvas.draw()  # type: ignore[union-attr]
            else:
                self._fig.canvas.draw()  # type: ignore[union-attr]

        if self._movie is not None:
            try:
                self._writer.grab_frame()  # type: ignore[union-attr]
            except AttributeError:
                self.fatal("cannot save movie, please install ffmpeg")  # type: ignore[union-attr]

    def done(self, block=False, **kwargs) -> None:
        if self._fig is not None:
            self._fig.canvas.start_event_loop(0.001)  # type: ignore[union-attr]
            if self._movie is not None:
                self._writer.finish()  # type: ignore[union-attr]
                # self.cleanup()
            plt.show(block=block)

    def savefig(self, filename=None, format="pdf", **kwargs) -> None:
        """
        Save the figure as an image file

        :param fname: Name of file to save graphics to
        :type fname: str
        :param ``**kwargs``: Options passed to `savefig <https://matplotlib.org/3.2.2/api/_as_gen/matplotlib.pyplot.savefig.html>`_

        The file format is taken from the file extension and can be
        jpeg, png or pdf.
        """
        try:
            assert self._fig is not None, "no figure to save"
            plt.figure(self._fig.number)  # make block's figure the current one
            if filename is None:
                filename = self.name or ""
            filename += "." + format
            print("saved {} -> {}".format(str(self), filename))
            plt.savefig(filename, **kwargs)  # save the current figure

        except:
            pass

    def create_figure(self, state) -> matplotlib.figure.Figure:
        def resolve_tiles_spec(spec: str | None) -> list[int] | None:
            if spec is None:
                return None
            spec_l = spec.strip().lower()
            if spec_l == "":
                return None
            if spec_l in {"square", "wide", "tall"}:
                ngraphics = sum(
                    1 for b in self.bd.blocklist if getattr(b, "isgraphics", False)
                )
                ngraphics = max(1, ngraphics)
                if spec_l == "wide":
                    # Arrange windows horizontally.
                    return [1, ngraphics]
                if spec_l == "tall":
                    # Arrange windows vertically.
                    return [ngraphics, 1]
                rows = int(math.ceil(math.sqrt(ngraphics)))
                cols = int(math.ceil(ngraphics / rows))
                return [rows, cols]

            parts = spec_l.split("x")
            if len(parts) != 2:
                raise ValueError(
                    f"bad tiles spec '{spec}', expected RxC or one of square|wide|tall"
                )
            try:
                rows, cols = int(parts[0]), int(parts[1])
            except ValueError as exc:
                raise ValueError(
                    f"bad tiles spec '{spec}', expected integer RxC"
                ) from exc
            if rows <= 0 or cols <= 0:
                raise ValueError(f"bad tiles spec '{spec}', row/col must be > 0")
            return [rows, cols]

        def move_figure(f, x, y) -> None:
            """Move figure's upper left corner to pixel (x, y)"""
            backend: str = matplotlib.get_backend()
            x = int(x) + gstate.xoffset
            y = int(y)
            if backend == "TkAgg":
                f.canvas.manager.window.wm_geometry("+%d+%d" % (x, y))
            elif backend == "WXAgg":
                f.canvas.manager.window.SetPosition((x, y))
            else:
                # This works for QT and GTK
                # You can also use window.setGeometry
                try:
                    f.canvas.manager.window.move(x, y)
                except AttributeError:
                    # Native MacOSX backend does not expose a window move API.
                    if (
                        backend.lower() == "macosx"
                        and getattr(gstate, "ntiles", [1, 1]) not in (None, [1, 1])
                        and not getattr(gstate, "_warned_nomove", False)
                    ):
                        print(
                            "bdsim: backend MacOSX cannot position figure windows;"
                            " tiled windows may overlap. Use --backend QtAgg or TkAgg"
                            " (or BDSIM backend=QtAgg/TkAgg)."
                        )
                        gstate._warned_nomove = True
                    pass  # can't do this for MacOSX

        gstate = state
        options = state.options
        f: matplotlib.figure.Figure
        dpi: float
        row = 0
        col = 0

        # Reset per-block subplot assignment each start.
        self._tile_axes = None

        self.bd.runtime.DEBUG(  # type: ignore[attr-defined]
            "graphics", "{} matplotlib figures exist", len(plt.get_fignums())
        )

        if gstate.fignum == 0:
            # no figures yet created, lazy initialization
            self.bd.runtime.DEBUG("graphics", "lazy initialization")  # type: ignore[attr-defined]

            def backend_available(name: str) -> bool:
                try:
                    from matplotlib.backends import backend_registry

                    return name.lower() in {
                        backend.lower() for backend in backend_registry.list_builtin()
                    }
                except Exception:
                    backends = getattr(matplotlib.rcsetup, "all_backends", [])
                    return name.lower() in {backend.lower() for backend in backends}

            if options.backend is None:
                # If %matplotlib magic (or any other code) already set a notebook
                # backend (e.g. module://matplotlib_inline... or module://ipympl...),
                # honour it and don't override with a Qt/Tk window backend.
                _current_backend = matplotlib.get_backend()
                if is_notebook_backend(_current_backend):
                    pass  # already a notebook backend, leave it alone
                elif sys.platform == "darwin":
                    # For macOS, prefer backends that allow window placement.
                    selected = False
                    for backend_name, module_names in (
                        ("QtAgg", ("PyQt6", "PySide6", "PyQt5", "PySide2")),
                        ("Qt5Agg", ("PyQt5", "PySide2")),
                        ("TkAgg", ("tkinter",)),
                    ):
                        if not backend_available(backend_name):
                            continue
                        for module_name in module_names:
                            try:
                                importlib.import_module(module_name)
                                matplotlib.use(backend_name)
                                print(
                                    "no graphics backend specified: "
                                    f"{backend_name} found, using instead of MacOSX"
                                )
                                selected = True
                                break
                            except Exception:
                                continue
                        if selected:
                            break
            else:
                try:
                    matplotlib.use(options.backend)
                except Exception as exc:
                    raise RuntimeError(
                        "can't select matplotlib backend "
                        f"'{options.backend}': {exc}. "
                        "If this is a Qt backend, install one of: PyQt6, PySide6, "
                        "PyQt5, or PySide2. Or use --backend TkAgg (requires tkinter)."
                    ) from exc

            mpl_backend: str = matplotlib.get_backend()
            gstate.backend = mpl_backend

            self.bd.runtime.DEBUG("graphics", "  backend={:s}", mpl_backend)  # type: ignore[attr-defined]

            # Resolve tile specification from explicit grid or shape keyword.
            # If no tiles are specified, graphics blocks each use their own figure.
            ntiles: list[int] | None = resolve_tiles_spec(options.tiles)

            xoffset = 0
            if options.shape is None:
                if mpl_backend == "Qt5Agg":
                    # next line actually creates a figure if none already exist
                    QScreen = plt.get_current_fig_manager().canvas.screen()  # type: ignore[union-attr]
                    # this is a QScreenClass object, see https://doc.qt.io/qt-5/qscreen.html#availableGeometry-prop
                    # next line creates a figure
                    sz = QScreen.availableSize()
                    dpiscale = (
                        QScreen.devicePixelRatio()
                    )  # is 2.0 for Mac laptop screen
                    self.bd.runtime.DEBUG(  # type: ignore[attr-defined]
                        "graphics",
                        "  {} x {} @ {}dpi",
                        sz.width(),
                        sz.height(),
                        dpiscale,
                    )

                    # check for a second screen
                    if options.altscreen:
                        vsize = QScreen.availableVirtualGeometry().getCoords()
                        if vsize[0] < 0:
                            # extra monitor to the left
                            xoffset = vsize[0]
                        elif vsize[0] >= sz.width():
                            # extra monitor to the right
                            xoffset = vsize[0]
                        self.bd.runtime.DEBUG(  # type: ignore[attr-defined]
                            "graphics", "  altscreen offset {}", xoffset
                        )

                    screen_width, screen_height = sz.width(), sz.height()
                    dpi = QScreen.physicalDotsPerInch()
                    f = plt.gcf()

                elif mpl_backend == "TkAgg":
                    window = plt.get_current_fig_manager().window  # type: ignore[union-attr]
                    screen_width, screen_height = (
                        window.winfo_screenwidth(),
                        window.winfo_screenheight(),
                    )
                    dpiscale = 1
                    self.bd.runtime.DEBUG(  # type: ignore[attr-defined]
                        "graphics",
                        "  screensize: {:d} x {:d}",
                        screen_width,
                        screen_height,
                    )
                    f = plt.gcf()
                    dpi = f.dpi

                else:
                    # all other backends (e.g. QtAgg, inline, widget)
                    # Modern backends handle HiDPI/Retina natively so dpiscale=1.
                    # Using dpiscale=2 double-counts the device pixel ratio on
                    # Retina Macs and makes everything visually half-sized.
                    f = plt.figure()
                    dpi = f.dpi
                    dpiscale = 1
                    screen_width, screen_height = f.get_size_inches() * f.dpi

                # Compute figure size from screen tiles, but avoid giant windows.
                # For a single tile, preserve matplotlib's default figure size.
                default_figsize = list(f.get_size_inches())
                effective_dpi = dpi * dpiscale
                if ntiles is None or ntiles == [1, 1]:
                    figsize = default_figsize
                else:
                    tile_figsize = [
                        screen_width / ntiles[1] / effective_dpi,
                        screen_height / ntiles[0] / effective_dpi,
                    ]
                    max_scale = 1.5
                    figsize = [
                        min(tile_figsize[0], default_figsize[0] * max_scale),
                        min(tile_figsize[1], default_figsize[1] * max_scale),
                    ]

            else:
                # shape is given explictly
                screen_width, screen_height = [int(x) for x in options.shape.split("x")]

                f = plt.gcf()
                dpi = f.dpi
                dpiscale = 1
                figsize = [
                    screen_width / dpi,
                    screen_height / dpi,
                ]

            # Notebook/inline backends have no window manager; skip desktop GUI ops.
            _is_notebook_backend = is_notebook_backend(mpl_backend)
            if not _is_notebook_backend:
                f.canvas.manager.set_window_title(f"bdsim: Figure {f.number:d}")  # type: ignore[union-attr]

            # save graphics info away in state
            gstate.figsize = figsize
            gstate.dpi = dpi * dpiscale
            gstate.screensize_pix = (screen_width, screen_height)
            gstate.ntiles = ntiles
            gstate.xoffset = xoffset
            gstate.tiled_figure = None
            gstate.notebook_backend = _is_notebook_backend

            # resize the figure (skip in notebook: Jupyter controls figure size)
            if not _is_notebook_backend:
                f.set_dpi(gstate.dpi)
                f.set_size_inches(figsize, forward=True)  # type: ignore[union-attr, arg-type]
                plt.ion()

        else:
            # subsequent graphics blocks
            if gstate.ntiles is None:
                f = plt.figure(figsize=gstate.figsize, dpi=gstate.dpi)
            else:
                tiled_figure = getattr(gstate, "tiled_figure", None)
                assert tiled_figure is not None
                f = tiled_figure

        _notebook = getattr(gstate, "notebook_backend", False)
        if gstate.ntiles is None:
            # Untiled mode: each graphics block gets its own figure.
            if gstate.fignum > 0 and not _notebook:
                f.canvas.manager.set_window_title(f"bdsim: Figure {f.number:d}")  # type: ignore[union-attr]
        else:
            # Tiled mode: one shared figure with subplots; each block gets a tile.
            rows, cols = gstate.ntiles
            max_tiles = rows * cols
            if gstate.fignum >= max_tiles:
                raise ValueError(
                    "tile specification "
                    f"'{options.tiles}' has {max_tiles} tile(s) but "
                    f"requires at least {gstate.fignum + 1}"
                )

            if gstate.fignum == 0:
                gstate.tiled_figure = f
                f.clf()
                # Constrained layout prevents title/xlabel overlap between tiles;
                # dark background makes the white subplot panels stand out.
                f.set_constrained_layout(True)
                try:
                    f.get_layout_engine().set(hspace=0.08, wspace=0.06)
                except Exception:
                    f.set_constrained_layout_pads(hspace=0.08, wspace=0.06)  # type: ignore[attr-defined]  # pre-3.6 fallback
                f.patch.set_facecolor("#323232")

            row = gstate.fignum // cols
            col = gstate.fignum % cols
            self._tile_axes = f.add_subplot(rows, cols, gstate.fignum + 1)

        # move figure windows only when not using shared tiled subplots,
        # and only when a real window manager is available (not notebook backends)
        if not _notebook:
            if gstate.ntiles is not None:
                if gstate.fignum == 0:
                    move_figure(f, 0, 0)
            else:
                move_figure(f, 0, 0)

        gstate.fignum += 1

        def onkeypress(event) -> None:

            if event.key == "x":
                print("\nclosing all windows")
                plt.close("all")
            elif event.key == "ctrl+c":
                print("\nterminating bdsim")
                sys.exit(1)
            else:
                print("key pressed", event.key)

        if not getattr(f, "_bdsim_global_keys", False):
            f.canvas.mpl_connect("key_press_event", onkeypress)
            f._bdsim_global_keys = True

        self.bd.runtime.DEBUG(  # type: ignore[attr-defined]
            "graphics", "create figure {:d} at ({:d}, {:d})", gstate.fignum, row, col
        )
        return f


if __name__ == "__main__":
    try:
        from ._selftest import run_module_test
    except ImportError:
        from bdsim._selftest import run_module_test

    raise SystemExit(run_module_test(__file__))
