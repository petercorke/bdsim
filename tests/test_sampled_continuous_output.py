#!/usr/bin/env python3
"""Unit tests for output() return-value conventions in sampled.py and continuous.py.

Convention under test:
  output() returns a list with one element per output port.
  - scalar signal  → element is a Python/numpy scalar, not a length-1 ndarray
  - vector signal  → element is an ndarray of shape (n,)
"""

import unittest
import numpy as np
import numpy.testing as nt

from bdsim.components import Clock
from bdsim.blocks.sampled import ZOH, Integrator_S, Deriv_S, LTI_SS_S
from bdsim.blocks.continuous import Integrator, LTI_SS


def _clock(T=0.1):
    """Create a bare Clock (no BlockDiagram needed)."""
    return Clock(T)


def _is_scalar(v):
    return isinstance(v, (int, float, np.floating, np.integer))


def _is_1d_ndarray(v, size):
    return isinstance(v, np.ndarray) and v.ndim == 1 and v.size == size


# ---------------------------------------------------------------------------
# ZOH
# ---------------------------------------------------------------------------


class TestZOHOutput(unittest.TestCase):

    def test_scalar_state_returns_float(self):
        blk = ZOH(_clock(), x0=0.0)
        result = blk.output(t=0.0, inputs=[3.14], x=np.array([3.14]))
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertTrue(
            _is_scalar(result[0]),
            f"expected scalar, got {type(result[0])}: {result[0]}",
        )
        self.assertAlmostEqual(float(result[0]), 3.14)

    def test_scalar_not_length1_ndarray(self):
        blk = ZOH(_clock(), x0=0.0)
        result = blk.output(t=0.0, inputs=[7.0], x=np.array([7.0]))
        self.assertNotIsInstance(
            result[0], np.ndarray, "scalar ZOH must not return a length-1 ndarray"
        )

    def test_vector_state_returns_ndarray(self):
        blk = ZOH(_clock(), x0=[0.0, 0.0, 0.0])
        x = np.array([1.0, 2.0, 3.0])
        result = blk.output(t=0.0, inputs=[x], x=x)
        self.assertTrue(
            _is_1d_ndarray(result[0], 3), f"expected ndarray(3), got {type(result[0])}"
        )
        nt.assert_array_equal(result[0], [1.0, 2.0, 3.0])


# ---------------------------------------------------------------------------
# Integrator_S — regression guard (was already correct)
# ---------------------------------------------------------------------------


class TestIntegratorSOutput(unittest.TestCase):

    def test_scalar_returns_float(self):
        blk = Integrator_S(_clock(), x0=0.0)
        result = blk.output(t=0.0, u=[1.0], x=np.array([5.0]))
        self.assertTrue(_is_scalar(result[0]))
        self.assertAlmostEqual(float(result[0]), 5.0)

    def test_vector_returns_ndarray(self):
        blk = Integrator_S(_clock(), x0=[0.0, 0.0])
        result = blk.output(t=0.0, u=[np.zeros(2)], x=np.array([1.5, 2.5]))
        self.assertTrue(_is_1d_ndarray(result[0], 2))
        nt.assert_array_almost_equal(result[0], [1.5, 2.5])


# ---------------------------------------------------------------------------
# Deriv_S — regression guard (was already correct)
# ---------------------------------------------------------------------------


class TestDerivSOutput(unittest.TestCase):

    def test_scalar_returns_float(self):
        blk = Deriv_S(_clock(T=0.1), x0=0.0)
        # derivative: (u - x) / T = (1.0 - 0.0) / 0.1 = 10.0
        result = blk.output(t=0.1, u=[1.0], x=np.array([0.0]))
        self.assertTrue(_is_scalar(result[0]))
        self.assertAlmostEqual(float(result[0]), 10.0)

    def test_not_length1_ndarray(self):
        blk = Deriv_S(_clock(T=0.1), x0=0.0)
        result = blk.output(t=0.1, u=[1.0], x=np.array([0.0]))
        self.assertNotIsInstance(result[0], np.ndarray)


# ---------------------------------------------------------------------------
# Integrator (continuous) — regression guard (was already correct)
# ---------------------------------------------------------------------------


class TestIntegratorOutput(unittest.TestCase):

    def test_scalar_returns_float(self):
        blk = Integrator(x0=0.0)
        result = blk.output(t=0.0, u=[1.0], x=np.array([2.5]))
        self.assertTrue(_is_scalar(result[0]))
        self.assertAlmostEqual(float(result[0]), 2.5)

    def test_vector_returns_ndarray(self):
        blk = Integrator(x0=[0.0, 0.0])
        result = blk.output(t=0.0, u=[np.zeros(2)], x=np.array([1.0, -1.0]))
        self.assertTrue(_is_1d_ndarray(result[0], 2))
        nt.assert_array_almost_equal(result[0], [1.0, -1.0])


# ---------------------------------------------------------------------------
# LTI_SS (continuous)
# ---------------------------------------------------------------------------


class TestLTISSOutput(unittest.TestCase):

    def _siso(self):
        return LTI_SS(A=np.array([[-2.0]]), B=np.array([[1.0]]), C=np.array([[1.0]]))

    def _siso_D(self):
        return LTI_SS(
            A=np.array([[-1.0]]),
            B=np.array([[1.0]]),
            C=np.array([[1.0]]),
            D=np.array([[1.0]]),
        )

    def _mimo(self):
        return LTI_SS(
            A=np.array([[-1.0, 0.0], [0.0, -2.0]]),
            B=np.array([[1.0], [1.0]]),
            C=np.eye(2),
        )

    def test_siso_returns_float(self):
        result = self._siso().output(t=0.0, u=[1.0], x=np.array([3.0]))
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertTrue(
            _is_scalar(result[0]),
            f"SISO LTI_SS must return scalar, got {type(result[0])}",
        )
        self.assertAlmostEqual(float(result[0]), 3.0)

    def test_siso_D_returns_float(self):
        # y = C*x + D*u = 3 + 2 = 5
        result = self._siso_D().output(t=0.0, u=[2.0], x=np.array([3.0]))
        self.assertTrue(_is_scalar(result[0]))
        self.assertAlmostEqual(float(result[0]), 5.0)

    def test_siso_not_length1_ndarray(self):
        result = self._siso().output(t=0.0, u=[1.0], x=np.array([1.0]))
        self.assertNotIsInstance(result[0], np.ndarray)

    def test_siso_nin_nout(self):
        blk = self._siso()
        self.assertEqual(blk.nin, 1)
        self.assertEqual(blk.nout, 1)

    def test_mimo_nout(self):
        self.assertEqual(self._mimo().nout, 2)

    def test_mimo_returns_ndarray(self):
        result = self._mimo().output(t=0.0, u=[1.0], x=np.array([4.0, 5.0]))
        self.assertEqual(
            len(result), 1, "MIMO output list must have 1 element (one vector port)"
        )
        self.assertTrue(
            _is_1d_ndarray(result[0], 2),
            f"MIMO LTI_SS must return ndarray(2), got {type(result[0])}",
        )
        nt.assert_array_almost_equal(result[0], [4.0, 5.0])


# ---------------------------------------------------------------------------
# LTI_SS_S (sampled)
# ---------------------------------------------------------------------------


class TestLTISSSOutput(unittest.TestCase):

    def _siso(self):
        return LTI_SS_S(
            _clock(),
            A=np.array([[0.5]]),
            B=np.array([[1.0]]),
            C=np.array([[1.0]]),
        )

    def _siso_D(self):
        return LTI_SS_S(
            _clock(),
            A=np.array([[0.5]]),
            B=np.array([[1.0]]),
            C=np.array([[1.0]]),
            D=np.array([[2.0]]),
        )

    def _mimo(self):
        return LTI_SS_S(
            _clock(),
            A=np.array([[0.5, 0.0], [0.0, 0.8]]),
            B=np.array([[1.0], [1.0]]),
            C=np.eye(2),
        )

    def test_siso_returns_float(self):
        result = self._siso().output(t=0.0, u=[1.0], x=np.array([2.0]))
        self.assertTrue(
            _is_scalar(result[0]),
            f"SISO LTI_SS_S must return scalar, got {type(result[0])}",
        )
        self.assertAlmostEqual(float(result[0]), 2.0)

    def test_siso_D_returns_float(self):
        # y = C*x + D*u = 2 + 2*3 = 8
        result = self._siso_D().output(t=0.0, u=[3.0], x=np.array([2.0]))
        self.assertTrue(_is_scalar(result[0]))
        self.assertAlmostEqual(float(result[0]), 8.0)

    def test_siso_not_length1_ndarray(self):
        result = self._siso().output(t=0.0, u=[1.0], x=np.array([1.0]))
        self.assertNotIsInstance(result[0], np.ndarray)

    def test_siso_nin_nout(self):
        blk = self._siso()
        self.assertEqual(blk.nin, 1)
        self.assertEqual(blk.nout, 1)

    def test_mimo_nout(self):
        self.assertEqual(self._mimo().nout, 2)

    def test_mimo_returns_ndarray(self):
        result = self._mimo().output(t=0.0, u=[1.0], x=np.array([3.0, 7.0]))
        self.assertEqual(len(result), 1)
        self.assertTrue(_is_1d_ndarray(result[0], 2))
        nt.assert_array_almost_equal(result[0], [3.0, 7.0])


if __name__ == "__main__":
    unittest.main()
