"""
Define source blocks for use in block diagrams.  These are blocks that:

- have outputs but no inputs
- have no state variables
- are a subclass of ``SourceBlock``

Each class MyClass in this module becomes a method MYCLASS() of the Simulation object.
"""

import numpy as np
import math

from bdsim.components import SourceBlock, block


# ------------------------------------------------------------------------ #
@block
class Constant(SourceBlock):
    
    def __init__(self, value=None, **kwargs):
        """
        Create a constant block.
        
        :param value: the constant, defaults to None
        :type value: any
        :param ``**kwargs``: common Block options
        :return: a CONSTANT block
        :rtype: Constant instance
        
        This block has only one output port, but the value can be any 
        Python type, so long as the connected input port can handle it.
        For example float, list or numpy ndarray.

        """
        super().__init__(nout=1, **kwargs)
        
        if isinstance(value, (tuple, list)):
            value = np.array(value)
        self.value = value
        self.type = 'constant'

    def output(self, t=None):
        return [self.value]               

# ------------------------------------------------------------------------ #

@block
class WaveForm(SourceBlock):
    def __init__(self, wave='square',
                 freq=1, unit='Hz', phase=0, amplitude=1, offset=0,
                 min=None, max=None, duty=0.5,
                 **kwargs):
        """
        Create a waveform generator block.
        
        :param wave: type of waveform to generate: 'sine', 'square' [default], 'triangle'
        :type wave: str, optional
        :param freq: frequency, defaults to 1
        :type freq: float, optional
        :param unit: frequency unit, can be 'rad/s', defaults to 'Hz'
        :type unit: str, optional
        :param amplitude: amplitude, defaults to 1
        :type amplitude: float, optional
        :param offset: signal offset, defaults to 0
        :type offset: float, optional
        :param phase: Initial phase of signal in the range [0,1], defaults to 0
        :type phase: float, optional
        :param min: minimum value, defaults to 0
        :type min: float, optional
        :param max: maximum value, defaults to 1
        :type max: float, optional
        :param duty: duty cycle for square wave in range [0,1], defaults to 0.5
        :type duty: float, optional
        :param ``**kwargs``: common Block options
        :return: a WAVEFORM block
        :rtype: WaveForm instance
        
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
        
        """
        super().__init__(nout=1, **kwargs)

        assert 0<duty<1, 'duty must be in range [0,1]'
        
        self.wave = wave
        if unit == 'Hz':
            self.freq = freq
        elif unit == 'rad/s':
            self.freq = freq / (2 * math.pi)
        self.phase = phase
        if max is not None and min is not None:
            amplitude = (max - min) / 2
            offset = (max + min) / 2 
            self.min = min
            self.mablock = max
        self.duty = duty
        self.amplitude = amplitude
        self.offset = offset
        self.type = 'waveform'

    def output(self, t=None):
        T = 1.0 / self.freq
        phase = (t * self.freq - self.phase ) % 1.0
        
        # define all signals in the range -1 to 1
        if self.wave == 'square':
            if phase < self.duty:
                out = 1
            else:
                out = -1
        elif self.wave == 'triangle':
            if phase < 0.25:
                out = phase * 4
            elif phase < 0.75:
                out = 1 - 4 * (phase - 0.25)
            else:
                out = -1 + 4 * (phase - 0.75)
        elif self.wave == 'sine':
            out = math.sin(phase*2*math.pi)
        else:
            raise ValueError('bad option for signal')

        out = out * self.amplitude + self.offset

        #print('waveform = ', out)
        return [out]

# ------------------------------------------------------------------------ #

@block
class Piecewise(SourceBlock):
    def __init__(self, *seq, **kwargs):
        """
        Create a piecewise constant signal block.
        
        :param ``*seq``: Sequence of time, value pairs
        :type ``*seq``: list of 2-tuples
        :param ``**kwargs``: common Block options
        :return: a PIECEWISE block
        :rtype: Piecewise instance
        
        Outputs a piecewise constant function of time.  This is described as
        a series of 2-tupes (time, value).  The output value is taken from the
        active tuple, that is, the latest one in the list whose time is no greater
        than simulation time.
        
        Note that there is no default initial value, the list should contain
        a tuple with time zero otherwise the output will be undefined.

        """
        super().__init__(nout=1, **kwargs)
        
        self.t = [ x[0] for x in seq]
        self.y = [ x[1] for x in seq]
        self.type = "piecewise"

    def output(self, t):
        i = sum([ 1 if t >= _t else 0  for _t in self.t]) - 1
        out = self.y[i]
        #print(out)
        return [out]
    
# ------------------------------------------------------------------------ #

@block
class Step(SourceBlock):
    def __init__(self, T=1,
                 off=0, on=1,
                 **kwargs):
        """
        Create a step signal block.
        
        :param T: time of step, defaults to 1
        :type T: float, optional
        :param off: initial value, defaults to 0
        :type off: float, optional
        :param on: final value, defaults to 1
        :type on: float, optional
        :param ``**kwargs``: common Block options
        :return: a STEP block
        :rtype: Step
        
        Output a step signal that transitions from the value ``off`` to ``on``
        when time equals ``T``.

        """
        super().__init__(nout=1, **kwargs)
        
        self.T = T
        self.off = off
        self.on = on
        self.type = "step"

    def output(self, t=None):
        if t >= self.T:
            out = self.on
        else:
            out = self.off

        #print(out)
        return [out]


if __name__ == "__main__":

    import pathlib
    import os.path

    exec(open(os.path.join(pathlib.Path(__file__).parent.absolute(), "test_sources.py")).read())
