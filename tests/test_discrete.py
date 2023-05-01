#!/usr/bin/env python3

import numpy as np
import math

import matplotlib.pyplot as plt

from bdsim.blocks.discrete import *
from bdsim import Clock

import unittest
import numpy.testing as nt

class DiscreteTest(unittest.TestCase):
    
    def test_ZOH(self):
        
        clock = Clock(2, 'Hz')
        x = 7
        block = ZOH(clock, x0=5)  # state is scalar
        self.assertEqual(block.ndstates, 1)
        self.assertEqual(block.nstates, 0)
        nt.assert_equal(block.getstate0(), np.r_[5])


        x = np.r_[1]
        nt.assert_equal(block.T_output(0, x=x)[0], x)

        u = 3
        nt.assert_equal(block.T_next(u, x=x), np.r_[u])
    
        u = np.r_[1]
        nt.assert_equal(block.T_next(u), u)
    
    def test_dintegrator(self):

        clock = Clock(2, 'Hz')
        block = DIntegrator(clock, x0=5)  # state is scalar
        self.assertEqual(block.ndstates, 1)
        self.assertEqual(block.nstates, 0)

        nt.assert_equal(block.getstate0(), np.r_[5])

        x = np.r_[10]
        u = -2
        nt.assert_equal(block.T_output(u, x=x)[0], x)
        nt.assert_equal(block.T_next(u, x=x), x + u *  clock.T)

        block = DIntegrator(clock, x0=5, min=-10, max=10)  # state is scalar
        x = np.r_[10]
        u = 2
        nt.assert_equal(block.T_next(u, x=x), x)

        x = np.r_[-10]
        u = -2
        nt.assert_equal(block.T_next(u, x=x), x)

    def test_dintegrator_vec(self):

        clock = Clock(2, 'Hz')
        block = DIntegrator(clock, x0=[5, 6])  # state is vector
        self.assertEqual(block.ndstates, 2)
        self.assertEqual(block.nstates, 0)

        nt.assert_equal(block.getstate0(), np.r_[5, 6])

        x = np.r_[10, 11]
        u = np.r_[-2, 3]
        nt.assert_equal(block.T_output(u, x=x)[0], x)
        nt.assert_equal(block.T_next(u, x=x), x + u * clock.T)

        # test with limits
        block = DIntegrator(clock, x0=[5, 6], min=[-5, -10], max=[5, 10])  # state is vector
        x = np.r_[-5, -10]
        u = np.r_[-2, -3]
        nt.assert_equal(block.T_next(u, x=x), x)

        x = np.r_[5, 10]
        u = np.r_[2, 3]
        nt.assert_equal(block.T_next(u, x=x), x)

    def test_pose_dintegrator(self):

        clock = Clock(2, 'Hz')
        T = SE3.Rand()
        block = DPoseIntegrator(clock, x0=T)
        nt.assert_equal(block.getstate0(), Twist3(T))

        self.assertEqual(block.ndstates, 6)
        self.assertEqual(block.nstates, 0)

        x = block.getstate0()
        u = np.r_[1,2,3,4,5,6]

        nt.assert_equal(block.T_output(u, x=x)[0], T)

        nt.assert_almost_equal(block.T_next(u, x=x), Twist3(T * SE3.Delta(u*clock.T)))

# ---------------------------------------------------------------------------------------#
if __name__ == '__main__':

    unittest.main()