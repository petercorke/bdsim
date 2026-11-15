#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Define fundamental blocks available for use in block diagrams.

Each class _MyClass in this module becomes a method MYCLASS() of the Simulation object.
This is done in Simulation.__init__()

All arguments to MYCLASS() must be named arguments and passed through to the constructor
_MyClass.__init__().

These classses must subclass one of

- Source, output is a constant or function of time
- Sink, input only
- Transfer, output is a function of state self.x (no pass through)
- Function, output is a direct function of input

These classes all subclass Block.

Every class defined here provides several methods:

- __init__, mandatory to handle block specific parameter arguments
- reset,
- output, to compute the output value as a function of self.inputs which is
  a dict indexed by input number
- deriv, for Transfer subclass only, return the state derivative vector
- check, to validate parameter settings

Created on Thu May 21 06:39:29 2020

@author: Peter Corke
"""

import numpy as np
import math

import bdsim
from bdsim import Clock
from bdsim.blocks.continuous import Integrator, LTI_SISO, LTI_SS, _tf2ss
from bdsim.blocks.sampled import LTI_SS_S
from bdsim.blocks.spatial import PoseIntegrator
from spatialmath import SE3, Twist3

import unittest
import numpy.testing as nt


class TransferTest(unittest.TestCase):
    def test_LTI_SS(self):
        A = np.array([[1, 2], [3, 4]])
        B = np.array([5, 6])
        C = np.array([7, 8])
        block = LTI_SS(A=A, B=B, C=C, x0=[30, 40])
        x = np.r_[10, 11]
        u = -2
        nt.assert_equal(block.test_deriv(u, x=x), A @ x + B * u)
        nt.assert_equal(block.test_output(u, x=x)[0], C @ x)
        nt.assert_equal(block.getstate0(), np.r_[30, 40])

        A = np.array([[1, 2], [3, 4]])
        B = np.array([[5], [6]])
        C = np.array([[7, 8]])
        block = LTI_SS(A=A, B=B, C=C, x0=[30, 40])
        x = np.r_[10, 11]
        u = -2
        nt.assert_equal(block.test_deriv(u, x=x), A @ x + B @ np.r_[u])
        nt.assert_equal(block.test_output(u, x=x)[0], C @ x)
        nt.assert_equal(block.getstate0(), np.r_[30, 40])

    def test_LTI_SISO(self):
        from scipy.signal import ss2tf

        N = [2, 1]
        D = [2, 4, 6]
        Nr = np.array([0, 2, 1]) / D[0]
        Dr = np.array(D) / D[0]

        # we test by converting the state-space matrices back to a transfer function and
        # comparing with the original numerator and denominator coefficients, which is a
        # more robust test than comparing the A, B, C matrices directly since there are
        # many equivalent state-space realizations of the same transfer function.

        block = LTI_SISO(num=N, den=D)
        n, d = ss2tf(block.A, block.B, block.C, np.zeros((1, 1)), input=0)
        nt.assert_almost_equal(n[0], Nr)
        nt.assert_almost_equal(d, Dr)

        block = LTI_SISO(num=N, den=D, form="ocf", order="backward")
        n, d = ss2tf(block.A, block.B, block.C, np.zeros((1, 1)), input=0)
        nt.assert_almost_equal(n[0], Nr)
        nt.assert_almost_equal(d, Dr)

        block = LTI_SISO(num=N, den=D, form="ocf", order="forward")
        n, d = ss2tf(block.A, block.B, block.C, np.zeros((1, 1)), input=0)
        nt.assert_almost_equal(n[0], Nr)
        nt.assert_almost_equal(d, Dr)

        block = LTI_SISO(num=N, den=D, form="ccf", order="backward")
        n, d = ss2tf(block.A, block.B, block.C, np.zeros((1, 1)), input=0)
        nt.assert_almost_equal(n[0], Nr)
        nt.assert_almost_equal(d, Dr)

        block = LTI_SISO(num=N, den=D, form="ccf", order="forward")
        n, d = ss2tf(block.A, block.B, block.C, np.zeros((1, 1)), input=0)
        nt.assert_almost_equal(n[0], Nr)
        nt.assert_almost_equal(d, Dr)

    def test_integrator(self):
        block = Integrator(x0=30)
        self.assertEqual(block.nstates, 1)
        self.assertEqual(block.ndstates, 0)
        x = np.r_[10]
        u = -2
        nt.assert_equal(block.test_deriv(u, x=x), u)
        nt.assert_equal(block.getstate0(), np.r_[30])

        # limits do not alter the derivative of a free state, only a held one
        block = Integrator(x0=5, min=-10, max=10)  # state is scalar
        x = np.r_[9]
        u = 2
        nt.assert_equal(block.test_deriv(u, x=x), 2)

        block._mode[0] = Integrator._UPPER
        nt.assert_equal(block.test_deriv(u, x=np.r_[10]), 0)

        block._mode[0] = Integrator._LOWER
        nt.assert_equal(block.test_deriv(-u, x=np.r_[-10]), 0)

        block.reset()
        nt.assert_equal(block.test_deriv(u, x=x), 2)

    def test_integrator_vec(self):
        block = Integrator(x0=[5, 6])  # state is vector
        self.assertEqual(block.nstates, 2)
        self.assertEqual(block.ndstates, 0)

        nt.assert_equal(block.getstate0(), np.r_[5, 6])

        x = np.r_[10, 11]
        u = np.r_[-2, 3]
        nt.assert_equal(block.test_output(u, x=x)[0], x)
        nt.assert_equal(block.test_deriv(u, x=x), u)

        # test with limits: only the held element stops
        block = Integrator(x0=[5, 6], min=[-5, -10], max=[5, 10])  # state is vector
        block._mode[:] = [Integrator._UPPER, Integrator._FREE]
        u = np.r_[2, 3]
        nt.assert_equal(block.test_deriv(u, x=np.r_[5, 0]), [0, 3])

        block._mode[:] = [Integrator._FREE, Integrator._LOWER]
        u = np.r_[-2, -3]
        nt.assert_equal(block.test_deriv(u, x=np.r_[0, -10]), [-2, 0])

    def test_pose_integrator_s(self):

        T = SE3.Rand()
        block = PoseIntegrator(x0=T)
        nt.assert_equal(block.getstate0(), Twist3(T))

        self.assertEqual(block.nstates, 6)
        self.assertEqual(block.ndstates, 0)

        x = block.getstate0()
        u = np.r_[1, 2, 3, 4, 5, 6]

        nt.assert_equal(block.test_output(u, x=x)[0], T)

        nt.assert_almost_equal(block.test_deriv(u, x=x), u)


class ContinuousSim(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(
            graphics=None, progress=False, banner=False, sysargs=False, quiet=True
        )

    def test_integrator(self):
        bd = self.sim.blockdiagram()

        signal = bd.STEP(T=1)
        integrator = bd.INTEGRATOR(x0=-1)
        sink = bd.NULL()
        bd.connect(signal, integrator)
        bd.connect(integrator, sink)
        bd.compile()
        out = self.sim.run(bd, T=5, watch=[integrator])
        nt.assert_almost_equal(out.y[0, 0], -1)
        nt.assert_almost_equal(out.y[-1, 0], 3, decimal=2)

    def test_integrator_gain(self):
        bd = self.sim.blockdiagram()

        signal = bd.STEP(T=1)
        integrator = bd.INTEGRATOR(gain=2, x0=-1)
        sink = bd.NULL()
        bd.connect(signal, integrator)
        bd.connect(integrator, sink)
        bd.compile()
        out = self.sim.run(bd, T=5, watch=[integrator])
        nt.assert_almost_equal(out.y[0, 0], -1)
        nt.assert_almost_equal(out.y[-1, 0], 7, decimal=2)

    def test_integrator_min(self):
        bd = self.sim.blockdiagram()

        signal = bd.STEP(T=1, on=-1)
        integrator = bd.INTEGRATOR(min=-2, max=2)
        sink = bd.NULL()
        bd.connect(signal, integrator)
        bd.connect(integrator, sink)
        bd.compile()
        out = self.sim.run(bd, T=5, watch=[integrator])
        nt.assert_almost_equal(out.y[0, 0], 0)
        nt.assert_almost_equal(out.y[-1, 0], -2, decimal=2)

    def test_integrator_max(self):
        bd = self.sim.blockdiagram()

        signal = bd.STEP(T=1, on=1)
        integrator = bd.INTEGRATOR(min=-2, max=2)
        sink = bd.NULL()
        bd.connect(signal, integrator)
        bd.connect(integrator, sink)
        bd.compile()
        out = self.sim.run(bd, T=5, watch=[integrator])
        nt.assert_almost_equal(out.y[0, 0], 0)
        nt.assert_almost_equal(out.y[-1, 0], 2, decimal=2)

    def test_deriv(self):
        bd = self.sim.blockdiagram()

        signal = bd.RAMP(T=1)
        deriv = bd.DERIV(alpha=2)
        sink = bd.NULL()
        bd.connect(signal, deriv)
        bd.connect(deriv, sink)
        bd.compile()
        bd.report_lists()
        bd.report_schedule()
        out = self.sim.run(bd, T=5, watch=[deriv, signal])
        nt.assert_almost_equal(out.y[0, 0], 0)
        nt.assert_almost_equal(out.y[-1, 0], 1, decimal=2)

    def test_deriv_gain(self):
        bd = self.sim.blockdiagram()

        signal = bd.RAMP(T=1)
        deriv = bd.DERIV(alpha=2, gain=2)
        sink = bd.NULL()
        bd.connect(signal, deriv)
        bd.connect(deriv, sink)
        bd.compile()
        out = self.sim.run(bd, T=5, watch=[deriv])
        nt.assert_almost_equal(out.y[0, 0], 0)
        nt.assert_almost_equal(out.y[-1, 0], 2, decimal=2)

    def test_deriv2(self):
        bd = self.sim.blockdiagram()

        signal = bd.RAMP(T=1)
        deriv = bd.DERIV2(wn=5, zeta=0.7071)
        sink = bd.NULL()
        bd.connect(signal, deriv)
        bd.connect(deriv, sink)
        bd.compile()
        out = self.sim.run(bd, T=5, watch=[deriv])
        nt.assert_almost_equal(out.y[0, 0], 0)
        nt.assert_almost_equal(out.y[-1, 0], 1, decimal=2)

    def test_deriv2_gain(self):
        bd = self.sim.blockdiagram()

        signal = bd.RAMP(T=1)
        deriv = bd.DERIV2(wn=5, zeta=0.7071, gain=2)
        sink = bd.NULL()
        bd.connect(signal, deriv)
        bd.connect(deriv, sink)
        bd.compile()
        out = self.sim.run(bd, T=5, watch=[deriv])
        nt.assert_almost_equal(out.y[0, 0], 0)
        nt.assert_almost_equal(out.y[-1, 0], 2, decimal=2)

    def test_pid(self):
        bd = self.sim.blockdiagram()

        signal = bd.RAMP(T=1)
        sink1 = bd.NULL()
        sink2 = bd.NULL()
        sink3 = bd.NULL()
        zero = bd.CONSTANT(0.0, name="zero")

        P, I, D = 5, 3, 2
        pid1 = bd.PID(P=P, I=I, D=D)
        pid2 = bd.PID(P=P, I=I / P, D=I / P, structure="ideal")
        Ps = (P + math.sqrt(P**2 - 4 * I * D)) / 2.0
        pid3 = bd.PID(P=Ps, I=I / Ps, D=D / Ps, structure="series")

        bd.connect(signal, pid1[1], pid2[1], pid3[1])  # reference
        bd.connect(zero, pid1[0], pid2[0], pid3[0])  # plant output
        bd.connect(pid1, sink1)
        bd.connect(pid2, sink2)
        bd.connect(pid3, sink3)

        bd.compile()
        out = self.sim.run(bd, T=5, watch=[pid1, pid2, pid3])

        # results are not quite the same, but close enough for this test
        nt.assert_almost_equal(out.y[0, 0], 0)
        nt.assert_almost_equal(out.y[-1, 0], 46, decimal=1)
        nt.assert_almost_equal(out.y[0, 1], 0)
        nt.assert_almost_equal(out.y[-1, 1], 47, decimal=1)
        nt.assert_almost_equal(out.y[0, 2], 0)
        nt.assert_almost_equal(out.y[-1, 2], 44, decimal=1)

    def test_pd(self):
        bd = self.sim.blockdiagram()

        signal = bd.RAMP(T=1)
        sink1 = bd.NULL()
        sink2 = bd.NULL()
        sink3 = bd.NULL()
        zero = bd.CONSTANT(0.0, name="zero")

        P, I, D = 5, 0, 2
        pid1 = bd.PID(P=P, I=I, D=D)
        pid2 = bd.PID(P=P, I=I / P, D=D / P, structure="ideal")
        Ps = (P + math.sqrt(P**2 - 4 * I * D)) / 2.0
        pid3 = bd.PID(P=Ps, I=I / Ps, D=D / Ps, structure="series")

        bd.connect(signal, pid1[1], pid2[1], pid3[1])  # reference
        bd.connect(zero, pid1[0], pid2[0], pid3[0])  # plant output
        bd.connect(pid1, sink1)
        bd.connect(pid2, sink2)
        bd.connect(pid3, sink3)

        bd.compile()
        out = self.sim.run(bd, T=5, watch=[pid1, pid2, pid3])

        # results are not quite the same, but close enough for this test
        nt.assert_almost_equal(out.y[0, 0], 0)
        nt.assert_almost_equal(out.y[-1, 0], 22, decimal=1)
        nt.assert_almost_equal(out.y[0, 1], 0)
        nt.assert_almost_equal(out.y[-1, 1], 22, decimal=1)
        nt.assert_almost_equal(out.y[0, 2], 0)
        nt.assert_almost_equal(out.y[-1, 2], 22, decimal=1)

    def test_pi(self):
        bd = self.sim.blockdiagram()

        signal = bd.RAMP(T=1)
        sink1 = bd.NULL()
        sink2 = bd.NULL()
        sink3 = bd.NULL()
        zero = bd.CONSTANT(0.0, name="zero")

        P, I, D = 5, 3, 0
        pid1 = bd.PID(P=P, I=I, D=D)
        pid2 = bd.PID(P=P, I=I / P, D=I / P, structure="ideal")
        Ps = (P + math.sqrt(P**2 - 4 * I * D)) / 2.0
        pid3 = bd.PID(P=Ps, I=I / Ps, D=D / Ps, structure="series")

        bd.connect(signal, pid1[1], pid2[1], pid3[1])  # reference
        bd.connect(zero, pid1[0], pid2[0], pid3[0])  # plant output
        bd.connect(pid1, sink1)
        bd.connect(pid2, sink2)
        bd.connect(pid3, sink3)

        bd.compile()
        out = self.sim.run(bd, T=5, watch=[pid1, pid2, pid3])

        # results are not quite the same, but close enough for this test
        nt.assert_almost_equal(out.y[0, 0], 0)
        nt.assert_almost_equal(out.y[-1, 0], 44, decimal=1)
        nt.assert_almost_equal(out.y[0, 1], 0)
        nt.assert_almost_equal(out.y[-1, 1], 47, decimal=1)
        nt.assert_almost_equal(out.y[0, 2], 0)
        nt.assert_almost_equal(out.y[-1, 2], 44, decimal=1)


class Tf2SsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.N = np.array([1, 2, 3])
        cls.D = np.array([2, 8, 10, 12])

        # Example System: (s^2 + 2s + 3) / (2s^3 + 8s^2 + 10s + 12)
        # Normalized: (0.5s^2 + s + 1.5) / (s^3 + 4s^2 + 5s + 6)
        # a_coeffs = [4, 5, 6], b_coeffs = [0.5, 1, 1.5]

    def test_ccf_forward(self):
        """CCF Forward: Bottom-row coeffs, Super-diagonal 1s"""
        A, B, C, D = _tf2ss(self.N, self.D, form="ccf", order="forward")

        expected_A = [[0, 1, 0], [0, 0, 1], [-6, -5, -4]]  # Coeffs reversed: a3, a2, a1
        expected_B = [[0], [0], [1]]
        expected_C = [[1.5, 1.0, 0.5]]  # b3, b2, b1

        nt.assert_array_equal(A, expected_A)
        nt.assert_array_equal(B, expected_B)
        nt.assert_array_equal(C, expected_C)

    def test_ccf_backward(self):
        """CCF Backward: Top-row coeffs, Sub-diagonal 1s (Scipy/Matlab style)"""
        A, B, C, D = _tf2ss(self.N, self.D, form="ccf", order="backward")

        expected_A = [[-4, -5, -6], [1, 0, 0], [0, 1, 0]]  # Coeffs original: a1, a2, a3
        expected_B = [[1], [0], [0]]
        expected_C = [[0.5, 1.0, 1.5]]  # b1, b2, b3

        nt.assert_array_equal(A, expected_A)
        nt.assert_array_equal(B, expected_B)
        nt.assert_array_equal(C, expected_C)

    def test_ocf_forward(self):
        """OCF Forward: Right-column coeffs, Sub-diagonal 1s"""
        A, B, C, D = _tf2ss(self.N, self.D, form="ocf", order="forward")

        expected_A = [[0, 0, -6], [1, 0, -5], [0, 1, -4]]
        expected_B = [[1.5], [1.0], [0.5]]
        expected_C = [[0, 0, 1]]

        nt.assert_array_equal(A, expected_A)
        nt.assert_array_equal(B, expected_B)
        nt.assert_array_equal(C, expected_C)

    def test_ocf_backward(self):
        """OCF Backward: Left-column coeffs, Super-diagonal 1s"""
        A, B, C, D = _tf2ss(self.N, self.D, form="ocf", order="backward")

        expected_A = [[-4, 1, 0], [-5, 0, 1], [-6, 0, 0]]
        expected_B = [[0.5], [1.0], [1.5]]
        expected_C = [[1, 0, 0]]

        nt.assert_array_equal(A, expected_A)
        nt.assert_array_equal(B, expected_B)
        nt.assert_array_equal(C, expected_C)

    def test_normalization_and_padding(self):
        """Ensure small numerator is padded and unnormalized denominator is handled."""
        # G(s) = 5 / (10s^2 + 20s + 30) -> 0.5 / (s^2 + 2s + 3)
        n_small = np.array([5])
        d_unnorm = np.array([10, 20, 30])

        A, B, C, D = _tf2ss(n_small, d_unnorm, form="ccf", order="forward")

        nt.assert_array_equal(A, [[0, 1], [-3, -2]])
        nt.assert_array_equal(C, [[0.5, 0]])  # b2=0.5, b1=0


class LTISSFeedthroughMatrixTest(unittest.TestCase):
    """The D argument of LTI_SS and LTI_SS_S: its forms, its errors, and the flag."""

    def make(self, D, sampled=False, nin=1, nout=1):
        n = 2
        A = np.eye(n)
        B = np.ones((n, nin)) if nin > 1 else np.ones(n)
        C = np.ones((nout, n)) if nout > 1 else np.ones(n)
        if sampled:
            return LTI_SS_S(Clock(2, "Hz"), A=A, B=B, C=C, D=D, x0=[0.0, 0.0])
        return LTI_SS(A=A, B=B, C=C, D=D)

    def both(self):
        return (False, True)

    def test_no_d_is_no_feedthrough(self):
        for sampled in self.both():
            with self.subTest(sampled=sampled):
                block = self.make(None, sampled)
                self.assertIsNone(block.D)
                self.assertFalse(block.feedthrough)

    def test_zero_d_is_no_feedthrough_and_is_not_stored(self):
        for sampled in self.both():
            with self.subTest(sampled=sampled):
                block = self.make(np.zeros((1, 1)), sampled)
                self.assertIsNone(block.D)
                self.assertFalse(block.feedthrough)

    def test_d_as_a_number(self):
        for sampled in self.both():
            with self.subTest(sampled=sampled):
                block = self.make(2.0, sampled)
                self.assertTrue(block.feedthrough)
                nt.assert_array_equal(block.D, [[2.0]])

    def test_d_as_a_flat_list_or_array(self):
        for sampled in self.both():
            with self.subTest(sampled=sampled):
                for D in ([1.0, 2.0, 3.0, 4.0], np.array([1.0, 2.0, 3.0, 4.0])):
                    block = self.make(D, sampled, nin=2, nout=2)
                    nt.assert_array_equal(block.D, [[1.0, 2.0], [3.0, 4.0]])

    def test_d_as_a_matrix_is_kept(self):
        for sampled in self.both():
            with self.subTest(sampled=sampled):
                D = np.array([[1.0, 0.0], [0.0, 3.0]])
                block = self.make(D, sampled, nin=2, nout=2)
                nt.assert_array_equal(block.D, D)
                self.assertTrue(block.feedthrough)

    def test_d_of_the_wrong_shape_is_refused_and_says_what_it_should_be(self):
        for sampled in self.both():
            with self.subTest(sampled=sampled):
                with self.assertRaises(ValueError) as cm:
                    self.make(np.ones((2, 2)), sampled)
                self.assertIn("1x1", str(cm.exception))
                self.assertIn("(2, 2)", str(cm.exception))
                with self.assertRaises(ValueError):
                    self.make([1.0, 2.0, 3.0], sampled, nin=2, nout=2)

    def test_the_setter_agrees_with_the_constructor(self):
        for sampled in self.both():
            with self.subTest(sampled=sampled):
                block = self.make(2.0, sampled)
                block.set_param("D", 3.0)
                nt.assert_array_equal(block.D, [[3.0]])
                with self.assertRaises(ValueError):
                    block.set_param("D", np.ones((2, 2)))

    def test_a_block_without_feedthrough_cannot_gain_it(self):
        for sampled in self.both():
            with self.subTest(sampled=sampled):
                block = self.make(None, sampled)
                with self.assertRaises(ValueError):
                    block.set_param("D", 1.0)
                block.set_param("D", 0.0)  # zero is fine
                self.assertIsNone(block.D)


class LTISSMultipleOutputsTest(unittest.TestCase):
    """C with several rows: the output is one port carrying a vector, see issue #201."""

    A = np.array([[0.0, 1.0], [-2.0, -3.0]])
    B = np.array([[0.0], [1.0]])

    def make(self, sampled, C=None, **kw):
        args = dict(A=self.A, B=self.B, C=np.eye(2) if C is None else C, x0=[1.0, 0.0])
        args.update(kw)
        return LTI_SS_S(Clock(2, "Hz"), **args) if sampled else LTI_SS(**args)

    def both(self):
        return (False, True)

    def sim(self):
        return bdsim.BDSim(
            sysargs=False, graphics=False, progress=False, banner=False, quiet=True
        )

    def test_there_is_one_output_port_whatever_the_rows_of_c(self):
        for sampled in self.both():
            for C in (np.array([1.0, 0.0]), np.eye(2), np.ones((3, 2))):
                with self.subTest(sampled=sampled, rows=np.atleast_2d(C).shape[0]):
                    self.assertEqual(self.make(sampled, C=C).nout, 1)

    def test_there_is_one_input_port_for_each_column_of_b(self):
        for sampled in self.both():
            block = self.make(sampled, B=np.array([[1.0, 2.0], [3.0, 4.0]]))
            self.assertEqual(block.nin, 2)

    def test_the_output_is_a_vector_with_an_element_for_each_row_of_c(self):
        for sampled in self.both():
            with self.subTest(sampled=sampled):
                out = self.make(sampled).test_output(0.0, x=np.r_[3.0, 4.0])
                self.assertEqual(len(out), 1)
                self.assertIsInstance(out[0], np.ndarray)
                nt.assert_array_equal(out[0], [3.0, 4.0])

    def test_one_row_is_still_a_float(self):
        for sampled in self.both():
            for C in (np.array([1.0, 2.0]), np.array([[1.0, 2.0]])):
                with self.subTest(sampled=sampled, shape=C.shape):
                    out = self.make(sampled, C=C).test_output(0.0, x=np.r_[3.0, 4.0])
                    self.assertEqual(out, [11.0])
                    self.assertNotIsInstance(out[0], np.ndarray)

    def test_d_with_several_rows_and_inputs(self):
        # y = C x + D u, three outputs and two inputs
        C = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
        D = np.array([[1.0, 0.0], [0.0, 2.0], [3.0, 4.0]])
        for sampled in self.both():
            with self.subTest(sampled=sampled):
                block = self.make(
                    sampled, C=C, B=np.array([[1.0, 0.0], [0.0, 1.0]]), D=D
                )
                out = block.test_output(1.0, 10.0, x=np.r_[5.0, 6.0])
                nt.assert_allclose(out[0], C @ [5.0, 6.0] + D @ [1.0, 10.0])

    def test_the_example_of_the_issue_compiles_and_the_vector_can_be_split(self):
        for sampled in self.both():
            with self.subTest(sampled=sampled):
                bd = self.sim().blockdiagram()
                clock = bd.clock(0.1)
                plant = (
                    bd.LTI_SS_S(clock, A=0.5 * self.A, B=self.B, C=np.eye(2), x0=[1, 2])
                    if sampled
                    else bd.LTI_SS(A=self.A, B=self.B, C=np.eye(2), x0=[1.0, 2.0])
                )
                demux = bd.DEMUX(2, name="demux")
                bd.connect(bd.CONSTANT(0.0, name="u"), plant)
                bd.connect(plant, demux)
                bd.connect(demux[0], bd.NULL(1, name="first"))
                bd.connect(demux[1], bd.NULL(1, name="second"))
                bd.compile(verbose=False)
                self.assertEqual(plant.nout, 1)
                state = bd.state_map(np.r_[1.0, 2.0] if not sampled else np.array([]))
                bd.evaluate(state, 0.0, sinks=False)
                self.assertEqual(bd["first"].inport_values, [1.0])
                self.assertEqual(bd["second"].inport_values, [2.0])

    def test_the_simulated_vector_is_the_solution(self):
        # x'' + 3 x' + 2 x = 0 with x(0) = 1 and x'(0) = 0, and C = I so y = (x, x')
        sim = self.sim()
        bd = sim.blockdiagram()
        plant = bd.LTI_SS(A=self.A, B=self.B, C=np.eye(2), x0=[1.0, 0.0], name="plant")
        bd.connect(bd.CONSTANT(0.0, name="u"), plant)
        bd.connect(plant, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        out = sim.run(bd, T=2.0, dt=0.01, watch=[plant])
        t = out.t
        exact = np.c_[
            2 * np.exp(-t) - np.exp(-2 * t), -2 * np.exp(-t) + 2 * np.exp(-2 * t)
        ]
        nt.assert_allclose(np.asarray(out.y).reshape(len(t), 2), exact, atol=1e-6)

    def test_a_sampled_vector_output_runs(self):
        sim = self.sim()
        bd = sim.blockdiagram()
        clock = bd.clock(0.1)
        plant = bd.LTI_SS_S(
            clock,
            A=np.diag([0.5, 0.25]),
            B=np.zeros((2, 1)),
            C=np.eye(2),
            x0=[1.0, 1.0],
            name="plant",
        )
        bd.connect(bd.CONSTANT(0.0, name="u"), plant)
        bd.connect(plant, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        out = sim.run(bd, T=0.5, dt=0.05, watch=[plant])
        y = np.asarray(out.y).reshape(len(out.t), 2)
        # x_k = Phi^k x0, so each element is a power of its own factor
        self.assertTrue(np.all(np.isclose(np.log(y[:, 0]) / np.log(0.5) % 1, 0)))
        self.assertTrue(np.all(np.isclose(np.log(y[:, 1]) / np.log(0.25) % 1, 0)))
        self.assertTrue(np.all(y[:, 0] <= 1) and y[-1, 0] < 1)

    def test_linearize_gives_c_with_a_row_for_each_output(self):
        bd = self.sim().blockdiagram()
        C = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
        plant = bd.LTI_SS(A=self.A, B=self.B, C=C, x0=[1.0, 0.0], name="plant")
        bd.connect(bd.CONSTANT(0.0, name="u"), plant)
        bd.connect(plant, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        lin = bd.linearize(full=True)
        nt.assert_allclose(lin.C, C, atol=1e-8)
        nt.assert_allclose(lin.A, self.A, atol=1e-8)
        self.assertEqual(lin.yindex.names, ["plant[0]", "plant[1]", "plant[2]"])


# ---------------------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()
