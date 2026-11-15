#!/usr/bin/env python3
"""Analytic tests: simulate small diagrams whose answer is known in closed form.

The golden-master tests show that results are *unchanged*; these show that they are
*correct*, because each expected value comes from a formula, not from earlier output.
The solver tolerances are tightened so the comparison is with the maths, not with the
default ``rtol=1e-3``.
"""

import unittest

import numpy as np
import numpy.testing as nt

import bdsim

SOLVER = dict(rtol=1e-10, atol=1e-12)


class AnalyticTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False, quiet=True)

    def run_diagram(self, bd, T, dt=0.01, **kwargs):
        bd.compile(verbose=False)
        return self.sim.run(bd, T=T, dt=dt, solver_args=SOLVER, **kwargs)


class ContinuousTest(AnalyticTestCase):
    def test_integral_of_a_constant_is_a_ramp(self):
        bd = self.sim.blockdiagram()
        integrator = bd.INTEGRATOR(x0=1.0)
        bd.connect(bd.CONSTANT(2.5), integrator)
        out = self.run_diagram(bd, T=4)
        nt.assert_allclose(out.x[:, 0], 1.0 + 2.5 * out.t, rtol=1e-9, atol=1e-9)

    def test_integral_of_time_is_half_t_squared(self):
        bd = self.sim.blockdiagram()
        integrator = bd.INTEGRATOR(x0=0.0)
        bd.connect(bd.TIME(), integrator)
        out = self.run_diagram(bd, T=3)
        nt.assert_allclose(out.x[:, 0], out.t**2 / 2, rtol=1e-9, atol=1e-9)

    def test_vector_integrator_integrates_each_element(self):
        bd = self.sim.blockdiagram()
        integrator = bd.INTEGRATOR(x0=np.r_[0.0, 10.0])
        bd.connect(bd.CONSTANT(np.r_[1.0, -2.0]), integrator)
        out = self.run_diagram(bd, T=2)
        nt.assert_allclose(out.x[:, 0], out.t, rtol=1e-9, atol=1e-9)
        nt.assert_allclose(out.x[:, 1], 10.0 - 2.0 * out.t, rtol=1e-9, atol=1e-9)

    def test_first_order_lag_step_response(self):
        # G(s) = 0.5 / (s/4 + 1) ... as num/den: 2 / (s + 4), gain 0.5, pole at -4
        bd = self.sim.blockdiagram()
        plant = bd.LTI_SISO(2, [1, 4], name="plant")
        bd.connect(bd.STEP(T=1, off=0.0, on=1.0), plant)
        out = self.run_diagram(bd, T=3, watch=[plant])
        t = out.t
        expected = np.where(t < 1, 0.0, 0.5 * (1 - np.exp(-4 * (t - 1))))
        nt.assert_allclose(out.y[:, 0], expected, rtol=1e-7, atol=1e-7)

    def test_harmonic_oscillator_is_a_cosine(self):
        # x'' = -w^2 x with x(0) = 1, x'(0) = 0 has x = cos(wt), x' = -w sin(wt)
        w = 2 * np.pi
        bd = self.sim.blockdiagram()
        velocity = bd.INTEGRATOR(x0=0.0, name="velocity")
        position = bd.INTEGRATOR(x0=1.0, name="position")
        bd.connect(position, bd.GAIN(-(w**2), name="spring"))
        bd.connect(bd.blocklist[-1], velocity)
        bd.connect(velocity, position)
        out = self.run_diagram(bd, T=3)
        v, x = out.x[:, 0], out.x[:, 1]
        nt.assert_allclose(x, np.cos(w * out.t), atol=1e-6)
        nt.assert_allclose(v, -w * np.sin(w * out.t), atol=1e-5)

    def test_energy_of_the_oscillator_is_conserved(self):
        w = 3.0
        bd = self.sim.blockdiagram()
        velocity = bd.INTEGRATOR(x0=0.0, name="velocity")
        position = bd.INTEGRATOR(x0=1.0, name="position")
        spring = bd.GAIN(-(w**2))
        bd.connect(position, spring)
        bd.connect(spring, velocity)
        bd.connect(velocity, position)
        out = self.run_diagram(bd, T=10)
        energy = 0.5 * out.x[:, 0] ** 2 + 0.5 * w**2 * out.x[:, 1] ** 2
        nt.assert_allclose(energy, 0.5 * w**2, rtol=1e-6)


class AlgebraTest(AnalyticTestCase):
    def test_matrix_gain_postmultiplies_by_default(self):
        # y = u K, the gain is on the right
        K = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        u = np.r_[0.5, -1.5]
        bd = self.sim.blockdiagram()
        gain = bd.GAIN(K, name="gain")
        bd.connect(bd.CONSTANT(u), gain)
        out = self.run_diagram(bd, T=1, watch=[gain])
        nt.assert_allclose(out.y, np.tile(u @ K, (len(out.t), 1)), rtol=1e-12)

    def test_matrix_gain_premultiplies_with_premul(self):
        # y = K u
        K = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
        u = np.r_[0.5, -1.5]
        bd = self.sim.blockdiagram()
        gain = bd.GAIN(K, premul=True, name="gain")
        bd.connect(bd.CONSTANT(u), gain)
        out = self.run_diagram(bd, T=1, watch=[gain])
        nt.assert_allclose(out.y, np.tile(K @ u, (len(out.t), 1)), rtol=1e-12)

    def test_sum_adds_and_subtracts(self):
        bd = self.sim.blockdiagram()
        total = bd.SUM("+-+", name="total")
        bd.connect(bd.CONSTANT(5.0), total[0])
        bd.connect(bd.CONSTANT(2.0), total[1])
        bd.connect(bd.CONSTANT(0.5), total[2])
        out = self.run_diagram(bd, T=1, watch=[total])
        nt.assert_allclose(out.y[:, 0], 3.5, rtol=1e-12)

    def test_waveform_is_a_sine(self):
        bd = self.sim.blockdiagram()
        wave = bd.WAVEFORM("sine", freq=2, amplitude=3.0, offset=1.0, name="wave")
        out = self.run_diagram(bd, T=1, watch=[wave])
        nt.assert_allclose(
            out.y[:, 0], 1.0 + 3.0 * np.sin(2 * np.pi * 2 * out.t), atol=1e-9
        )


class DiscreteTest(AnalyticTestCase):
    def test_discrete_integrator_of_a_constant(self):
        # x[k+1] = x[k] + u T with x[0] = 0, so the state after the update at time t
        # is t.  Whichever tick is the first, the logged state equals the tick time,
        # and the ticks are a multiple of T apart.
        T = 0.25
        bd = self.sim.blockdiagram()
        clock = bd.clock(T)
        integrator = bd.INTEGRATOR_S(clock, x0=0.0)
        bd.connect(bd.CONSTANT(1.0), integrator)
        out = self.run_diagram(bd, T=2)
        log = out[clock.name.replace(".", "")]  # results are keyed by the clock's name
        nt.assert_allclose(log.X[:, 0], log.t, atol=1e-12)
        nt.assert_allclose(np.diff(log.t), T, atol=1e-12)
        self.assertEqual(len(log.t), 8)

    def test_discrete_integrator_gain(self):
        # x[k+1] = x[k] + gain u T from x[0] = 1, so each tick adds gain u T = 0.6
        T, gain = 0.1, 3.0
        bd = self.sim.blockdiagram()
        clock = bd.clock(T)
        integrator = bd.INTEGRATOR_S(clock, x0=1.0, gain=gain)
        bd.connect(bd.CONSTANT(2.0), integrator)
        out = self.run_diagram(bd, T=1)
        log = out[clock.name.replace(".", "")]
        nt.assert_allclose(log.X[:, 0], 1.0 + gain * 2.0 * log.t, atol=1e-12)

    def test_zoh_holds_the_input_of_the_previous_tick(self):
        # y at time t in [kT, (k+1)T) is the input at the previous tick, (k-1)T
        T = 0.5
        bd = self.sim.blockdiagram()
        clock = bd.clock(T)
        zoh = bd.ZOH(clock, x0=0.0, name="zoh")
        bd.connect(bd.TIME(), zoh)
        out = self.run_diagram(bd, T=3, watch=[zoh])
        k = np.floor(out.t / T + 1e-9)
        expected = np.maximum(k - 1, 0) * T
        nt.assert_allclose(out.y[:, 0], expected, atol=1e-9)


class BouncingBallTest(AnalyticTestCase):
    g = -9.81
    e = 0.8
    h0 = 10.0

    def ball(self):
        bd = self.sim.blockdiagram()
        velocity = bd.INTEGRATOR(name="velocity", x0=0)
        position = bd.INTEGRATOR(name="position", x0=self.h0)

        def impact(event_block, state_map):
            state_map[velocity] *= -self.e

        ground = bd.EVENT("-", impact)
        bd.connect(bd.CONSTANT(self.g), velocity)
        bd.connect(velocity, position)
        bd.connect(position, ground)
        return bd

    def test_free_fall_before_the_first_impact(self):
        out = self.run_diagram(self.ball(), T=1.4, dt=None)
        v, p = out.x[:, 0], out.x[:, 1]
        nt.assert_allclose(v, self.g * out.t, atol=1e-8)
        nt.assert_allclose(p, self.h0 + 0.5 * self.g * out.t**2, atol=1e-8)

    def test_first_impact_and_the_bounce(self):
        t1 = np.sqrt(2 * self.h0 / -self.g)
        out = self.run_diagram(self.ball(), T=3.0, dt=None)
        self.assertEqual(out.stats["events_detected_total"], 1)

        # after the impact the ball leaves at e times the speed it arrived with
        v_after = self.e * -self.g * t1
        after = out.t > t1 + 1e-6
        dt = out.t[after] - t1
        nt.assert_allclose(out.x[after, 0], v_after + self.g * dt, atol=1e-6)
        nt.assert_allclose(
            out.x[after, 1], v_after * dt + 0.5 * self.g * dt**2, atol=1e-6
        )

    def test_number_of_impacts(self):
        # impact n is at t1 (1 + 2 (e + e^2 + ... + e^n))
        t1 = np.sqrt(2 * self.h0 / -self.g)
        times = [
            t1 * (1 + 2 * sum(self.e**k for k in range(1, n + 1))) for n in range(4)
        ]
        for T, n in [
            (times[0] - 0.01, 0),
            (times[0] + 0.01, 1),
            (times[1] + 0.01, 2),
            (times[2] + 0.01, 3),
        ]:
            with self.subTest(T=round(T, 3), impacts=n):
                out = self.run_diagram(self.ball(), T=T, dt=None)
                self.assertEqual(out.stats["events_detected_total"], n)


if __name__ == "__main__":
    unittest.main()
