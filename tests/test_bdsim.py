#!/usr/bin/env python3

import numpy as np
import math

import bdsim
import unittest
import numpy.testing as nt

class BDSimTest(unittest.TestCase):

    def test_options(self):
        sim = bdsim.BDSim()

        self.assertFalse(sim.options.verbose)
        self.assertTrue(sim.options.graphics)
        self.assertFalse(sim.options.animation)

        sim.options.verbose=True
        self.assertTrue(sim.options.verbose)

        sim.options.set(verbose=False)
        self.assertFalse(sim.options.verbose)

        sim.set_options(verbose=True)
        self.assertTrue(sim.options.verbose)

        sim.options.graphics=False
        self.assertFalse(sim.options.graphics)

        sim.options.animation=True
        self.assertTrue(sim.options.graphics)
        self.assertTrue(sim.options.animation)

# ---------------------------------------------------------------------------------------#
if __name__ == '__main__':

    unittest.main()
    
