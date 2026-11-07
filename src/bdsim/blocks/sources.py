"""
Source blocks:

- have outputs but no inputs
- have no state variables
- are a subclass of ``SourceBlock`` |rarr| ``Block``

"""

from __future__ import annotations

import numpy as np
import math
from typing import TYPE_CHECKING, Any

from bdsim.components import EventSource, SourceBlock
from bdsim.signature import maybe_asarray, unify

if TYPE_CHECKING:
    from bdsim.analysis import Index
    from bdsim.components import Block, Clock


# ------------------------------------------------------------------------ #
class Constant(SourceBlock):
    """
    :blockname:`CONSTANT`

    Constant value.

    :inputs: 0
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Output
            - 0
            - any
            - constant ``value``

    The output value is a constant and can be any Python type, for example
    float, string or Numpy ndarray.

    **A** ``list`` **or** ``tuple`` **of numbers is converted to a Numpy**
    ``ndarray`` **by default, with dtype** ``int64`` **if the elements are all
    integers and** ``float64`` **if any is a float**, so ``CONSTANT([1, 2, 3])``
    is a vector of ``int64``.  Anything else, such as a list of strings or of
    objects, is emitted as given.  Other dtypes are chosen by passing an array,
    and a list of numbers is emitted as a list with ``asarray=False``::

        bd.CONSTANT([1, 2, 3])                   # int64 array
        bd.CONSTANT([1, 2.5])                    # float64 array
        bd.CONSTANT([1, 2, 3], asarray=False)    # the list [1, 2, 3]
        bd.CONSTANT(np.float32([1, 2, 3]))       # float32 array
    """

    nin = 0
    nout = 1
    _display_param = "value"  # shown in the label of an implicit block

    def __init__(self, value: Any = 0, asarray: bool = True, **blockargs: Any) -> None:
        """
        :param value: the constant, defaults to 0
        :type value: any, optional
        :param asarray: convert a list or tuple of numbers to an ``ndarray``
            of ``int64`` or ``float64``, defaults to True
        :type asarray: bool, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(**blockargs)

        self.value = maybe_asarray(value, asarray)

        self.add_param("value")
        self.add_param("asarray", when="never")

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        return [self.value]


# ------------------------------------------------------------------------ #


class _StateReader:
    """
    What STATE and STATE_S share: choosing blocks and reading their state.

    The state of every stateful block is in the diagram's state map, which
    ``BlockDiagram.evaluate`` sets before it executes any block, so a block can
    read it while the diagram is evaluated.  A subclass says which blocks have
    state to offer, in ``_candidates``, and how wide each block's state is.

    The blocks asked for are not parameters of the block: they say which parts
    of the diagram to read, as the inputs of a block say what is connected to it.
    They are named by block or by name, and resolved on first use, because a block
    named may be created after this one.
    """

    _not_an_input: str | None = "it is the state of the system, an argument of f and g"
    _reads_state: bool = True
    _blocks_arg: Block | str | list[Block | str] | None = None
    _selected: list[Block] | None = None

    def reset(self) -> None:
        self._selected = None  # the diagram may have changed since it was resolved
        super().reset()  # type: ignore[misc]

    def _candidates(self) -> list[Block]:
        raise NotImplementedError  # pragma: no cover

    def _width(self, block: Block) -> int:
        raise NotImplementedError  # pragma: no cover

    def _domain(self) -> str:
        raise NotImplementedError  # pragma: no cover

    def _blocks(self) -> list[Block]:
        """The blocks whose state is the output, in the order of the output."""
        if self._selected is None:
            self._selected = self._resolve()
        return self._selected

    def _resolve(self) -> list[Block]:
        candidates = self._candidates()
        arg = self._blocks_arg
        if arg is None:
            selected = list(candidates)
        else:
            items = list(arg) if isinstance(arg, (list, tuple)) else [arg]
            selected = []
            for item in items:
                if isinstance(item, str):
                    try:
                        block = self.bd[item]  # type: ignore[attr-defined]
                    except KeyError:
                        raise ValueError(
                            f"{self.name}: no block named {item!r}"  # type: ignore[attr-defined]
                        ) from None
                else:
                    block = item
                if not any(block is c for c in candidates):
                    raise ValueError(
                        f"{self.name}: {getattr(block, 'name', block)!r} has no "  # type: ignore[attr-defined]
                        f"{self._domain()} in this diagram"
                    )
                if any(block is b for b in selected):
                    raise ValueError(
                        f"{self.name}: {block.name!r} is given twice"  # type: ignore[attr-defined]
                    )
                selected.append(block)
        if not selected:
            raise ValueError(
                f"{self.name}: the diagram has no {self._domain()}"  # type: ignore[attr-defined]
            )
        return selected

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        state_map = self.bd._state_map  # type: ignore[attr-defined]
        return [
            np.concatenate(
                [
                    np.asarray(state_map[b], dtype=float).reshape(-1)
                    for b in self._blocks()
                ]
            )
        ]

    @property
    def index(self) -> Index:
        """
        Which elements of the output belong to which block.

        :return: an :class:`~bdsim.analysis.Index`, the same kind of object that
            ``bd.functions()`` and ``bd.linearize()`` use for the state ``x``
        """
        from bdsim.analysis import Index

        return Index.of_states(self._blocks(), self._width)

    @property
    def statenames(self) -> list[str]:
        """
        The name of every element of the output, in order.

        :return: a list of names: those a block gave its states, with ``snames``,
            and otherwise a block's own name if it has one state and ``name[k]`` for
            the ``k``-th of several
        """
        return self.index.names


class Time(SourceBlock):
    """
    :blockname:`TIME`

    Simulation time.

    :inputs: 0
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Output
            - 0
            - float
            - :math:`t`

    Outputs the current simulation time.

    For example::

        time = bd.TIME()
    """

    nin = 0
    nout = 1
    _not_an_input = "it is the t argument"

    def __init__(self, value: Any | None = None, **blockargs: Any) -> None:
        """
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(**blockargs)
        self.add_param("value", when="never")  # accepted and ignored

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        return [t]


# ------------------------------------------------------------------------ #


class State(_StateReader, SourceBlock):
    r"""
    :blockname:`STATE`

    Continuous state of the system.

    :inputs: 0
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Output
            - 0
            - ndarray(n)
            - :math:`x(t)`

    Outputs the state vector :math:`x` of the diagram, which is what state
    feedback needs.  For example, to apply the force :math:`F = -K x` to a cart
    and pole with a gain matrix :math:`K` from linear quadratic regulator (LQR)
    design::

        F = -K * bd.STATE()

    **What the state is.**  A block that has continuous state, such as an
    ``INTEGRATOR`` or an ``LTI_SS``, contributes its state to the state vector
    of the diagram, and this is the vector that the solver advances.  The
    blocks contribute in the order they were added to the diagram, so the output
    is in the same order as ``bd.statenames``, and as the states of
    :meth:`~bdsim.BlockDiagram.functions` and
    :meth:`~bdsim.BlockDiagram.linearize`.  A gain matrix designed
    from the ``A`` and ``B`` of ``linearize`` therefore applies directly to this
    output.  The output of an integrator is its state, so this block gives the
    same signal as a ``MUX`` of the integrators, in a guaranteed order.

    If the controller has states of its own, such as an integrator added for
    integral action, they are also in the diagram's state.  To read only the
    states of the plant, list its blocks, by block or by name, in the order
    that suits the gain matrix::

        x = bd.STATE([x_dot, x, theta_dot, theta])
        x = bd.STATE(["x_dot", "x", "theta_dot", "theta"])

    **Checking the state.**  The block reports what its output is made of.
    After the diagram is compiled::

        x = bd.STATE()
        x.statenames   # ['x_dot', 'x', 'theta_dot', 'theta']
        x.index        # which slice of the output belongs to which block

    ``bd.statenames`` gives the state names of the whole diagram.

    This is the state of the simulation, a perfect and instantaneous
    measurement.  It does not exist on hardware, where a controller uses sensors
    or an estimator, and it is not offered as an input of ``functions()`` or
    ``linearize()``: the state is the argument ``x`` of those functions.

    .. note:: The output is a vector, so ``K * x`` with a NumPy matrix ``K``
        makes a ``GAIN`` block that multiplies it.  A single state is a scalar,
        as for any size-1 signal.

    :param blocks: blocks, or their names, whose state to output, in this order,
        defaults to the continuous states of every block in the diagram
    :type blocks: block, str, or list of block or str, optional

    :seealso: :meth:`~bdsim.BlockDiagram.linearize`
        :meth:`~bdsim.BlockDiagram.functions`
        :class:`~bdsim.blocks.sources.State_S` :class:`~bdsim.blocks.sources.Time`
    """

    nin = 0
    nout = 1

    def __init__(
        self, blocks: Block | str | list[Block | str] | None = None, **blockargs: Any
    ) -> None:
        """
        :param blocks: blocks, or their names, whose state to output, in this
            order, defaults to the continuous states of every block
        :type blocks: block, str, or list of block or str, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(**blockargs)
        # not a parameter: which blocks to read is structure, like a connection
        self._blocks_arg = blocks
        self._selected = None

    def _candidates(self) -> list[Block]:
        return list(self.bd.xindex)

    def _width(self, block: Block) -> int:
        return block.nstates

    def _domain(self) -> str:
        return "continuous state"


# ------------------------------------------------------------------------ #


class State_S(_StateReader, SourceBlock):
    r"""
    :blockname:`STATE_S`

    Discrete-time state of the system.

    :inputs: 0
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Output
            - 0
            - ndarray(n)
            - :math:`X(k)`

    Outputs the discrete-time state vector :math:`X` of the blocks that run on a
    clock, for example the state of an observer or a digital controller.  For
    example::

        clock = bd.clock(0.01)
        X = bd.STATE_S(clock)

    **What the state is.**  A clocked block such as ``INTEGRATOR_S``, ``ZOH`` or
    ``LTI_SS_S`` has discrete state that changes only at the ticks of its clock.
    The output is the state of the blocks on the clock, in the order they were
    added to it, which is the order of ``clock.statenames``.  Between ticks it
    is the state after the most recent tick, and before the first tick it is
    the initial state.

    To read only some of the clock's blocks, list them, by block or by name, in
    the order wanted::

        X = bd.STATE_S(clock, [observer])

    To feed the continuous state of a plant to a digital controller, sample it
    with a ``ZOH`` on the same clock, ``bd.ZOH(clock)`` applied to
    ``bd.STATE()``; this block is for the state that belongs to the discrete
    time blocks.

    **Checking the state.**  After the diagram is compiled::

        X.statenames   # the name of each element of the output
        X.index        # which slice of the output belongs to which block

    Like ``STATE``, this is a perfect and instantaneous measurement of the
    simulation, and is not offered as an input of ``functions()`` or
    ``linearize()``.

    :param clock: the clock whose blocks' state is output
    :type clock: Clock
    :param blocks: blocks on the clock, or their names, whose state to output, in
        this order, defaults to every block on the clock
    :type blocks: block, str, or list of block or str, optional

    :seealso: :class:`~bdsim.blocks.sources.State`
        :meth:`~bdsim.BlockDiagram.linearize`
        :class:`~bdsim.blocks.sampled.ZOH`
    """

    nin = 0
    nout = 1

    def __init__(
        self,
        clock: Clock,
        blocks: Block | str | list[Block | str] | None = None,
        **blockargs: Any,
    ) -> None:
        """
        :param clock: the clock whose blocks' state is output
        :type clock: Clock
        :param blocks: blocks on the clock, or their names, whose state to output,
            in this order, defaults to every block on the clock
        :type blocks: block, str, or list of block or str, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(**blockargs)
        self.clock = clock
        self.add_param("clock", when="never")
        # not a parameter: which blocks to read is structure, like a connection
        self._blocks_arg = blocks
        self._selected = None

    def _candidates(self) -> list[Block]:
        return list(self.clock.blocklist)

    def _width(self, block: Block) -> int:
        return block.ndstates

    def _domain(self) -> str:
        return f"discrete state on clock {self.clock.name}"


# ------------------------------------------------------------------------ #


class WaveForm(SourceBlock, EventSource):
    """
    :blockname:`WAVEFORM`

    Waveform generator.

    :inputs: 0
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Output
            - 0
            - float
            - :math:`y(t)`

    A general waveform generator.  For example::

        wave = bd.WAVEFORM(wave='sine', freq=2)   # 2Hz sine wave varying from -1 to 1
        wave = bd.WAVEFORM(wave='square', freq=2, unit='rad/s') # 2rad/s square wave varying from -1 to 1

    The minimum and maximum values of the waveform are given by default in
    terms of amplitude and offset. The signals are symmetric about the offset
    value. For example::

        wave = bd.WAVEFORM(wave='sine') # varies between -1 and +1
        wave = bd.WAVEFORM(wave='sine', amplitude=2) # varies between -2 and +2
        wave = bd.WAVEFORM(wave='sine', offset=1) # varies between 0 and +2
        wave = bd.WAVEFORM(wave='sine', amplitude=2, offset=1) # varies between -1 and +3

    Alternatively we can specify the minimum and maximum values which override
    amplitude and offset::

        wave = bd.WAVEFORM(wave='triangle', min=0, max=5) # varies between 0 and +5

    At time 0 the sine and triangle wave are zero and increasing, and the
    square wave has its first rise.  We can specify a phase shift with
    a number in the range [0,1] where 1 corresponds to one cycle.

    .. note:: For discontinuous signals (square, triangle) the block declares
        events for every discontinuity.

    :seealso: :meth:`declare_events`
    """

    nin = 0
    nout = 1

    def __init__(
        self,
        wave: str = "square",
        freq: float = 1,
        unit: str = "Hz",
        phase: float = 0,
        amplitude: float = 1,
        offset: float = 0,
        min: float | None = None,
        max: float | None = None,
        duty: float = 0.5,
        **blockargs: Any,
    ) -> None:
        """
        :param wave: type of waveform to generate, one of: 'sine', 'square' [default], 'triangle'
        :type wave: str, optional
        :param freq: frequency, defaults to 1
        :type freq: float, optional
        :param unit: frequency unit, one of: 'rad/s', 'Hz' [default]
        :type unit: str, optional
        :param amplitude: amplitude, defaults to 1
        :type amplitude: float, optional
        :param offset: signal offset, defaults to 0
        :type offset: float, optional
        :param phase: Initial phase of signal in the range [0,1], defaults to 0
        :type phase: float, optional
        :param min: minimum value, defaults to None
        :type min: float, optional
        :param max: maximum value, defaults to None
        :type max: float, optional
        :param duty: duty cycle for square wave in range [0,1], defaults to 0.5
        :type duty: float, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict

        """
        super().__init__(**blockargs)

        if not (0 < duty < 1):
            raise ValueError("duty must be in range [0,1]")

        if wave in ("square", "triangle", "sine"):
            self.wave: str = wave
        else:
            raise ValueError("bad waveform")
        if unit not in ("Hz", "rad/s"):
            raise ValueError("bad unit")
        self.unit = unit
        self.freq = freq
        if 0 <= phase <= 1:
            self.phase: float = phase
        else:
            raise ValueError("phase out of range")
        if max is not None and min is not None:
            amplitude = (max - min) / 2
            offset = (max + min) / 2
        if 0 <= duty <= 1:
            self.duty: float = duty
        else:
            raise ValueError("duty out of range")
        self.amplitude = amplitude
        self.offset = offset
        self.add_param("wave", when="setup")
        self.add_param("freq", when="setup", validate=self._check_freq)
        self.add_param("unit", when="never")
        self.add_param("phase", when="setup")
        self.add_param("amplitude")
        self.add_param("offset")
        self.add_param("min")
        self.add_param("max")
        self.add_param("duty", when="setup")

    @staticmethod
    def _check_freq(value: float) -> None:
        if value <= 0:
            raise ValueError("freq must be positive")

    @property
    def freq(self) -> float:
        """Frequency, in ``unit``."""
        return self._hz if self.unit == "Hz" else self._hz * (2 * math.pi)

    @freq.setter
    def freq(self, value: float) -> None:
        self._hz = value if self.unit == "Hz" else value / (2 * math.pi)

    @property
    def min(self) -> float:
        """Minimum value of the signal, derived from ``amplitude`` and ``offset``."""
        return self.offset - self.amplitude

    @min.setter
    def min(self, value: float) -> None:
        self._set_range(value, self.max)

    @property
    def max(self) -> float:
        """Maximum value of the signal, derived from ``amplitude`` and ``offset``."""
        return self.offset + self.amplitude

    @max.setter
    def max(self, value: float) -> None:
        self._set_range(self.min, value)

    def _set_range(self, lo: float, hi: float) -> None:
        if lo >= hi:
            raise ValueError(f"min ({lo}) must be less than max ({hi})")
        self.amplitude = (hi - lo) / 2
        self.offset = (hi + lo) / 2

    def start(self, simstate: Any) -> None:
        super().start(simstate)

        t1: float
        t2: float
        if self.wave == "square":
            t1 = self.phase / self._hz
            t2 = (self.duty + self.phase) / self._hz
        elif self.wave == "triangle":
            t1 = (0.25 + self.phase) / self._hz
            t2 = (0.75 + self.phase) / self._hz
        else:
            return

        # t1 < t2
        T: float = 1.0 / self._hz
        if simstate is not None:
            while t1 < simstate.tf:
                simstate.declare_event(self, t1)
                simstate.declare_event(self, t2)
                t1 += T
                t2 += T

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        phase = (t * self._hz - self.phase) % 1.0

        # define all signals in the range -1 to 1
        out: float
        if self.wave == "square":
            if phase < self.duty:
                out = 1
            else:
                out = -1
        elif self.wave == "triangle":
            if phase < 0.25:
                out = phase * 4
            elif phase < 0.75:
                out = 1 - 4 * (phase - 0.25)
            else:
                out = -1 + 4 * (phase - 0.75)
        elif self.wave == "sine":
            out = math.sin(phase * 2 * math.pi)
        else:
            raise ValueError("bad option for signal")

        out = out * self.amplitude + self.offset

        # print('waveform = ', out)
        return [out]


# ------------------------------------------------------------------------ #


class Piecewise(SourceBlock, EventSource):
    """
    :blockname:`PIECEWISE`

    Piecewise constant signal.

    :inputs: 0
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Output
            - 0
            - float
            - :math:`y(t)`

    Generate a signal that is a piecewise constant function of time.  This is described
    as a series of 2-tuples (time, value).  The output value is taken from the active
    tuple, that is, the latest one in the list whose time is no greater than simulation
    time.

    The tuples can be provided in two different ways.  Firstly, a form convenient for
    Python programming::

        steering = bd.PIECEWISE((0,0), (2, 0.5), (3,0), (4,-0.5), (5,0))

    Secondly, in a form that can be used from ``bdsim`` where we explicitly pass
    in a list in a way that can be represented in a JSON file::

        steering = bd.PIECEWISE(seq=[(0,0), (3, 0.5), (4,0), (5,-0.5), (6,0)])

    .. plot::

        import matplotlib.pyplot as plt
        plt.plot([0, 2, 2,   3,   3, 4,   4,   5,   5, 5.2],
                 [0, 0, 0.5, 0.5, 0, 0, -0.5, -0.5, 0, 0], lw=2)
        plt.grid(True)

    .. note::
        - The tuples must be ordered by monotonically increasing time.
        - There is no default initial value, the list should contain
          a tuple with time zero otherwise the output will be undefined.

    .. note:: The block declares an event for the start of each segment.

    :seealso: :meth:`declare_events`
    """

    nin = 0
    nout = 1

    def __init__(
        self,
        *args: tuple[float, float],
        seq: list[tuple[float, float]] | None = None,
        asarray: bool = True,
        **blockargs: Any,
    ) -> None:
        """
        :param seq: sequence of time, value pairs
        :type seq: list of 2-element iterables
        :param asarray: convert a list or tuple of numbers used as a value to an
            ``ndarray`` of ``int64`` or ``float64``, defaults to True
        :type asarray: bool, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict

        """
        super().__init__(**blockargs)

        _seq: tuple[tuple[float, float], ...] | list[tuple[float, float]] | None
        if len(args) > 0:
            _seq = args
        else:
            _seq = seq

        if _seq is None:
            raise ValueError("no sequence provided")

        self.asarray = asarray
        self.seq = _seq
        self.add_param("seq", coerce=False)
        self.add_param("asarray", when="never")

    @property
    def seq(self) -> list[tuple[float, Any]]:
        """The (time, value) pairs, in order of time."""
        return list(zip(self.t, self.y))

    @seq.setter
    def seq(self, value: Any) -> None:
        pairs = list(value)
        if any(len(pair) != 2 for pair in pairs):
            raise ValueError("seq must be a sequence of (time, value) pairs")
        times = [pair[0] for pair in pairs]
        if any(b < a for a, b in zip(times, times[1:])):
            raise ValueError("the times in seq must not decrease")
        names = [f"seq[{i}] value" for i in range(len(pairs))]
        values = [maybe_asarray(pair[1], self.asarray) for pair in pairs]
        old = getattr(self, "y", None)
        if old:
            # stay of the type the output has already been seen to have
            values = list(unify(old[0], *values, names=["current", *names]))[1:]
        else:
            values = list(unify(*values, names=names))
        self.t, self.y = times, values

    def start(self, simstate: Any) -> None:
        super().start(simstate)

        if simstate is not None:
            for t in self.t:
                simstate.declare_event(self, t)

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        i: int = sum([1 if t >= _t else 0 for _t in self.t]) - 1
        out = self.y[i]
        # print(out)
        return [out]


# ------------------------------------------------------------------------ #


def _promote_pair(block: Any, name: str, partner: str, value: Any) -> Any:
    """
    Check a new value against the parameter it is paired with, and promote both.

    :param block: the block
    :param name: the parameter being set
    :param partner: the parameter it must stay consistent with
    :param value: the new value of ``name``
    :return: the new value, promoted to a common type with the partner
    :raises TypeError: the two are of different types
    :raises ValueError: the two are arrays of different shape or dtype

    The values of a ``Step`` or ``Ramp`` are the signal itself, so they must stay one
    type (:func:`~bdsim.signature.unify`).  If setting one from an integer to a float
    promotes the pair, the partner follows, otherwise neither could ever be changed
    without the other.
    """
    new, other = unify(value, getattr(block, partner), names=(name, partner))
    setattr(block, partner, other)
    return new


class Step(SourceBlock, EventSource):
    """
    :blockname:`STEP`

    Step signal.

    :inputs: 0
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Output
            - 0
            - float
            - :math:`y(t)`

    Generate a step signal that transitions from the value ``off`` to ``on`` when time
    equals ``T``.

    Example:

        step = bd.STEP(2, off=-1, on=1)

    .. plot::

        import matplotlib.pyplot as plt
        plt.plot([0, 2, 2, 5], [-1, -1, 1, 1], lw=2)
        plt.grid(True)

    .. note:: The block declares an event for the step time.

    :seealso: :meth:`declare_events`
    """

    nin = 0
    nout = 1

    def __init__(
        self,
        T: float = 1,
        off: Any = 0,
        on: Any = 1,
        asarray: bool = True,
        **blockargs: Any,
    ) -> None:
        """
        :param T: time of step, defaults to 1
        :type T: float, optional
        :param off: initial value, defaults to 0
        :type off: any, optional
        :param on: final value, defaults to 1
        :type on: any, optional
        :param asarray: convert a list or tuple of numbers to an ``ndarray`` of
            ``int64`` or ``float64``, defaults to True
        :type asarray: bool, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        :raises TypeError: ``off`` and ``on`` are of different types
        :raises ValueError: ``off`` and ``on`` are arrays with different shape or dtype

        The output is always of one type.  ``off`` and ``on`` can be any Python
        object, but must be the same type, for example two arrays or two
        strings.  **A list or tuple of numbers is first converted to an**
        ``ndarray`` **of** ``int64`` **or** ``float64`` (see ``asarray``).  Numbers are promoted to a common type, so
        ``off=0, on=1.0`` gives ``0.0`` and ``1.0``.  A bool cannot be mixed
        with a number.
        """
        super().__init__(**blockargs)

        self.T: float = T
        self.off, self.on = unify(
            maybe_asarray(off, asarray),
            maybe_asarray(on, asarray),
            names=("off", "on"),
        )
        self.add_param("T", when="setup")
        self.add_param("off", validate=self._check_off)
        self.add_param("on", validate=self._check_on)
        self.add_param("asarray", when="never")

    def start(self, simstate: Any) -> None:
        simstate.declare_event(self, self.T)

    def _check_off(self, value: Any) -> Any:
        return _promote_pair(self, "off", "on", value)

    def _check_on(self, value: Any) -> Any:
        return _promote_pair(self, "on", "off", value)

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[float]:
        out: float
        if t >= self.T:
            out = self.on
        else:
            out = self.off

        # print(out)
        return [out]


# ------------------------------------------------------------------------ #


class Ramp(SourceBlock, EventSource):
    """
    :blockname:`RAMP`

    Ramp signal.

    :inputs: 0
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Output
            - 0
            - float
            - :math:`y(t)`

    Generate a signal that starts increasing from the value ``off`` when time equals
    ``T`` linearly with time, with a gradient of ``slope``.

    Example:

        step = bd.RAMP(2, off=-1, slope=2/3, T=2)

    .. plot::

        import matplotlib.pyplot as plt
        plt.plot([0, 2, 5], [-1, -1, 5], lw=2)
        plt.grid(True)

    .. note:: The block declares an event for the ramp start time.

    :seealso: :meth:`declare_event`
    """

    nin = 0
    nout = 1

    def __init__(
        self, T: float = 1, off: float = 0, slope: float = 1, **blockargs: Any
    ) -> None:
        """
        :param T: time of ramp start, defaults to 1
        :type T: float, optional
        :param off: initial value, defaults to 0
        :type off: float, optional
        :param slope: gradient of slope, defaults to 1
        :type slope: float, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(**blockargs)

        off, slope = maybe_asarray(off), maybe_asarray(slope)
        unify(off, slope, names=("off", "slope"))  # same shape, or both numbers
        try:
            # off + slope * (t - T) is a float, so the output is a float before T too
            off = off + 0.0 * slope
        except TypeError as err:
            raise TypeError("off and slope must be numbers or arrays") from err

        self.T: float = T
        self.off = off
        self.slope = slope
        self.add_param("T", when="setup")
        self.add_param("off", validate=self._check_off)
        self.add_param("slope", validate=self._check_slope)

    def start(self, simstate: Any) -> None:
        simstate.declare_event(self, self.T)

    def _check_off(self, value: Any) -> Any:
        return _promote_pair(self, "off", "slope", value)

    def _check_slope(self, value: Any) -> Any:
        return _promote_pair(self, "slope", "off", value)

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        out: float | int
        if t >= self.T:
            out = self.off + self.slope * (t - self.T)
        else:
            out = self.off

        # print(out)
        return [out]


if __name__ == "__main__":  # pragma: no cover
    from pathlib import Path
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[3]
    test_file = (
        root / "tests" / "blocks" / f"test_blocks_{Path(__file__).stem.lower()}.py"
    )

    if not test_file.exists():
        print(f"No module unit tests found for {Path(__file__).name}: {test_file}")
        raise SystemExit(0)

    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", str(test_file)]))
