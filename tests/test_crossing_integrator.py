#!/usr/bin/env python3
"""Analytic tests of INTEGRATOR limits, which are handled by crossing events.

A limited integrator holds its state exactly at the limit and is released when its
derivative reverses, rather than clipping the state.  Each case has an exact answer.
"""

import unittest

import numpy as np
import numpy.testing as nt

import bdsim

SOLVER = dict(rtol=1e-10, atol=1e-12)


class IntegratorLimitTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False, quiet=True)

    def run_integrator(self, source, T, dt=None, **integ):
        """Run ``source -> INTEGRATOR``; the state log is ``out.x``, one row per sample."""
        bd = self.sim.blockdiagram()
        x = bd.INTEGRATOR(**integ)
        bd.connect(source(bd), x)
        bd.compile(verbose=False)
        out = self.sim.run(bd, T=T, dt=dt, solver_args=SOLVER)
        return out, np.asarray(out.x).reshape(len(out.t), -1)

    def test_ramp_reaches_limit_at_L_over_rate(self):
        out, x = self.run_integrator(lambda bd: bd.CONSTANT(2.0), 3.0, max=1.0)
        t = out.t
        # follows the ramp up to t = 0.5, then is held exactly at the limit
        before = t < 0.5 - 1e-6
        nt.assert_allclose(x[before, 0], 2.0 * t[before], atol=1e-8)
        nt.assert_array_equal(x[t >= 0.5 + 1e-6, 0], 1.0)
        self.assertLessEqual(x.max(), 1.0)
        self.assertEqual(out.stats.events_detected_total, 1)
        # no chatter at the limit: about the cost of the same run without a limit
        free, _ = self.run_integrator(lambda bd: bd.CONSTANT(2.0), 3.0)
        self.assertLess(out.stats.ydot_calls, 1.5 * free.stats.ydot_calls)

    def test_lower_limit(self):
        out, x = self.run_integrator(
            lambda bd: bd.CONSTANT(-4.0), 2.0, x0=1.0, min=-1.0
        )
        t = out.t
        nt.assert_array_equal(x[t >= 0.5 + 1e-6, 0], -1.0)
        self.assertEqual(out.stats.events_detected_total, 1)

    def test_released_when_input_reverses(self):
        # u = cos(t), so the unlimited state is sin(t).  A limit of 0.5 is reached at
        # t = pi/6 and held until u goes negative at pi/2, when the state is released.
        def cos_t(bd):
            f = bd.FUNCTION(lambda t: np.cos(t))
            bd.connect(bd.TIME(), f)
            return f

        out, x = self.run_integrator(cos_t, 4.0, max=0.5)
        t = out.t
        held = (t > np.pi / 6 + 1e-6) & (t < np.pi / 2 - 1e-6)
        nt.assert_array_equal(x[held, 0], 0.5)
        # released at pi/2, then x(t) = 0.5 + (sin(t) - 1)
        after = (t > np.pi / 2 + 1e-6) & (t < 3 * np.pi / 2 - 1e-6)
        nt.assert_allclose(x[after, 0], 0.5 + np.sin(t[after]) - 1.0, atol=1e-7)
        self.assertEqual(out.stats.events_detected_total, 2)

    def test_zero_input_at_limit_does_not_chatter(self):
        out, x = self.run_integrator(lambda bd: bd.CONSTANT(0.0), 2.0, x0=1.0, max=1.0)
        nt.assert_array_equal(x[:, 0], 1.0)
        self.assertEqual(out.stats.events_detected_total, 0)

    def test_vector_elements_have_their_own_limits(self):
        out, x = self.run_integrator(
            lambda bd: bd.CONSTANT([1.0, 1.0]), 3.0, x0=[0, 0], max=[1.0, 10.0]
        )
        t = out.t
        nt.assert_array_equal(x[t > 1 + 1e-6, 0], 1.0)
        nt.assert_allclose(x[:, 1], t, atol=1e-8)

    def test_gain_is_applied_to_the_input_and_limits_are_on_the_state(self):
        out, x = self.run_integrator(
            lambda bd: bd.CONSTANT(1.0), 2.0, gain=4.0, max=1.0
        )
        t = out.t
        nt.assert_allclose(x[t < 0.25 - 1e-6, 0], 4.0 * t[t < 0.25 - 1e-6], atol=1e-8)
        nt.assert_array_equal(x[t > 0.25 + 1e-6, 0], 1.0)

    def test_negative_gain_hits_the_lower_limit(self):
        out, x = self.run_integrator(
            lambda bd: bd.CONSTANT(1.0), 2.0, gain=-2.0, min=-1.0
        )
        nt.assert_array_equal(x[out.t > 0.5 + 1e-6, 0], -1.0)

    def test_starting_on_a_limit_heading_out(self):
        out, x = self.run_integrator(lambda bd: bd.CONSTANT(1.0), 1.0, x0=1.0, max=1.0)
        nt.assert_array_equal(x[:, 0], 1.0)

    def test_starting_on_a_limit_heading_in(self):
        out, x = self.run_integrator(lambda bd: bd.CONSTANT(-1.0), 1.0, x0=1.0, max=1.0)
        nt.assert_allclose(x[:, 0], 1.0 - out.t, atol=1e-8)
        self.assertEqual(out.stats.events_detected_total, 0)

    def test_fixed_output_grid(self):
        out, x = self.run_integrator(lambda bd: bd.CONSTANT(2.0), 1.0, dt=0.1, max=1.0)
        nt.assert_array_equal(x[out.t > 0.5 + 1e-6, 0], 1.0)
        self.assertTrue(np.all(np.diff(out.t) > 0))

    def test_rerun_gives_identical_results(self):
        bd = self.sim.blockdiagram()
        x = bd.INTEGRATOR(max=1.0)
        bd.connect(bd.CONSTANT(2.0), x)
        bd.compile(verbose=False)
        a = self.sim.run(bd, T=2.0, solver_args=SOLVER)
        b = self.sim.run(bd, T=2.0, solver_args=SOLVER)
        nt.assert_array_equal(a.t, b.t)
        nt.assert_array_equal(a.x, b.x)


if __name__ == "__main__":
    unittest.main()
