r"""Analysis of a compiled block diagram as a nonlinear system.

For nonlinear control it is usual to write a system as

.. math::

    \dot{x} = f(x, u, t), \qquad y = g(x, u, t)

:meth:`~bdsim.blockdiagram.BlockDiagram.functions` returns these two functions
for a compiled diagram, and :meth:`~bdsim.blockdiagram.BlockDiagram.linearize`
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
from typing import TYPE_CHECKING, Any, Iterator

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
    :meth:`~bdsim.blockdiagram.BlockDiagram.functions` are the values of several
    blocks, flattened and concatenated in the order the blocks were added to the
    diagram.  An ``Index`` says which elements belong to which block.

    ``index[block]`` or ``index["name"]`` is the ``slice`` of the vector holding
    that block's elements, and ``index.labels[i]`` is the ``(block, k)`` of
    element ``i``, where ``k`` is the position within the block.  Blocks with no
    elements have no entry.
    """

    def __init__(self, entries: list[tuple[Block, int]]) -> None:
        """
        :param entries: ``(block, k)`` for each element of the vector
        """
        self.labels: list[tuple[Block, int]] = entries
        self.slices: dict[Block, slice] = {}
        for i, (block, _) in enumerate(entries):
            if block in self.slices:
                self.slices[block] = slice(self.slices[block].start, i + 1)
            else:
                self.slices[block] = slice(i, i + 1)
        self._by_name = {b.name: b for b in self.slices}

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
        block, k = self.labels[i]
        count = self.slices[block].stop - self.slices[block].start
        return f"{block.name}[{k}]" if count > 1 else f"{block.name}"

    @property
    def names(self) -> list[str]:
        """The display name of every element."""
        return [self.name(i) for i in range(len(self))]

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


class SystemFunctions:
    """
    The functions :math:`f` and :math:`g` of a block diagram.

    Returned by :meth:`~bdsim.blockdiagram.BlockDiagram.functions`.  It unpacks
    as the two functions::

        f, g = bd.functions()
        xdot = f(x, u, t)
        y = g(x, u, t)

    :meth:`fg` computes both from one propagation through the diagram, which is
    half the work of calling ``f`` and then ``g``.

    :ivar nx: number of continuous states
    :ivar nu: number of inputs
    :ivar ny: number of outputs
    :ivar x0: initial continuous state of the diagram
    :ivar xindex: which states belong to which block
    :vartype xindex: Index
    :ivar uindex: which inputs are the outputs of which source block
    :vartype uindex: Index
    :ivar yindex: which outputs are the signals of which block
    :vartype yindex: Index

    Calling it evaluates the diagram, so it is not meant to be used during a
    simulation: the values on the wires and the diagram's state map are
    overwritten.
    """

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
        self._xblocks = [b for b in bd.blocklist if b.blockclass == "continuous"]
        self.xindex = Index([(b, k) for b in self._xblocks for k in range(b.nstates)])
        self.nx = len(self.xindex)
        self.x0 = np.asarray(bd.getstate0(), dtype=float).reshape(-1)

        # inputs: source blocks, or the ports of them given.  TIME is not an
        # input, it is the t argument.
        if inputs is None:
            inputs = [
                b
                for b in bd.blocklist
                if isinstance(b, SourceBlock) and b.type != "time"
            ]
        selected: dict[Block, list[int]] = {}
        for item in inputs:
            block, ports = _block_and_ports(bd, item, "nout")
            if not isinstance(block, SourceBlock):
                raise TypeError(f"input {block.name} is not a source block")
            if block.type == "time":
                raise ValueError("TIME is not an input: it is the t argument")
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


@dataclass
class Linearization:
    r"""
    A local linear model of a block diagram, from
    :meth:`~bdsim.blockdiagram.BlockDiagram.linearize`.

    It unpacks as ``A, B, C, D``.

    :ivar A: :math:`\partial f / \partial x`, shape ``(nx, nx)``
    :ivar B: :math:`\partial f / \partial u`, shape ``(nx, nu)``
    :ivar C: :math:`\partial g / \partial x`, shape ``(ny, nx)``
    :ivar D: :math:`\partial g / \partial u`, shape ``(ny, nu)``
    :ivar f0: :math:`f(x, u, t)` at the operating point; zero at an equilibrium
    :ivar y0: :math:`g(x, u, t)` at the operating point
    :ivar x: state of the operating point
    :ivar u: input of the operating point
    :ivar t: time of the operating point
    :ivar error: estimated error of ``A, B, C, D``, or ``None`` if not requested
    :ivar xindex: rows and columns of ``A``, columns of ``C``
    :ivar uindex: columns of ``B`` and ``D``
    :ivar yindex: rows of ``C`` and ``D``

    The model is

    .. math::

        \frac{d}{dt}(\delta x) = A\,\delta x + B\,\delta u + f_0
    """

    A: NDArray
    B: NDArray
    C: NDArray
    D: NDArray
    f0: NDArray
    y0: NDArray
    x: NDArray
    u: NDArray
    t: float
    xindex: Index
    uindex: Index
    yindex: Index
    error: dict[str, NDArray] | None = field(default=None)

    def __iter__(self) -> Iterator[NDArray]:
        return iter((self.A, self.B, self.C, self.D))


class AnalysisMixin:
    """Methods of :class:`~bdsim.blockdiagram.BlockDiagram` that analyse it as a system.

    The attributes declared below are the ones these methods read; they are set
    by ``BlockDiagram``.
    """

    if TYPE_CHECKING:
        blocklist: list[Block]
        wirelist: list[Wire]
        compiled: bool

    def functions(
        self,
        inputs: list[Block | Plug | str] | None = None,
        outputs: list[Block | Plug | str] | None = None,
    ) -> SystemFunctions:
        r"""
        The diagram as the functions :math:`f` and :math:`g` of a nonlinear system

        :param inputs: the source blocks, or the outputs of them, that are the
            input :math:`u`, see below.  Defaults to every source block except
            ``TIME``.
        :param outputs: the signals that are the output :math:`y`, see below.
            Defaults to the signal into every sink input.
        :return: the functions, which unpack as ``f, g``
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

        The returned object also has ``nx``, ``nu`` and ``ny``, the initial
        state ``x0``, ``u_at(t)`` for the natural input at a time, and
        ``xindex``, ``uindex`` and ``yindex`` saying which elements belong to
        which block.

        The state of the blocks is as the last run left it.  After a run, for
        example, an integrator held at its limit is still held, so the model is
        that of the diagram at the end of the run.  A diagram that has not been
        run has its blocks reset first.  Do not call the functions during a
        simulation: they overwrite the values on the wires.

        :seealso: :meth:`linearize` :class:`~bdsim.analysis.SystemFunctions`
        """
        return SystemFunctions(self, inputs, outputs)

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
        :param full: return a :class:`~bdsim.analysis.Linearization`
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
        :math:`y_0`.

        The result has the form of the matrices of a linear time-invariant system
        and can be used directly to make a
        :class:`~bdsim.blocks.continuous.LTI_SS` block.  For control system
        design, including poles, stability and optimal control, see the
        python-control package, https://github.com/python-control/python-control,
        which takes the same ``(A, B, C, D)``.

        For example, to linearize at the end of a simulation::

            out = sim.run(bd, T=5)
            A, B, C, D = bd.linearize(out.x[-1])

        If the operating point is at a corner of a non-smooth block (a limit, a
        dead band, a switch) the derivative is not defined there.  The result is
        then the slope across the step; with ``estimate_error`` a warning says
        that the estimate is not reliable.

        :seealso: :meth:`functions` :class:`~bdsim.blocks.continuous.LTI_SS`
        """
        sysf = self.functions(inputs, outputs)

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
        f0, y0 = sysf.fg(x, u, t)

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
                y0=y0,
                x=x,
                u=u,
                t=t,
                xindex=sysf.xindex,
                uindex=sysf.uindex,
                yindex=sysf.yindex,
                error=error,
            )
        return A, B, C, D
