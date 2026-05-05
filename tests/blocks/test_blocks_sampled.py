#!/usr/bin/env python3

import numpy as np
import math

import matplotlib.pyplot as plt

from bdsim.blocks.sampled import *
from bdsim import Clock

import unittest
import numpy.testing as nt

import bdsim
from bdsim.blocks.sampled import *


class DiscreteTest(unittest.TestCase):

    def test_ZOH(self):

        clock = Clock(2, "Hz")
        x = 7
        block = ZOH(clock, x0=5)  # state is scalar
        self.assertEqual(block.ndstates, 1)
        self.assertEqual(block.nstates, 0)
        nt.assert_equal(block.getstate0(), np.r_[5])

        x = np.r_[1]
        nt.assert_equal(block.test_output(0, x=x)[0], x)

        u = 3
        nt.assert_equal(block.test_next(u, x=x), np.r_[u])

        u = np.r_[1]
        nt.assert_equal(block.test_next(u), u)

    def test_integrator_s(self):

        clock = Clock(2, "Hz")
        block = Integrator_S(clock, x0=5)  # state is scalar
        self.assertEqual(block.ndstates, 1)
        self.assertEqual(block.nstates, 0)

        nt.assert_equal(block.getstate0(), np.r_[5])

        x = np.r_[10]
        u = -2
        nt.assert_equal(block.test_output(u, x=x)[0], x)
        nt.assert_equal(block.test_next(u, x=x), x + u * clock.T)

        block = Integrator_S(clock, x0=5, min=-10, max=10)  # state is scalar
        x = np.r_[10]
        u = 2
        nt.assert_equal(block.test_next(u, x=x), x)

        x = np.r_[-10]
        u = -2
        nt.assert_equal(block.test_next(u, x=x), x)

    def test_integrator_s_vec(self):

        clock = Clock(2, "Hz")
        block = Integrator_S(clock, x0=[5, 6])  # state is vector
        self.assertEqual(block.ndstates, 2)
        self.assertEqual(block.nstates, 0)

        nt.assert_equal(block.getstate0(), np.r_[5, 6])

        x = np.r_[10, 11]
        u = np.r_[-2, 3]
        nt.assert_equal(block.test_output(u, x=x)[0], x)
        nt.assert_equal(block.test_next(u, x=x), x + u * clock.T)

        # test with limits
        block = Integrator_S(
            clock, x0=[5, 6], min=[-5, -10], max=[5, 10]
        )  # state is vector
        x = np.r_[-5, -10]
        u = np.r_[-2, -3]
        nt.assert_equal(block.test_next(u, x=x), x)

        x = np.r_[5, 10]
        u = np.r_[2, 3]
        nt.assert_equal(block.test_next(u, x=x), x)

    def test_pose_integrator_s(self):

        clock = Clock(2, "Hz")
        T = SE3.Rand()
        block = PoseIntegrator_S(clock, x0=T)
        nt.assert_equal(block.getstate0(), Twist3(T))

        self.assertEqual(block.ndstates, 6)
        self.assertEqual(block.nstates, 0)

        x = block.getstate0()
        u = np.r_[1, 2, 3, 4, 5, 6]

        nt.assert_equal(block.test_output(u, x=x)[0], T)

        nt.assert_almost_equal(
            block.test_next(u, x=x), Twist3(T * SE3.Delta(u * clock.T))
        )


class DiscreteTransferTest(unittest.TestCase):
    def test_LTI_SS(self):
        clock = Clock(2, "Hz")

        A = np.array([[1, 2], [3, 4]])
        B = np.array([5, 6])
        C = np.array([7, 8])
        block = LTI_SS_S(clock, A=A, B=B, C=C, x0=[30, 40])
        x = np.r_[10, 11]
        u = -2
        nt.assert_equal(block.test_next(u, x=x), A @ x + B * u)
        nt.assert_equal(block.test_output(u, x=x)[0], C @ x)
        nt.assert_equal(block.getstate0(), np.r_[30, 40])

        A = np.array([[1, 2], [3, 4]])
        B = np.array([[5], [6]])
        C = np.array([[7, 8]])
        block = LTI_SS_S(clock, A=A, B=B, C=C, x0=[30, 40])
        x = np.r_[10, 11]
        u = -2
        nt.assert_equal(block.test_next(u, x=x), A @ x + B @ np.r_[u])
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

        clock = Clock(2, "Hz")

        block = LTI_SISO_S(clock, N=N, D=D)
        n, d = ss2tf(block.A, block.B, block.C, np.zeros((1, 1)), input=0)
        nt.assert_almost_equal(n[0], Nr)
        nt.assert_almost_equal(d, Dr)

        block = LTI_SISO_S(clock, N=N, D=D, form="ocf", order="backward")
        n, d = ss2tf(block.A, block.B, block.C, np.zeros((1, 1)), input=0)
        nt.assert_almost_equal(n[0], Nr)
        nt.assert_almost_equal(d, Dr)

        block = LTI_SISO_S(clock, N=N, D=D, form="ocf", order="forward")
        n, d = ss2tf(block.A, block.B, block.C, np.zeros((1, 1)), input=0)
        nt.assert_almost_equal(n[0], Nr)
        nt.assert_almost_equal(d, Dr)

        block = LTI_SISO_S(clock, N=N, D=D, form="ccf", order="backward")
        n, d = ss2tf(block.A, block.B, block.C, np.zeros((1, 1)), input=0)
        nt.assert_almost_equal(n[0], Nr)
        nt.assert_almost_equal(d, Dr)

        block = LTI_SISO_S(clock, N=N, D=D, form="ccf", order="forward")
        n, d = ss2tf(block.A, block.B, block.C, np.zeros((1, 1)), input=0)
        nt.assert_almost_equal(n[0], Nr)
        nt.assert_almost_equal(d, Dr)

    def test_integrator(self):
        clock = Clock(2, "Hz")

        block = Integrator_S(clock, x0=30)
        self.assertEqual(block.ndstates, 1)
        self.assertEqual(block.nstates, 0)
        x = np.r_[10]
        u = -2
        nt.assert_equal(block.test_next(u, x=x), 9.0)
        nt.assert_equal(block.getstate0(), 30)

        block = Integrator_S(clock, x0=5, min=-10, max=10)  # state is scalar
        x = np.r_[11]
        u = 2
        nt.assert_equal(block.test_next(u, x=x), 10)

        x = np.r_[-11]
        u = -2
        nt.assert_equal(block.test_next(u, x=x), -10)

    def test_integrator_vec(self):
        clock = Clock(2, "Hz")

        block = Integrator_S(clock, x0=[5, 6])  # state is vector
        self.assertEqual(block.ndstates, 2)
        self.assertEqual(block.nstates, 0)

        nt.assert_equal(block.getstate0(), np.r_[5, 6])

        x = np.r_[10, 11]
        u = np.r_[-2, 3]
        nt.assert_equal(block.test_output(u, x=x)[0], x)
        nt.assert_equal(block.test_next(u, x=x), (9.0, 12.5))

        # test with limits
        block = Integrator_S(
            clock, x0=[5, 6], min=[-5, -10], max=[5, 10]
        )  # state is vector
        x = np.r_[-6, -11]
        u = np.r_[-2, -3]
        nt.assert_equal(block.test_next(u, x=x), (-5.0, -10.0))

        x = np.r_[6, 11]
        u = np.r_[2, 3]
        nt.assert_equal(block.test_next(u, x=x), (5.0, 10.0))


class SampledSim(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(
            graphics=None, progress=False, banner=False, sysargs=False, quiet=True
        )

    def test_integrator(self):
        bd = self.sim.blockdiagram()

        clock = bd.clock(10, "Hz")
        signal = bd.STEP(T=1)
        integrator = bd.INTEGRATOR_S(clock, x0=-1)
        sink = bd.NULL()
        bd.connect(signal, integrator)
        bd.connect(integrator, sink)
        bd.compile()
        out = self.sim.run(bd, T=5, watch=[integrator])
        nt.assert_almost_equal(out.y0[0], -1)
        nt.assert_almost_equal(out.y0[-1], 3, decimal=2)

    def test_integrator_gain(self):
        bd = self.sim.blockdiagram()

        clock = bd.clock(10, "Hz")
        signal = bd.STEP(T=1)
        integrator = bd.INTEGRATOR_S(clock, gain=2, x0=-1)
        sink = bd.NULL()
        bd.connect(signal, integrator)
        bd.connect(integrator, sink)
        bd.compile()
        out = self.sim.run(bd, T=5, watch=[integrator])
        nt.assert_almost_equal(out.y0[0], -1)
        nt.assert_almost_equal(out.y0[-1], 7, decimal=2)

    def test_integrator_min(self):
        bd = self.sim.blockdiagram()

        clock = bd.clock(10, "Hz")
        signal = bd.STEP(T=1, on=-1)
        integrator = bd.INTEGRATOR_S(clock, min=-2, max=2)
        sink = bd.NULL()
        bd.connect(signal, integrator)
        bd.connect(integrator, sink)
        bd.compile()
        out = self.sim.run(bd, T=5, watch=[integrator])
        nt.assert_almost_equal(out.y0[0], 0)
        nt.assert_almost_equal(out.y0[-1], -2, decimal=2)

    def test_integrator_max(self):
        bd = self.sim.blockdiagram()

        clock = bd.clock(10, "Hz")
        signal = bd.STEP(T=1, on=1)
        integrator = bd.INTEGRATOR_S(clock, min=-2, max=2)
        sink = bd.NULL()
        bd.connect(signal, integrator)
        bd.connect(integrator, sink)
        bd.compile()
        out = self.sim.run(bd, T=5, watch=[integrator])
        nt.assert_almost_equal(out.y0[0], 0)
        nt.assert_almost_equal(out.y0[-1], 2, decimal=2)

    def test_deriv(self):
        bd = self.sim.blockdiagram()

        clock = bd.clock(10, "Hz")
        signal = bd.RAMP(T=1)
        deriv = bd.DERIV_S(clock)
        sink = bd.NULL()
        bd.connect(signal, deriv)
        bd.connect(deriv, sink)
        bd.compile()
        bd.report_lists()
        bd.report_schedule()
        out = self.sim.run(bd, T=5, watch=[deriv])
        nt.assert_almost_equal(out.y0[0], 0)
        nt.assert_almost_equal(out.y0[-1], 1, decimal=2)

    def test_deriv_gain(self):
        bd = self.sim.blockdiagram()

        clock = bd.clock(10, "Hz")
        signal = bd.RAMP(T=1)
        deriv = bd.DERIV_S(clock, gain=2)
        sink = bd.NULL()
        bd.connect(signal, deriv)
        bd.connect(deriv, sink)
        bd.compile()
        out = self.sim.run(bd, T=5, watch=[deriv])
        nt.assert_almost_equal(out.y0[0], 0)
        nt.assert_almost_equal(out.y0[-1], 2, decimal=2)

    def test_pid(self):
        bd = self.sim.blockdiagram()

        clock = bd.clock(10, "Hz")
        signal = bd.RAMP(T=1)
        sink1 = bd.NULL()
        sink2 = bd.NULL()
        sink3 = bd.NULL()
        zero = bd.CONSTANT(0.0, name="zero")

        P, I, D = 5, 3, 2
        pid1 = bd.PID_S(clock, P=P, I=I, D=D)
        pid2 = bd.PID_S(clock, P=P, I=I / P, D=I / P, structure="ideal")
        Ps = (P + math.sqrt(P**2 - 4 * I * D)) / 2.0
        pid3 = bd.PID_S(clock, P=Ps, I=I / Ps, D=D / Ps, structure="series")

        bd.connect(signal, pid1[1], pid2[1], pid3[1])  # reference
        bd.connect(zero, pid1[0], pid2[0], pid3[0])  # plant output
        bd.connect(pid1, sink1)
        bd.connect(pid2, sink2)
        bd.connect(pid3, sink3)

        bd.compile()
        out = self.sim.run(bd, T=5, watch=[pid1, pid2, pid3])

        # results are not quite the same, but close enough for this test
        nt.assert_almost_equal(out.y0[0], 0)
        nt.assert_almost_equal(out.y0[-1], 45.4, decimal=1)
        nt.assert_almost_equal(out.y1[0], 0)
        nt.assert_almost_equal(out.y1[-1], 46.4, decimal=1)
        nt.assert_almost_equal(out.y2[0], 0)
        nt.assert_almost_equal(out.y2[-1], 45.2, decimal=1)

    def test_pd(self):
        bd = self.sim.blockdiagram()

        clock = bd.clock(10, "Hz")
        signal = bd.RAMP(T=1)
        sink1 = bd.NULL()
        sink2 = bd.NULL()
        sink3 = bd.NULL()
        zero = bd.CONSTANT(0.0, name="zero")

        P, I, D = 5, 0, 2
        pid1 = bd.PID_S(clock, P=P, I=I, D=D)
        pid2 = bd.PID_S(clock, P=P, I=I / P, D=D / P, structure="ideal")
        Ps = (P + math.sqrt(P**2 - 4 * I * D)) / 2.0
        pid3 = bd.PID_S(clock, P=Ps, I=I / Ps, D=D / Ps, structure="series")

        bd.connect(signal, pid1[1], pid2[1], pid3[1])  # reference
        bd.connect(zero, pid1[0], pid2[0], pid3[0])  # plant output
        bd.connect(pid1, sink1)
        bd.connect(pid2, sink2)
        bd.connect(pid3, sink3)

        bd.compile()
        out = self.sim.run(bd, T=5, watch=[pid1, pid2, pid3])

        # results are not quite the same, but close enough for this test
        nt.assert_almost_equal(out.y0[0], 0)
        nt.assert_almost_equal(out.y0[-1], 22, decimal=1)
        nt.assert_almost_equal(out.y1[0], 0)
        nt.assert_almost_equal(out.y1[-1], 22, decimal=1)
        nt.assert_almost_equal(out.y2[0], 0)
        nt.assert_almost_equal(out.y2[-1], 22, decimal=1)

    def test_pi(self):
        bd = self.sim.blockdiagram()

        clock = bd.clock(10, "Hz")
        signal = bd.RAMP(T=1)
        sink1 = bd.NULL()
        sink2 = bd.NULL()
        sink3 = bd.NULL()
        zero = bd.CONSTANT(0.0, name="zero")

        P, I, D = 5, 3, 0
        pid1 = bd.PID_S(clock, P=P, I=I, D=D)
        pid2 = bd.PID_S(clock, P=P, I=I / P, D=I / P, structure="ideal")
        Ps = (P + math.sqrt(P**2 - 4 * I * D)) / 2.0
        pid3 = bd.PID_S(clock, P=Ps, I=I / Ps, D=D / Ps, structure="series")

        bd.connect(signal, pid1[1], pid2[1], pid3[1])  # reference
        bd.connect(zero, pid1[0], pid2[0], pid3[0])  # plant output
        bd.connect(pid1, sink1)
        bd.connect(pid2, sink2)
        bd.connect(pid3, sink3)

        bd.compile()
        out = self.sim.run(bd, T=5, watch=[pid1, pid2, pid3])

        # results are not quite the same, but close enough for this test
        nt.assert_almost_equal(out.y0[0], 0)
        nt.assert_almost_equal(out.y0[-1], 43.4, decimal=1)
        nt.assert_almost_equal(out.y1[0], 0)
        nt.assert_almost_equal(out.y1[-1], 46.4, decimal=1)
        nt.assert_almost_equal(out.y2[0], 0)
        nt.assert_almost_equal(out.y2[-1], 43.4, decimal=1)


# ---------------------------------------------------------------------------------------#
if __name__ == "__main__":

    unittest.main()
