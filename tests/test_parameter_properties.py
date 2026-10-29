#!/usr/bin/env python3
"""Parameters that are properties: the value is not kept under its own name, or setting it
has to rebuild something.  (The registry and the simple cases are in test_parameters.py.)
"""

import unittest

import numpy as np
import numpy.testing as nt
from spatialmath import SE3, Twist3

import bdsim


class PropTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False, quiet=True)

    def bd(self):
        return self.sim.blockdiagram()

    def run_with(self, bd, *setparam, T=1.0, **kwargs):
        sim = bdsim.BDSim(
            graphics=None,
            progress=False,
            banner=False,
            quiet=True,
            setparam=list(setparam),
        )
        bd.compile(verbose=False)
        return sim.run(bd, T=T, dt=0.1, **kwargs)


class InitialStateTest(PropTestCase):
    """x0 is a property of the continuous and sampled base classes, settable before the run."""

    def test_continuous_blocks(self):
        bd = self.bd()
        blocks = {
            "Integrator": bd.INTEGRATOR(x0=[1.0, 2.0]),
            "LTI_SS": bd.LTI_SS(
                -np.eye(2), np.ones((2, 1)), np.ones((1, 2)), x0=[1.0, 2.0]
            ),
            "LTI_SISO": bd.LTI_SISO(1, [1, 2, 3], x0=[1.0, 2.0]),
            "Deriv2": bd.DERIV2(wn=10, x0=[1.0, 2.0]),
        }
        for name, block in blocks.items():
            with self.subTest(block=name):
                nt.assert_array_equal(block.x0, [1.0, 2.0])
                old = block.set_param("x0", [5.0, 6.0])
                nt.assert_array_equal(old, [1.0, 2.0])
                nt.assert_array_equal(block.getstate0(), [5.0, 6.0])

    def test_sampled_blocks(self):
        bd = self.bd()
        clock = bd.clock(0.1)
        blocks = {
            "ZOH": bd.ZOH(clock, x0=[1.0, 2.0]),
            "Integrator_S": bd.INTEGRATOR_S(clock, x0=[1.0, 2.0]),
            "Deriv_S": bd.DERIV_S(clock, x0=[1.0, 2.0]),
            "LTI_SS_S": bd.LTI_SS_S(
                clock, -np.eye(2), np.ones((2, 1)), np.ones((1, 2)), x0=[1.0, 2.0]
            ),
            "LTI_SISO_S": bd.LTI_SISO_S(clock, 1, [1, 2, 3], x0=[1.0, 2.0]),
        }
        for name, block in blocks.items():
            with self.subTest(block=name):
                block.set_param("x0", [5.0, 6.0])
                nt.assert_array_equal(block.getstate0(), [5.0, 6.0])

    def test_the_number_of_states_cannot_change(self):
        integrator = self.bd().INTEGRATOR(x0=[1.0, 2.0])
        with self.assertRaises(ValueError) as cm:
            integrator.set_param("x0", [1.0, 2.0, 3.0])
        self.assertIn("x0", str(cm.exception))

    def test_a_scalar_for_a_one_state_block(self):
        integrator = self.bd().INTEGRATOR(x0=0.0)
        integrator.set_param("x0", 3)
        nt.assert_array_equal(integrator.getstate0(), [3.0])

    def test_x0_is_a_setup_parameter(self):
        integrator = self.bd().INTEGRATOR(x0=0.0)
        simstate = integrator.test_start()
        integrator.start_safe(simstate)
        with self.assertRaises(ValueError) as cm:
            integrator.set_param("x0", 1.0)
        self.assertIn("running", str(cm.exception))

    def test_set_from_the_command_line_takes_effect_in_the_run(self):
        # this needs --set to be applied before the initial state is collected
        bd = self.bd()
        integrator = bd.INTEGRATOR(x0=0.0, name="i")
        bd.connect(bd.CONSTANT(0.0), integrator)
        out = self.run_with(bd, "i:x0=7")
        nt.assert_allclose(out.x[:, 0], 7.0)

    def test_a_sampled_initial_state_takes_effect_in_the_run(self):
        bd = self.bd()
        clock = bd.clock(0.1)
        zoh = bd.ZOH(clock, x0=0.0, name="z")
        bd.connect(bd.CONSTANT(0.0), zoh)
        out = self.run_with(bd, "z:x0=4", watch=[zoh])
        self.assertEqual(out.y[0, 0], 4.0)

    def test_pose_integrators_take_an_se3(self):
        bd = self.bd()
        clock = bd.clock(0.1)
        for block in (bd.POSEINTEGRATOR(), bd.POSEINTEGRATOR_S(clock)):
            with self.subTest(block=type(block).__name__):
                pose = SE3.Tx(2) * SE3.Rz(0.3)
                block.set_param("x0", pose)
                nt.assert_allclose(block.getstate0(), Twist3(pose).A)
                block.set_param("x0", Twist3(pose))
                nt.assert_allclose(block.getstate0(), Twist3(pose).A)
                block.set_param("x0", np.zeros(6))
                nt.assert_array_equal(block.getstate0(), np.zeros(6))


if __name__ == "__main__":
    unittest.main()
