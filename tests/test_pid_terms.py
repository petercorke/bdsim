#!/usr/bin/env python3
"""PID and PID_S: which terms are built, and the pure-P case.

``terms=None`` builds P, plus I and D if their gain is non-zero.  ``terms="PID"`` (or
"P", "PI", "PD") builds exactly those terms, even at zero gain, so a term can be
tuned later.
"""

import io
import itertools
import unittest
from contextlib import redirect_stdout

import numpy as np
import numpy.testing as nt

import bdsim

STRUCTURES = ("parallel", "series", "ideal", "standard")


class PidTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False, quiet=True)

    def make(self, kind, bd=None, **kwargs):
        """A PID or PID_S in a diagram of its own."""
        bd = bd or self.sim.blockdiagram()
        if kind == "PID":
            return bd, bd.PID(**kwargs)
        return bd, bd.PID_S(bd.clock(0.1), **kwargs)

    @staticmethod
    def inner_types(block):
        return sorted(b.type for b in block.subsystem.blocklist)

    def terms_built(self, block):
        """The terms present, from the blocks inside."""
        types = self.inner_types(block)
        built = "P"  # the proportional block is a gain, as is nothing else here
        if "integrator" in types or "integrator_s" in types:
            built += "I"
        if "deriv" in types or "deriv_s" in types:
            built += "D"
        return built


class DefaultTermsTest(PidTestCase):
    def test_terms_follow_the_non_zero_gains(self):
        for kind in ("PID", "PID_S"):
            for kwargs, expected in [
                (dict(P=1.0), "P"),
                (dict(P=1.0, I=0.5), "PI"),
                (dict(P=1.0, D=0.1), "PD"),
                (dict(P=1.0, I=0.5, D=0.1), "PID"),
                (dict(D=0.1), "PD"),  # P is always built
            ]:
                with self.subTest(kind=kind, **kwargs):
                    _, block = self.make(kind, **kwargs)
                    self.assertEqual(self.terms_built(block), expected)

    def test_pure_p_works_in_every_structure(self):
        # parallel and ideal used to fail with UnboundLocalError
        for kind, structure in itertools.product(("PID", "PID_S"), STRUCTURES):
            with self.subTest(kind=kind, structure=structure):
                _, block = self.make(kind, P=2.0, structure=structure)
                self.assertEqual(self.terms_built(block), "P")

    def test_nothing_is_printed(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.make("PID", P=1.0, I=0.5)
        self.assertEqual(buf.getvalue(), "")


class ExplicitTermsTest(PidTestCase):
    def test_terms_are_built_even_at_zero_gain(self):
        for kind in ("PID", "PID_S"):
            for terms in ("P", "PI", "PD", "PID"):
                with self.subTest(kind=kind, terms=terms):
                    _, block = self.make(kind, P=1.0, terms=terms)
                    self.assertEqual(self.terms_built(block), terms)

    def test_every_structure_and_terms_combination_compiles(self):
        for kind, structure, terms in itertools.product(
            ("PID", "PID_S"), STRUCTURES, ("P", "PI", "PD", "PID")
        ):
            with self.subTest(kind=kind, structure=structure, terms=terms):
                bd, block = self.make(kind, P=1.0, structure=structure, terms=terms)
                bd.connect(bd.CONSTANT(0.0), block[0])
                bd.connect(bd.CONSTANT(1.0), block[1])
                bd.connect(block, bd.NULL(1))
                bd.compile(verbose=False)

    def test_a_term_that_is_present_but_zero_changes_nothing(self):
        # an integrator or derivative with gain 0 contributes exactly nothing
        for kind in ("PID", "PID_S"):
            for kwargs in (dict(P=2.0), dict(P=2.0, I=0.5), dict(P=2.0, D=0.1)):
                with self.subTest(kind=kind, **kwargs):
                    # a diagram with no states is sampled only at its end points,
                    # so compare the final value, not the whole trace
                    default = self.run_open_loop(kind, **kwargs)
                    full = self.run_open_loop(kind, terms="PID", **kwargs)
                    nt.assert_allclose(full[-1], default[-1], atol=1e-12)

    def run_open_loop(self, kind, **kwargs):
        bd, block = self.make(kind, **kwargs)
        bd.connect(bd.CONSTANT(0.25), block[0])
        bd.connect(bd.CONSTANT(1.0), block[1])
        bd.connect(block, bd.NULL(1))
        bd.compile(verbose=False)
        return self.sim.run(bd, T=1.0, dt=0.1, watch=[block]).y[:, 0]

    def test_pure_p_output_is_p_times_the_error(self):
        for kind in ("PID", "PID_S"):
            for structure in STRUCTURES:
                with self.subTest(kind=kind, structure=structure):
                    y = self.run_open_loop(kind, P=2.0, structure=structure)
                    nt.assert_allclose(np.abs(y), 2.0 * 0.75, atol=1e-12)


class ErrorsTest(PidTestCase):
    def test_terms_must_be_p_pi_pd_or_pid(self):
        for kind in ("PID", "PID_S"):
            for bad in ("ID", "", "PIDX", "pid", "D", "I", "DP"):
                with (
                    self.subTest(kind=kind, terms=bad),
                    self.assertRaises(Exception) as cm,
                ):
                    self.make(kind, P=1.0, terms=bad)
                self.assertIn("terms", str(cm.exception))

    def test_a_gain_for_a_term_that_is_not_built_is_an_error(self):
        for kind in ("PID", "PID_S"):
            with self.subTest(kind=kind), self.assertRaises(Exception) as cm:
                self.make(kind, P=1.0, I=0.5, terms="PD")
            self.assertIn("I", str(cm.exception))
            self.assertIn("terms", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
