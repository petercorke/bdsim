#!/usr/bin/env python3
"""A crossing event with a fixed output grid (``dt``).

With ``dt`` set the results are sampled on a grid of multiples of ``dt``, and every
interval boundary is also a sample (clock ticks, step times).  A crossing event ends
an interval, so it is a boundary too: the log gets one sample at the event time,
holding the state the next segment starts from, and the grid samples either side of
it are left alone.

The bouncing ball has an exact solution, so the samples can be checked against it.
"""

import unittest

import numpy as np
import numpy.testing as nt

import bdsim

G = -9.81
E = 0.8
H0 = 10.0
T1 = np.sqrt(2 * H0 / -G)  # first impact
SOLVER = dict(rtol=1e-10, atol=1e-12)


def impact_time(n):
    """Time of impact n (n = 1 is the first)."""
    return T1 * (1 + 2 * sum(E**k for k in range(1, n)))


class BallTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False, quiet=True)

    def run_ball(self, T, dt):
        bd = self.sim.blockdiagram()
        velocity = bd.INTEGRATOR(name="velocity", x0=0)
        position = bd.INTEGRATOR(name="position", x0=H0)

        def impact(event_block, state_map):
            state_map[velocity] *= -E

        ground = bd.EVENT("-", impact)
        bd.connect(bd.CONSTANT(G), velocity)
        bd.connect(velocity, position)
        bd.connect(position, ground)
        bd.compile(verbose=False)
        return self.sim.run(bd, T=T, dt=dt, solver_args=SOLVER, watch=[position])

    @staticmethod
    def at(out, t):
        """Index of the sample at time t, which must be there."""
        i = int(np.argmin(np.abs(out.t - t)))
        assert abs(out.t[i] - t) < 1e-9, f"no sample at t={t}, nearest is {out.t[i]}"
        return i


class FixedGridTest(BallTestCase):
    dt = 0.01

    def test_every_grid_point_is_a_sample(self):
        out = self.run_ball(T=3.0, dt=self.dt)
        for k in range(0, 301):
            self.at(out, k * self.dt)

    def test_times_increase_and_the_logs_are_the_same_length(self):
        out = self.run_ball(T=5.0, dt=self.dt)
        self.assertTrue(np.all(np.diff(out.t) > 0))
        self.assertEqual(len(out.t), len(out.x))
        self.assertEqual(len(out.t), len(out.y))

    def test_the_grid_sample_before_the_event_is_not_overwritten(self):
        out = self.run_ball(T=3.0, dt=self.dt)
        i = self.at(out, 1.42)  # the last grid point before the impact at 1.4278
        nt.assert_allclose(out.x[i, 0], G * 1.42, atol=1e-8)
        nt.assert_allclose(out.x[i, 1], H0 + 0.5 * G * 1.42**2, atol=1e-8)

    def test_the_event_is_a_sample_at_the_event_time(self):
        out = self.run_ball(T=3.0, dt=self.dt)
        i = self.at(out, T1)
        nt.assert_allclose(out.x[i, 1], 0.0, atol=1e-7)  # on the ground
        nt.assert_allclose(out.x[i, 0], E * -G * T1, atol=1e-7)  # leaving at e v

    def test_samples_after_the_event_are_at_their_true_times(self):
        out = self.run_ball(T=3.0, dt=self.dt)
        after = out.t > T1 + 1e-6
        dt = out.t[after] - T1
        v_after = E * -G * T1
        nt.assert_allclose(out.x[after, 0], v_after + G * dt, atol=1e-6)
        nt.assert_allclose(out.x[after, 1], v_after * dt + 0.5 * G * dt**2, atol=1e-6)

    def test_the_watched_signal_agrees_with_the_state(self):
        out = self.run_ball(T=3.0, dt=self.dt)
        nt.assert_allclose(out.y[:, 0], out.x[:, 1], atol=1e-6)

    def test_later_bounces_do_not_accumulate_an_error(self):
        out = self.run_ball(T=6.0, dt=self.dt)
        self.assertEqual(out.stats["events_detected_total"], 3)
        for n in (1, 2, 3):
            i = self.at(out, impact_time(n))
            nt.assert_allclose(out.x[i, 1], 0.0, atol=1e-6)
            nt.assert_allclose(out.x[i, 0], E**n * -G * T1, atol=1e-6)

    def test_a_coarse_grid_gives_the_same_physics(self):
        # the event times do not depend on the grid
        for dt in (0.1, 0.25, 0.5):
            with self.subTest(dt=dt):
                out = self.run_ball(T=4.0, dt=dt)
                self.assertEqual(out.stats["events_detected_total"], 2)
                i = self.at(out, impact_time(2))
                nt.assert_allclose(out.x[i, 0], E**2 * -G * T1, atol=1e-6)


class VariableStepTest(BallTestCase):
    """Without dt the event sample was already right: it must stay so."""

    def test_the_event_is_a_sample_at_the_event_time(self):
        out = self.run_ball(T=3.0, dt=None)
        i = self.at(out, T1)
        nt.assert_allclose(out.x[i, 1], 0.0, atol=1e-7)
        nt.assert_allclose(out.x[i, 0], E * -G * T1, atol=1e-7)
        self.assertTrue(np.all(np.diff(out.t) > 0))
        self.assertEqual(len(out.t), len(out.x))
        self.assertEqual(len(out.t), len(out.y))

    def test_later_bounces(self):
        out = self.run_ball(T=6.0, dt=None)
        self.assertEqual(out.stats["events_detected_total"], 3)
        for n in (1, 2, 3):
            i = self.at(out, impact_time(n))
            nt.assert_allclose(out.x[i, 0], E**n * -G * T1, atol=1e-6)


if __name__ == "__main__":
    unittest.main()
