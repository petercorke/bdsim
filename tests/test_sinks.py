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

import matplotlib.pyplot as plt
from matplotlib.pyplot import Polygon
import unittest
import numpy.testing as nt

from bdsim.blocks.sinks import *


class SinkBlockTest(unittest.TestCase):

    def test_print(self):

        class State:
            pass

        # print to a string so we can check result
        import io
        f = io.StringIO()

        # needed for time
        s = State()
        s.t = 1

        b = Print(name='print block', file=f)
        b._step(1.23, state=s)
        self.assertEqual(f.getvalue(), 
            'PRINT(print block (t=1.000) 1.23\n')

        # test print of object
        class testObject:
            def strline(self):
                return f"testObject={self.value:d}"

        to = testObject()
        to.value = 123

        # rewind the string buffer
        f.truncate(0)
        f.seek(0, 0)
        b._step(to, state=s)
        self.assertEqual(f.getvalue(), 
            'PRINT(print block (t=1.000) testObject=123\n')

        ## test with format string
        f = io.StringIO()
        b = Print(name='print block', file=f, fmt="{:.1f}")

        b._step(1.23456, state=s)
        self.assertEqual(f.getvalue(), 
            'PRINT(print block (t=1.000) 1.2\n')

        # rewind the string buffer
        f.truncate(0)
        f.seek(0, 0)

        b._step(np.r_[1.23456, 4.5679], state=s)
        self.assertEqual(f.getvalue(), 
            'PRINT(print block (t=1.000) [1.2 4.6]\n')

        # rewind the string buffer
        f.truncate(0)
        f.seek(0, 0)

        b._step("a string", state=s)
        self.assertEqual(f.getvalue(), 
            'PRINT(print block (t=1.000) a string\n')


    def test_stop(self):

        b = Stop(lambda x: x > 5)
        b.start()
        class State:
            pass
        s = State()
        s.stop = None

        b._step(0, state=s)
        self.assertIsNone(s.stop)

        b._step(10, state=s)
        self.assertTrue(s.stop)
        self.assertIs(s.stop, b)

        b = Stop()
        s.stop = None

        b._step(0, state=s)
        self.assertIsNone(s.stop)

        b._step(1, state=s)
        self.assertTrue(s.stop)
        self.assertIs(s.stop, b)

        s.stop = None
        b._step(False, state=s)
        self.assertIsNone(s.stop)

        b._step(True, state=s)
        self.assertTrue(s.stop)
        self.assertIs(s.stop, b)

        with self.assertRaises(TypeError):
            b = Stop(func=3)

    def test_watch(self):
        from bdsim import bdsim

        sim = bdsim.BDSim()  # create simulator
        bd = sim.blockdiagram()
        b1 = bd.CONSTANT(2)
        b2 = bd.NULL()
        b3 = bd.WATCH()
        bd.connect(b1, b2, b3)
        bd.compile()

        #bd.start()
        # state is not yet setup
        #bd.state.watchlist

# --------------------------------------------------------------------------------------#
if __name__ == '__main__':

    unittest.main()