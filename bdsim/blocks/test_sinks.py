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
    
    
    def test_quadrotor(self):
        
        from quad_model import quadrotor as qm
        
        b = MultiRotorPlot(qm)
        
        b.start()
        
        b.setinputs(np.r_[0.5, 0, -1, 0, 0, 0, 0,0,0,0,0,0])
        b.step()

# --------------------------------------------------------------------------------------#
if __name__ == '__main__':

    unittest.main()