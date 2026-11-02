#!/usr/bin/env python3
"""ANOISE_S and MNOISE_S: unit behaviour, and a simulation against the exact draws.

The sample for tick k is ``default_rng([seed, k]).normal(mean, sigma)`` and is held over
[kT, (k+1)T), except that the tick at t = 0 is not applied, so the first period carries x0.
Integrating the output of a block fed with 0 (additive) or 1 (multiplicative) therefore
has a closed form: T times the sum of the samples for k = 1 ...
"""

import unittest

import numpy as np
import numpy.testing as nt

import bdsim
from bdsim import Clock
from bdsim.blocks.sampled import Anoise_S, Mnoise_S

SOLVER = dict(rtol=1e-10, atol=1e-12)
T = 0.1


def draw(seed, k, mean, sigma):
    return np.random.default_rng([seed, k]).normal(mean, sigma)


class NoiseUnitTest(unittest.TestCase):
    def test_state_is_the_held_sample(self):
        a = Anoise_S(Clock(T, "s"), sigma=0.5, seed=1)
        self.assertEqual(a.ndstates, 1)
        nt.assert_equal(a.getstate0(), [0.0])
        nt.assert_equal(Mnoise_S(Clock(T, "s"), sigma=0.5).getstate0(), [1.0])
        nt.assert_equal(
            Anoise_S(Clock(T, "s"), sigma=[1, 2, 3]).getstate0(), np.zeros(3)
        )
        nt.assert_equal(
            Mnoise_S(Clock(T, "s"), sigma=[1, 2, 3]).getstate0(), np.ones(3)
        )
        nt.assert_equal(Anoise_S(Clock(T, "s"), x0=[0.1, 0.2]).getstate0(), [0.1, 0.2])

    def test_output_adds_or_multiplies_the_held_sample(self):
        c = Clock(T, "s")
        self.assertEqual(Anoise_S(c).test_output(3.0, x=np.r_[0.25])[0], 3.25)
        self.assertEqual(Mnoise_S(c).test_output(3.0, x=np.r_[1.5])[0], 4.5)
        nt.assert_allclose(
            Anoise_S(c, sigma=[1, 1]).test_output(np.r_[1.0, 2.0], x=np.r_[0.5, -0.5])[
                0
            ],
            [1.5, 1.5],
        )

    def test_next_is_a_pure_function_of_seed_and_tick(self):
        a = Anoise_S(Clock(T, "s"), sigma=0.5, seed=7)
        first = a.test_next(0.0, t=3 * T)
        nt.assert_array_equal(first, a.test_next(0.0, t=3 * T))
        nt.assert_allclose(first, [draw(7, 3, 0.0, 0.5)])
        self.assertNotEqual(first[0], a.test_next(0.0, t=4 * T)[0])
        # the input does not matter, and nor does the state
        nt.assert_array_equal(first, a.test_next(99.0, t=3 * T, x=np.r_[5.0]))

    def test_tick_index_respects_the_clock_offset(self):
        a = Anoise_S(Clock(T, "s", offset=0.05), sigma=1.0, seed=2)
        nt.assert_allclose(a.test_next(0.0, t=0.05 + 4 * T), [draw(2, 4, 0.0, 1.0)])

    def test_mean_and_sigma(self):
        for cls, mean in ((Anoise_S, 0.0), (Mnoise_S, 1.0)):
            b = cls(Clock(T, "s"), sigma=[0.0, 2.0], seed=3)
            samples = np.array(
                [b.test_next(np.r_[0.0, 0.0], t=k * T) for k in range(1, 20001)]
            )
            self.assertEqual(samples.shape, (20000, 2))
            nt.assert_array_equal(samples[:, 0], mean)  # sigma 0
            self.assertAlmostEqual(samples[:, 1].mean(), mean, delta=0.06)
            self.assertAlmostEqual(samples[:, 1].std(), 2.0, delta=0.06)

    def test_unseeded_runs_differ_and_seeded_runs_repeat(self):
        u = Anoise_S(Clock(T, "s"), sigma=1.0)
        u.reset()
        one = u.test_next(0.0, t=T)
        u.reset()
        self.assertNotEqual(one[0], u.test_next(0.0, t=T)[0])
        s = Anoise_S(Clock(T, "s"), sigma=1.0, seed=5)
        s.reset()
        one = s.test_next(0.0, t=T)
        s.reset()
        nt.assert_array_equal(one, s.test_next(0.0, t=T))

    def test_validation(self):
        c = Clock(T, "s")
        with self.assertRaises(ValueError):
            Anoise_S(c, sigma=-1)
        with self.assertRaises(ValueError):
            Anoise_S(c, seed=-1)
        with self.assertRaises(ValueError):
            Anoise_S(c, seed=1.5)
        with self.assertRaises(ValueError):
            Anoise_S(c, sigma=np.ones((2, 2)))
        with self.assertRaises(ValueError):
            Anoise_S(c, sigma=[1, 2], x0=[0, 0, 0])
        a = Anoise_S(c, sigma=1.0)
        with self.assertRaises(ValueError):
            a.set_param("sigma", -2)
        a.set_param("sigma", 0.25)
        self.assertEqual(a.sigma, 0.25)


class NoiseSimulationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False, quiet=True)

    def run_noise(self, name, source, T_end=2.0, seed=4, sigma=0.3, **kw):
        bd = self.sim.blockdiagram()
        clock = bd.clock(T)
        src = bd.CONSTANT(source)
        noise = getattr(bd, name)(clock, sigma=sigma, seed=seed, **kw)
        area = bd.INTEGRATOR()
        bd.connect(src, noise)
        bd.connect(noise, area)
        bd.compile(verbose=False)
        out = self.sim.run(bd, T=T_end, solver_args=SOLVER)
        return np.asarray(out.x)[-1, -1]

    def expected(self, mean, base, seed=4, sigma=0.3, ticks=20):
        # periods 1 .. 19 carry the samples for ticks 1 .. 19, period 0 carries x0
        samples = [draw(seed, k, mean, sigma) for k in range(1, ticks)]
        return T * (
            base * 1.0 + sum(base + s if mean == 0 else base * s for s in samples)
        )

    def test_additive_matches_the_exact_draws(self):
        # input 0: the area is T times the sum of the samples
        self.assertAlmostEqual(
            self.run_noise("ANOISE_S", 0.0), self.expected(0.0, 0.0), delta=1e-9
        )

    def test_additive_with_a_constant_input(self):
        # a constant input of 2 adds 2 * T_end
        self.assertAlmostEqual(
            self.run_noise("ANOISE_S", 2.0), self.expected(0.0, 2.0), delta=1e-9
        )

    def test_multiplicative_matches_the_exact_draws(self):
        self.assertAlmostEqual(
            self.run_noise("MNOISE_S", 2.0), self.expected(1.0, 2.0), delta=1e-9
        )

    def test_seeded_run_is_identical_and_independent_of_the_solver(self):
        a = self.run_noise("ANOISE_S", 0.0)
        self.assertEqual(a, self.run_noise("ANOISE_S", 0.0))
        bd = self.sim.blockdiagram()
        clock = bd.clock(T)
        n = bd.ANOISE_S(clock, sigma=0.3, seed=4)
        area = bd.INTEGRATOR()
        bd.connect(bd.CONSTANT(0.0), n)
        bd.connect(n, area)
        bd.compile(verbose=False)
        # a loose tolerance changes the steps the solver takes but not the noise
        out = self.sim.run(bd, T=2.0, solver_args=dict(rtol=1e-3, atol=1e-6))
        self.assertAlmostEqual(np.asarray(out.x)[-1, -1], a, delta=1e-6)

    def test_unseeded_runs_differ(self):
        bd = self.sim.blockdiagram()
        clock = bd.clock(T)
        n = bd.ANOISE_S(clock, sigma=0.3)
        area = bd.INTEGRATOR()
        bd.connect(bd.CONSTANT(0.0), n)
        bd.connect(n, area)
        bd.compile(verbose=False)
        r1 = np.asarray(self.sim.run(bd, T=2.0, solver_args=SOLVER).x)[-1, -1]
        r2 = np.asarray(self.sim.run(bd, T=2.0, solver_args=SOLVER).x)[-1, -1]
        self.assertNotEqual(r1, r2)

    def test_vector_input_needs_one_sigma_per_element(self):
        bd = self.sim.blockdiagram()
        clock = bd.clock(T)
        n = bd.ANOISE_S(clock, sigma=0.3, seed=1)
        bd.connect(bd.CONSTANT(np.r_[1.0, 2.0]), n)
        bd.connect(n, bd.INTEGRATOR(x0=[0, 0]))
        bd.compile(verbose=False)
        with self.assertRaises(RuntimeError):
            self.sim.run(bd, T=1.0)

    def test_vector_input(self):
        bd = self.sim.blockdiagram()
        clock = bd.clock(T)
        n = bd.ANOISE_S(clock, sigma=[0.3, 0.6], seed=1)
        bd.connect(bd.CONSTANT(np.r_[0.0, 0.0]), n)
        area = bd.INTEGRATOR(x0=[0, 0])
        bd.connect(n, area)
        bd.compile(verbose=False)
        out = np.asarray(self.sim.run(bd, T=1.0, solver_args=SOLVER).x)[-1, -2:]
        want = T * np.array(
            [
                sum(
                    np.random.default_rng([1, k]).normal(0, [0.3, 0.6])[i]
                    for k in range(1, 10)
                )
                for i in (0, 1)
            ]
        )
        nt.assert_allclose(out, want, atol=1e-9)


if __name__ == "__main__":
    unittest.main()
