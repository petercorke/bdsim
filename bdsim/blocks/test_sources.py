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

from bdsim.blocks.sources import *

import unittest
import numpy.testing as nt
    

class SourceBlockTest(unittest.TestCase):

    def test_constant(self):

        block = Constant(value=7)
        out = block.output()
        self.assertIsInstance(out, list)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0], 7)

        block = Constant(value=np.r_[1,2,3])
        out = block.output()
        self.assertIsInstance(out, list)
        self.assertEqual(len(out), 1)
        nt.assert_array_almost_equal(out[0], np.r_[1,2,3])

    def test_waveform_sine(self):

        block = WaveForm(wave='sine')

        self.assertAlmostEqual(block._eval(t=0)[0], 0)
        self.assertAlmostEqual(block._eval(t=0.25)[0], 1)
        self.assertAlmostEqual(block._eval(t=0.75)[0], -1)

        block = WaveForm(wave='sine', amplitude=2)
        self.assertAlmostEqual(block._eval(t=0)[0], 0)
        self.assertAlmostEqual(block._eval(t=0.25)[0], 2)
        self.assertAlmostEqual(block._eval(t=0.75)[0], -2)

        block = WaveForm(wave='sine', offset=1)
        self.assertAlmostEqual(block._eval(t=0)[0], 1)
        self.assertAlmostEqual(block._eval(t=0.25)[0], 2)
        self.assertAlmostEqual(block._eval(t=0.75)[0], 0)

        block = WaveForm(wave='sine', amplitude=2, offset=1)
        self.assertAlmostEqual(block._eval(t=0)[0], 1)
        self.assertAlmostEqual(block._eval(t=0.25)[0], 3)
        self.assertAlmostEqual(block._eval(t=0.75)[0], -1)

        block = WaveForm(wave='sine', min=10, max=12)
        self.assertAlmostEqual(block._eval(t=0)[0], 11)
        self.assertAlmostEqual(block._eval(t=0.25)[0], 12)
        self.assertAlmostEqual(block._eval(t=0.75)[0], 10)

        block = WaveForm(wave='sine', phase=0.25)
        self.assertAlmostEqual(block._eval(t=0)[0], -1)
        self.assertAlmostEqual(block._eval(t=0.25)[0], 0)
        self.assertAlmostEqual(block._eval(t=0.75)[0], 0)

        block = WaveForm(wave='sine', unit='rad/s')
        self.assertAlmostEqual(block._eval(t=0)[0], 0)
        self.assertAlmostEqual(block._eval(t=math.pi/2)[0], 1)
        self.assertAlmostEqual(block._eval(t=3/2*math.pi)[0], -1)
        
    def test_waveform_triangle(self):

        block = WaveForm(wave='triangle')
        out = block.output(0)

        self.assertAlmostEqual(block._eval(t=0)[0], 0)
        self.assertAlmostEqual(block._eval(t=0)[0], 0)
        self.assertAlmostEqual(block._eval(t=0.25)[0], 1)
        self.assertAlmostEqual(block._eval(t=0.75)[0], -1)

        block = WaveForm(wave='triangle', amplitude=2)
        self.assertAlmostEqual(block._eval(t=0)[0], 0)
        self.assertAlmostEqual(block._eval(t=0.25)[0], 2)
        self.assertAlmostEqual(block._eval(t=0.75)[0], -2)

        block = WaveForm(wave='triangle', offset=1)
        self.assertAlmostEqual(block._eval(t=0)[0], 1)
        self.assertAlmostEqual(block._eval(t=0.25)[0], 2)
        self.assertAlmostEqual(block._eval(t=0.75)[0], 0)

        block = WaveForm(wave='triangle', amplitude=2, offset=1)
        self.assertAlmostEqual(block._eval(t=0)[0], 1)
        self.assertAlmostEqual(block._eval(t=0.25)[0], 3)
        self.assertAlmostEqual(block._eval(t=0.75)[0], -1)

        block = WaveForm(wave='triangle', min=10, max=12)
        self.assertAlmostEqual(block._eval(t=0)[0], 11)
        self.assertAlmostEqual(block._eval(t=0.25)[0], 12)
        self.assertAlmostEqual(block._eval(t=0.75)[0], 10)

        block = WaveForm(wave='triangle', phase=0.25)
        self.assertAlmostEqual(block._eval(t=0)[0], -1)
        self.assertAlmostEqual(block._eval(t=0.25)[0], 0)
        self.assertAlmostEqual(block._eval(t=0.75)[0], 0)

        block = WaveForm(wave='triangle', unit='rad/s')
        self.assertAlmostEqual(block._eval(t=0)[0], 0)
        self.assertAlmostEqual(block._eval(t=math.pi/2)[0], 1)
        self.assertAlmostEqual(block._eval(t=3/2*math.pi)[0], -1)
        
    def test_waveform_square(self):

        block = WaveForm(wave='square')
        self.assertAlmostEqual(block._eval(t=0)[0], 1)
        self.assertAlmostEqual(block._eval(t=0.25)[0], 1)
        self.assertAlmostEqual(block._eval(t=0.75)[0], -1)

        block = WaveForm(wave='square', amplitude=2)
        self.assertAlmostEqual(block._eval(t=0)[0], 2)
        self.assertAlmostEqual(block._eval(t=0.25)[0], 2)
        self.assertAlmostEqual(block._eval(t=0.75)[0], -2)

        block = WaveForm(wave='square', offset=1)
        self.assertAlmostEqual(block._eval(t=0)[0], 2)
        self.assertAlmostEqual(block._eval(t=0.25)[0], 2)
        self.assertAlmostEqual(block._eval(t=0.75)[0], 0)

        block = WaveForm(wave='square', amplitude=2, offset=1)
        self.assertAlmostEqual(block._eval(t=0)[0], 3)
        self.assertAlmostEqual(block._eval(t=0.25)[0], 3)
        self.assertAlmostEqual(block._eval(t=0.75)[0], -1)

        block = WaveForm(wave='square', min=10, max=12)
        self.assertAlmostEqual(block._eval(t=0)[0], 12)
        self.assertAlmostEqual(block._eval(t=0.25)[0], 12)
        self.assertAlmostEqual(block._eval(t=0.75)[0], 10)

        block = WaveForm(wave='square', phase=0.25)
        self.assertAlmostEqual(block._eval(t=0)[0], -1)
        self.assertAlmostEqual(block._eval(t=0.25)[0], 1)
        self.assertAlmostEqual(block._eval(t=0.75)[0], -1)

        block = WaveForm(wave='square', unit='rad/s')
        self.assertAlmostEqual(block._eval(t=0)[0], 1)
        self.assertAlmostEqual(block._eval(t=math.pi/2)[0], 1)
        self.assertAlmostEqual(block._eval(t=3/2*math.pi)[0], -1)
        

    def test_step(self):

        block = Step()
        self.assertEqual(block._eval(t=0)[0], 0)

        self.assertEqual(block._eval(t=0.9)[0], 0)
        self.assertEqual(block._eval(t=1)[0], 1)

        block = Step(off=1, on=2)
        self.assertEqual(block._eval(t=0.9)[0], 1)
        self.assertEqual(block._eval(t=1)[0], 2)
        
        block = Step(T=2)
        self.assertEqual(block._eval(t=1.9)[0], 0)
        self.assertEqual(block._eval(t=2.1)[0], 1)
        

    def test_piecewise(self):
        
        block = Piecewise( (0,0), (1,1), (2,1), (2,0), (10,0))
        out = block.output(0)
        self.assertIsInstance(out, list)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0], 0)
        
        self.assertEqual(block.output(0.5)[0], 0)
        self.assertEqual(block.output(1)[0], 1)
        self.assertEqual(block.output(1.1)[0], 1)
        self.assertEqual(block.output(1.9)[0], 1)
        self.assertEqual(block.output(2)[0], 0)
        self.assertEqual(block.output(2.1)[0], 0)
        self.assertEqual(block.output(9)[0], 0)

# ---------------------------------------------------------------------------------------#
if __name__ == '__main__':

    unittest.main()
