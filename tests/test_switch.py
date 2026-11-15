#!/usr/bin/env python3
"""SWITCH: the selection rule, the checks on its inputs, and the jump in a simulation.

Switching a constant 2 against a constant 0 on a selector that changes at t = 1, the
integral over [0, 3] is 4 whichever way the selector is expressed.  A solver step that
straddles the change gets this wrong by an amount set by the tolerance; with the
restart at the change it is exact.
"""

import unittest
from unittest import mock

import numpy as np
import numpy.testing as nt

import bdsim
from bdsim.blocks.functions import Switch
from bdsim.crossing import CrossingMixin

LOOSE = dict(rtol=1e-2, atol=1e-4)


class SwitchRuleTest(unittest.TestCase):
    def out(self, s, **kw):
        """Z for X = 1.0, Y = 2.0 and selector s."""
        return Switch(**kw).test_output(1.0, 2.0, s)[0]

    def test_bool(self):
        self.assertEqual(self.out(True), 1.0)
        self.assertEqual(self.out(False), 2.0)
        self.assertEqual(self.out(np.True_), 1.0)
        self.assertEqual(self.out(np.False_), 2.0)

    def test_bool_ignores_a_threshold(self):
        self.assertEqual(self.out(True, threshold=5), 1.0)

    def test_int_is_truthy(self):
        self.assertEqual(self.out(1), 1.0)
        self.assertEqual(self.out(-1), 1.0)  # nonzero
        self.assertEqual(self.out(0), 2.0)
        self.assertEqual(self.out(np.int64(0)), 2.0)

    def test_float_is_compared_with_zero_by_default(self):
        self.assertEqual(self.out(0.3), 1.0)
        self.assertEqual(self.out(0.0), 1.0)  # on the threshold counts as above
        self.assertEqual(self.out(-0.3), 2.0)
        self.assertEqual(self.out(np.float64(-1e-12)), 2.0)

    def test_float_with_a_threshold(self):
        self.assertEqual(self.out(1.0, threshold=1.0), 1.0)
        self.assertEqual(self.out(0.999, threshold=1.0), 2.0)
        self.assertEqual(self.out(-0.3, threshold=-0.5), 1.0)

    def test_int_with_a_threshold_is_compared(self):
        self.assertEqual(self.out(1, threshold=1), 1.0)
        self.assertEqual(self.out(0, threshold=1), 2.0)
        self.assertEqual(self.out(-1, threshold=-2), 1.0)  # not just nonzero

    def test_nan_selects_y(self):
        self.assertEqual(self.out(float("nan")), 2.0)

    def test_anything_else_is_truthy(self):
        self.assertEqual(self.out("a"), 1.0)
        self.assertEqual(self.out(""), 2.0)
        self.assertEqual(self.out([]), 2.0)
        self.assertEqual(self.out([0]), 1.0)
        self.assertEqual(self.out(None), 2.0)

    def test_size_one_array_is_a_scalar(self):
        self.assertEqual(self.out(np.r_[-0.3]), 2.0)
        self.assertEqual(self.out(np.r_[0.3]), 1.0)

    def test_array_selector_is_an_error(self):
        with self.assertRaises(ValueError):
            self.out(np.r_[1.0, 2.0])
        with self.assertRaises(ValueError):
            self.out(np.array([["a", "b"]]))

    def test_the_unselected_input_does_not_reach_the_output(self):
        nan, inf = float("nan"), float("inf")
        self.assertEqual(Switch().test_output(1.0, nan, True)[0], 1.0)
        self.assertEqual(Switch().test_output(inf, 2.0, False)[0], 2.0)

    def test_arrays_pass_through(self):
        x, y = np.r_[1.0, 2.0], np.r_[3.0, 4.0]
        nt.assert_array_equal(Switch().test_output(x, y, True)[0], x)
        nt.assert_array_equal(Switch().test_output(x, y, False)[0], y)

    def test_any_type_passes_through(self):
        self.assertEqual(Switch().test_output("a", "b", True)[0], "a")
        self.assertEqual(Switch().test_output({"k": 1}, {"k": 2}, False)[0], {"k": 2})

    def test_threshold_is_validated(self):
        for bad in ("a", True, float("nan"), [1], 1j):
            with self.assertRaises(ValueError, msg=repr(bad)):
                Switch(threshold=bad)
        s = Switch(threshold=1)
        with self.assertRaises(ValueError):
            s.set_param("threshold", "x")
        s.set_param("threshold", 0.5)
        self.assertEqual(s.threshold, 0.5)
        s.set_param("threshold", None)
        self.assertIsNone(s.threshold)

    def test_ports_are_named(self):
        s = Switch()
        self.assertEqual((s.nin, s.nout), (3, 1))
        self.assertEqual(list(s._inport_names), ["X", "Y", "S"])
        self.assertEqual(list(s._outport_names), ["Z"])
        for i, name in enumerate("XYS"):
            self.assertEqual(getattr(s, name).port, i)


class SwitchSimulationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False, quiet=True)

    def integrate(self, x, y, s, T=3.0, x0=0, solver_args=None, **kw):
        """Final integral of SWITCH(x, y, s); x, y and s are functions of the diagram."""
        bd = self.sim.blockdiagram()
        sw = bd.SWITCH(**kw)
        bd.connect(x(bd), sw.X)
        bd.connect(y(bd), sw.Y)
        bd.connect(s(bd), sw.S)
        area = bd.INTEGRATOR(x0=x0)
        bd.connect(sw, area)
        bd.compile(verbose=False)
        out = self.sim.run(bd, T=T, solver_args=solver_args or LOOSE)
        return out, np.asarray(out.x).reshape(len(out.t), -1)[-1]

    @staticmethod
    def two(bd):
        return bd.CONSTANT(2.0)

    @staticmethod
    def zero(bd):
        return bd.CONSTANT(0.0)

    @staticmethod
    def signal(f):
        def make(bd):
            b = bd.FUNCTION(f)
            bd.connect(bd.TIME(), b)
            return b

        return make

    def check_better_with_events(self, s, expected=4.0, **kw):
        out, x = self.integrate(self.two, self.zero, s, **kw)
        with mock.patch.object(CrossingMixin, "declare_thresholds"):
            _, x_without = self.integrate(self.two, self.zero, s, **kw)
        self.assertLess(abs(x[0] - expected), 1e-8)
        self.assertGreater(
            abs(x_without[0] - expected), 1e-4
        )  # what it protects against
        return out

    def test_float_selector_changing_at_zero(self):
        out = self.check_better_with_events(self.signal(lambda t: t - 1.0))
        self.assertEqual(out.stats.events_detected_total, 1)

    def test_float_selector_with_a_threshold(self):
        self.check_better_with_events(self.signal(lambda t: t), threshold=1.0)

    def test_selector_falling_through_the_threshold(self):
        # X for t < 1: the integral is 2
        self.check_better_with_events(
            self.signal(lambda t: 1.0 - t), expected=2.0, threshold=0.0
        )
        self.check_better_with_events(
            self.signal(lambda t: 1.0 - t + 1e-9), expected=2.0
        )

    def test_bool_selector(self):
        self.check_better_with_events(self.signal(lambda t: bool(t >= 1.0)))

    def test_int_selector(self):
        self.check_better_with_events(self.signal(lambda t: int(t >= 1.0)))

    def test_int_selector_through_nonzero_values_either_side_of_zero(self):
        # -1 for t < 1, 0 for 1 <= t < 2, 1 afterwards: nonzero, zero, nonzero
        f = self.signal(lambda t: -1 if t < 1.0 else (0 if t < 2.0 else 1))
        # X, then Y, then X: the integral of 2 over [0, 1] and [2, 3]
        self.check_better_with_events(f, expected=4.0)

    def test_vectors(self):
        _, x = self.integrate(
            lambda bd: bd.CONSTANT(np.r_[1.0, 2.0]),
            lambda bd: bd.CONSTANT(np.r_[0.0, 0.0]),
            self.signal(lambda t: t - 1.0),
            x0=[0, 0],
        )
        nt.assert_allclose(x, [2.0, 4.0], atol=1e-8)

    def test_a_selector_that_never_changes(self):
        out, x = self.integrate(self.two, self.zero, lambda bd: bd.CONSTANT(True))
        self.assertAlmostEqual(x[0], 6.0, delta=1e-9)
        self.assertEqual(out.stats.events_detected_total, 0)

    def test_x_and_y_of_different_type_are_rejected(self):
        with self.assertRaises(RuntimeError):
            self.integrate(
                self.two, lambda bd: bd.CONSTANT(0), self.signal(lambda t: t - 1.0)
            )

    def test_x_and_y_of_different_shape_are_rejected(self):
        with self.assertRaises(RuntimeError):
            self.integrate(
                lambda bd: bd.CONSTANT(np.r_[1.0, 2.0]),
                lambda bd: bd.CONSTANT(np.r_[1.0, 2.0, 3.0]),
                self.signal(lambda t: t - 1.0),
                x0=[0, 0],
            )

    def test_mismatch_is_caught_before_the_run_when_the_selector_never_changes(self):
        # S always selects X, so the output never changes type or shape: only the check
        # at the start of the run, not the run-time check for a change of signature, can
        # find that Y differs

        def always(bd):
            return bd.CONSTANT(True)

        with self.assertRaises(RuntimeError):
            self.integrate(self.two, lambda bd: bd.CONSTANT(0), always)
        with self.assertRaises(RuntimeError):
            self.integrate(
                lambda bd: bd.CONSTANT(np.r_[1.0, 2.0]),
                lambda bd: bd.CONSTANT(np.r_[1.0, 2.0, 3.0]),
                always,
                x0=[0, 0],
            )

    def test_an_array_selector_is_rejected(self):
        with self.assertRaises(RuntimeError):
            self.integrate(self.two, self.zero, lambda bd: bd.CONSTANT(np.r_[1.0, 2.0]))


if __name__ == "__main__":
    unittest.main()
