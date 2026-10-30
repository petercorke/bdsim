#!/usr/bin/env python3
"""Parameters that are properties: the value is not kept under its own name, or setting it
has to rebuild something.  (The registry and the simple cases are in test_parameters.py.)
"""

import unittest

import contextlib
import io

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


class SourceParameterTest(PropTestCase):
    def test_waveform_freq_is_in_the_unit_it_was_given(self):
        bd = self.bd()
        hz = bd.WAVEFORM("sine", freq=2)
        rad = bd.WAVEFORM("sine", freq=2 * np.pi, unit="rad/s")
        self.assertEqual(hz.freq, 2)
        self.assertAlmostEqual(rad.freq, 2 * np.pi)
        hz.set_param("freq", 5)  # a quarter cycle at t = 0.05 s: the peak
        self.assertAlmostEqual(hz.test_output(t=0.05)[0], 1.0)
        rad.set_param("freq", 4 * np.pi)  # 2 Hz: the peak is at t = 0.125 s
        self.assertAlmostEqual(rad.test_output(t=0.125)[0], 1.0)

    def test_waveform_min_and_max_follow_amplitude_and_offset(self):
        wave = self.bd().WAVEFORM("sine", min=-1, max=3)
        self.assertEqual((wave.min, wave.max), (-1, 3))
        self.assertEqual((wave.amplitude, wave.offset), (2, 1))
        wave.set_param("max", 5)
        self.assertEqual((wave.min, wave.max), (-1, 5))
        self.assertEqual((wave.amplitude, wave.offset), (3, 2))
        wave.set_param("min", 0)
        self.assertEqual((wave.amplitude, wave.offset), (2.5, 2.5))
        wave.set_param("amplitude", 1)
        self.assertEqual((wave.min, wave.max), (1.5, 3.5))

    def test_waveform_min_and_max_exist_without_being_given(self):
        wave = self.bd().WAVEFORM("sine", amplitude=2, offset=1)
        self.assertEqual((wave.min, wave.max), (-1, 3))

    def test_waveform_min_must_stay_below_max(self):
        wave = self.bd().WAVEFORM("sine", min=-1, max=3)
        with self.assertRaises(ValueError):
            wave.set_param("min", 4)

    def test_waveform_freq_is_a_setup_parameter(self):
        wave = self.bd().WAVEFORM("sine", freq=1)
        wave.start_safe(wave.test_start())
        with self.assertRaises(ValueError):
            wave.set_param("freq", 2)

    def test_piecewise_seq(self):
        pw = self.bd().PIECEWISE((0, 0.0), (1, 5.0))
        self.assertEqual(pw.seq, [(0, 0.0), (1, 5.0)])
        old = pw.set_param("seq", [(0, 1.0), (2, 7.0), (3, 2.0)])
        self.assertEqual(old, [(0, 0.0), (1, 5.0)])
        self.assertEqual(pw.test_output(t=2.5)[0], 7.0)
        self.assertEqual(pw.test_output(t=3.5)[0], 2.0)

    def test_piecewise_seq_must_be_in_order(self):
        pw = self.bd().PIECEWISE((0, 0.0), (1, 5.0))
        with self.assertRaises(ValueError):
            pw.set_param("seq", [(2, 1.0), (1, 5.0)])

    def test_piecewise_seq_values_stay_one_type(self):
        pw = self.bd().PIECEWISE((0, 0.0), (1, 5.0))
        with self.assertRaises(TypeError):
            pw.set_param("seq", [(0, 1.0), (1, "high")])

    def test_time_value_is_registered_but_fixed(self):
        # the argument is accepted and ignored: Time outputs t
        time = self.bd().TIME()
        with self.assertRaises(ValueError) as cm:
            time.set_param("value", 1)
        self.assertIn("fixed", str(cm.exception))


class SinkParameterTest(PropTestCase):
    def test_print_fmt(self):
        pr = self.bd().PRINT(fmt="{:.1f}")
        self.assertEqual(pr.fmt, "{:.1f}")
        pr.set_param("fmt", "{:.3f}")
        self.assertEqual(pr.fmt, "{:.3f}")

    def test_stop_func(self):
        stop = self.bd().STOP(lambda x: x > 3)
        stop.set_param("func", lambda x: x > 5)
        self.assertFalse(stop.func(4))
        self.assertTrue(stop.func(6))
        with self.assertRaises(TypeError):
            stop.set_param("func", 3)

    def test_event_direction_is_the_string(self):
        event = self.bd().EVENT("^", lambda *a: None)
        self.assertEqual(event.direction, "^")
        event.set_param("direction", "v")
        self.assertEqual(event.direction, "v")
        self.assertEqual(event._direction, -1.0)
        event.set_param("direction", "+")
        self.assertEqual(event._direction, 1.0)
        self.assertEqual(event.direction, "^")
        with self.assertRaises(ValueError):
            event.set_param("direction", "x")

    def test_event_fargs_and_fkwargs(self):
        event = self.bd().EVENT("^", lambda *a: None, fargs=(1, 2), fkwargs={"k": 3})
        self.assertEqual(event.fargs, [1, 2])
        self.assertEqual(event.fkwargs, {"k": 3})
        event.set_param("fargs", (4,))
        event.set_param("fkwargs", {"j": 5})
        self.assertEqual((event.args, event.kwargs), ([4], {"j": 5}))

    def test_event_direction_is_a_setup_parameter(self):
        event = self.bd().EVENT("^", lambda *a: None)
        event.start_safe(event.test_start())
        with self.assertRaises(ValueError):
            event.set_param("direction", "v")


class FunctionParameterTest(PropTestCase):
    def test_function_fargs_and_fkwargs(self):
        func = self.bd().FUNCTION(
            lambda x, a, b=1: x * a + b, fargs=(2,), fkwargs={"b": 10}
        )
        self.assertEqual(func.test_output(3)[0], 16)
        func.set_param("fargs", (5,))
        self.assertEqual(func.test_output(3)[0], 25)
        func.set_param("fkwargs", {"b": 0})
        self.assertEqual(func.test_output(3)[0], 15)
        self.assertEqual((func.fargs, func.fkwargs), ([5], {"b": 0}))

    def test_function_persistent_adds_and_removes_the_state_dict(self):
        func = self.bd().FUNCTION(lambda x, d: x, persistent=True)
        self.assertTrue(func.persistent)
        self.assertIsNotNone(func.userdata)
        func.set_param("persistent", False)
        self.assertFalse(func.persistent)
        self.assertIsNone(func.userdata)
        self.assertEqual(func.fargs, [])
        func.set_param("persistent", True)
        self.assertIsInstance(func.userdata, dict)
        self.assertIs(func.args[-1], func.userdata)

    def test_function_fargs_keep_the_state_dict_when_persistent(self):
        func = self.bd().FUNCTION(lambda x, a, d: x, fargs=(1,), persistent=True)
        func.set_param("fargs", (2,))
        self.assertEqual(func.fargs, [2])
        self.assertIs(func.args[-1], func.userdata)

    def test_norm_ord_and_axis(self):
        norm = self.bd().NORM(ord=2)
        v = np.r_[3.0, 4.0]
        self.assertAlmostEqual(norm.test_output(v)[0], 5.0)
        self.assertEqual(norm.ord, 2)
        norm.set_param("ord", 1)
        self.assertAlmostEqual(norm.test_output(v)[0], 7.0)
        norm.set_param("ord", np.inf)
        self.assertAlmostEqual(norm.test_output(v)[0], 4.0)
        self.assertIsNone(norm.axis)

    def test_slice_index_forms(self):
        sl = self.bd().SLICE1(index=(0, 3, 1))
        v = np.arange(10)
        nt.assert_array_equal(sl.test_output(v)[0], [0, 1, 2])
        sl.set_param("index", (2, 5, 1))
        nt.assert_array_equal(sl.test_output(v)[0], [2, 3, 4])
        sl.set_param("index", [1, 8])
        nt.assert_array_equal(sl.test_output(v)[0], [1, 8])
        sl.set_param("index", None)
        nt.assert_array_equal(sl.test_output(v)[0], v)
        with self.assertRaises(ValueError):
            sl.set_param("index", "oops")

    def test_slice1_integer_index_gives_an_element(self):
        # as the documentation says: index=2 is element 2, as a scalar
        sl = self.bd().SLICE1(index=2)
        self.assertEqual(sl.test_output(np.arange(10))[0], 2)
        sl.set_param("index", 5)
        self.assertEqual(sl.test_output(np.arange(10))[0], 5)

    def test_function_start_does_not_print(self):
        func = self.bd().FUNCTION(lambda x, d: x, persistent=True)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            func.start_safe(func.test_start())
        self.assertEqual(out.getvalue(), "")

    def test_slice2_rows_and_cols(self):
        sl = self.bd().SLICE2(rows=(0, 2, 1), cols=(0, 2, 1))
        m = np.arange(16).reshape(4, 4)
        nt.assert_array_equal(sl.test_output(m)[0], m[:2, :2])
        sl.set_param("rows", (1, 3, 1))
        sl.set_param("cols", [0, 3])
        nt.assert_array_equal(sl.test_output(m)[0], m[1:3][:, [0, 3]])

    def test_index_forms(self):
        idx = self.bd().INDEX("1:3")
        v = np.arange(6)
        nt.assert_array_equal(idx.test_output(v)[0], [1, 2])
        idx.set_param("index", "2:5")
        nt.assert_array_equal(idx.test_output(v)[0], [2, 3, 4])
        idx.set_param("index", [0, 5])
        nt.assert_array_equal(idx.test_output(v)[0], [0, 5])


class InterpolateParameterTest(PropTestCase):
    def test_x_and_y(self):
        interp = self.bd().INTERPOLATE(x=[0, 1, 2], y=[0, 10, 20])
        self.assertAlmostEqual(interp.test_output(0.5)[0], 5.0)
        nt.assert_array_equal(interp.x, [0, 1, 2])
        interp.set_param("y", [0, 20, 40])
        self.assertAlmostEqual(interp.test_output(0.5)[0], 10.0)
        interp.set_param("x", [0, 2, 4])
        self.assertAlmostEqual(interp.test_output(2.0)[0], 20.0)

    def test_x_and_y_must_stay_the_same_length(self):
        interp = self.bd().INTERPOLATE(x=[0, 1, 2], y=[0, 10, 20])
        with self.assertRaises(ValueError) as cm:
            interp.set_param("y", [0, 1])
        self.assertIn("length", str(cm.exception))
        nt.assert_array_equal(interp.y, [0, 10, 20])  # unchanged

    def test_the_length_can_change_with_x_and_y_together(self):
        interp = self.bd().INTERPOLATE(x=[0, 1, 2], y=[0, 10, 20])
        interp.set_param("xy", [[0, 0], [1, 5], [2, 10], [3, 15]])
        self.assertAlmostEqual(interp.test_output(2.5)[0], 12.5)
        self.assertEqual(len(interp.x), 4)

    def test_kind(self):
        interp = self.bd().INTERPOLATE(x=[0, 1, 2, 3], y=[0, 1, 4, 9], kind="linear")
        self.assertAlmostEqual(interp.test_output(1.5)[0], 2.5)
        interp.set_param("kind", "nearest")
        self.assertIn(interp.test_output(1.4)[0], (1.0, 4.0))
        with self.assertRaises(ValueError):
            interp.set_param("kind", "wiggly")
        self.assertEqual(interp.kind, "nearest")

    def test_time_based_interpolant_must_cover_the_run(self):
        interp = self.bd().INTERPOLATE(x=[0, 5], y=[0, 1], time=True)
        interp.start_safe(type("S", (), {"tf": 4.0})())
        with self.assertRaises(ValueError):
            interp.set_param("x", [0, 3])


class Deriv2ParameterTest(PropTestCase):
    def test_wn_zeta_and_gain_rebuild_the_realisation(self):
        bd = self.bd()
        d = bd.DERIV2(wn=10, zeta=0.5, gain=2.0)
        d.set_param("wn", 20)
        d.set_param("zeta", 1.0)
        d.set_param("gain", 3.0)
        fresh = bd.DERIV2(wn=20, zeta=1.0, gain=3.0)
        for name in "ABC":
            nt.assert_allclose(getattr(d, name), getattr(fresh, name), atol=1e-12)
        self.assertEqual((d.wn, d.zeta, d.gain), (20, 1.0, 3.0))

    def test_wn_is_in_the_unit_it_was_given(self):
        bd = self.bd()
        d = bd.DERIV2(wn=2, unit="Hz")
        self.assertEqual(d.wn, 2)
        d.set_param("wn", 3)
        fresh = bd.DERIV2(wn=3, unit="Hz")
        nt.assert_allclose(d.A, fresh.A, atol=1e-12)

    def test_wn_must_be_positive(self):
        d = self.bd().DERIV2(wn=10)
        with self.assertRaises(ValueError):
            d.set_param("wn", -1)


if __name__ == "__main__":
    unittest.main()
