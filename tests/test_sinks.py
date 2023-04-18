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

        b = Print(name="print block", file=f)

        b.T_step(1.23, t=1.0)
        self.assertEqual(f.getvalue(), "PRINT(print block (t=1.000) 1.23\n")

        # test print of object
        class testObject:
            def strline(self):
                return f"testObject={self.value:d}"

        to = testObject()
        to.value = 123

        # rewind the string buffer
        f.truncate(0)
        f.seek(0, 0)
        b.T_step(to, t=1.0)
        self.assertEqual(f.getvalue(), "PRINT(print block (t=1.000) testObject=123\n")

        ## test with format string
        f = io.StringIO()
        b = Print(name="print block", file=f, fmt="{:.1f}")

        b.T_step(1.23456, t=1.0)
        self.assertEqual(f.getvalue(), "PRINT(print block (t=1.000) 1.2\n")

        # rewind the string buffer
        f.truncate(0)
        f.seek(0, 0)

        b.T_step(np.r_[1.23456, 4.5679], t=1.0)
        self.assertEqual(f.getvalue(), "PRINT(print block (t=1.000) [1.2 4.6]\n")

        # rewind the string buffer
        f.truncate(0)
        f.seek(0, 0)

        b.T_step("a string", t=1.0)
        self.assertEqual(f.getvalue(), "PRINT(print block (t=1.000) a string\n")

    def test_stop(self):
        class State:
            def __init__(self):
                self.stop = None

        s = State()

        b = Stop(lambda x: x > 5)
        b.start(s)

        b.T_step(0)
        self.assertIsNone(s.stop)

        b.T_step(10)
        self.assertTrue(s.stop)
        self.assertIs(s.stop, b)

        b = Stop()
        s.stop = None
        b.start(s)

        b.T_step(0)
        self.assertIsNone(s.stop)

        b.T_step(1)
        self.assertTrue(s.stop)
        self.assertIs(s.stop, b)

        s.stop = None
        b.T_step(False)
        self.assertIsNone(s.stop)

        b.T_step(True)
        self.assertTrue(s.stop)
        self.assertIs(s.stop, b)

        with self.assertRaises(TypeError):
            b = Stop(func=3)

    def test_watch(self):
        from bdsim import BDSim

        sim = BDSim()  # create simulator
        bd = sim.blockdiagram()
        b1 = bd.CONSTANT(2)
        b2 = bd.NULL()
        b3 = bd.WATCH()
        bd.connect(b1, b2, b3)
        bd.compile()

        # bd.start()
        # state is not yet setup
        # bd.state.watchlist


# --------------------------------------------------------------------------------------#
if __name__ == "__main__":

    unittest.main()
