"""
Source blocks:

- have outputs but no inputs
- have no state variables
- are a subclass of ``SourceBlock`` |rarr| ``Block``

"""

import numpy as np
import math
from bdsim.components import SourceBlock, EventSource

# ------------------------------------------------------------------------ #
class Constant(SourceBlock):
    """
    :blockname:`CONSTANT`

    .. table::
       :align: left

    +--------+---------+---------+
    | inputs | outputs |  states |
    +--------+---------+---------+
    | 0      | 1       | 0       |
    +--------+---------+---------+
    |        | float,  |         |
    |        | A(N,)   |         |
    +--------+---------+---------+
    """

    nin = 0
    nout = 1

    def __init__(self, value=0, **blockargs):
        """
        Constant value.

        :param value: the constant, defaults to 0
        :type value: any, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a CONSTANT block
        :rtype: Constant instance

        This block has only one output port, but the value can be any
        Python type, for example float, list or Numpy ndarray.
        """
        super().__init__(**blockargs)

        if isinstance(value, (tuple, list)):
            value = np.array(value)
        self.value = value

        self.add_param("value")

    def output(self, t=None):
        return [self.value]


# ------------------------------------------------------------------------ #


class Time(SourceBlock):
    """
    :blockname:`TIME`

    .. table::
       :align: left

    +--------+---------+---------+
    | inputs | outputs |  states |
    +--------+---------+---------+
    | 0      | 1       | 0       |
    +--------+---------+---------+
    |        | float   |         |
    +--------+---------+---------+
    """

    nin = 0
    nout = 1

    def __init__(self, value=None, **blockargs):
        """
        Simulation time.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a TIME block
        :rtype: Time instance

        The block has only one output port which is the current simulation time.

        """
        super().__init__(**blockargs)

    def output(self, t=None):
        return [t]


# ------------------------------------------------------------------------ #


class WaveForm(SourceBlock, EventSource):
    """
    :blockname:`WAVEFORM`

    .. table::
       :align: left

    +--------+---------+---------+
    | inputs | outputs |  states |
    +--------+---------+---------+
    | 0      | 1       | 0       |
    +--------+---------+---------+
    |        | float   |         |
    +--------+---------+---------+
    """

    nin = 0
    nout = 1

    def __init__(
        self,
        wave="square",
        freq=1,
        unit="Hz",
        phase=0,
        amplitude=1,
        offset=0,
        min=None,
        max=None,
        duty=0.5,
        **blockargs,
    ):
        """
        Waveform as function of time.

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
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a WAVEFORM block
        :rtype: WaveForm instance

        Create a waveform generator block.

        Examples::

            WAVEFORM(wave='sine', freq=2)   # 2Hz sine wave varying from -1 to 1
            WAVEFORM(wave='square', freq=2, unit='rad/s') # 2rad/s square wave varying from -1 to 1

        The minimum and maximum values of the waveform are given by default in
        terms of amplitude and offset. The signals are symmetric about the offset
        value. For example::

            WAVEFORM(wave='sine') varies between -1 and +1
            WAVEFORM(wave='sine', amplitude=2) varies between -2 and +2
            WAVEFORM(wave='sine', offset=1) varies between 0 and +2
            WAVEFORM(wave='sine', amplitude=2, offset=1) varies between -1 and +3

        Alternatively we can specify the minimum and maximum values which override
        amplitude and offset::

            WAVEFORM(wave='triangle', min=0, max=5) varies between 0 and +5

        At time 0 the sine and triangle wave are zero and increasing, and the
        square wave has its first rise.  We can specify a phase shift with
        a number in the range [0,1] where 1 corresponds to one cycle.

        .. note:: For discontinuous signals (square, triangle) the block declares
            events for every discontinuity.

        :seealso :meth:`declare_events`
        """
        super().__init__(**blockargs)

        assert 0 < duty < 1, "duty must be in range [0,1]"

        if wave in ("square", "triangle", "sine"):
            self.wave = wave
        else:
            raise ValueError("bad waveform")
        if unit == "Hz":
            self.freq = freq
        elif unit == "rad/s":
            self.freq = freq / (2 * math.pi)
        else:
            raise ValueError("bad unit")
        if 0 <= phase <= 1:
            self.phase = phase
        else:
            raise ValueError("phase out of range")
        if max is not None and min is not None:
            amplitude = (max - min) / 2
            offset = (max + min) / 2
            self.min = min
            self.mablock = max
        if 0 <= duty <= 1:
            self.duty = duty
        else:
            raise ValueError("duty out of range")
        self.amplitude = amplitude
        self.offset = offset

    def start(self, state=None):
        if self.wave == "square":
            t1 = self.phase / self.freq
            t2 = (self.duty + self.phase) / self.freq
        elif self.wave == "triangle":
            t1 = (0.25 + self.phase) / self.freq
            t2 = (0.75 + self.phase) / self.freq
        else:
            return

        # t1 < t2
        T = 1.0 / self.freq
        while t1 < self.bd.simstate.T:
            self.bd.simstate.declare_event(self, t1)
            self.bd.simstate.declare_event(self, t2)
            t1 += T
            t2 += T

    def output(self, t=None):
        T = 1.0 / self.freq
        phase = (t * self.freq - self.phase) % 1.0

        # define all signals in the range -1 to 1
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

    .. table::
       :align: left

    +--------+---------+---------+
    | inputs | outputs |  states |
    +--------+---------+---------+
    | 0      | 1       | 0       |
    +--------+---------+---------+
    |        | float   |         |
    +--------+---------+---------+
    """

    nin = 0
    nout = 1

    def __init__(self, *seq, **blockargs):
        """
        Piecewise constant signal.

        :param seq: sequence of time, value pairs
        :type seq: list of 2-tuples
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a PIECEWISE block
        :rtype: Piecewise instance

        Outputs a piecewise constant function of time.  This is described as
        a series of 2-tuples (time, value).  The output value is taken from the
        active tuple, that is, the latest one in the list whose time is no greater
        than simulation time.

        .. note::
            - The tuples must be order by monotonically increasing time.
            - There is no default initial value, the list should contain
              a tuple with time zero otherwise the output will be undefined.

        .. note:: The block declares an event for the start of each segment.

        :seealso: :meth:`declare_events`
        """
        super().__init__(**blockargs)

        self.t = [x[0] for x in seq]
        self.y = [x[1] for x in seq]

    def start(self, state=None):
        for t in self.t:
            state.declare_event(self, t)

    def output(self, t):
        i = sum([1 if t >= _t else 0 for _t in self.t]) - 1
        out = self.y[i]
        # print(out)
        return [out]


# ------------------------------------------------------------------------ #


class Step(SourceBlock, EventSource):
    """
    :blockname:`STEP`

    .. table::
       :align: left

    +--------+---------+---------+
    | inputs | outputs |  states |
    +--------+---------+---------+
    | 0      | 1       | 0       |
    +--------+---------+---------+
    |        | float   |         |
    +--------+---------+---------+
    """

    nin = 0
    nout = 1

    def __init__(self, T=1, off=0, on=1, **blockargs):
        """
        Step signal.

        :param T: time of step, defaults to 1
        :type T: float, optional
        :param off: initial value, defaults to 0
        :type off: float, optional
        :param on: final value, defaults to 1
        :type on: float, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a STEP block
        :rtype: Step

        Output a step signal that transitions from the value ``off`` to ``on``
        when time equals ``T``.

        .. note:: The block declares an event for the step time.

        :seealso: :meth:`declare_events`
        """
        super().__init__(**blockargs)

        self.T = T
        self.off = off
        self.on = on

    def start(self, state=None):
        state.declare_event(self, self.T)

    def output(self, t=None):
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

    .. table::
       :align: left

    +--------+---------+---------+
    | inputs | outputs |  states |
    +--------+---------+---------+
    | 0      | 1       | 0       |
    +--------+---------+---------+
    |        | float   |         |
    +--------+---------+---------+
    """

    nin = 0
    nout = 1

    def __init__(self, T=1, off=0, slope=1, **blockargs):

        """
        Ramp signal.

        :param T: time of ramp start, defaults to 1
        :type T: float, optional
        :param off: initial value, defaults to 0
        :type off: float, optional
        :param slope: gradient of slope, defaults to 1
        :type slope: float, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a RAMP block
        :rtype: Ramp

        Output a ramp signal that starts increasing from the value ``off``
        when time equals ``T`` linearly with time, with a gradient of ``slope``.

        .. note:: The block declares an event for the ramp start time.

        :seealso: :method:`declare_event`
        """
        super().__init__(**blockargs)

        self.T = T
        self.off = off
        self.slope = slope

    def start(self, state=None):
        state.declare_event(self, self.T)

    def output(self, t=None):
        if t >= self.T:
            out = self.off + self.slope * (t - self.T)
        else:
            out = self.off

        # print(out)
        return [out]


if __name__ == "__main__":  # pragma: no cover

    from pathlib import Path

    exec(open(Path(__file__).parent.parent.parent / "tests" / "test_sources.py").read())
