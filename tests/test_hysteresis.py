#!/usr/bin/env python3
"""HYSTERESIS_S in a simulation, against an answer known in closed form.

The input is a triangle, rising from 0 to 2 at unit rate and then falling back.  With
the output switching on at 0.95 and off at 0.45, and sampled every 0.1 s, the output is
on from the tick at t = 1.0, where the input first reaches 0.95, until the tick at
t = 3.6, where it first falls to 0.45.  It stays on through the whole falling edge down
to 0.5, which a plain relay would not: that is the memory.
"""

import unittest

import numpy as np
import numpy.testing as nt

import bdsim

SOLVER = dict(rtol=1e-10, atol=1e-12)


class HysteresisSimulationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False, quiet=True)

    def run_triangle(self, T=5.0, **kw):
        bd = self.sim.blockdiagram()
        clock = bd.clock(0.1)
        tri = bd.FUNCTION(lambda t: t if t < 2.0 else 4.0 - t)
        h = bd.HYSTERESIS_S(clock, switch_on=0.95, switch_off=0.45, **kw)
        area = bd.INTEGRATOR()
        bd.connect(bd.TIME(), tri)
        bd.connect(tri, h)
        bd.connect(h, area)
        bd.compile(verbose=False)
        return self.sim.run(bd, T=T, solver_args=SOLVER)

    def test_on_from_1_0_to_3_6(self):
        out = self.run_triangle()
        # the integral of the output is the time it is on
        self.assertAlmostEqual(np.asarray(out.x)[-1, -1], 3.6 - 1.0, delta=1e-7)

    def test_stays_on_while_the_input_falls_back_through_the_band(self):
        # output on at 2.0 s (input 2.0) and still on at 3.0 s (input 1.0) and at 3.5 s
        # (input 0.5), which is inside the band: a plain relay at 0.95 would be off
        out = self.run_triangle(T=3.55)
        self.assertAlmostEqual(np.asarray(out.x)[-1, -1], 3.55 - 1.0, delta=1e-7)

    def test_starts_on_when_x0_is_on(self):
        # initially on, the first period holds x0; the input (0) is below switch_off at
        # the first tick, so it switches off then and never comes back before t = 1.0
        out = self.run_triangle(T=0.5, x0=1.0)
        self.assertAlmostEqual(np.asarray(out.x)[-1, -1], 0.1, delta=1e-7)

    def test_rerun_gives_the_same_result(self):
        a = self.run_triangle()
        b = self.run_triangle()
        nt.assert_array_equal(a.x, b.x)


if __name__ == "__main__":
    unittest.main()
