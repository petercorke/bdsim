#!/usr/bin/env python3
"""``feedthrough`` is a read-only property of blocks with state.

It is fixed when the block is created because it decides the block's place in the
execution order, so it must not be settable, either directly or as a parameter.
"""

import unittest

import numpy as np

import bdsim


class FeedthroughTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False, quiet=True)

    def setUp(self):
        self.bd = self.sim.blockdiagram()
        self.clock = self.bd.clock(0.1)
        self.A, self.B, self.C = np.array([[0.5]]), np.array([1.0]), np.array([1.0])

    def test_continuous_blocks(self):
        self.assertFalse(self.bd.INTEGRATOR().feedthrough)
        self.assertFalse(self.bd.LTI_SS(self.A, self.B, self.C).feedthrough)
        proper = self.bd.LTI_SS(self.A, self.B, self.C, D=np.array([[2.0]]))
        self.assertTrue(proper.feedthrough)

    def test_sampled_blocks(self):
        self.assertFalse(self.bd.ZOH(self.clock).feedthrough)
        self.assertFalse(self.bd.INTEGRATOR_S(self.clock).feedthrough)
        self.assertTrue(self.bd.DERIV_S(self.clock).feedthrough)
        lti = self.bd.LTI_SS_S(
            self.clock, A=self.A, B=self.B, C=self.C, D=np.array([[2.0]]), x0=[0.0]
        )
        self.assertTrue(lti.feedthrough)

    def test_it_cannot_be_assigned(self):
        for block in (self.bd.INTEGRATOR(), self.bd.ZOH(self.clock)):
            with self.assertRaises(AttributeError):
                block.feedthrough = True

    def test_it_is_not_a_parameter(self):
        block = self.bd.INTEGRATOR()
        with self.assertRaises(Exception):
            block.set_param("feedthrough", True)
        self.assertFalse(block.feedthrough)

    def loop(self, make):
        """A feedback loop through a GAIN and the block ``make(bd, clock)`` makes."""
        block = make(self.bd, self.clock)
        gain = self.bd.GAIN(2.0)
        self.bd.connect(block, gain)
        self.bd.connect(gain, block)

    def test_the_scheduler_sees_an_algebraic_loop_through_feedthrough(self):
        self.loop(lambda bd, clock: bd.DERIV_S(clock))
        with self.assertRaises(Exception) as cm:
            self.bd.compile(verbose=False)
        self.assertIn("could not compile", str(cm.exception))

    def test_the_scheduler_allows_a_loop_without_feedthrough(self):
        self.loop(lambda bd, clock: bd.ZOH(clock))
        self.bd.compile(verbose=False)

    def test_a_block_with_feedthrough_is_evaluated_after_its_input(self):
        # DERIV_S on a unit ramp outputs (u - x) / T, a sawtooth of mean 1/2, so its
        # integral over one second is 0.5.  Evaluated before its input is known it would
        # use a stale u and the area would differ.
        ramp = self.bd.FUNCTION(lambda t: t)
        deriv = self.bd.DERIV_S(self.clock)
        area = self.bd.INTEGRATOR()
        self.bd.connect(self.bd.TIME(), ramp)
        self.bd.connect(ramp, deriv)
        self.bd.connect(deriv, area)
        self.bd.compile(verbose=False)
        out = self.sim.run(self.bd, T=1.0, solver_args=dict(rtol=1e-10, atol=1e-12))
        self.assertAlmostEqual(np.asarray(out.x)[-1, -1], 0.5, delta=1e-6)


if __name__ == "__main__":
    unittest.main()
