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
        sim.options.animation=False

        self.assertFalse(sim.options.graphics)
        self.assertFalse(sim.options.animation)

        sim.options.set(animation=True)
        self.assertTrue(sim.options.graphics)
        self.assertTrue(sim.options.animation)

        sim.options.set(graphics=False)
        self.assertFalse(sim.options.graphics)
        self.assertFalse(sim.options.animation)

        with self.assertRaises(ValueError):
            sim.options.set(graphics=False, animation=True)
# ---------------------------------------------------------------------------------------#
if __name__ == '__main__':

    unittest.main()
    
