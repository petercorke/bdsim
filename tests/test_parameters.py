#!/usr/bin/env python3
"""Block parameters that can be set after construction: Block.set_param and --set.

Every __init__ argument of a block is registered with ``self.add_param(name)`` and
is one of

* ``when="anytime"`` (the default): settable at any time, between evaluations
* ``when="setup"``: settable before the run starts, refused while it runs
* ``when="never"``: fixed when the block is created (``nin``, ``clock``)

A parameter whose value is not a plain attribute, because the block built other
blocks or derived state from it, is a Python ``property``: the setter does the
work, and the registration is the same.
"""

import ast
import io
from contextlib import redirect_stdout
from pathlib import Path
import unittest
import warnings

import numpy as np
import numpy.testing as nt

import bdsim
from bdsim.block_types import FunctionBlock


class ParamTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False, quiet=True)

    def bd(self):
        return self.sim.blockdiagram()


class ParametersTest(ParamTestCase):
    def test_parameters_lists_the_settable_ones_with_their_values(self):
        gain = self.bd().GAIN(2.5, premul=True)
        self.assertEqual(gain.parameters(), {"K": 2.5, "premul": True})

    def test_set_param_returns_the_old_value_and_prints_nothing(self):
        gain = self.bd().GAIN(2.0)
        buf = io.StringIO()
        with redirect_stdout(buf):
            old = gain.set_param("K", 3.0)
        self.assertEqual(old, 2.0)
        self.assertEqual(gain.K, 3.0)
        self.assertEqual(buf.getvalue(), "")


class ErrorsTest(ParamTestCase):
    def test_unknown_name_lists_what_can_be_set(self):
        gain = self.bd().GAIN(2.0, name="g")
        with self.assertRaises(ValueError) as cm:
            gain.set_param("nope", 1)
        msg = str(cm.exception)
        self.assertIn("g", msg)
        self.assertIn("nope", msg)
        self.assertIn("K", msg)
        self.assertIn("premul", msg)

    def test_a_fixed_parameter_says_so(self):
        mux = self.bd().MUX(2, name="m")
        with self.assertRaises(ValueError) as cm:
            mux.set_param("nin", 3)
        self.assertIn("fixed", str(cm.exception))

    def test_start_time_parameter_is_refused_while_running(self):
        step = self.bd().STEP(T=1.0, off=0.0, on=1.0, name="s")
        step.set_param("T", 2.0)  # fine before the run starts
        self.assertEqual(step.T, 2.0)
        simstate = step.test_start()
        step.start_safe(simstate)
        with self.assertRaises(ValueError) as cm:
            step.set_param("T", 3.0)
        self.assertIn("running", str(cm.exception))
        step.done_safe()
        step.set_param("T", 4.0)  # and again once the run is over
        self.assertEqual(step.T, 4.0)

    def test_a_live_parameter_can_be_set_while_running(self):
        gain = self.bd().GAIN(2.0)
        gain.start_safe(gain.test_start())
        gain.set_param("K", 5.0)
        self.assertEqual(gain.K, 5.0)


class TypeEnforcementTest(ParamTestCase):
    def test_numbers_widen_but_never_narrow(self):
        gain = self.bd().GAIN(2)  # an int
        gain.set_param("K", 2.5)
        self.assertIs(type(gain.K), float)
        gain = self.bd().GAIN(2.0)  # a float
        gain.set_param("K", 3)
        self.assertIs(type(gain.K), float)
        self.assertEqual(gain.K, 3.0)

    def test_a_number_cannot_replace_a_matrix(self):
        gain = self.bd().GAIN(np.eye(2), name="g")
        with self.assertRaises(TypeError) as cm:
            gain.set_param("K", 3)
        self.assertIn("ndarray(2, 2)", str(cm.exception))

    def test_a_number_can_replace_a_one_element_array(self):
        const = self.bd().CONSTANT(np.array([1.0]))
        const.set_param("value", 4)
        nt.assert_array_equal(const.value, [4.0])
        self.assertEqual(const.value.shape, (1,))
        two = self.bd().CONSTANT(np.array([1.0, 2.0]))
        with self.assertRaises(TypeError):
            two.set_param("value", 4)  # not a one-element array

    def test_a_matrix_cannot_replace_a_number(self):
        gain = self.bd().GAIN(2.0)
        with self.assertRaises(TypeError):
            gain.set_param("K", np.eye(2))

    def test_arrays_must_keep_their_shape(self):
        gain = self.bd().GAIN(np.eye(2))
        with self.assertRaises(ValueError) as cm:
            gain.set_param("K", np.eye(3))
        self.assertIn("(2, 2)", str(cm.exception))
        self.assertIn("(3, 3)", str(cm.exception))

    def test_a_list_of_numbers_becomes_an_array_of_the_same_dtype(self):
        gain = self.bd().GAIN(np.zeros((2, 2)))
        gain.set_param("K", [[1, 2], [3, 4]])
        self.assertEqual(gain.K.dtype, np.float64)
        nt.assert_array_equal(gain.K, [[1, 2], [3, 4]])

    def test_float_cannot_go_into_an_integer_array(self):
        const = self.bd().CONSTANT(np.array([1, 2, 3]))
        with self.assertRaises(ValueError) as cm:
            const.set_param("value", np.array([1.5, 2.5, 3.5]))
        self.assertIn("int64", str(cm.exception))

    def test_an_integer_array_goes_into_a_float_array(self):
        const = self.bd().CONSTANT(np.array([1.0, 2.0]))
        const.set_param("value", np.array([3, 4]))
        self.assertEqual(const.value.dtype, np.float64)

    def test_bool_stays_bool(self):
        gain = self.bd().GAIN(2.0, premul=False)
        gain.set_param("premul", True)
        for bad in (1, 0.0, "yes"):
            with self.subTest(bad=bad), self.assertRaises(TypeError):
                gain.set_param("premul", bad)

    def test_text_stays_text_and_callables_stay_callable(self):
        bd = self.bd()
        wave = bd.WAVEFORM("sine", freq=1)
        with self.assertRaises(TypeError):
            wave.set_param("wave", 3)
        func = bd.FUNCTION(lambda x: x, name="f")
        func.set_param("func", abs)  # another callable
        with self.assertRaises(TypeError):
            func.set_param("func", 3)


class ValidatorTest(ParamTestCase):
    def test_validate_is_called_with_the_new_value(self):
        class Checked(FunctionBlock):
            nin = 1
            nout = 1

            def __init__(self, level=1.0, **blockargs):
                super().__init__(**blockargs)
                self.level = level
                self.add_param("level", validate=self._check)

            def _check(self, value):
                if value > 10:
                    raise ValueError("level is at most 10")

            def output(self, t, inputs, x):
                return [inputs[0]]

        block = Checked(bd=self.bd())
        block.set_param("level", 5.0)
        with self.assertRaises(ValueError):
            block.set_param("level", 11.0)
        self.assertEqual(block.level, 5.0)

    def test_sum_signs_must_match_the_number_of_inputs(self):
        total = self.bd().SUM("+-")
        total.set_param("signs", "-+")
        self.assertEqual(total.signs, "-+")
        for bad in ("+++", "+", "+x"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                total.set_param("signs", bad)

    def test_prod_ops_must_match_the_number_of_inputs(self):
        prod = self.bd().PROD("**")
        prod.set_param("ops", "*/")
        for bad in ("***", "*+"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                prod.set_param("ops", bad)

    def test_step_values_must_stay_one_type(self):
        step = self.bd().STEP(off=0.0, on=1.0)
        step.set_param("off", 0.5)
        with self.assertRaises(TypeError):
            step.set_param("off", np.zeros(2))


class _Tuned(FunctionBlock):
    """A block whose parameter is a property: the setter rebuilds derived state."""

    nin = 1
    nout = 1

    def __init__(self, gain=1.0, **blockargs):
        super().__init__(**blockargs)
        self._gain = gain
        self.scaled = 10 * gain  # derived state
        self.add_param("gain")

    @property
    def gain(self):
        return self._gain

    @gain.setter
    def gain(self, value):
        if value <= 0:
            raise ValueError("gain must be positive")
        self._gain = value
        self.scaled = 10 * value

    def output(self, t, inputs, x):
        return [inputs[0] * self.scaled]


class PropertyTest(ParamTestCase):
    def test_the_setter_rebuilds_derived_state(self):
        block = _Tuned(2.0, bd=self.bd())
        self.assertEqual(block.parameters(), {"gain": 2.0})
        old = block.set_param("gain", 3.0)
        self.assertEqual(old, 2.0)
        self.assertEqual(block.scaled, 30.0)

    def test_the_setter_can_refuse(self):
        block = _Tuned(2.0, bd=self.bd())
        with self.assertRaises(ValueError):
            block.set_param("gain", -1.0)
        self.assertEqual(block.gain, 2.0)

    def test_type_is_enforced_through_the_getter(self):
        block = _Tuned(2.0, bd=self.bd())
        with self.assertRaises(TypeError):
            block.set_param("gain", "big")


class EndToEndTest(ParamTestCase):
    def run_gain(self, k):
        bd = self.bd()
        gain = bd.GAIN(2.0, name="g")
        bd.connect(bd.CONSTANT(1.5), gain)
        bd.compile(verbose=False)
        if k is not None:
            gain.set_param("K", k)
        return self.sim.run(bd, T=1, dt=0.1, watch=[gain]).y[:, 0]

    def test_a_new_value_is_used_by_the_run(self):
        nt.assert_allclose(self.run_gain(None), 3.0)
        nt.assert_allclose(self.run_gain(4.0), 6.0)


class SetOptionTest(ParamTestCase):
    def update(self, bd, *setparam):
        sim = bdsim.BDSim(
            graphics=None,
            progress=False,
            banner=False,
            quiet=True,
            setparam=list(setparam),
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            sim.update_parameters(bd)
        return buf.getvalue()

    def test_set_goes_through_set_param(self):
        bd = self.bd()
        gain = bd.GAIN(2.0, name="gain.0")
        text = self.update(bd, "gain.0:K=3")
        self.assertEqual(gain.K, 3.0)
        self.assertIs(type(gain.K), float)
        self.assertIn("gain.0", text)

    def test_unknown_parameter_is_a_value_error_naming_the_choices(self):
        bd = self.bd()
        bd.GAIN(2.0, name="gain.0")
        with self.assertRaises(ValueError) as cm:
            self.update(bd, "gain.0:nope=3")
        self.assertIn("settable", str(cm.exception))
        self.assertIn("K", str(cm.exception))

    def test_type_is_enforced(self):
        bd = self.bd()
        bd.GAIN(np.eye(2), name="gain.0")
        with self.assertRaises(ValueError) as cm:
            self.update(bd, "gain.0:K=3")
        self.assertIn("gain.0:K", str(cm.exception))

    def test_a_start_time_parameter_can_be_set(self):
        bd = self.bd()
        step = bd.STEP(T=1.0, off=0.0, on=1.0, name="step.0")
        self.update(bd, "step.0:T=2.5")
        self.assertEqual(step.T, 2.5)


class TransferFunctionTest(ParamTestCase):
    """LTI_SISO and LTI_SISO_S: num and den are parameters, A, B and C are rebuilt from them."""

    def make(self, kind, num=1, den=(1, 1)):
        bd = self.bd()
        den = list(den)
        if kind == "LTI_SISO":
            return bd.LTI_SISO(num, den, name="tf")
        return bd.LTI_SISO_S(bd.clock(0.1), num, den, name="tf")

    def assertSameRealisation(self, got, expected):
        for name in "ABC":
            nt.assert_allclose(getattr(got, name), getattr(expected, name), atol=1e-12)

    def test_the_parameters_are_num_den_and_the_initial_state(self):
        for kind in ("LTI_SISO", "LTI_SISO_S"):
            with self.subTest(kind=kind):
                self.assertEqual(
                    sorted(self.make(kind).parameters()), ["den", "num", "x0"]
                )

    def test_num_and_den_are_the_polynomials_as_coefficients(self):
        for kind in ("LTI_SISO", "LTI_SISO_S"):
            with self.subTest(kind=kind):
                tf = self.make(kind, num=[1, 2], den=[[1, 1], [1, 2]])  # (s+1)(s+2)
                nt.assert_array_equal(tf.num, [1.0, 2.0])
                nt.assert_array_equal(tf.den, [1.0, 3.0, 2.0])

    def test_D_is_still_the_feedthrough_matrix(self):
        strictly_proper = self.make("LTI_SISO", num=[1], den=(1, 1))
        self.assertIsNone(strictly_proper.D)
        proper = self.make("LTI_SISO", num=[1, 1], den=(1, 2))  # s+1 over s+2
        nt.assert_allclose(proper.D, [[1.0]])

    def test_changing_den_rebuilds_the_realisation(self):
        for kind in ("LTI_SISO", "LTI_SISO_S"):
            with self.subTest(kind=kind):
                tf = self.make(kind, den=(1, 1))
                old = tf.set_param("den", [1, 3])
                nt.assert_array_equal(old, [1.0, 1.0])
                self.assertSameRealisation(tf, self.make(kind, den=(1, 3)))

    def test_changing_num_uses_the_denominator_it_already_has(self):
        for kind in ("LTI_SISO", "LTI_SISO_S"):
            with self.subTest(kind=kind):
                tf = self.make(kind, num=[1], den=(1, 2, 3))
                tf.set_param("num", [1, 2])
                self.assertSameRealisation(
                    tf, self.make(kind, num=[1, 2], den=(1, 2, 3))
                )
                nt.assert_array_equal(tf.den, [1.0, 2.0, 3.0])

    def test_factors_are_accepted(self):
        tf = self.make("LTI_SISO", den=(1, 3, 2))
        tf.set_param("den", [[1, 1], [1, 4]])  # (s+1)(s+4) = s^2 + 5s + 4
        nt.assert_array_equal(tf.den, [1.0, 5.0, 4.0])

    def test_the_order_cannot_change_and_nothing_is_left_half_done(self):
        for kind in ("LTI_SISO", "LTI_SISO_S"):
            with self.subTest(kind=kind):
                tf = self.make(kind, den=(1, 1))
                before = tf.A.copy()
                with self.assertRaises(ValueError) as cm:
                    tf.set_param("den", [1, 2, 3])
                self.assertIn("order", str(cm.exception))
                nt.assert_array_equal(tf.A, before)
                nt.assert_array_equal(tf.den, [1.0, 1.0])

    def test_a_non_causal_numerator_is_refused(self):
        tf = self.make("LTI_SISO", den=(1, 1))
        with self.assertRaises(ValueError):
            tf.set_param("num", [1, 2, 3])

    def test_a_numerator_that_would_add_feedthrough_is_refused(self):
        tf = self.make("LTI_SISO", den=(1, 1))  # strictly proper: no feedthrough
        with self.assertRaises(ValueError) as cm:
            tf.set_param("num", [1, 0])  # s/(s+1)
        self.assertIn("feedthrough", str(cm.exception))

    def test_a_zero_leading_denominator_coefficient_is_refused(self):
        tf = self.make("LTI_SISO", den=(1, 1))
        with self.assertRaises(ValueError):
            tf.set_param("den", [0, 1])

    def test_the_step_response_follows_the_new_denominator(self):
        bd = self.bd()
        tf = bd.LTI_SISO(1, [1, 1], name="tf")
        bd.connect(bd.CONSTANT(1.0), tf)
        bd.compile(verbose=False)
        tf.set_param("den", [1, 2])  # 1/(s+2): y = 0.5 (1 - exp(-2 t))
        out = self.sim.run(
            bd, T=3, dt=0.1, watch=[tf], solver_args=dict(rtol=1e-10, atol=1e-12)
        )
        nt.assert_allclose(out.y[:, 0], 0.5 * (1 - np.exp(-2 * out.t)), atol=1e-7)

    def test_set_from_text(self):
        bd = self.bd()
        tf = bd.LTI_SISO([1, 2], [1, 2, 3], name="tf")
        sim = bdsim.BDSim(
            graphics=None,
            progress=False,
            banner=False,
            quiet=True,
            setparam=["tf:num=5 6", "tf:den=1,4,5"],
        )
        with redirect_stdout(io.StringIO()):
            sim.update_parameters(bd)
        nt.assert_array_equal(tf.num, [5.0, 6.0])
        nt.assert_array_equal(tf.den, [1.0, 4.0, 5.0])


class OldNamesTest(ParamTestCase):
    """N= and D= were renamed num= and den=; the old keywords work for now, with a warning."""

    def build(self, kind, **kwargs):
        bd = self.bd()
        if kind == "LTI_SISO":
            return bd.LTI_SISO(**kwargs)
        return bd.LTI_SISO_S(bd.clock(0.1), **kwargs)

    def test_the_old_keywords_still_work_and_warn(self):
        for kind in ("LTI_SISO", "LTI_SISO_S"):
            with self.subTest(kind=kind):
                new = self.build(kind, num=[1, 2], den=[1, 2, 3])
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    old = self.build(kind, N=[1, 2], D=[1, 2, 3])
                messages = [
                    str(w.message)
                    for w in caught
                    if issubclass(w.category, DeprecationWarning)
                ]
                self.assertTrue(
                    any("'N'" in m and "num" in m for m in messages), messages
                )
                self.assertTrue(
                    any("'D'" in m and "den" in m for m in messages), messages
                )
                for name in "ABC":
                    nt.assert_array_equal(getattr(old, name), getattr(new, name))
                nt.assert_array_equal(old.num, new.num)

    def test_one_old_keyword_with_one_new(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            tf = self.build("LTI_SISO", N=[3], den=[1, 2])
        nt.assert_array_equal(tf.num, [3.0])
        nt.assert_array_equal(tf.den, [1.0, 2.0])

    def test_old_and_new_together_is_an_error(self):
        # the class directly: the block factory wraps the error in BlockCreationError
        from bdsim.blocks.continuous import LTI_SISO
        from bdsim.blocks.sampled import LTI_SISO_S

        bd = self.bd()
        with self.assertRaises(TypeError) as cm:
            LTI_SISO(num=[1], N=[2], bd=bd)
        self.assertIn("num", str(cm.exception))
        with self.assertRaises(TypeError) as cm:
            LTI_SISO_S(bd.clock(0.1), den=[1, 2], D=[1, 3], bd=bd)
        self.assertIn("den", str(cm.exception))

    def test_positional_calls_are_unchanged(self):
        tf = self.bd().LTI_SISO(0.5, [2, 1])
        nt.assert_array_equal(tf.num, [0.5])
        nt.assert_array_equal(tf.den, [2.0, 1.0])

    def test_an_old_bd_model_still_loads(self):
        import json
        import tempfile

        from bdsim.bin.bdrun import bdload

        def block(i, kind, ins, outs, params):
            return {
                "id": i,
                "block_type": kind,
                "title": kind.lower(),
                "pos_x": 0,
                "pos_y": 0,
                "width": 100,
                "height": 100,
                "flipped": False,
                "inputsNum": len(ins),
                "outputsNum": len(outs),
                "inputs": [{"id": k, "index": j} for j, k in enumerate(ins)],
                "outputs": [{"id": k, "index": j} for j, k in enumerate(outs)],
                "parameters": params,
            }

        model = {
            "blocks": [
                block(1, "CONSTANT", [], [10], [["value", 1.0]]),
                block(
                    2, "LTI_SISO", [20], [21], [["N", 0.5], ["D", [2, 1]], ["x0", None]]
                ),
                block(3, "NULL", [30], [], []),
            ],
            "wires": [
                {"start_socket": 10, "end_socket": 20},
                {"start_socket": 21, "end_socket": 30},
            ],
        }
        with tempfile.NamedTemporaryFile("w", suffix=".bd", delete=False) as f:
            json.dump(model, f)
        bd = self.bd()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            bdload(bd, f.name, allow_eval=False)
        self.assertTrue(any(issubclass(w.category, DeprecationWarning) for w in caught))
        tf = bd["lti_siso"]
        nt.assert_array_equal(tf.num, [0.5])
        nt.assert_array_equal(tf.den, [2.0, 1.0])


class FeedthroughMatrixTest(ParamTestCase):
    """LTI_SS.D: it must conform, and a block built without feedthrough cannot gain it."""

    A = np.array([[-1.0]])
    B = np.array([[1.0]])
    C = np.array([[1.0]])

    def test_the_state_space_matrices_are_parameters(self):
        lti = self.bd().LTI_SS(self.A, self.B, self.C)
        self.assertEqual(sorted(lti.parameters()), ["A", "B", "C", "D", "x0"])

    def test_zero_d_stays_none_and_non_zero_is_refused(self):
        lti = self.bd().LTI_SS(self.A, self.B, self.C)  # no feedthrough
        self.assertIsNone(lti.D)
        lti.set_param("D", 0.0)
        self.assertIsNone(lti.D)
        with self.assertRaises(ValueError) as cm:
            lti.set_param("D", 2.0)
        self.assertIn("feedthrough", str(cm.exception))

    def test_d_must_conform_to_b_and_c(self):
        lti = self.bd().LTI_SS(self.A, self.B, self.C, D=np.array([[1.0]]))
        with self.assertRaises(ValueError) as cm:
            lti.set_param("D", np.ones((2, 2)))
        self.assertIn("(1, 1)", str(cm.exception))
        self.assertIn("(2, 2)", str(cm.exception))

    def test_d_can_change_when_the_block_has_feedthrough(self):
        lti = self.bd().LTI_SS(self.A, self.B, self.C, D=np.array([[1.0]]))
        lti.set_param("D", np.array([[3.0]]))
        nt.assert_array_equal(lti.D, [[3.0]])
        lti.set_param(
            "D", np.array([[0.0]])
        )  # zero, but the block still has feedthrough
        nt.assert_array_equal(lti.D, [[0.0]])

    def test_a_matrix_keeps_its_shape(self):
        lti = self.bd().LTI_SS(self.A, self.B, self.C)
        with self.assertRaises(ValueError):
            lti.set_param("A", np.eye(2))
        lti.set_param("A", np.array([[-5.0]]))
        nt.assert_array_equal(lti.A, [[-5.0]])


class SubsystemSetTest(ParamTestCase):
    def test_a_block_inside_a_subsystem_can_be_set_by_its_path(self):
        ss = self.sim.blockdiagram(name="inner")
        inp = ss.INPORT(1)
        gain = ss.GAIN(2.0, name="g")
        outp = ss.OUTPORT(1)
        ss.connect(inp, gain)
        ss.connect(gain, outp)
        bd = self.bd()
        sub = bd.SUBSYSTEM(ss, name="sub")
        bd.connect(bd.CONSTANT(1.0), sub)
        bd.connect(sub, bd.NULL(1))
        bd.compile(verbose=False)

        sim = bdsim.BDSim(
            graphics=None,
            progress=False,
            banner=False,
            quiet=True,
            setparam=["sub/g:K=5"],
        )
        with redirect_stdout(io.StringIO()):
            sim.update_parameters(bd)
        self.assertEqual(bd["sub/g"].K, 5.0)


class TextValueTest(ParamTestCase):
    """--set reads the text according to the type of the current value."""

    def update(self, bd, *setparam):
        sim = bdsim.BDSim(
            graphics=None,
            progress=False,
            banner=False,
            quiet=True,
            setparam=list(setparam),
        )
        with redirect_stdout(io.StringIO()):
            sim.update_parameters(bd)

    def test_a_string_parameter_takes_the_text(self):
        bd = self.bd()
        total = bd.SUM("++", name="err")
        self.update(bd, "err:signs=+-")
        self.assertEqual(total.signs, "+-")
        self.update(bd, "err:mode=rc")
        self.assertEqual(total.mode, "rc")

    def test_quotes_around_text_are_removed(self):
        bd = self.bd()
        total = bd.SUM("++", name="err")
        self.update(bd, "err:signs='-+'")
        self.assertEqual(total.signs, "-+")

    def test_a_bool_parameter_takes_true_or_false(self):
        bd = self.bd()
        gain = bd.GAIN(2.0, name="g")
        for text, expected in [
            ("true", True),
            ("False", False),
            ("1", True),
            ("no", False),
        ]:
            with self.subTest(text=text):
                self.update(bd, f"g:premul={text}")
                self.assertIs(gain.premul, expected)

    def test_a_bool_parameter_refuses_other_text(self):
        bd = self.bd()
        bd.GAIN(2.0, name="g")
        with self.assertRaises(ValueError) as cm:
            self.update(bd, "g:premul=maybe")
        self.assertIn("true or false", str(cm.exception))

    def test_a_number_parameter_takes_an_int_or_a_float(self):
        bd = self.bd()
        gain = bd.GAIN(2.0, name="g")
        self.update(bd, "g:K=3")
        self.assertEqual((gain.K, type(gain.K)), (3.0, float))
        self.update(bd, "g:K=2.5e-1")
        self.assertEqual(gain.K, 0.25)
        with self.assertRaises(ValueError):
            self.update(bd, "g:K=lots")

    def test_an_array_parameter_takes_a_vector_or_a_matrix(self):
        bd = self.bd()
        vec = bd.CONSTANT(np.zeros(3), name="v")
        mat = bd.GAIN(np.eye(2), name="m")
        self.update(bd, "v:value=1 2 3", "m:K=1 2; 3 4")
        nt.assert_array_equal(vec.value, [1, 2, 3])
        nt.assert_array_equal(mat.K, [[1, 2], [3, 4]])
        self.update(bd, "v:value=4,5,6")
        nt.assert_array_equal(vec.value, [4, 5, 6])

    def test_an_integer_array_stays_integer(self):
        bd = self.bd()
        vec = bd.CONSTANT(np.array([1, 2, 3]), name="v")
        self.update(bd, "v:value=7 8 9")
        self.assertEqual(vec.value.dtype, np.int64)
        nt.assert_array_equal(vec.value, [7, 8, 9])

    def test_the_shape_of_an_array_is_still_enforced(self):
        bd = self.bd()
        bd.CONSTANT(np.zeros(3), name="v")
        with self.assertRaises(ValueError) as cm:
            self.update(bd, "v:value=1 2")
        self.assertIn("v:value", str(cm.exception))

    def test_a_list_cannot_be_set_from_text(self):
        bd = self.bd()
        bd.SCOPE(labels=["a"], name="sc")
        with self.assertRaises(ValueError) as cm:
            self.update(bd, "sc:labels=a b")
        self.assertIn("text", str(cm.exception))


class FunctionFromTextTest(ParamTestCase):
    def test_a_function_cannot_be_set_from_text(self):
        bd = self.bd()
        bd.FUNCTION(lambda x: x, name="f")
        sim = bdsim.BDSim(
            graphics=None,
            progress=False,
            banner=False,
            quiet=True,
            setparam=["f:func=3"],
        )
        with self.assertRaises(ValueError) as cm:
            sim.update_parameters(bd)
        self.assertIn("function", str(cm.exception))
        self.assertIn("set_param", str(cm.exception))


class ReportParamsTest(ParamTestCase):
    def diagram(self):
        bd = self.bd()
        gain = bd.GAIN(2.5, name="gain.0")
        bd.connect(bd.CONSTANT(np.r_[1.0, 2.0], name="c"), bd.MUX(1, name="mux"))
        bd.connect(bd.CONSTANT(1.0, name="k"), gain)
        bd.connect(gain, bd.NULL(1))
        bd.STEP(T=2.0, name="s")
        return bd

    def printed(self, bd, *args, **kwargs):
        buf = io.StringIO()
        with redirect_stdout(buf):
            bd.report_params(*args, **kwargs)
        return buf.getvalue()

    def test_names_are_as_used_by_set_and_values_are_current(self):
        text = self.printed(self.diagram())
        self.assertIn("gain.0:K", text)
        self.assertIn("2.5", text)
        self.assertIn("s:T", text)
        self.assertIn("setup", text)
        self.assertIn("anytime", text)

    def test_every_listed_name_can_be_used_with_set(self):
        bd = self.diagram()
        text = self.printed(bd)
        for b in bd.blocklist:
            for name in b.parameters():
                self.assertIn(f"{b.name}:{name}", text)

    def test_fixed_parameters_are_left_out_unless_asked_for(self):
        bd = self.diagram()
        self.assertNotIn("mux:nin", self.printed(bd))
        self.assertIn("mux:nin", self.printed(bd, fixed=True))

    def test_arrays_are_shown_compactly(self):
        bd = self.bd()
        bd.CONSTANT(np.arange(1000.0), name="long")
        text = self.printed(bd)
        self.assertIn("long:value", text)
        self.assertLess(max(len(line) for line in text.splitlines()), 140)

    def test_shows_the_value_after_it_has_been_set(self):
        bd = self.diagram()
        bd["gain.0"].set_param("K", 9.0)
        self.assertIn("9.0", self.printed(bd))

    def test_sim_report_type_params(self):
        sim = bdsim.BDSim(graphics=None, progress=False, banner=False)
        bd = sim.blockdiagram()
        bd.GAIN(2.5, name="gain.0")
        buf = io.StringIO()
        with redirect_stdout(buf):
            sim.report(bd, type="params")
        self.assertIn("gain.0:K", buf.getvalue())


class ParamOptionTest(ParamTestCase):
    def compile_output(self, **options):
        sim = bdsim.BDSim(
            graphics=None, progress=False, banner=False, quiet=True, **options
        )
        bd = sim.blockdiagram()
        bd.connect(bd.CONSTANT(1.0), bd.GAIN(2.5, name="gain.0"))
        bd.connect(bd["gain.0"], bd.NULL(1))
        buf = io.StringIO()
        with redirect_stdout(buf):
            bd.compile(verbose=False)
        return buf.getvalue()

    def test_off_by_default(self):
        self.assertNotIn("gain.0:K", self.compile_output())

    def test_param_prints_the_table_at_the_end_of_compilation(self):
        self.assertIn("gain.0:K", self.compile_output(param=True))

    def test_command_line_switch(self):
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["prog", "--param"]):
            sim = bdsim.BDSim(graphics=None, progress=False, banner=False)
        self.assertTrue(sim.options.param)
        self.assertFalse(
            bdsim.BDSim(
                graphics=None, progress=False, banner=False, sysargs=False
            ).options.param
        )


# ---------------------------------------------------------------------------- #
#  every parameter of every block is accounted for


BLOCKS = Path(bdsim.__file__).parent / "blocks"

# Parameters that need a handler (derived state, a unit, an initial state, a
# structure that may be absent) and do not have one yet.  This list is the work
# still to do: it must shrink, and a parameter that is handled or declared must
# be removed from it.
PENDING: set[str] = set()


def block_parameters():
    """{Class.param: registered or not} from the source of every block module."""
    found = {}
    for path in sorted(BLOCKS.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            init = next(
                (
                    n
                    for n in cls.body
                    if isinstance(n, ast.FunctionDef) and n.name == "__init__"
                ),
                None,
            )
            if init is None:
                continue
            a = init.args
            params = [
                x.arg
                for x in a.posonlyargs + a.args + a.kwonlyargs
                if x.arg not in ("self", "blockargs", "kwargs")
            ]
            registered = set()
            for node in ast.walk(init):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "add_param"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                ):
                    registered.add(node.args[0].value)
            for p in params:
                found[f"{cls.name}.{p}"] = "registered" if p in registered else "none"
            for p in registered - set(params):
                found[f"{cls.name}.{p}"] = "not an __init__ argument"
    return found


class EveryParameterIsAccountedForTest(unittest.TestCase):
    """The parameter name is the __init__ argument name; each is registered or pending."""

    def test_no_parameter_is_left_out(self):
        left_out = sorted(
            k
            for k, how in block_parameters().items()
            if how == "none" and k not in PENDING
        )
        self.assertEqual(
            left_out,
            [],
            'register with self.add_param(name) (when="never" if it is fixed), or add to PENDING',
        )

    def test_names_registered_or_fixed_are_real_arguments(self):
        wrong = {
            k: how for k, how in block_parameters().items() if "not an __init__" in how
        }
        self.assertEqual(wrong, {})

    def test_pending_only_lists_parameters_that_still_need_doing(self):
        done = sorted(k for k in PENDING if block_parameters().get(k) == "registered")
        self.assertEqual(done, [], "remove from PENDING")
        gone = sorted(k for k in PENDING if k not in block_parameters())
        self.assertEqual(gone, [], "not a block parameter")


if __name__ == "__main__":
    unittest.main()
