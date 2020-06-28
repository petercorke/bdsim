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

from bdsim.blocks.transfers import *

import unittest
import numpy.testing as nt


class TransferTest(unittest.TestCase):
    

        
    def test_LTI_SS(self):
        
        A=np.array([[1, 2], [3, 4]])
        B=np.array([5, 6])
        C=np.array([7, 8])
        block = LTI_SS(A=A, B=B, C=C, x0=[30,40])
        x = np.r_[10, 11]
        block.setstate(np.r_[x])
        u = -2
        block.inputs = [u]
        nt.assert_equal(block.deriv(), A@x  + B*u)
        nt.assert_equal(block.output()[0], C@x)
        nt.assert_equal(block.getstate(), np.r_[30, 40])
        
        A=np.array([[1, 2], [3, 4]])
        B=np.array([[5], [6]])
        C=np.array([[7, 8]])
        block = LTI_SS(A=A, B=B, C=C, x0=[30,40])
        x = np.r_[10, 11]
        block._x = np.r_[x]
        u = -2
        block.inputs = [u]
        nt.assert_equal(block.deriv(), A@x  + B@np.r_[u])
        nt.assert_equal(block.output()[0], C@x)
        nt.assert_equal(block.getstate(), np.r_[30, 40])
        
    def test_LTI_SISO(self):
        
        block = LTI_SISO( [2, 1], [2, 4, 6])
        nt.assert_equal(block.A, np.array([[0, 1], [-2, -3]]))
        nt.assert_equal(block.B, np.array([[0], [1]]))
        nt.assert_equal(block.C, np.array([[1, 0.5]]))
    
    def test_integrator(self):
        block = Integrator(x0=30)
        x = np.r_[10]
        block._x = x
        u = -2
        block.inputs = [u]
        nt.assert_equal(block.deriv(), u)
        nt.assert_equal(block.getstate(), np.r_[30])

# ---------------------------------------------------------------------------------------#
if __name__ == '__main__':

    unittest.main()