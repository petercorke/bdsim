import numpy as np
import math

import matplotlib.pyplot as plt
import time

from bdsim.blocks.robots import *

import unittest
import numpy.testing as nt

class RobotBlockTest(unittest.TestCase):


    def test_quadrotor(self):
        
        from quad_model import quadrotor as qm
        
        block = MultiRotor(qm)
        print(block.D)
        z = np.r_[0, 0, 0, 0]
        block.inputs = [z]
        block.setstate(block.getstate())
        nt.assert_equal(block.getstate(), np.zeros((12,)))
        block.setstate(block.getstate())
        
        block._x[2] = -100  # set altitude
        block.inputs[0] = 100 * np.r_[1, -1, 1, -1]

        # check outputs
        out = block.output()
        self.assertIsInstance(out, list)
        self.assertEqual(len(out), 1)
        out = out[0]
        self.assertIsInstance(out, dict)
        self.assertIn('x', out)
        self.assertIn('vb', out)
        self.assertIn('w', out)
        self.assertEqual(out['x'][2], -100)

        # check deriv, checked against MATLAB version 20200621
        block.inputs[0] = 800 * np.r_[1, -1, 1, -1]   # too little thrust, falling
        d = block.deriv()
        self.assertIsInstance(d, np.ndarray)
        self.assertEqual(d.shape, (12,))
        self.assertGreater(d[8], 0)
        nt.assert_array_almost_equal(np.delete(d, 8), np.zeros((11,))) # other derivs are zero

        block.inputs[0] = 900 * np.r_[1, -1, 1, -1]  # too much thrust, rising
        self.assertLess(block.deriv()[8], 0)

        block.inputs[0] = 800 * np.r_[0.8, -1, 1.2, -1]  # pitching
        self.assertGreater(block.deriv()[10], 20)

        block.inputs[0] = 800 * np.r_[1, -1.2, 1, -0.8]  # rolling
        self.assertGreater(block.deriv()[9], 20)
        
# ---------------------------------------------------------------------------------------#
if __name__ == '__main__':

    unittest.main()