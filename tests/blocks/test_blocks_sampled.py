#!/usr/bin/env python3

import numpy as np
import math

from bdsim.blocks.sampled import (
    Hysteresis_S,
    Integrator_S,
    LTI_SISO_S,
    LTI_SS_S,
    ZOH,
)
from bdsim import Clock

import unittest
import numpy.testing as nt

import bdsim
from bdsim.blocks.spatial import PoseIntegrator_S, DPoseIntegrator
from spatialmath import SE3, Twist3


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

    def test_pose_integrator_s_default_x0(self):

        clock = Clock(2, "Hz")
        block = PoseIntegrator_S(clock)  # x0 defaults to None -> null twist
        nt.assert_equal(block.getstate0(), np.zeros(6))

        with self.assertWarns(FutureWarning):
            deprecated_block = DPoseIntegrator(clock)
        nt.assert_equal(deprecated_block.getstate0(), np.zeros(6))


class HysteresisTest(unittest.TestCase):
    clock = Clock(10, "Hz")

    def block(self, **kw):
        return Hysteresis_S(self.clock, switch_on=1.0, switch_off=0.0, **kw)

    def test_defaults(self):
        block = Hysteresis_S(self.clock)
        self.assertEqual((block.switch_on, block.switch_off), (0.5, -0.5))
        self.assertEqual((block.output_on, block.output_off), (1.0, 0.0))
        self.assertEqual(block.ndstates, 1)
        nt.assert_equal(block.getstate0(), np.r_[0.0])  # initially off

    def test_switches_on_and_off(self):
        block = self.block()
        off, on = np.r_[0.0], np.r_[1.0]
        nt.assert_equal(block.test_next(2.0, x=off), on)
        nt.assert_equal(block.test_next(-1.0, x=on), off)

    def test_keeps_its_value_between_the_switching_points(self):
        block = self.block()
        off, on = np.r_[0.0], np.r_[1.0]
        nt.assert_equal(block.test_next(0.5, x=off), off)
        nt.assert_equal(block.test_next(0.5, x=on), on)

    def test_the_switching_points_themselves_switch(self):
        block = self.block()
        off, on = np.r_[0.0], np.r_[1.0]
        nt.assert_equal(block.test_next(1.0, x=off), on)  # at switch_on
        nt.assert_equal(block.test_next(0.0, x=on), off)  # at switch_off

    def test_equal_switching_points_are_an_ideal_relay(self):
        block = Hysteresis_S(self.clock, switch_on=0.0, switch_off=0.0)
        off, on = np.r_[0.0], np.r_[1.0]
        nt.assert_equal(block.test_next(0.0, x=off), on)  # exactly at it: on
        nt.assert_equal(block.test_next(-0.1, x=on), off)
        nt.assert_equal(block.test_next(0.1, x=off), on)

    def test_output_levels(self):
        block = self.block(output_on=5.0, output_off=-2.0)
        nt.assert_equal(block.getstate0(), np.r_[-2.0])
        nt.assert_equal(block.test_next(2.0, x=np.r_[-2.0]), np.r_[5.0])
        nt.assert_equal(block.test_next(-1.0, x=np.r_[5.0]), np.r_[-2.0])
        self.assertEqual(block.test_output(0, x=np.r_[5.0])[0], 5.0)

    def test_initial_output(self):
        block = self.block(x0=1.0)
        nt.assert_equal(block.getstate0(), np.r_[1.0])
        # in the band it keeps the initial value
        nt.assert_equal(block.test_next(0.5, x=block.getstate0()), np.r_[1.0])

    def test_vector_with_elementwise_parameters(self):
        block = Hysteresis_S(
            self.clock,
            switch_on=[1.0, 10.0],
            switch_off=[0.0, 5.0],
            x0=[0.0, 1.0],
        )
        self.assertEqual(block.ndstates, 2)
        x = np.r_[0.0, 1.0]
        # element 0 at 2 switches on; element 1 at 7 is in its band and stays on
        nt.assert_equal(block.test_next(np.r_[2.0, 7.0], x=x), np.r_[1.0, 1.0])
        # element 0 at 0.5 stays; element 1 at 4 switches off
        nt.assert_equal(
            block.test_next(np.r_[0.5, 4.0], x=np.r_[1.0, 1.0]), np.r_[1.0, 0.0]
        )

    def test_scalar_state_gives_a_scalar_output(self):
        out = self.block().test_output(0, x=np.r_[1.0])[0]
        self.assertNotIsInstance(out, np.ndarray)

    def test_bad_parameters(self):
        with self.assertRaises(ValueError):
            Hysteresis_S(self.clock, switch_on=0.0, switch_off=1.0)
        with self.assertRaises(ValueError):
            Hysteresis_S(self.clock, output_on=1.0, output_off=1.0)
        with self.assertRaises(ValueError):
            self.block(x0=0.5)  # neither output level

    def test_parameters_are_validated_when_set(self):
        block = self.block()
        block.set_param("switch_on", 2.0)
        self.assertEqual(block.switch_on, 2.0)
        with self.assertRaises(ValueError):
            block.set_param("switch_off", 3.0)  # above switch_on
        with self.assertRaises(ValueError):
            block.set_param("switch_on", -1.0)  # below switch_off
        with self.assertRaises(ValueError):
            block.set_param("output_on", 0.0)  # equals output_off
        self.assertEqual((block.switch_on, block.switch_off), (2.0, 0.0))


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

        block = LTI_SISO_S(clock, num=N, den=D)
        n, d = ss2tf(block.A, block.B, block.C, np.zeros((1, 1)), input=0)
        nt.assert_almost_equal(n[0], Nr)
        nt.assert_almost_equal(d, Dr)

        block = LTI_SISO_S(clock, num=N, den=D, form="ocf", order="backward")
        n, d = ss2tf(block.A, block.B, block.C, np.zeros((1, 1)), input=0)
        nt.assert_almost_equal(n[0], Nr)
        nt.assert_almost_equal(d, Dr)

        block = LTI_SISO_S(clock, num=N, den=D, form="ocf", order="forward")
        n, d = ss2tf(block.A, block.B, block.C, np.zeros((1, 1)), input=0)
        nt.assert_almost_equal(n[0], Nr)
        nt.assert_almost_equal(d, Dr)

        block = LTI_SISO_S(clock, num=N, den=D, form="ccf", order="backward")
        n, d = ss2tf(block.A, block.B, block.C, np.zeros((1, 1)), input=0)
        nt.assert_almost_equal(n[0], Nr)
        nt.assert_almost_equal(d, Dr)

        block = LTI_SISO_S(clock, num=N, den=D, form="ccf", order="forward")
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
        nt.assert_almost_equal(out.y[0, 0], -1)
        nt.assert_almost_equal(out.y[-1, 0], 3, decimal=2)

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
        nt.assert_almost_equal(out.y[0, 0], -1)
        nt.assert_almost_equal(out.y[-1, 0], 7, decimal=2)

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
        nt.assert_almost_equal(out.y[0, 0], 0)
        nt.assert_almost_equal(out.y[-1, 0], -2, decimal=2)

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
        nt.assert_almost_equal(out.y[0, 0], 0)
        nt.assert_almost_equal(out.y[-1, 0], 2, decimal=2)

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
        nt.assert_almost_equal(out.y[0, 0], 0)
        nt.assert_almost_equal(out.y[-1, 0], 1, decimal=2)

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
        nt.assert_almost_equal(out.y[0, 0], 0)
        nt.assert_almost_equal(out.y[-1, 0], 2, decimal=2)

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
        nt.assert_almost_equal(out.y[0, 0], 0)
        nt.assert_almost_equal(out.y[-1, 0], 45.4, decimal=1)
        nt.assert_almost_equal(out.y[0, 1], 0)
        nt.assert_almost_equal(out.y[-1, 1], 46.4, decimal=1)
        nt.assert_almost_equal(out.y[0, 2], 0)
        nt.assert_almost_equal(out.y[-1, 2], 45.2, decimal=1)

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
        nt.assert_almost_equal(out.y[0, 0], 0)
        nt.assert_almost_equal(out.y[-1, 0], 22, decimal=1)
        nt.assert_almost_equal(out.y[0, 1], 0)
        nt.assert_almost_equal(out.y[-1, 1], 22, decimal=1)
        nt.assert_almost_equal(out.y[0, 2], 0)
        nt.assert_almost_equal(out.y[-1, 2], 22, decimal=1)

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
        nt.assert_almost_equal(out.y[0, 0], 0)
        nt.assert_almost_equal(out.y[-1, 0], 43.4, decimal=1)
        nt.assert_almost_equal(out.y[0, 1], 0)
        nt.assert_almost_equal(out.y[-1, 1], 46.4, decimal=1)
        nt.assert_almost_equal(out.y[0, 2], 0)
        nt.assert_almost_equal(out.y[-1, 2], 43.4, decimal=1)


# ---------------------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()
