#!/usr/bin/env python3
"""The run-time checks in BlockDiagram.evaluate() and the switch that turns them off."""

import io
import sys
import unittest
import warnings
from contextlib import redirect_stdout
from unittest.mock import patch

import numpy as np

import bdsim
from bdsim.block_types import ContinuousBlock, FunctionBlock
from bdsim.signature import Signature


_PASS = object()


class Misbehave(FunctionBlock):
    """Emits ``early`` (by default its input) until t > 0.5, then ``late``."""

    nin = 1
    nout = 1

    def __init__(self, late, early=_PASS, **blockargs):
        super().__init__(**blockargs)
        self.late = late
        self.early = early

    def output(self, t, inputs, x):
        if t > 0.5:
            return [self.late]
        return [inputs[0] if self.early is _PASS else self.early]


class BadList(FunctionBlock):
    """Returns the wrong number of outputs, or not a list at all."""

    nin = 1
    nout = 1

    def __init__(self, result, **blockargs):
        super().__init__(**blockargs)
        self.result = result

    def output(self, t, inputs, x):
        return self.result if t > 0.5 else [inputs[0]]


class BadDeriv(ContinuousBlock):
    nin = 1
    nout = 1

    def __init__(self, deriv, **blockargs):
        super().__init__(nstates=2, x0=[0.0, 0.0], **blockargs)
        self.deriv_value = deriv

    def output(self, t, inputs, x):
        return [x[0]]

    def deriv(self, t, inputs, x):
        return self.deriv_value


class ChecksTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False, quiet=True)

    def _run(self, source_value, block_factory, T=1.0, **run_args):
        """Run source -> block -> NULL; return (output text, exception or None)."""
        bd = self.sim.blockdiagram()
        src = bd.CONSTANT(source_value)
        block = block_factory(bd)
        bd.connect(src, block)
        bd.connect(block, bd.NULL(1))
        bd.compile(verbose=False)
        buf = io.StringIO()
        error = None
        with redirect_stdout(buf):
            try:
                self.sim.run(bd, T=T, **run_args)
            except Exception as err:
                error = err
        return buf.getvalue(), error, block


class FiniteTest(ChecksTestCase):
    def test_nan_stops_the_run(self):
        for late in (float("nan"), float("inf"), -float("inf"), np.float64("nan")):
            with self.subTest(late=late):
                text, error, block = self._run(1.0, lambda bd: Misbehave(late, bd=bd))
                self.assertIsInstance(error, RuntimeError)
                self.assertIn(block.name, text)
                self.assertIn("NaN or Inf", text)

    def test_nan_in_an_array(self):
        text, error, block = self._run(
            np.r_[1.0, 2.0], lambda bd: Misbehave(np.r_[1.0, np.nan], bd=bd)
        )
        self.assertIsInstance(error, RuntimeError)
        self.assertIn("NaN or Inf", text)

    def test_complex(self):
        text, error, block = self._run(
            1j, lambda bd: Misbehave(complex(1, float("nan")), bd=bd)
        )
        self.assertIsInstance(error, RuntimeError)

    def test_ints_bools_and_objects_are_not_examined(self):
        for early, late in [(1, 2), (True, False), ("a", "b"), ([1], [float("nan")])]:
            with self.subTest(early=early):
                text, error, block = self._run(
                    0, lambda bd: Misbehave(late, early=early, bd=bd)
                )
                self.assertIsNone(error, text)

    def test_finite_values_pass(self):
        text, error, block = self._run(1.0, lambda bd: Misbehave(2.5, bd=bd))
        self.assertIsNone(error, text)

    def test_check_off_lets_nan_through(self):
        text, error, block = self._run(
            1.0, lambda bd: Misbehave(float("nan"), bd=bd), check=False
        )
        self.assertIsNone(error, text)


class OutputFormTest(ChecksTestCase):
    def test_wrong_length(self):
        text, error, block = self._run(1.0, lambda bd: BadList([1.0, 2.0], bd=bd))
        self.assertIsInstance(error, RuntimeError)
        self.assertIn("incorrect length", text)

    def test_not_a_list(self):
        text, error, block = self._run(1.0, lambda bd: BadList(3.0, bd=bd))
        self.assertIsInstance(error, RuntimeError)
        self.assertIn("must be a list", text)


class DriftTest(ChecksTestCase):
    """The signature recorded at compile time is checked at every evaluation."""

    def test_type_change_stops_the_run(self):
        text, error, block = self._run(1, lambda bd: Misbehave(2.5, bd=bd))
        self.assertIsInstance(error, RuntimeError)
        self.assertIn(block.name, text)
        self.assertIn("int", text)
        self.assertIn("float", text)
        self.assertIn("t=", text)

    def test_shape_change_stops_the_run(self):
        text, error, block = self._run(
            np.zeros(3), lambda bd: Misbehave(np.zeros(4), bd=bd)
        )
        self.assertIsInstance(error, RuntimeError)
        self.assertIn("(3,)", text)
        self.assertIn("(4,)", text)

    def test_dtype_change_stops_the_run(self):
        text, error, block = self._run(
            np.zeros(3), lambda bd: Misbehave(np.zeros(3, dtype=int), bd=bd)
        )
        self.assertIsInstance(error, RuntimeError)

    def test_list_to_array_stops_the_run(self):
        text, error, block = self._run(
            0, lambda bd: Misbehave(np.r_[1.0, 2.0], early=[1.0, 2.0], bd=bd)
        )
        self.assertIsInstance(error, RuntimeError)

    def test_python_and_numpy_scalars_of_one_kind_agree(self):
        for early, late in [
            (1.0, np.float64(2.0)),
            (np.float64(1.0), 2.0),
            (1, np.int64(2)),
        ]:
            with self.subTest(early=early, late=late):
                text, error, block = self._run(early, lambda bd: Misbehave(late, bd=bd))
                self.assertIsNone(error, text)

    def test_size_one_vector_collapse_is_not_drift(self):
        # a (1,) array is published as a scalar, so it matches a scalar wire
        text, error, block = self._run(
            1.0, lambda bd: Misbehave(np.array([2.0]), bd=bd)
        )
        self.assertIsNone(error, text)

    def test_unobserved_wires_are_not_checked(self):
        # compile(evaluate=False) records nothing to compare with
        bd = self.sim.blockdiagram()
        src = bd.CONSTANT(1)
        block = Misbehave(2.5, bd=bd)
        bd.connect(src, block)
        bd.connect(block, bd.NULL(1))
        bd.compile(evaluate=False, verbose=False)
        with redirect_stdout(io.StringIO()):
            self.sim.run(bd, T=1.0)

    def test_check_off_allows_drift(self):
        text, error, block = self._run(1, lambda bd: Misbehave(2.5, bd=bd), check=False)
        self.assertIsNone(error, text)


class DerivShapeTest(ChecksTestCase):
    def test_wrong_shape_stops_the_run(self):
        text, error, block = self._run(1.0, lambda bd: BadDeriv(np.zeros(3), bd=bd))
        self.assertIsInstance(error, RuntimeError)
        self.assertIn("wrong shape", text)

    def test_not_an_array(self):
        text, error, block = self._run(1.0, lambda bd: BadDeriv([0.0, 0.0], bd=bd))
        self.assertIsInstance(error, RuntimeError)
        self.assertIn("ndarray", text)


class SwitchTest(unittest.TestCase):
    """--no-check, the check option, and the deprecated checkfinite."""

    def test_default_is_on(self):
        sim = bdsim.BDSim(graphics=None, progress=False, banner=False)
        self.assertTrue(sim.options.check)

    def test_keyword_option(self):
        sim = bdsim.BDSim(graphics=None, progress=False, banner=False, check=False)
        self.assertFalse(sim.options.check)

    def test_command_line_switch(self):
        with patch.object(sys, "argv", ["prog", "--no-check"]):
            sim = bdsim.BDSim(graphics=None, progress=False, banner=False)
        self.assertFalse(sim.options.check)

    def test_run_argument_overrides_the_option(self):
        sim = bdsim.BDSim(
            graphics=None, progress=False, banner=False, quiet=True, check=False
        )
        bd = sim.blockdiagram()
        bd.connect(bd.CONSTANT(1.0), Misbehave(float("nan"), bd=bd))
        bd.connect(bd.blocklist[-1], bd.NULL(1))
        bd.compile(verbose=False)
        with redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
            sim.run(bd, T=1.0, check=True)

    def test_option_off_is_used_by_run(self):
        sim = bdsim.BDSim(
            graphics=None, progress=False, banner=False, quiet=True, check=False
        )
        bd = sim.blockdiagram()
        bd.connect(bd.CONSTANT(1.0), Misbehave(float("nan"), bd=bd))
        bd.connect(bd.blocklist[-1], bd.NULL(1))
        bd.compile(verbose=False)
        with redirect_stdout(io.StringIO()):
            sim.run(bd, T=1.0)  # no error: the option turned the checks off

    def test_checkfinite_is_deprecated_and_means_check(self):
        sim = bdsim.BDSim(graphics=None, progress=False, banner=False, quiet=True)
        bd = sim.blockdiagram()
        bd.connect(bd.CONSTANT(1.0), Misbehave(float("nan"), bd=bd))
        bd.connect(bd.blocklist[-1], bd.NULL(1))
        bd.compile(verbose=False)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with redirect_stdout(io.StringIO()):
                sim.run(bd, T=1.0, checkfinite=False)
        self.assertTrue(any(issubclass(w.category, DeprecationWarning) for w in caught))


class SignatureMatchTest(unittest.TestCase):
    def test_same_kind_matches(self):
        self.assertTrue(Signature.of(1.0).matches(Signature.of(np.float64(2.0))))
        self.assertTrue(Signature.of(1).matches(Signature.of(np.int32(2))))
        self.assertTrue(Signature.of(True).matches(Signature.of(np.True_)))
        self.assertTrue(Signature.of(1j).matches(Signature.of(np.complex128(1))))

    def test_different_kinds_differ(self):
        self.assertFalse(Signature.of(1).matches(Signature.of(1.0)))
        self.assertFalse(Signature.of(True).matches(Signature.of(1)))
        self.assertFalse(Signature.of(1.0).matches(Signature.of(1j)))

    def test_arrays_need_shape_and_dtype(self):
        a = Signature.of(np.zeros(3))
        self.assertTrue(a.matches(Signature.of(np.ones(3))))
        self.assertFalse(a.matches(Signature.of(np.zeros(4))))
        self.assertFalse(a.matches(Signature.of(np.zeros(3, dtype=int))))
        self.assertFalse(a.matches(Signature.of(1.0)))

    def test_other_types_must_be_identical(self):
        self.assertTrue(Signature.of([1]).matches(Signature.of([1, 2])))
        self.assertFalse(Signature.of([1]).matches(Signature.of((1,))))
        self.assertTrue(Signature.of("a").matches(Signature.of("bb")))
        self.assertTrue(Signature.of(None).matches(Signature.of(None)))


if __name__ == "__main__":
    unittest.main()
