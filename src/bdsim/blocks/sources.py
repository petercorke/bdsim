"""
Source blocks:

- have outputs but no inputs
- have no state variables
- are a subclass of ``SourceBlock`` |rarr| ``Block``

"""

from __future__ import annotations

import numpy as np
import math
from typing import Any

from bdsim.components import EventSource, SourceBlock
from bdsim.signature import maybe_asarray, unify


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

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        return [self.value]


# ------------------------------------------------------------------------ #


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

    def __init__(self, value: Any | None = None, **blockargs: Any) -> None:
        """
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(**blockargs)

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        return [t]


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
        frequency: float
        if unit == "Hz":
            frequency = freq
        elif unit == "rad/s":
            frequency = freq / (2 * math.pi)
        else:
            raise ValueError("bad unit")
        self.freq: float = frequency
        if 0 <= phase <= 1:
            self.phase: float = phase
        else:
            raise ValueError("phase out of range")
        if max is not None and min is not None:
            amplitude = (max - min) / 2
            offset = (max + min) / 2
            self.min = min
            self.mablock = max
        if 0 <= duty <= 1:
            self.duty: float = duty
        else:
            raise ValueError("duty out of range")
        self.amplitude = amplitude
        self.offset = offset

    def start(self, simstate: Any) -> None:
        super().start(simstate)

        t1: float
        t2: float
        if self.wave == "square":
            t1 = self.phase / self.freq
            t2 = (self.duty + self.phase) / self.freq
        elif self.wave == "triangle":
            t1 = (0.25 + self.phase) / self.freq
            t2 = (0.75 + self.phase) / self.freq
        else:
            return

        # t1 < t2
        T: float = 1.0 / self.freq
        if simstate is not None:
            while t1 < simstate.tf:
                simstate.declare_event(self, t1)
                simstate.declare_event(self, t2)
                t1 += T
                t2 += T

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        phase = (t * self.freq - self.phase) % 1.0

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

        self.t = [x[0] for x in _seq]
        self.y = list(
            unify(
                *[maybe_asarray(x[1], asarray) for x in _seq],
                names=[f"seq[{i}] value" for i in range(len(_seq))],
            )
        )

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

    def start(self, simstate: Any) -> None:
        simstate.declare_event(self, self.T)

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

    def start(self, simstate: Any) -> None:
        simstate.declare_event(self, self.T)

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
