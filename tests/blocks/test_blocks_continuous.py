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

import matplotlib.pyplot as plt

import bdsim
from bdsim.blocks.continuous import *
from bdsim.blocks.continuous import _tf2ss

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

        block = LTI_SISO(N=N, D=D)
        n, d = ss2tf(block.A, block.B, block.C, np.zeros((1, 1)), input=0)
        nt.assert_almost_equal(n[0], Nr)
        nt.assert_almost_equal(d, Dr)

        block = LTI_SISO(N=N, D=D, form="ocf", order="backward")
        n, d = ss2tf(block.A, block.B, block.C, np.zeros((1, 1)), input=0)
        nt.assert_almost_equal(n[0], Nr)
        nt.assert_almost_equal(d, Dr)

        block = LTI_SISO(N=N, D=D, form="ocf", order="forward")
        n, d = ss2tf(block.A, block.B, block.C, np.zeros((1, 1)), input=0)
        nt.assert_almost_equal(n[0], Nr)
        nt.assert_almost_equal(d, Dr)

        block = LTI_SISO(N=N, D=D, form="ccf", order="backward")
        n, d = ss2tf(block.A, block.B, block.C, np.zeros((1, 1)), input=0)
        nt.assert_almost_equal(n[0], Nr)
        nt.assert_almost_equal(d, Dr)

        block = LTI_SISO(N=N, D=D, form="ccf", order="forward")
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

        block = Integrator(x0=5, min=-10, max=10)  # state is scalar
        x = np.r_[11]
        u = 2
        nt.assert_equal(block.test_deriv(u, x=x), 0)

        x = np.r_[-11]
        u = -2
        nt.assert_equal(block.test_deriv(u, x=x), 0)

    def test_integrator_vec(self):
        block = Integrator(x0=[5, 6])  # state is vector
        self.assertEqual(block.nstates, 2)
        self.assertEqual(block.ndstates, 0)

        nt.assert_equal(block.getstate0(), np.r_[5, 6])

        x = np.r_[10, 11]
        u = np.r_[-2, 3]
        nt.assert_equal(block.test_output(u, x=x)[0], x)
        nt.assert_equal(block.test_deriv(u, x=x), u)

        # test with limits
        block = Integrator(x0=[5, 6], min=[-5, -10], max=[5, 10])  # state is vector
        x = np.r_[-6, -11]
        u = np.r_[-2, -3]
        nt.assert_equal(block.test_deriv(u, x=x), [0, 0])

        x = np.r_[6, 11]
        u = np.r_[2, 3]
        nt.assert_equal(block.test_deriv(u, x=x), [0, 0])


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


# ---------------------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()
