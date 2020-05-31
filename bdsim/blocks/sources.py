#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Define fundamental blocks available for use in block diagrams.

Each class _MyClass in this module becomes a method MYCLASS() of the Simulation object.
This is done in Simulation.__init__()

All arguments to MYCLASS() must be named arguments and passed through to the constructor
_MyClass.__init__().

These classses must subclass one of

- Source, output is a constant or function of time
- Sink, input only
- Transfer, output is a function of state self.x (no pass through)
- Function, output is a direct function of input

These classes all subclass Block.

Every class defined here provides several methods:
    
- __init__, mandatory to handle block specific parameter arguments
- reset, 
- output, to compute the output value as a function of self.inputs which is 
  a dict indexed by input number
- deriv, for Transfer subclass only, return the state derivative vector
- check, to validate parameter settings

Created on Thu May 21 06:39:29 2020

@author: Peter Corke
"""
import numpy as np
import math

from bdsim.components import *

print('in sources')

# ------------------------------------------------------------------------ #
@block
class _Constant(Source):
    
    def __init__(self, value=None, **kwargs):
        """
        Create a constant block.
        
        :param value: the constant, defaults to None
        :type value: any
        :param **kwargs: common Block options
        :return: a STEP block
        :rtype: _Constant
        
        This block has only one output port, but the value can be any 
        Python type, so long as the connected input port can handle it.
        For example float, list or numpy ndarray.

        """
        super().__init__(**kwargs)
        self.value = [value]
        self.type = 'constant'

    def output(self, t=None):
        return self.value               

# ------------------------------------------------------------------------ #

@block
class _WaveForm(Source):
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
        :param **kwargs: common Block options
        :return: a STEP block
        :rtype: _Step
        
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
        super().__init__(**kwargs)

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

# class _Pulse(Source):
#     def __init__(self, T=1, width=1,
#                  off=0, on=1,
#                  **kwargs):
#         super().__init__(**kwargs)
        
#         self.t_on = T
#         self.t_off =T + width
#         self.off = off
#         self.on = on
#         self.type = "pulsegen"

#     def output(self, t):
#         if self.t_on <= t <= self.t_off:
#             out = self.on
#         else:
#             out = self.off

#         #print(out)
#         return [out]
    
# ------------------------------------------------------------------------ #

@block
class _Step(Source):
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
        :param **kwargs: common Block options
        :return: a STEP block
        :rtype: _Step

        """
        super().__init__(**kwargs)
        
        self.T = T
        self.off = off
        self.on = on
        self.type = "step"
        self.nout = 1

    def output(self, t=None):
        if t >= self.T:
            out = self.on
        else:
            out = self.off

        #print(out)
        return [out]


if __name__ == "__main__":


    import unittest
    import numpy.testing as nt

    class SourceBlockTest(unittest.TestCase):

        def test_constant(self):

            block = _Constant(value=7)
            out = block.output()
            self.assertIsInstance(out, list)
            self.assertEqual(len(out), 1)
            self.assertEqual(out[0], 7)

            block = _Constant(value=np.r_[1,2,3])
            out = block.output()
            self.assertIsInstance(out, list)
            self.assertEqual(len(out), 1)
            nt.assert_array_almost_equal(out[0], np.r_[1,2,3])

        def test_waveform_sine(self):

            block = _WaveForm(wave='sine')
            out = block.output(0)
            self.assertIsInstance(out, list)
            self.assertEqual(len(out), 1)
            self.assertAlmostEqual(out[0], 0)
            out = block.output(0.25)
            self.assertAlmostEqual(out[0], 1)
            out = block.output(0.75)
            self.assertAlmostEqual(out[0], -1)

            block = _WaveForm(wave='sine', amplitude=2)
            out = block.output(0)
            self.assertAlmostEqual(out[0], 0)
            out = block.output(0.25)
            self.assertAlmostEqual(out[0], 2)
            out = block.output(0.75)
            self.assertAlmostEqual(out[0], -2)

            block = _WaveForm(wave='sine', offset=1)
            out = block.output(0)
            self.assertAlmostEqual(out[0], 1)
            out = block.output(0.25)
            self.assertAlmostEqual(out[0], 2)
            out = block.output(0.75)
            self.assertAlmostEqual(out[0], 0)

            block = _WaveForm(wave='sine', amplitude=2, offset=1)
            out = block.output(0)
            self.assertAlmostEqual(out[0], 1)
            out = block.output(0.25)
            self.assertAlmostEqual(out[0], 3)
            out = block.output(0.75)
            self.assertAlmostEqual(out[0], -1)

            block = _WaveForm(wave='sine', min=10, max=12)
            out = block.output(0)
            self.assertAlmostEqual(out[0], 11)
            out = block.output(0.25)
            self.assertAlmostEqual(out[0], 12)
            out = block.output(0.75)
            self.assertAlmostEqual(out[0], 10)

            block = _WaveForm(wave='sine', phase=0.25)
            out = block.output(0)
            self.assertAlmostEqual(out[0], -1)
            out = block.output(0.25)
            self.assertAlmostEqual(out[0], 0)
            out = block.output(0.75)
            self.assertAlmostEqual(out[0], 0)

            block = _WaveForm(wave='sine', unit='rad/s')
            out = block.output(0)
            self.assertIsInstance(out, list)
            self.assertAlmostEqual(len(out), 1)
            self.assertAlmostEqual(out[0], 0)
            out = block.output(math.pi/2)
            self.assertAlmostEqual(out[0], 1)
            out = block.output(3/2*math.pi)
            self.assertAlmostEqual(out[0], -1)
            
        def test_waveform_triangle(self):

            block = _WaveForm(wave='triangle')
            out = block.output(0)
            self.assertIsInstance(out, list)
            self.assertEqual(len(out), 1)
            self.assertAlmostEqual(out[0], 0)
            out = block.output(0.25)
            self.assertAlmostEqual(out[0], 1)
            out = block.output(0.75)
            self.assertAlmostEqual(out[0], -1)

            block = _WaveForm(wave='triangle', amplitude=2)
            out = block.output(0)
            self.assertAlmostEqual(out[0], 0)
            out = block.output(0.25)
            self.assertAlmostEqual(out[0], 2)
            out = block.output(0.75)
            self.assertAlmostEqual(out[0], -2)

            block = _WaveForm(wave='triangle', offset=1)
            out = block.output(0)
            self.assertAlmostEqual(out[0], 1)
            out = block.output(0.25)
            self.assertAlmostEqual(out[0], 2)
            out = block.output(0.75)
            self.assertAlmostEqual(out[0], 0)

            block = _WaveForm(wave='triangle', amplitude=2, offset=1)
            out = block.output(0)
            self.assertAlmostEqual(out[0], 1)
            out = block.output(0.25)
            self.assertAlmostEqual(out[0], 3)
            out = block.output(0.75)
            self.assertAlmostEqual(out[0], -1)

            block = _WaveForm(wave='triangle', min=10, max=12)
            out = block.output(0)
            self.assertAlmostEqual(out[0], 11)
            out = block.output(0.25)
            self.assertAlmostEqual(out[0], 12)
            out = block.output(0.75)
            self.assertAlmostEqual(out[0], 10)

            block = _WaveForm(wave='triangle', phase=0.25)
            out = block.output(0)
            self.assertAlmostEqual(out[0], -1)
            out = block.output(0.25)
            self.assertAlmostEqual(out[0], 0)
            out = block.output(0.75)
            self.assertAlmostEqual(out[0], 0)

            block = _WaveForm(wave='triangle', unit='rad/s')
            out = block.output(0)
            self.assertIsInstance(out, list)
            self.assertAlmostEqual(len(out), 1)
            self.assertAlmostEqual(out[0], 0)
            out = block.output(math.pi/2)
            self.assertAlmostEqual(out[0], 1)
            out = block.output(3/2*math.pi)
            self.assertAlmostEqual(out[0], -1)
            
        def test_waveform_square(self):

            block = _WaveForm(wave='square')
            out = block.output(0)
            self.assertIsInstance(out, list)
            self.assertEqual(len(out), 1)
            self.assertAlmostEqual(out[0], 1)
            out = block.output(0.25)
            self.assertAlmostEqual(out[0], 1)
            out = block.output(0.75)
            self.assertAlmostEqual(out[0], -1)

            block = _WaveForm(wave='square', amplitude=2)
            out = block.output(0)
            self.assertAlmostEqual(out[0], 2)
            out = block.output(0.25)
            self.assertAlmostEqual(out[0], 2)
            out = block.output(0.75)
            self.assertAlmostEqual(out[0], -2)

            block = _WaveForm(wave='square', offset=1)
            out = block.output(0)
            self.assertAlmostEqual(out[0], 2)
            out = block.output(0.25)
            self.assertAlmostEqual(out[0], 2)
            out = block.output(0.75)
            self.assertAlmostEqual(out[0], 0)

            block = _WaveForm(wave='square', amplitude=2, offset=1)
            out = block.output(0)
            self.assertAlmostEqual(out[0], 3)
            out = block.output(0.25)
            self.assertAlmostEqual(out[0], 3)
            out = block.output(0.75)
            self.assertAlmostEqual(out[0], -1)

            block = _WaveForm(wave='square', min=10, max=12)
            out = block.output(0)
            self.assertAlmostEqual(out[0], 12)
            out = block.output(0.25)
            self.assertAlmostEqual(out[0], 12)
            out = block.output(0.75)
            self.assertAlmostEqual(out[0], 10)

            block = _WaveForm(wave='square', phase=0.25)
            out = block.output(0)
            self.assertAlmostEqual(out[0], -1)
            out = block.output(0.25)
            self.assertAlmostEqual(out[0], 1)
            out = block.output(0.75)
            self.assertAlmostEqual(out[0], -1)

            block = _WaveForm(wave='square', unit='rad/s')
            out = block.output(0)
            self.assertIsInstance(out, list)
            self.assertAlmostEqual(len(out), 1)
            self.assertAlmostEqual(out[0], 1)
            out = block.output(math.pi/2)
            self.assertAlmostEqual(out[0], 1)
            out = block.output(3/2*math.pi)
            self.assertAlmostEqual(out[0], -1)
            

        def test_step(self):

            block = _Step()
            out = block.output(0)
            self.assertIsInstance(out, list)
            self.assertEqual(len(out), 1)
            self.assertEqual(out[0], 0)

            out = block.output(0.9)
            self.assertEqual(out[0], 0)
            out = block.output(1)
            self.assertEqual(out[0], 1)

            block = _Step(off=1, on=2)
            out = block.output(1)
            out = block.output(0.9)
            self.assertEqual(out[0], 1)
            out = block.output(1)
            self.assertEqual(out[0], 2)
            
            block = _Step(T=2)
            out = block.output(1.9)
            self.assertEqual(out[0], 0)
            out = block.output(2.1)
            self.assertEqual(out[0], 1)
            
    unittest.main()
