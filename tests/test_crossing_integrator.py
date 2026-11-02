#!/usr/bin/env python3
"""Analytic tests of INTEGRATOR limits, which are handled by crossing events.

A limited integrator holds its state exactly at the limit and is released when its
derivative reverses, rather than clipping the state.  Each case has an exact answer.
"""

import unittest
from unittest import mock

import numpy as np
import numpy.testing as nt

import bdsim
from bdsim.crossing import CrossingMixin

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

    def test_simultaneous_limits_are_both_held(self):
        # the solver reports only the earlier of two crossings at the same instant,
        # and restarts just past it: the other must not be lost
        out, x = self.run_integrator(
            lambda bd: bd.CONSTANT([1.0, 1.0]), 2.0, x0=[0, 0], max=[1.0, 1.0]
        )
        nt.assert_array_equal(x[out.t > 1 + 1e-6], 1.0)
        self.assertLessEqual(x.max(), 1.0)

    def test_simultaneous_lower_limits_are_both_held(self):
        out, x = self.run_integrator(
            lambda bd: bd.CONSTANT([-1.0, -1.0]), 2.0, x0=[0, 0], min=[-1.0, -1.0]
        )
        nt.assert_array_equal(x[out.t > 1 + 1e-6], -1.0)

    def test_one_element_released_as_another_reaches_its_limit(self):
        # element 0 reaches its limit at t = 1, when element 1, held since t = 0.5,
        # is released because u1 = 2 - 2t falls through zero
        def source(bd):
            f = bd.FUNCTION(lambda t: np.array([1.0, 2.0 - 2.0 * t]))
            bd.connect(bd.TIME(), f)
            return f

        out, x = self.run_integrator(source, 2.0, x0=[0, 0], max=[1.0, 0.75])
        t = out.t
        nt.assert_array_equal(x[t > 1 + 1e-6, 0], 1.0)
        held = (t > 0.5 + 1e-6) & (t < 1 - 1e-6)
        nt.assert_array_equal(x[held, 1], 0.75)
        after = (t > 1 + 1e-6) & (t < 2)
        nt.assert_allclose(x[after, 1], 2 * t[after] - t[after] ** 2 - 0.25, atol=1e-7)

    def test_initial_state_outside_the_limits_is_an_error(self):
        with self.assertRaises(RuntimeError):
            self.run_integrator(lambda bd: bd.CONSTANT(1.0), 1.0, x0=2.0, max=1.0)

    def test_limits_changed_after_creation_are_checked_at_start(self):
        bd = self.sim.blockdiagram()
        x = bd.INTEGRATOR(x0=0.5, max=1.0)
        bd.connect(bd.CONSTANT(1.0), x)
        bd.compile(verbose=False)
        x.max = 0.25
        with self.assertRaises(RuntimeError):
            self.sim.run(bd, T=1.0)

    def test_rerun_gives_identical_results(self):
        bd = self.sim.blockdiagram()
        x = bd.INTEGRATOR(max=1.0)
        bd.connect(bd.CONSTANT(2.0), x)
        bd.compile(verbose=False)
        a = self.sim.run(bd, T=2.0, solver_args=SOLVER)
        b = self.sim.run(bd, T=2.0, solver_args=SOLVER)
        nt.assert_array_equal(a.t, b.t)
        nt.assert_array_equal(a.x, b.x)


class IntegratorEnableTestCase(unittest.TestCase):
    """The optional ``enable`` input: false zeroes and holds the state."""

    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False, quiet=True)

    def run_enabled(self, enable, T=3.0, **integ):
        """``CONSTANT(1) -> INTEGRATOR(enable=True)``, enable driven by ``enable(t)``."""
        bd = self.sim.blockdiagram()
        x = bd.INTEGRATOR(enable=True, **integ)
        e = bd.FUNCTION(enable)
        bd.connect(bd.CONSTANT(1.0), x[0])
        bd.connect(bd.TIME(), e)
        bd.connect(e, x[1])
        bd.compile(verbose=False)
        out = self.sim.run(bd, T=T, solver_args=SOLVER)
        return out, np.asarray(out.x).reshape(len(out.t), -1)

    def test_has_a_second_input_only_when_asked(self):
        bd = self.sim.blockdiagram()
        self.assertEqual(bd.INTEGRATOR().nin, 1)
        self.assertEqual(bd.INTEGRATOR(enable=True).nin, 2)

    def test_disabled_then_enabled(self):
        # enabled for t < 1, disabled for 1 <= t < 2, enabled again from t = 2
        out, x = self.run_enabled(lambda t: 1.0 if (t < 1 or t >= 2) else 0.0)
        t = out.t
        a = t < 1 - 1e-6
        nt.assert_allclose(x[a, 0], t[a], atol=1e-8)
        held = (t > 1 + 1e-6) & (t < 2 - 1e-6)
        nt.assert_array_equal(x[held, 0], 0.0)
        c = t > 2 + 1e-6
        nt.assert_allclose(x[c, 0], t[c] - 2.0, atol=1e-7)
        self.assertEqual(out.stats.events_detected_total, 2)

    def test_disabled_at_the_start_zeroes_the_initial_state(self):
        out, x = self.run_enabled(lambda t: 0.0 if t < 1 else 1.0, x0=5.0)
        t = out.t
        # the first sample is the initial condition, before the event at t = 0
        self.assertEqual(x[0, 0], 5.0)
        nt.assert_array_equal(x[(t > 0) & (t < 1 - 1e-6), 0], 0.0)
        nt.assert_allclose(x[t > 1 + 1e-6, 0], t[t > 1 + 1e-6] - 1.0, atol=1e-7)

    def test_limits_apply_after_re_enabling(self):
        out, x = self.run_enabled(
            lambda t: 1.0 if (t < 0.5 or t >= 1) else 0.0, max=0.25
        )
        t = out.t
        nt.assert_array_equal(x[(t > 0.25 + 1e-6) & (t < 0.5 - 1e-6), 0], 0.25)
        nt.assert_array_equal(x[(t > 0.5 + 1e-6) & (t < 1 - 1e-6), 0], 0.0)
        nt.assert_allclose(
            x[(t > 1 + 1e-6) & (t < 1.25 - 1e-6), 0],
            t[(t > 1 + 1e-6) & (t < 1.25 - 1e-6)] - 1.0,
            atol=1e-7,
        )
        nt.assert_array_equal(x[t > 1.25 + 1e-6, 0], 0.25)

    def test_rerun_after_ending_disabled(self):
        # the run ends disabled; a second run must start enabled again
        bd = self.sim.blockdiagram()
        x = bd.INTEGRATOR(enable=True)
        e = bd.FUNCTION(lambda t: 1.0 if t < 1 else 0.0)
        bd.connect(bd.CONSTANT(1.0), x[0])
        bd.connect(bd.TIME(), e)
        bd.connect(e, x[1])
        bd.compile(verbose=False)
        a = self.sim.run(bd, T=2.0, solver_args=SOLVER)
        b = self.sim.run(bd, T=2.0, solver_args=SOLVER)
        nt.assert_array_equal(a.x, b.x)


class ClipEventsTestCase(unittest.TestCase):
    """CLIP has a corner at each limit: the solver is restarted exactly there."""

    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False, quiet=True)

    def integrate_clipped(
        self, source, T, x0=0, solver_args=None, block="CLIP", dt=None, **kwargs
    ):
        """``source -> CLIP -> INTEGRATOR``, returning the run and the final integral."""
        bd = self.sim.blockdiagram()
        c = getattr(bd, block)(**kwargs)
        i = bd.INTEGRATOR(x0=x0)
        bd.connect(source(bd), c)
        bd.connect(c, i)
        bd.compile(verbose=False)
        out = self.sim.run(bd, T=T, dt=dt, solver_args=solver_args or SOLVER)
        return out, np.asarray(out.x).reshape(len(out.t), -1)[-1]

    def test_state_at_the_corner_is_accurate_at_loose_tolerance(self):
        # the integral of min(t, 1) over [0, 3] is 0.5 + 2.  The solver takes the
        # state at a crossing from the interpolant of the step that contained it, and
        # a step that straddled the corner is wrong by an amount set by the
        # tolerance.  The state is recomputed up to the crossing, so it is
        # accurate however loose the tolerance.
        loose = dict(rtol=1e-3, atol=1e-6, max_step=10.0)
        out, x = self.integrate_clipped(
            lambda bd: bd.TIME(), 3.0, solver_args=loose, max=1.0
        )
        self.assertEqual(out.stats.events_detected_total, 1)
        self.assertAlmostEqual(x[0], 2.5, delta=1e-8)
        with mock.patch.object(CrossingMixin, "declare_thresholds"):
            _, x_without = self.integrate_clipped(
                lambda bd: bd.TIME(), 3.0, solver_args=loose, max=1.0
            )
        self.assertGreater(abs(x_without[0] - 2.5), 1e-3)  # what it protects against

    def test_both_limits(self):
        # clip(t - 1, -0.5, 0.5) over [0, 3]
        def source(bd):
            f = bd.FUNCTION(lambda t: t - 1.0)
            bd.connect(bd.TIME(), f)
            return f

        out, x = self.integrate_clipped(source, 3.0, min=-0.5, max=0.5)
        # -0.5 on [0, 0.5], ramp -0.5..0.5 on [0.5, 1.5] (integral 0), 0.5 on [1.5, 3]
        self.assertAlmostEqual(x[0], -0.25 + 0.0 + 0.75, delta=1e-7)
        self.assertEqual(out.stats.events_detected_total, 2)

    def test_no_events_without_finite_limits(self):
        out, x = self.integrate_clipped(lambda bd: bd.TIME(), 2.0)
        self.assertEqual(out.stats.events_detected_total, 0)

    def test_vector_with_elementwise_limits(self):
        def source(bd):
            f = bd.FUNCTION(lambda t: np.array([t, t]))
            bd.connect(bd.TIME(), f)
            return f

        out, x = self.integrate_clipped(source, 3.0, x0=[0, 0], max=[1.0, 2.0])
        self.assertAlmostEqual(x[0], 2.5, delta=1e-7)  # 0.5 + 2
        self.assertAlmostEqual(x[1], 4.0, delta=1e-7)  # 2 + 2
        self.assertEqual(out.stats.events_detected_total, 2)

    def test_signal_sitting_on_the_limit_does_not_chatter(self):
        # a constant exactly at the limit must not be reported as a crossing at
        # every restart
        out, x = self.integrate_clipped(lambda bd: bd.CONSTANT(1.0), 2.0, max=1.0)
        self.assertEqual(out.stats.events_detected_total, 0)
        self.assertAlmostEqual(x[0], 2.0, delta=1e-7)

    def test_integrator_held_at_a_limit_feeding_a_clip_with_the_same_limit(self):
        bd = self.sim.blockdiagram()
        held = bd.INTEGRATOR(max=1.0)
        c = bd.CLIP(max=1.0)
        sink = bd.INTEGRATOR()
        bd.connect(bd.CONSTANT(2.0), held)
        bd.connect(held, c)
        bd.connect(c, sink)
        bd.compile(verbose=False)
        out = self.sim.run(bd, T=3.0, solver_args=SOLVER)
        # held reaches 1 at t = 0.5 and stays: the clip output is 1 from there, so
        # the sink integrates 0.25 + (3 - 0.5) = 2.75
        self.assertAlmostEqual(np.asarray(out.x)[-1, -1], 2.75, delta=1e-7)
        self.assertLess(out.stats.events_detected_total, 8)


class CornerBlockEventsTestCase(ClipEventsTestCase):
    """DEADBAND and ABS have corners, SIGN a jump: the solver restarts at each."""

    LOOSE = dict(rtol=1e-3, atol=1e-6, max_step=10.0)

    @staticmethod
    def shifted(bd):
        """The signal t - 1, which crosses zero at t = 1."""
        f = bd.FUNCTION(lambda t: t - 1.0)
        bd.connect(bd.TIME(), f)
        return f

    def check_better_with_events(self, expected, block, T=3.0, **kwargs):
        out, x = self.integrate_clipped(
            self.shifted, T, solver_args=self.LOOSE, block=block, **kwargs
        )
        with mock.patch.object(CrossingMixin, "declare_thresholds"):
            _, x_without = self.integrate_clipped(
                self.shifted, T, solver_args=self.LOOSE, block=block, **kwargs
            )
        self.assertLess(abs(x[0] - expected), 1e-8)
        self.assertGreater(abs(x_without[0] - expected), 1e-4)
        return out

    def test_samples_inside_the_straddling_step_are_corrected(self):
        # on a fixed output grid, samples that fall inside the step that contained the
        # corner come from its interpolant too, and are recomputed with the state
        out, _ = self.integrate_clipped(
            self.shifted,
            3.0,
            solver_args=self.LOOSE,
            block="ABS",
            dt=0.05,
        )
        t = out.t
        x = np.asarray(out.x).reshape(len(t), -1)[:, 0]
        exact = np.where(t < 1, t - t**2 / 2, 0.5 + (t - 1) ** 2 / 2)
        nt.assert_allclose(x, exact, atol=1e-8)

    def test_abs_corner_at_zero(self):
        # integral of |t - 1| over [0, 3] is 0.5 + 2
        out = self.check_better_with_events(2.5, "ABS")
        self.assertEqual(out.stats.events_detected_total, 1)

    def test_sign_jump_at_zero(self):
        # integral of sign(t - 1) over [0, 3] is -1 + 2
        out = self.check_better_with_events(1.0, "SIGN")
        self.assertEqual(out.stats.events_detected_total, 1)

    def test_deadband_corner_at_each_edge(self):
        # deadband(t - 1, 0.5) over [0, 3]: -0.125 on [0, 0.5], 0 until 1.5, then
        # 1.125 on [1.5, 3]
        out = self.check_better_with_events(1.0, "DEADBAND", d=0.5)
        self.assertEqual(out.stats.events_detected_total, 2)

    def test_deadband_with_asymmetric_edges(self):
        out, x = self.integrate_clipped(
            self.shifted, 3.0, block="DEADBAND", d=[-0.25, 0.5]
        )
        self.assertEqual(out.stats.events_detected_total, 2)
        # -0.5*0.75^2/2... integral of (t-1+0.25) on [0, 0.75] is -0.28125; zero until
        # 1.5; then 1.125
        self.assertAlmostEqual(x[0], -0.28125 + 1.125, delta=1e-7)

    def test_signal_sitting_on_zero_does_not_chatter(self):
        for block in ("ABS", "SIGN"):
            out, x = self.integrate_clipped(
                lambda bd: bd.CONSTANT(0.0), 2.0, block=block
            )
            self.assertEqual(out.stats.events_detected_total, 0, block)

    def test_vector_input(self):
        def source(bd):
            f = bd.FUNCTION(lambda t: np.array([t - 1.0, t - 2.0]))
            bd.connect(bd.TIME(), f)
            return f

        out, x = self.integrate_clipped(source, 3.0, x0=[0, 0], block="ABS")
        self.assertEqual(out.stats.events_detected_total, 2)
        self.assertAlmostEqual(x[0], 2.5, delta=1e-7)  # |t-1| over [0, 3]
        self.assertAlmostEqual(x[1], 2.5, delta=1e-7)  # |t-2| over [0, 3]


if __name__ == "__main__":
    unittest.main()
