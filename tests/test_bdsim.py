#!/usr/bin/env python3

import numpy as np
import math

import bdsim
import unittest
import numpy.testing as nt
from pathlib import Path


class BDSimTest(unittest.TestCase):
    def test_options(self):
        sim = bdsim.BDSim()

        self.assertFalse(sim.options.verbose)
        self.assertTrue(sim.options.graphics)
        self.assertFalse(sim.options.animation)

        sim.options.verbose = True
        self.assertTrue(sim.options.verbose)

        sim.options.set(verbose=False)
        self.assertFalse(sim.options.verbose)

        sim.set_options(verbose=True)
        self.assertTrue(sim.options.verbose)

        sim.options.graphics = False
        sim.options.animation = False

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

    def test_bdrun(self):

        file = Path(__file__).parent.parent / "examples" / "eg1.bd"

        sim = bdsim.BDSim(graphics=None, progress=False)
        bd = sim.blockdiagram()

        bd = bdsim.bdload(bd, file)
        self.assertEqual(len(bd.blocklist), 5)
        self.assertEqual(len(bd.wirelist), 6)
        bd.compile()
        sim.run(bd, T=2)

    def test_sim(self):
        # all up test

        sim = bdsim.BDSim(graphics=None, progress=False)
        bd = sim.blockdiagram()

        integ = bd.INTEGRATOR()
        step = bd.STEP(t=1)
        null = bd.NULL()
        bd.connect(step, integ)
        bd.connect(integ, null)

        bd.compile()
        out = sim.run(bd, 2)

        self.assertIsInstance(out, bdsim.components.BDStruct)
        self.assertTrue(hasattr(out, "t"))
        self.assertIsInstance(out.t, np.ndarray)
        self.assertEqual(out.t.ndim, 1)
        n = out.t.shape[0]
        self.assertGreater(n, 100)

        self.assertTrue(hasattr(out, "x"))
        self.assertIsInstance(out.x, np.ndarray)
        self.assertEqual(out.x.shape, (n, 1))

        self.assertTrue(hasattr(out, "xnames"))
        self.assertIsInstance(out.xnames, list)
        self.assertEqual(len(out.xnames), 1)
        self.assertEqual(out.xnames[0], "integrator.0x0")

        self.assertTrue(hasattr(out, "ynames"))
        self.assertIsInstance(out.ynames, list)
        self.assertEqual(len(out.ynames), 0)

    def test_sim_implicit(self):
        # all up test

        sim = bdsim.BDSim(graphics=None, progress=False)
        bd = sim.blockdiagram()

        integ = bd.INTEGRATOR()
        step = bd.STEP(t=1)
        null = bd.NULL()
        integ[0] = step
        null[0] = integ

        bd.compile()
        out = sim.run(bd, 2)

        self.assertIsInstance(out, bdsim.components.BDStruct)
        self.assertTrue(hasattr(out, "t"))
        self.assertIsInstance(out.t, np.ndarray)
        self.assertEqual(out.t.ndim, 1)
        n = out.t.shape[0]
        self.assertGreater(n, 100)

        self.assertTrue(hasattr(out, "x"))
        self.assertIsInstance(out.x, np.ndarray)
        self.assertEqual(out.x.shape, (n, 1))

        self.assertTrue(hasattr(out, "xnames"))
        self.assertIsInstance(out.xnames, list)
        self.assertEqual(len(out.xnames), 1)
        self.assertEqual(out.xnames[0], "integrator.0x0")

        self.assertTrue(hasattr(out, "ynames"))
        self.assertIsInstance(out.ynames, list)
        self.assertEqual(len(out.ynames), 0)


# ---------------------------------------------------------------------------------------#
if __name__ == "__main__":

    unittest.main()
