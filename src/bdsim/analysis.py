r"""Analysis of a compiled block diagram as a nonlinear system.

For nonlinear control it is usual to write a system as

.. math::

    \dot{x} = f(x, u, t), \qquad y = g(x, u, t)

:meth:`~bdsim.BlockDiagram.functions` returns these two functions
for a compiled diagram, and :meth:`~bdsim.BlockDiagram.linearize`
estimates the matrices :math:`(A, B, C, D)` of the local linear model by
numerical differentiation of them.

The input :math:`u` is the output of the diagram's source blocks, which are
replaced by the values given, and the output :math:`y` is a set of signals of the
diagram, by default those that the sink blocks receive.  :math:`x` is the
continuous state of the diagram, in the order the blocks were added.

These methods are split out of :mod:`bdsim.blockdiagram` as a mixin.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    Iterator,
    Literal,
    Protocol,
    overload,
)

import numpy as np
from numpy.typing import ArrayLike, NDArray

from bdsim.block import SinkBlock, SourceBlock
from bdsim.exceptions import BlockRuntimeError

if TYPE_CHECKING:
    from bdsim.components import Block, Plug, Wire

# step size of a central difference: the cube root of the machine epsilon
_EPS3 = float(np.finfo(float).eps ** (1.0 / 3.0))

# Richardson estimate of the difference error, relative to the larger of 1 and
# the element, above which linearize() warns
_KINK_TOLERANCE = 1e-6


class Index:
    """
    Maps the elements of a flattened vector to the blocks they belong to.

    The vectors :math:`x`, :math:`u` and :math:`y` of
    :meth:`~bdsim.BlockDiagram.functions` are the values of several
    blocks, flattened and concatenated in the order the blocks were added to the
    diagram.  An ``Index`` says which elements belong to which block.

    ``index[block]`` or ``index["name"]`` is the ``slice`` of the vector holding
    that block's elements, and ``index.labels[i]`` is the ``(block, k)`` of
    element ``i``, where ``k`` is the position within the block.  Blocks with no
    elements have no entry.
    """

    labels: list[tuple[Block, int]]  #: ``(block, k)`` for each element, in order
    slices: dict[Block, slice]  #: the slice of the vector holding each block's elements

    def __init__(
        self,
        entries: list[tuple[Block, int]],
        names: list[str | None] | None = None,
    ) -> None:
        """
        :param entries: ``(block, k)`` for each element of the vector
        :param names: a name for each element to use instead of the one made from
            the block's name, or ``None`` for an element that has no name of its own
        """
        self.labels: list[tuple[Block, int]] = entries
        self.slices: dict[Block, slice] = {}
        for i, (block, _) in enumerate(entries):
            if block in self.slices:
                self.slices[block] = slice(self.slices[block].start, i + 1)
            else:
                self.slices[block] = slice(i, i + 1)
        self._by_name = {b.name: b for b in self.slices}

        self._names = []
        for i, (block, k) in enumerate(entries):
            count = self.slices[block].stop - self.slices[block].start
            self._names.append(f"{block.name}[{k}]" if count > 1 else f"{block.name}")
        if names is not None:
            if len(names) != len(entries):
                raise ValueError(
                    f"{len(names)} names for {len(entries)} elements of the index"
                )
            for i, given in enumerate(names):
                if given is not None:
                    self._names[i] = given

    @classmethod
    def of_states(cls, blocks: Iterable[Block], width: Callable[[Block], int]) -> Index:
        """
        The index of the state of some blocks, in the order given.

        :param blocks: the blocks
        :param width: the number of states of a block, ``nstates`` for continuous
            state and ``ndstates`` for discrete
        :return: an index whose names are the ones a block gave its states, with
            ``snames=``, and otherwise the block's name, or ``name[k]`` for the
            ``k``-th of several
        """
        entries: list[tuple[Block, int]] = []
        names: list[str | None] = []
        for block in blocks:
            given = block._state_names
            for k in range(width(block)):
                entries.append((block, k))
                names.append(given[k] if given is not None and k < len(given) else None)
        return cls(entries, names)

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, key: Block | str) -> slice:
        if isinstance(key, str):
            try:
                key = self._by_name[key]
            except KeyError:
                raise KeyError(f"no block named {key!r} in this index") from None
        try:
            return self.slices[key]
        except KeyError:
            raise KeyError(f"block {key} has no elements in this index") from None

    def __contains__(self, key: Any) -> bool:
        return key in self.slices or key in self._by_name

    def __iter__(self) -> Iterator[Block]:
        return iter(self.slices)

    def name(self, i: int) -> str:
        """Name of element ``i`` for display, for example ``"integrator.0[1]"``."""
        return self._names[i]

    @property
    def names(self) -> list[str]:
        """The display name of every element."""
        return list(self._names)

    def __repr__(self) -> str:
        return f"Index({len(self)} elements: {', '.join(self.names)})"


def _flatten(value: Any, block: Block, port: int, what: str) -> NDArray:
    """A port value as a 1-D float array, or an error that names the port."""
    try:
        return np.asarray(value, dtype=float).reshape(-1)
    except (TypeError, ValueError):
        raise TypeError(
            f"{what} {block.name}[{port}] carries a {type(value).__name__}, "
            "which is not a number or an array of numbers"
        ) from None


def _block_and_ports(
    bd: Any, item: Block | Plug | str, port_attr: str
) -> tuple[Block, list[int]]:
    """The block, and the numbers of its ports, selected by a block, a plug or a name.

    :param port_attr: ``"nout"`` or ``"nin"``, the attribute giving the number of ports
    """
    from bdsim.components import Block, Plug

    if isinstance(item, str):
        item = bd[item]
    if isinstance(item, Plug):
        nports = getattr(item.block, port_attr)
        port = item.port
        ports = list(range(nports))[port] if isinstance(port, slice) else [port]
        return item.block, ports
    if not isinstance(item, Block):
        raise TypeError(f"expected a block, a plug or a block name, not {item!r}")
    return item, list(range(getattr(item, port_attr)))


def _output_signals(bd: Any, item: Block | Plug | str) -> list[tuple[Block, int]]:
    """The signals, as (producing block, output port), that an entry of ``outputs`` names.

    A sink has no outputs, so naming a sink, or one of its inputs, means the signal
    wired into it.  Anything else means its own outputs.
    """
    block, _ = _block_and_ports(bd, item, "nout")
    if isinstance(block, SinkBlock):
        block, ports = _block_and_ports(bd, item, "nin")
        signals = []
        for p in ports:
            wire = block._input_wires[p]
            if wire is None:
                raise ValueError(f"{block.name} has an unconnected input {p}")
            port = wire.start.port
            if not isinstance(port, int):  # a wire starts at one port
                raise ValueError(f"{block.name} input {p} is wired from {port!r}")
            signals.append((wire.start.block, port))
        return signals
    block, ports = _block_and_ports(bd, item, "nout")
    return [(block, p) for p in ports]


def _not_a_source(block: Block) -> str:
    """Why a block cannot be an input, and what to use instead.

    A signal made by an expression, such as ``step1 - step2``, is the output of an
    automatically named block (``_sum.0``), which is not a source.  The sources it
    is computed from are found by following its inputs back through algebraic
    blocks.  A block that depends on a state cannot be an input at all.
    """
    sources: list[str] = []
    stateful = False
    seen: set[Block] = set()
    todo = [block]
    while todo:
        b = todo.pop()
        if b in seen:
            continue
        seen.add(b)
        for plug in b.inports:
            upstream = plug.block
            if isinstance(upstream, SourceBlock):
                name = str(upstream.name)
                if upstream._reads_state:
                    stateful = True
                elif upstream._not_an_input is None and name not in sources:
                    sources.append(name)
            elif upstream.blockclass == "function":
                todo.append(upstream)
            else:
                stateful = True

    message = (
        f"input {block.name} is not a source block: inputs are source blocks or "
        f"their ports, but {block.name} is a {block.type} block. "
    )
    if stateful:
        return message + (
            "It depends on the state of the system, so it cannot be an input."
        )
    if sources:
        return message + (
            f"It is computed from the source blocks {', '.join(sources)}: use "
            "those, or make the signal a single source block."
        )
    return message + "Make the signal a single source block."


class SystemFunction(Protocol):
    """
    A function of the state, the input and the time: the ``f`` or the ``g`` that
    :meth:`~bdsim.BlockDiagram.functions` returns.
    """

    def __call__(self, x: ArrayLike, u: ArrayLike, t: float = 0.0) -> NDArray: ...


class SystemFunctions:
    r"""
    Contains the non-linear system functions of a block diagram 
    
    .. math::
    
        \dot{x} &= f(x, u, t), \\
        y &= g(x, u, t)
    
    along with the sizes and the maps that say what the vectors are made of.

    Returned by :meth:`~bdsim.BlockDiagram.functions` when it is called with
    ``full=True``.  It unpacks as the two functions, which are the pair that
    ``functions()`` returns by default::

        sysf = bd.functions(full=True)
        f, g = sysf
        xdot = f(x, u, t)
        y = g(x, u, t)

    ``x``, ``u`` and ``y`` are Numpy arrays and ``t`` is a float.


    :meth:`fg` computes both from one propagation through the diagram, which is
    half the work of calling ``f`` and then ``g``.


    Calling it evaluates the diagram, so it is not meant to be used during a
    simulation: the values on the wires and the diagram's state map are
    overwritten.

    .. note:: A hybrid system, which has blocks with discrete (clocked) state as well as
        continuous state, has no such pair of functions: its next discrete state is
        not a function of :math:`(x, u, t)` alone, since it depends on the state of the
        clocks and the discrete state itself.  Such a diagram is not accepted, and
        :class:`NotImplementedError` names the sampled blocks that are the reason.  To
        analyse the continuous-time part of a hybrid diagram, build it with source
        blocks in place of the sampled blocks and make those sources the ``inputs`` of
        :meth:`~bdsim.BlockDiagram.functions`, so that what the sampled blocks would
        have output becomes part of :math:`u`.

    :seealso: :meth:`~bdsim.BlockDiagram.functions` :class:`~bdsim.analysis.Linearization`
    """

    nx: int  #: number of continuous states
    nu: int  #: number of inputs
    ny: int  #: number of outputs
    x0: NDArray  #: initial continuous state of the diagram
    xindex: Index  #: which states belong to which block
    uindex: Index  #: which inputs are the outputs of which source block
    yindex: Index  #: which outputs are the signals of which block

    def __init__(
        self,
        bd: Any,
        inputs: list[Block | Plug | str] | None = None,
        outputs: list[Block | Plug | str] | None = None,
    ) -> None:
        self.bd = bd
        if not bd.compiled:
            raise RuntimeError("the block diagram has not been compiled")

        sampled = [b for b in bd.blocklist if b.ndstates > 0]
        if sampled:
            names = ", ".join(b.name for b in sampled)
            raise NotImplementedError(
                f"the diagram has sampled (discrete-time) blocks: {names}. "
                "functions() and linearize() cover continuous-time diagrams only"
            )

        # continuous state, in the order the blocks were added
        self.xindex = bd.xindex
        self.nx = len(self.xindex)
        self.x0 = np.asarray(bd.getstate0(), dtype=float).reshape(-1)

        # inputs: source blocks, or the ports of them given.  TIME is not an
        # input, it is the t argument.
        if inputs is None:
            inputs = [
                b
                for b in bd.blocklist
                if isinstance(b, SourceBlock)
                and b._not_an_input is None
                and not b._implicit
            ]
        selected: dict[Block, list[int]] = {}
        for item in inputs:
            block, ports = _block_and_ports(bd, item, "nout")
            if not isinstance(block, SourceBlock):
                raise TypeError(_not_a_source(block))
            if block._not_an_input is not None:
                raise ValueError(
                    f"{block.type.upper()} is not an input: {block._not_an_input}"
                )
            selected.setdefault(block, [])
            selected[block].extend(p for p in ports if p not in selected[block])
        self._inputs: dict[Block, list[int]] = {
            b: sorted(p) for b, p in selected.items()
        }

        # outputs: signals, each named by the block and output port that
        # produces it.  The default is the signal into every sink input.
        if outputs is None:
            outputs = [b for b in bd.blocklist if isinstance(b, SinkBlock)]
        signals: dict[Block, list[int]] = {}
        for item in outputs:
            for block, port in _output_signals(bd, item):
                signals.setdefault(block, [])
                if port not in signals[block]:
                    signals[block].append(port)
        self._outputs: dict[Block, list[int]] = {
            b: sorted(p) for b, p in signals.items()
        }

        # the blocks must have run once for a source or an output to have a shape
        self._prepare()
        self._probe()

    # ------------------------------------------------------------------ #

    def _prepare(self) -> None:
        """Make the blocks ready to evaluate if the diagram has not been started.

        After a run the blocks keep their internal state, for example a limited
        integrator held at its limit, and that is wanted.  A diagram that was
        only compiled has had the blocks touched by compile's trial evaluation,
        so they are reset and configured as a run would.
        """
        bd = self.bd
        if not bd._started:
            bd.reset()
            try:
                for b in bd.blocklist:
                    b.configure_safe()
            except BlockRuntimeError as err:
                bd._handle_block_runtime_error(err)

    def _probe(self) -> None:
        """Evaluate once to learn the shape of every input and output, and build the maps."""
        bd = self.bd
        t = 0.0
        state_map = bd.state_map(self.x0)
        bd.evaluate(state_map, t, sinks=False, check=False)

        # shapes of the natural output of every selected source port
        self._ushapes: dict[Block, dict[int, tuple[int, ...]]] = {}
        uentries: list[tuple[Block, int]] = []
        for block, ports in self._inputs.items():
            shapes = {}
            count = 0
            for p in ports:
                value = block.outport_value(p)
                flat = _flatten(value, block, p, "input")
                shapes[p] = np.shape(value)
                count += flat.size
            self._ushapes[block] = shapes
            uentries.extend((block, k) for k in range(count))
        # in the order the blocks were added, not the order requested
        order = {b: i for i, b in enumerate(bd.blocklist)}
        self._input_order = sorted(self._inputs, key=order.__getitem__)
        uentries.sort(key=lambda e: order[e[0]])
        self.uindex = Index(uentries)
        self.nu = len(self.uindex)

        yentries: list[tuple[Block, int]] = []
        self._output_order = sorted(self._outputs, key=order.__getitem__)
        for block in self._output_order:
            count = sum(
                _flatten(block.outport_value(p), block, p, "output").size
                for p in self._outputs[block]
            )
            yentries.extend((block, k) for k in range(count))
        self.yindex = Index(yentries)
        self.ny = len(self.yindex)

    # ------------------------------------------------------------------ #

    def u_at(self, t: float = 0.0) -> NDArray:
        """
        The values of the inputs at time ``t``, flattened.

        :param t: time
        :return: what the selected source blocks output at time ``t``

        This is the natural input of the diagram at ``t``, a good point to
        linearize about.
        """
        parts = []
        for block in self._input_order:
            out = block.output_safe(t, [], None)
            for p in self._inputs[block]:
                parts.append(_flatten(out[p], block, p, "input"))
        return np.concatenate(parts) if parts else np.zeros(0)

    def _overrides(self, u: NDArray, t: float) -> dict[Block, list[Any]]:
        overrides: dict[Block, list[Any]] = {}
        i = 0
        for block in self._input_order:
            ports = self._inputs[block]
            if len(ports) == block.nout:
                out: list[Any] = [None] * block.nout
            else:  # only some ports are inputs, the others keep their natural value
                out = list(block.output_safe(t, [], None))
            for p in ports:
                shape = self._ushapes[block][p]
                n = int(np.prod(shape)) if shape else 1
                chunk = u[i : i + n]
                out[p] = float(chunk[0]) if shape == () else chunk.reshape(shape).copy()
                i += n
            overrides[block] = out
        return overrides

    def fg(self, x: ArrayLike, u: ArrayLike, t: float = 0.0) -> tuple[NDArray, NDArray]:
        r"""
        Evaluate :math:`\dot{x} = f(x, u, t)` and :math:`y = g(x, u, t)` together.

        :param x: continuous state
        :type x: array_like(nx)
        :param u: input
        :type u: array_like(nu)
        :param t: time, defaults to 0
        :return: :math:`(\dot{x}, y)`
        """
        x = np.asarray(x, dtype=float).reshape(-1)
        u = np.asarray(u, dtype=float).reshape(-1)
        if x.size != self.nx:
            raise ValueError(f"x has {x.size} elements, expected {self.nx}")
        if u.size != self.nu:
            raise ValueError(f"u has {u.size} elements, expected {self.nu}")

        bd = self.bd
        state_map = bd.state_map(x.copy())
        bd.evaluate(
            state_map,
            t,
            sinks=False,
            check=False,
            overrides=self._overrides(u, t),
        )
        xdot = np.asarray(bd.deriv(t, state_map), dtype=float).reshape(-1)

        parts = []
        for block in self._output_order:
            for p in self._outputs[block]:
                parts.append(_flatten(block.outport_value(p), block, p, "output"))
        y = np.concatenate(parts) if parts else np.zeros(0)
        return xdot, y

    def f(self, x: ArrayLike, u: ArrayLike, t: float = 0.0) -> NDArray:
        r"""State derivative :math:`\dot{x} = f(x, u, t)`."""
        return self.fg(x, u, t)[0]

    def g(self, x: ArrayLike, u: ArrayLike, t: float = 0.0) -> NDArray:
        """Output :math:`y = g(x, u, t)`."""
        return self.fg(x, u, t)[1]

    def __iter__(self) -> Iterator[Any]:
        return iter((self.f, self.g))

    def __repr__(self) -> str:
        return f"SystemFunctions(nx={self.nx}, nu={self.nu}, ny={self.ny})"


def _matrix_str(M: NDArray) -> str:
    """A matrix for display: commas, four digits, and noise-sized values as 0."""
    return np.array2string(M, precision=4, suppress_small=True, separator=", ")


@dataclass(repr=False)
class Linearization:
    r"""
    A local linear model of a block diagram, from
    :meth:`~bdsim.BlockDiagram.linearize`.

    The model is

    .. math::

        \begin{aligned}
        \frac{d}{dt}(\delta x) &= A\,\delta x + B\,\delta u + f_0 \\
        y &= C\,\delta x + D\,\delta u + g_0
        \end{aligned}

    where :math:`\delta x` and :math:`\delta u` are the deviations of the state and
    the input from the operating point, and :math:`f_0` and :math:`g_0` are the
    functions :math:`f` and :math:`g` at the operating point.  The matrices are
    attributes, as are the operating point and the maps that say which signal each
    row and column is.

    It unpacks as ``A, B, C, D``::

        lin = bd.linearize(outputs=[x, theta], full=True)
        A, B, C, D = lin

    ``print`` shows the model with each matrix labelled by the names of the
    signals that are its rows and columns, see :meth:`__str__`.  :attr:`poles` are the
    eigenvalues of ``A``.

    :seealso: :meth:`~bdsim.BlockDiagram.linearize` :class:`~bdsim.analysis.SystemFunctions`
    """

    A: NDArray  #: :math:`\partial f / \partial x`, shape ``(nx, nx)``
    B: NDArray  #: :math:`\partial f / \partial u`, shape ``(nx, nu)``
    C: NDArray  #: :math:`\partial g / \partial x`, shape ``(ny, nx)``
    D: NDArray  #: :math:`\partial g / \partial u`, shape ``(ny, nu)``
    f0: NDArray  #: :math:`f(x, u, t)` at the operating point, zero at an equilibrium
    g0: NDArray  #: :math:`g(x, u, t)` at the operating point
    x: NDArray  #: state of the operating point
    u: NDArray  #: input of the operating point
    t: float  #: time of the operating point
    xindex: Index  #: names the rows and columns of ``A`` and the columns of ``C``
    uindex: Index  #: names the columns of ``B`` and ``D``
    yindex: Index  #: names the rows of ``C`` and ``D``
    #: estimated error of each of ``A, B, C, D``, as a dict with those keys, or
    #: ``None`` if ``estimate_error`` was not requested
    error: dict[str, NDArray] | None = field(default=None)

    def __iter__(self) -> Iterator[NDArray]:
        """Unpack as ``A, B, C, D``."""
        return iter((self.A, self.B, self.C, self.D))

    def ss(self, name: str | None = None) -> Any:
        r"""
        The model as a python-control state-space system.

        :param name: name of the system, defaults to one chosen by python-control
        :return: a :class:`control.StateSpace` with the matrices ``A, B, C, D`` of this
            model, and with the names of the states, inputs and outputs as its signal
            names, taken from ``xindex``, ``uindex`` and ``yindex``
        :raises ImportError: python-control is not installed

        `python-control <https://github.com/python-control/python-control>`_ is the
        usual package for the design of control systems, and this is the way to use
        it on a diagram.  For example, to design a linear quadratic regulator
        (:func:`control.lqr`) for a cart and pole and apply it::

            import control

            lin = bd.linearize(outputs=[x, theta], full=True)
            sys = lin.ss()
            K, S, E = control.lqr(sys, Q, R)
            F = -K * bd.STATE()

        The signal names carry through, so that systems made this way can be
        connected by name with :func:`control.interconnect`.

        python-control is an optional dependency, imported when this method is
        called: ``pip install control``, or install bdsim with the ``control`` extra.
        Version 0.10 or later is needed, for the signal names.



        The system is linear and time invariant, which is the model
        :math:`\delta\dot{x} = A\,\delta x + B\,\delta u`.  The offset :math:`f_0` of an
        operating point that is not an equilibrium, the output :math:`g_0`, and the
        operating point itself are not part of it, and stay on this object.  The
        values of the matrices are those of the numerical derivative, so an element
        that is zero may be of the order of 1e-10, which can matter for tests of
        rank such as :func:`control.ctrb`.

        .. note:: python-control cannot make a system that has no inputs and a single state
            or a single output, because it mistakes a matrix of shape ``(1, 0)`` for an
            empty one.  Use :attr:`poles` for an autonomous system like that.


        :seealso: :meth:`~bdsim.BlockDiagram.linearize`
            :class:`~bdsim.blocks.continuous.LTI_SS`
        """
        try:
            import control
        except ImportError:
            raise ImportError(
                "Linearization.ss() needs the python-control package: "
                "pip install control"
            ) from None
        return control.ss(
            self.A,
            self.B,
            self.C,
            self.D,
            dt=0,
            states=self.xindex.names,
            inputs=self.uindex.names,
            outputs=self.yindex.names,
            name=name,
        )

    @property
    def poles(self) -> NDArray:
        """
        The poles of the model, the eigenvalues of ``A``, sorted by real part.

        :return: complex array of length ``nx``
        """
        return np.sort_complex(np.linalg.eigvals(self.A))

    def _poles_str(self) -> str:
        poles = self.poles
        if poles.size == 0:
            return "[]"
        if np.all(np.abs(poles.imag) <= 1e-9 * np.maximum(1.0, np.abs(poles))):
            return np.array2string(
                poles.real,
                separator=", ",
                formatter={"float_kind": lambda v: f"{v:.4g}"},
            )
        return np.array2string(
            poles, separator=", ", formatter={"complex_kind": lambda z: f"{z:.4g}"}
        )

    def __str__(self) -> str:
        r"""
        The model, with each matrix labelled by the signals that are its rows and
        columns.

        This is what ``print`` shows.  For a cart and pole with the force on the cart
        as the input and the cart position and pole angle as the outputs::

            Linearization at t = 0

            states  x (4): x_dot, x, theta_dot, theta
            inputs  u (1): disturbance
            outputs y (2): x, theta

            A = df/dx  (4x4)
              rows and columns: x_dot, x, theta_dot, theta
            [[-10.   ,   0.   ,   0.   ,  -0.981],
             [  1.   ,   0.   ,   0.   ,   0.   ],
             [ 20.   ,   0.   ,   0.   ,  21.582],
             [  0.   ,   0.   ,   1.   ,   0.   ]]

            B = df/du  (4x1)
              rows: x_dot, x, theta_dot, theta
              columns: disturbance
            [[ 1.],
             [ 0.],
             [-2.],
             [ 0.]]

            C = dg/dx  (2x4)
              rows: x, theta
              columns: x_dot, x, theta_dot, theta
            [[0., 1., 0., 0.],
             [0., 0., 0., 1.]]

            D = dg/du  (2x1)
              rows: x, theta
              columns: disturbance
            [[0.],
             [0.]]

            poles: [-10.24, -4.262, 0, 4.498]

        The names are those of the blocks that are the states, inputs and outputs,
        or the names a block gave its states.  A value smaller than about 5e-5 is
        shown as 0, which hides the noise of the numerical derivative; the matrices
        themselves are not changed.  The poles are listed as real numbers if they all
        are.

        If the operating point is not an equilibrium, so that :math:`f_0` is not zero,
        a last line says so, because the model then includes :math:`f_0`.
        """
        nx, nu, ny = len(self.xindex), len(self.uindex), len(self.yindex)
        states = ", ".join(self.xindex.names)
        inputs = ", ".join(self.uindex.names)
        outputs = ", ".join(self.yindex.names)

        lines = [f"Linearization at t = {self.t:g}", ""]
        lines.append(f"states  x ({nx}): {states}")
        lines.append(f"inputs  u ({nu}): {inputs}")
        lines.append(f"outputs y ({ny}): {outputs}")
        lines.append("")

        blocks = (
            ("A = df/dx", self.A, "rows and columns", states),
            ("B = df/du", self.B, "rows x, columns u", None),
            ("C = dg/dx", self.C, "rows y, columns x", None),
            ("D = dg/du", self.D, "rows y, columns u", None),
        )
        for label, M, meaning, same in blocks:
            r, c = M.shape
            lines.append(f"{label}  ({r}x{c})")
            if same is not None:
                lines.append(f"  {meaning}: {same}")
            else:
                rows = states if label[0] == "B" else outputs
                cols = inputs if label[0] in "BD" else states
                lines.append(f"  rows: {rows}")
                lines.append(f"  columns: {cols}")
            lines.append(_matrix_str(M))
            lines.append("")

        lines.append(f"poles: {self._poles_str()}")
        worst = float(np.max(np.abs(self.f0))) if self.f0.size else 0.0
        if worst > 1e-9:
            lines.append(
                f"not an equilibrium: max |f0| = {worst:.3g}, the model is "
                "d(dx)/dt = A dx + B du + f0"
            )
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"Linearization(t={self.t:g}, nx={len(self.xindex)}, "
            f"nu={len(self.uindex)}, ny={len(self.yindex)})"
        )


class AnalysisMixin:
    """Methods of :class:`~bdsim.BlockDiagram` that analyse it as a system.

    The attributes declared below are the ones these methods read; they are set
    by ``BlockDiagram``.
    """

    if TYPE_CHECKING:
        blocklist: list[Block]
        wirelist: list[Wire]
        compiled: bool

    @property
    def xindex(self) -> Index:
        """
        Which elements of the continuous state vector belong to which block.

        :return: an :class:`~bdsim.analysis.Index`

        This is the one definition of the layout of the state :math:`x` of the
        diagram, the vector the solver advances: the states of the blocks that
        have continuous state, in the order the blocks were added.  The state
        passed to :meth:`functions`, returned by :meth:`BDSim.run` as ``out.x``,
        and output by a :class:`~bdsim.blocks.sources.State` block are all in this
        order.

        The names are those a block gave its states, with ``snames``, and
        otherwise the block's name, or ``name[k]`` for the ``k``-th of several.
        ``bd.statenames`` names the same elements in the same order, in the form
        ``name:x_k``, which is also what ``out.xnames`` holds.
        """
        return Index.of_states(
            (b for b in self.blocklist if b.blockclass == "continuous"),
            lambda b: b.nstates,
        )

    @overload
    def functions(
        self,
        inputs: list[Block | Plug | str] | None = ...,
        outputs: list[Block | Plug | str] | None = ...,
        *,
        full: Literal[False] = ...,
    ) -> tuple[SystemFunction, SystemFunction]: ...

    @overload
    def functions(
        self,
        inputs: list[Block | Plug | str] | None = ...,
        outputs: list[Block | Plug | str] | None = ...,
        *,
        full: Literal[True],
    ) -> SystemFunctions: ...

    @overload
    def functions(
        self,
        inputs: list[Block | Plug | str] | None = ...,
        outputs: list[Block | Plug | str] | None = ...,
        *,
        full: bool,
    ) -> tuple[SystemFunction, SystemFunction] | SystemFunctions: ...

    def functions(
        self,
        inputs: list[Block | Plug | str] | None = None,
        outputs: list[Block | Plug | str] | None = None,
        *,
        full: bool = False,
    ) -> tuple[SystemFunction, SystemFunction] | SystemFunctions:
        r"""
        The diagram as the functions :math:`f` and :math:`g` of a nonlinear system

        :param inputs: the source blocks, or the outputs of them, that are the
            input :math:`u`, see below.  Defaults to every source block except
            ``TIME`` and the constants bdsim creates for numbers written in
            expressions, which are parameters, not inputs.
        :param outputs: the signals that are the output :math:`y`, see below.
            Defaults to the signal into every sink input.
        :param full: return a :class:`~bdsim.analysis.SystemFunctions` object, which
            also has the sizes of the vectors and the maps that say what they are made
            of, instead of just the two functions
        :return: the pair ``(f, g)``, or a :class:`~bdsim.analysis.SystemFunctions`
            object if ``full``, which also unpacks as ``f, g``
        :raises NotImplementedError: the diagram has sampled (discrete-time) blocks
        :raises RuntimeError: the diagram has not been compiled

        .. math::

            \dot{x} = f(x, u, t), \qquad y = g(x, u, t)

        The diagram must be compiled.  The source blocks are replaced by the
        values of :math:`u`, ``TIME`` supplies :math:`t`, and :math:`y` is read
        from the diagram.  The sink blocks are not executed (nothing is plotted,
        printed or logged).  :math:`x` is the continuous state in the order the
        blocks were added to the diagram, as in ``bd.statenames``.

        **Choosing the input and the output**

        Both are lists.  An entry is a block, one of its ports (a plug, such as
        ``plant[0]``), or the name of a block (such as ``"plant"``).

        .. list-table::
            :header-rows: 1
            :widths: 45 55

            * - Entry of ``inputs``
              - :math:`u` contains
            * - a source block, ``demand``
              - all its outputs
            * - a port of a source block, ``demand[0]``
              - that output

        Source blocks that are not selected keep producing their own values.
        ``TIME`` cannot be an input, it is the argument ``t``.  To add a signal
        into the middle of a diagram, which has no input there, insert a ``SUM``
        block and a ``CONSTANT(0)`` block at that point: the constant is then an
        input.

        .. list-table::
            :header-rows: 1
            :widths: 45 55

            * - Entry of ``outputs``
              - :math:`y` contains
            * - any other block, ``plant``
              - all its outputs
            * - a port of a block, ``plant[0]``
              - that output
            * - a sink block, ``scope``
              - the signals wired into all its inputs
            * - a port of a sink block, ``scope[1]``
              - the signal wired into that input

        The output is a signal, named by the block and port that produce it.  A
        sink has no outputs, so naming a sink means the signals it receives.
        This is also how the default is made, and a signal that is wired to
        several sinks is included once.

        The elements of :math:`u` and :math:`y` are ordered by the order in which
        the blocks were added to the diagram, and then by port, whatever the order
        of the lists.  A block's array output is flattened, and ``uindex`` and
        ``yindex`` say where each block's elements are.

        For example::

            f, g = bd.functions()
            xdot = f(x, u, t)
            y = g(x, u, t)

        To check what ``x``, ``u`` and ``y`` are made of, and how long they are, ask
        for the full object, as ``linearize`` does with ``full=True``::

            sysf = bd.functions(full=True)
            sysf.xindex  # which states belong to which block
            sysf.nu, sysf.ny  # the lengths of u and y
            f, g = sysf  # the same two functions
            xdot, y = sysf.fg(x, u, t)  # both, from one evaluation of the diagram

        The object also has ``nx``, the initial state ``x0``, ``u_at(t)`` for the
        natural input at a time, and ``uindex`` and ``yindex`` for the inputs and
        outputs.  ``f`` and ``g`` each evaluate the diagram, so ``fg`` is half the
        work when both are needed at the same point.

        The state of the blocks is as the last run left it.  After a run, for
        example, an integrator held at its limit is still held, so the model is
        that of the diagram at the end of the run.  A diagram that has not been
        run has its blocks reset first.  Do not call the functions during a
        simulation: they overwrite the values on the wires.

        :seealso: :meth:`linearize` :class:`~bdsim.analysis.SystemFunctions`
            :class:`~bdsim.blocks.sources.State` :class:`~bdsim.blocks.sources.State_S`
        """
        sysf = SystemFunctions(self, inputs, outputs)
        return sysf if full else (sysf.f, sysf.g)

    @overload
    def linearize(
        self,
        x: ArrayLike | None = ...,
        u: ArrayLike | None = ...,
        t: float = ...,
        *,
        inputs: list[Block | Plug | str] | None = ...,
        outputs: list[Block | Plug | str] | None = ...,
        h: float | None = ...,
        scale: ArrayLike | None = ...,
        estimate_error: bool = ...,
        full: Literal[False] = ...,
    ) -> tuple[NDArray, NDArray, NDArray, NDArray]: ...

    @overload
    def linearize(
        self,
        x: ArrayLike | None = ...,
        u: ArrayLike | None = ...,
        t: float = ...,
        *,
        inputs: list[Block | Plug | str] | None = ...,
        outputs: list[Block | Plug | str] | None = ...,
        h: float | None = ...,
        scale: ArrayLike | None = ...,
        estimate_error: bool = ...,
        full: Literal[True],
    ) -> Linearization: ...

    @overload
    def linearize(
        self,
        x: ArrayLike | None = ...,
        u: ArrayLike | None = ...,
        t: float = ...,
        *,
        inputs: list[Block | Plug | str] | None = ...,
        outputs: list[Block | Plug | str] | None = ...,
        h: float | None = ...,
        scale: ArrayLike | None = ...,
        estimate_error: bool = ...,
        full: bool,
    ) -> tuple[NDArray, NDArray, NDArray, NDArray] | Linearization: ...

    def linearize(
        self,
        x: ArrayLike | None = None,
        u: ArrayLike | None = None,
        t: float = 0.0,
        *,
        inputs: list[Block | Plug | str] | None = None,
        outputs: list[Block | Plug | str] | None = None,
        h: float | None = None,
        scale: ArrayLike | None = None,
        estimate_error: bool = False,
        full: bool = False,
    ) -> tuple[NDArray, NDArray, NDArray, NDArray] | Linearization:
        r"""
        Linearize the diagram about an operating point

        :param x: state of the operating point, defaults to the initial state of
            the diagram.  After a run use ``out.x[-1]``.
        :type x: array_like(nx), optional
        :param u: input of the operating point, defaults to the natural input of
            the sources at ``t``
        :type u: array_like(nu), optional
        :param t: time of the operating point
        :param inputs: the source blocks or ports that are the input, see :meth:`functions`
        :param outputs: the blocks or ports whose signals are the output, see :meth:`functions`
        :param h: step of the numerical derivative, defaults to a size chosen for
            each variable
        :param scale: typical size of the variables, a number or an array with
            one element for each state and then each input, defaults to 1.  Give
            it when a variable is far from 1 in size and zero at the point.
        :param estimate_error: also differentiate with twice the step, to estimate
            the error and warn where a block is not smooth enough
        :param full: return a :class:`~bdsim.analysis.Linearization`, which also has
            the operating point and the names of the states, inputs and outputs, and
            prints as a labelled model, see :meth:`~bdsim.analysis.Linearization.__str__`
        :return: ``(A, B, C, D)``, or the ``Linearization`` if ``full``
        :raises NotImplementedError: the diagram has sampled (discrete-time) blocks

        The matrices of the local linear model are the Jacobians

        .. math::

            A = \frac{\partial f}{\partial x},\quad
            B = \frac{\partial f}{\partial u},\quad
            C = \frac{\partial g}{\partial x},\quad
            D = \frac{\partial g}{\partial u}

        of the functions :math:`f` and :math:`g` of :meth:`functions`, estimated
        by central differences with a step :math:`h \approx \epsilon^{1/3}
        \max(|v|, s)` for a variable :math:`v` of typical size :math:`s`, where
        :math:`\epsilon` is the machine precision.

        A state reached part way through a simulation is not usually an
        equilibrium, so :math:`f \neq 0` there and the model is
        :math:`\delta\dot{x} = A\,\delta x + B\,\delta u + f_0`.  The result
        does not include :math:`f_0`, but ``full=True`` returns it with
        :math:`g_0`.

        The result has the form of the matrices of a linear time-invariant system
        and can be used directly to make a
        :class:`~bdsim.blocks.continuous.LTI_SS` block.  For control system
        design, including poles, stability and optimal control, see the
        python-control package, https://github.com/python-control/python-control,
        which takes the same ``(A, B, C, D)``.

        For example, to linearize at the end of a simulation::

            out = sim.run(bd, T=5)
            A, B, C, D = bd.linearize(out.x[-1])

        To design state feedback from the result, take a gain matrix ``K`` from
        the ``A`` and ``B`` and feed the state back with a
        :class:`~bdsim.blocks.sources.State` block, ``F = -K * bd.STATE()``.  The
        state of that block is in the order of the states of this method, so
        ``K`` applies directly, and linearizing the closed loop gives
        :math:`A - BK`.  The state of a clocked block is available from
        :class:`~bdsim.blocks.sources.State_S`.

        If the operating point is at a corner of a non-smooth block (a limit, a
        dead band, a switch) the derivative is not defined there.  The result is
        then the slope across the step; with ``estimate_error`` a warning says
        that the estimate is not reliable.

        :seealso: :meth:`functions` :class:`~bdsim.blocks.continuous.LTI_SS`
            :class:`~bdsim.blocks.sources.State` :class:`~bdsim.blocks.sources.State_S`
        """
        sysf = self.functions(inputs, outputs, full=True)

        x = sysf.x0.copy() if x is None else np.asarray(x, dtype=float).reshape(-1)
        u = sysf.u_at(t) if u is None else np.asarray(u, dtype=float).reshape(-1)
        if x.size != sysf.nx:
            raise ValueError(f"x has {x.size} elements, expected {sysf.nx}")
        if u.size != sysf.nu:
            raise ValueError(f"u has {u.size} elements, expected {sysf.nu}")

        nv = sysf.nx + sysf.nu
        scales = (
            np.ones(nv)
            if scale is None
            else np.broadcast_to(np.asarray(scale, dtype=float), (nv,))
        )
        if np.any(scales <= 0):
            raise ValueError("scale must be positive")

        v0 = np.r_[x, u]
        f0, g0 = sysf.fg(x, u, t)

        def jacobian(factor: float) -> NDArray:
            """Columns of d(f,g)/d(x,u) by central differences, step times factor."""
            J = np.zeros((sysf.nx + sysf.ny, nv))
            for i in range(nv):
                step = factor * (
                    h if h is not None else _EPS3 * max(abs(v0[i]), scales[i])
                )
                vp = v0.copy()
                vm = v0.copy()
                vp[i] += step
                vm[i] -= step
                # the step actually taken, after rounding
                actual = vp[i] - vm[i]
                fp, gp = sysf.fg(vp[: sysf.nx], vp[sysf.nx :], t)
                fm, gm = sysf.fg(vm[: sysf.nx], vm[sysf.nx :], t)
                J[:, i] = np.r_[fp - fm, gp - gm] / actual
            return J

        J1 = jacobian(1.0)
        nx = sysf.nx
        A, B = J1[:nx, :nx], J1[:nx, nx:]
        C, D = J1[nx:, :nx], J1[nx:, nx:]

        error = None
        if estimate_error:
            J2 = jacobian(2.0)
            diff = np.abs(J1 - J2) / 3.0  # Richardson estimate of the error of J1
            error = {
                "A": diff[:nx, :nx],
                "B": diff[:nx, nx:],
                "C": diff[nx:, :nx],
                "D": diff[nx:, nx:],
            }
            bad = diff > _KINK_TOLERANCE * np.maximum(1.0, np.abs(J1))
            if np.any(bad):
                worst = np.unravel_index(
                    np.argmax(diff / np.maximum(1.0, np.abs(J1))), diff.shape
                )
                row, col = int(worst[0]), int(worst[1])
                outname = (
                    sysf.xindex.name(row) + "'"
                    if row < nx
                    else sysf.yindex.name(row - nx)
                )
                varname = (
                    sysf.xindex.name(col) if col < nx else sysf.uindex.name(col - nx)
                )
                warnings.warn(
                    f"linearize: the derivative of {outname} with respect to "
                    f"{varname} changes with the step size (estimated error "
                    f"{diff[row, col]:.2g}); the operating point may be at a corner "
                    "of a non-smooth block such as a limit, dead band or switch",
                    stacklevel=2,
                )

        if full:
            return Linearization(
                A=A,
                B=B,
                C=C,
                D=D,
                f0=f0,
                g0=g0,
                x=x,
                u=u,
                t=t,
                xindex=sysf.xindex,
                uindex=sysf.uindex,
                yindex=sysf.yindex,
                error=error,
            )
        return A, B, C, D
