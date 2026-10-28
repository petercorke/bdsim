#!/usr/bin/env python3
"""NumPy dtype literals for parameters given as text: float32([1, 2]), uint16(5), ...

A .bd file is JSON, so a parameter that is not a JSON type is a string.  The text
form is the NumPy constructor, parsed safely (no eval), so it works with
``allow_eval=False``.
"""

import json
import tempfile
import unittest
import warnings

import numpy as np
import numpy.testing as nt

import bdsim
from bdsim.bin.bdrun import bdload
from bdsim.literals import NOT_A_LITERAL, format_literal, parse_literal


class ParseScalarTest(unittest.TestCase):
    def test_scalars_have_the_requested_type(self):
        for text, kind, value in [
            ("float32(2)", np.float32, 2.0),
            ("float64(2.5)", np.float64, 2.5),
            ("float16(0.5)", np.float16, 0.5),
            ("uint16(5)", np.uint16, 5),
            ("uint8(255)", np.uint8, 255),
            ("int8(-5)", np.int8, -5),
            ("int64(-7)", np.int64, -7),
            ("complex64(1+2j)", np.complex64, 1 + 2j),
            ("complex128(-1.5-2j)", np.complex128, -1.5 - 2j),
            ("complex128(3j)", np.complex128, 3j),
            ("bool_(1)", np.bool_, True),
            ("bool_(False)", np.bool_, False),
        ]:
            with self.subTest(text=text):
                got = parse_literal(text)
                self.assertIs(type(got), kind)
                self.assertEqual(got, value)

    def test_special_values(self):
        self.assertTrue(np.isinf(parse_literal("float32(inf)")))
        self.assertTrue(parse_literal("float32(-inf)") < 0)
        self.assertTrue(np.isnan(parse_literal("float64(nan)")))
        self.assertEqual(parse_literal("float64(pi)"), np.pi)
        self.assertTrue(np.signbit(parse_literal("float32(-0.0)")))

    def test_exact_values(self):
        self.assertEqual(parse_literal("float32(0.1)"), np.float32(0.1))
        self.assertEqual(parse_literal("int64(9007199254740993)"), 9007199254740993)
        self.assertEqual(parse_literal("uint64(18446744073709551615)"), 2**64 - 1)

    def test_prefix_whitespace_and_equals(self):
        for text in (
            "np.float32(2)",
            "numpy.float32(2)",
            "  float32( 2 )  ",
            "=float32(2)",
        ):
            with self.subTest(text=text):
                got = parse_literal(text)
                self.assertIs(type(got), np.float32)
                self.assertEqual(got, 2.0)


class ParseArrayTest(unittest.TestCase):
    def test_arrays_have_the_requested_dtype(self):
        for text, dtype, value in [
            ("float32([1, 2])", np.float32, [1, 2]),
            ("uint16([5, 6])", np.uint16, [5, 6]),
            ("int8([-1, 0, 1])", np.int8, [-1, 0, 1]),
            ("float64((1.5, 2.5))", np.float64, [1.5, 2.5]),
            ("complex64([1+2j, 3])", np.complex64, [1 + 2j, 3]),
            ("bool_([1, 0, 1])", np.bool_, [True, False, True]),
        ]:
            with self.subTest(text=text):
                got = parse_literal(text)
                self.assertIsInstance(got, np.ndarray)
                self.assertEqual(got.dtype, dtype)
                nt.assert_array_equal(got, value)

    def test_nested_lists_are_n_dimensional(self):
        got = parse_literal("int16([[1, 2], [3, 4]])")
        self.assertEqual(got.shape, (2, 2))
        self.assertEqual(got.dtype, np.int16)
        self.assertEqual(parse_literal("float32([[[1], [2]]])").shape, (1, 2, 1))

    def test_empty(self):
        got = parse_literal("float32([])")
        self.assertEqual(got.shape, (0,))
        self.assertEqual(got.dtype, np.float32)

    def test_special_values_in_arrays(self):
        got = parse_literal("float32([inf, -inf, nan, pi])")
        self.assertTrue(np.isinf(got[0]) and np.isinf(got[1]) and np.isnan(got[2]))


class NotALiteralTest(unittest.TestCase):
    def test_other_text_is_left_alone(self):
        for text in [
            "",
            "hello",
            "V[1]",
            "[1, 2, 3]",
            "2+3",
            "float32",
            "float32()",
            "float32(1, 2)",
            "float32(a=1)",
            "float32(x)",
            "float32([1, x])",
            "float32(1) + 1",
            "float32(2)[0]",
            "foo(1)",
            "np.os.system(1)",
            "float32(__import__('os'))",
            "float32(abs(-1))",
            "float32(1 if 1 else 2)",
            "float32(lambda: 1)",
            "float32('2')",
            "float32(None)",
            "float32([[1, 2], 3])",  # ragged
            "(",
        ]:
            with self.subTest(text=text):
                self.assertIs(parse_literal(text), NOT_A_LITERAL)

    def test_nothing_is_ever_executed(self):
        marker = []
        namespace = {"mark": lambda: marker.append(1) or 1}
        # parse_literal has no namespace; a call inside the argument is not a literal
        self.assertIs(parse_literal("float32(mark())"), NOT_A_LITERAL)
        self.assertEqual(marker, [])
        self.assertIs(
            parse_literal("float32(__import__('sys').exit(3))"), NOT_A_LITERAL
        )
        del namespace

    def test_non_strings(self):
        for value in (1, 2.5, [1, 2], None, np.zeros(2)):
            self.assertIs(parse_literal(value), NOT_A_LITERAL)


class OutOfRangeTest(unittest.TestCase):
    def test_integer_out_of_range_is_an_error_not_a_wrap(self):
        for text in ("uint16(70000)", "uint8(-1)", "int8(128)", "uint8([1, 300])"):
            with self.subTest(text=text), self.assertRaises(ValueError) as cm:
                parse_literal(text)
            self.assertIn(text.split("(")[0], str(cm.exception))

    def test_float_overflow_is_an_error(self):
        for text in ("float32(1e60)", "float16(70000)", "float32([1, 1e60])"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_literal(text)

    def test_an_explicit_inf_is_fine(self):
        self.assertTrue(np.isinf(parse_literal("float32(inf)")))


class FormatLiteralTest(unittest.TestCase):
    def roundtrip(self, value):
        text = format_literal(value)
        got = parse_literal(text)
        self.assertIsNot(got, NOT_A_LITERAL, text)
        self.assertEqual(np.asarray(got).dtype, np.asarray(value).dtype, text)
        self.assertEqual(np.shape(got), np.shape(value), text)
        np.testing.assert_array_equal(got, value, err_msg=text)
        return text

    def test_scalars_round_trip(self):
        for value in [
            np.float32(0.1),
            np.float32(1e-30),
            np.float32(3.4e38),
            np.float64(0.1),
            np.float64(1e-300),
            np.float64(2**53 + 2),
            np.float16(0.333),
            np.uint16(5),
            np.uint64(2**64 - 1),
            np.int8(-128),
            np.int64(-(2**63)),
            np.complex64(1.5 - 2j),
            np.complex128(0.1 + 0.2j),
            np.bool_(True),
            np.float64(np.inf),
            np.float32(-np.inf),
        ]:
            with self.subTest(value=repr(value)):
                self.roundtrip(value)

    def test_nan_round_trips(self):
        text = format_literal(np.float32(np.nan))
        self.assertTrue(np.isnan(parse_literal(text)))

    def test_negative_zero(self):
        self.assertTrue(np.signbit(parse_literal(format_literal(np.float32(-0.0)))))

    def test_arrays_round_trip(self):
        rng = np.random.default_rng(1)
        for dtype in (np.float16, np.float32, np.float64):
            with self.subTest(dtype=dtype):
                self.roundtrip(rng.normal(size=(3, 2)).astype(dtype))
        for dtype in (np.uint8, np.uint16, np.int32, np.int64):
            with self.subTest(dtype=dtype):
                self.roundtrip(np.array([[1, 2], [3, 4]], dtype=dtype))
        self.roundtrip(np.array([True, False]))
        self.roundtrip(np.array([1 + 2j, 3 - 1j], dtype=np.complex64))
        self.roundtrip(np.zeros((0,), dtype=np.float32))
        self.roundtrip(np.arange(8, dtype=np.int16).reshape(2, 2, 2))

    def test_shortest_text_for_floats(self):
        self.assertEqual(format_literal(np.float32(0.1)), "float32(0.1)")
        self.assertEqual(format_literal(np.float64(0.1)), "float64(0.1)")
        self.assertEqual(
            format_literal(np.array([1, 2], dtype=np.uint16)), "uint16([1, 2])"
        )

    def test_what_cannot_be_written(self):
        for value in (
            np.array(["a"]),
            np.array([None], dtype=object),
            "text",
            5,
            [1, 2],
            np.complex128(complex(np.nan, 1)),
        ):
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                format_literal(value)


def _model(value_text, gain_text):
    """CONSTANT -> GAIN -> NULL, as a .bd model whose parameters are given as text."""
    return {
        "blocks": [
            {
                "id": 100,
                "block_type": "CONSTANT",
                "title": "const",
                "pos_x": 0,
                "pos_y": 0,
                "width": 100,
                "height": 100,
                "flipped": False,
                "inputsNum": 0,
                "outputsNum": 1,
                "inputs": [],
                "outputs": [{"id": 1000, "index": 0}],
                "parameters": [["value", value_text]],
            },
            {
                "id": 200,
                "block_type": "GAIN",
                "title": "gain",
                "pos_x": 100,
                "pos_y": 0,
                "width": 100,
                "height": 100,
                "flipped": False,
                "inputsNum": 1,
                "outputsNum": 1,
                "inputs": [{"id": 2000, "index": 0}],
                "outputs": [{"id": 2001, "index": 0}],
                "parameters": [["K", gain_text]],
            },
            {
                "id": 300,
                "block_type": "NULL",
                "title": "null",
                "pos_x": 200,
                "pos_y": 0,
                "width": 100,
                "height": 100,
                "flipped": False,
                "inputsNum": 1,
                "outputsNum": 0,
                "inputs": [{"id": 3000, "index": 0}],
                "outputs": [],
                "parameters": [],
            },
        ],
        "wires": [
            {"start_socket": 1000, "end_socket": 2000},
            {"start_socket": 2001, "end_socket": 3000},
        ],
    }


class BdloadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False, quiet=True)

    def load(self, model, **kwargs):
        with tempfile.NamedTemporaryFile("w", suffix=".bd", delete=False) as f:
            json.dump(model, f)
        bd = self.sim.blockdiagram()
        bdload(bd, f.name, **kwargs)
        return bd

    def test_literals_work_without_eval(self):
        bd = self.load(_model("float32([1, 2])", "float32(3)"), allow_eval=False)
        const, gain = bd["const"], bd["gain"]
        self.assertEqual(const.value.dtype, np.float32)
        nt.assert_array_equal(const.value, [1, 2])
        self.assertIs(type(gain.K), np.float32)

    def test_leading_equals_is_accepted_too(self):
        bd = self.load(_model("=uint16([5, 6])", "=int8(-2)"), allow_eval=False)
        self.assertEqual(bd["const"].value.dtype, np.uint16)
        self.assertIs(type(bd["gain"].K), np.int8)

    def test_no_eval_warning_for_a_literal_only_model(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            self.load(_model("float32([1, 2])", "float32(3)"))

    def test_plain_json_values_are_unchanged(self):
        bd = self.load(_model([1, 2, 3], 3), allow_eval=False)
        self.assertIsInstance(bd["const"].value, np.ndarray)  # asarray default
        self.assertEqual(bd["gain"].K, 3)

    def test_an_empty_string_parameter_loads(self):
        # value[0] used to raise IndexError for ""
        bd = self.load(_model("", 2), allow_eval=False)
        self.assertEqual(bd["const"].value, "")

    def test_ordinary_text_stays_text(self):
        bd = self.load(_model("V[1]", 2), allow_eval=False)
        self.assertEqual(bd["const"].value, "V[1]")

    def test_expressions_are_still_refused_without_eval(self):
        with self.assertRaises(RuntimeError):
            self.load(_model("float32(2)", "=2+1"), allow_eval=False)

    def test_out_of_range_names_the_parameter(self):
        with self.assertRaises(Exception) as cm:
            self.load(_model("uint16(70000)", 1), allow_eval=False)
        self.assertIn("uint16", str(cm.exception))


class SetOptionTest(unittest.TestCase):
    def test_set_accepts_a_literal(self):
        sim = bdsim.BDSim(
            graphics=None,
            progress=False,
            banner=False,
            quiet=True,
            setparam=["gain.0:K=float32([1,2])", "const.0:value=uint16(5)"],
        )
        bd = sim.blockdiagram()
        bd.connect(bd.CONSTANT(0, name="const.0"), bd.GAIN(1, name="gain.0"))
        sim.update_parameters(bd)
        self.assertEqual(bd["gain.0"].K.dtype, np.float32)
        self.assertIs(type(bd["const.0"].value), np.uint16)

    def test_set_still_accepts_numbers_and_matrices(self):
        sim = bdsim.BDSim(
            graphics=None,
            progress=False,
            banner=False,
            quiet=True,
            setparam=["gain.0:K=3", "const.0:value=1 2; 3 4"],
        )
        bd = sim.blockdiagram()
        bd.connect(bd.CONSTANT(0, name="const.0"), bd.GAIN(1, name="gain.0"))
        sim.update_parameters(bd)
        self.assertEqual(bd["gain.0"].K, 3)
        self.assertEqual(bd["const.0"].value.shape, (2, 2))


if __name__ == "__main__":
    unittest.main()
