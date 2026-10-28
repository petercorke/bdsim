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

from bdsim.blocks.sources import Constant, Piecewise, Ramp, Step, Time, WaveForm

import unittest
import numpy.testing as nt


class SourceBlockTest(unittest.TestCase):
    def test_constant(self):

        block = Constant(value=7)
        out = block.test_output()
        self.assertIsInstance(out, list)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0], 7)

        block = Constant(value=np.r_[1, 2, 3])
        out = block.test_output()
        self.assertIsInstance(out, list)
        self.assertEqual(len(out), 1)
        nt.assert_array_almost_equal(out[0], np.r_[1, 2, 3])

    def test_time(self):

        block = Time()
        self.assertEqual(block.test_output(t=0.0)[0], 0.0)
        self.assertEqual(block.test_output(t=1.25)[0], 1.25)
        self.assertEqual(block.test_output(t=10)[0], 10)

    def test_waveform_sine(self):

        block = WaveForm(wave="sine")

        self.assertAlmostEqual(block.test_output(t=0)[0], 0)
        self.assertAlmostEqual(block.test_output(t=0.25)[0], 1)
        self.assertAlmostEqual(block.test_output(t=0.75)[0], -1)

        block = WaveForm(wave="sine", amplitude=2)
        self.assertAlmostEqual(block.test_output(t=0)[0], 0)
        self.assertAlmostEqual(block.test_output(t=0.25)[0], 2)
        self.assertAlmostEqual(block.test_output(t=0.75)[0], -2)

        block = WaveForm(wave="sine", offset=1)
        self.assertAlmostEqual(block.test_output(t=0)[0], 1)
        self.assertAlmostEqual(block.test_output(t=0.25)[0], 2)
        self.assertAlmostEqual(block.test_output(t=0.75)[0], 0)

        block = WaveForm(wave="sine", amplitude=2, offset=1)
        self.assertAlmostEqual(block.test_output(t=0)[0], 1)
        self.assertAlmostEqual(block.test_output(t=0.25)[0], 3)
        self.assertAlmostEqual(block.test_output(t=0.75)[0], -1)

        block = WaveForm(wave="sine", min=10, max=12)
        self.assertAlmostEqual(block.test_output(t=0)[0], 11)
        self.assertAlmostEqual(block.test_output(t=0.25)[0], 12)
        self.assertAlmostEqual(block.test_output(t=0.75)[0], 10)

        block = WaveForm(wave="sine", phase=0.25)
        self.assertAlmostEqual(block.test_output(t=0)[0], -1)
        self.assertAlmostEqual(block.test_output(t=0.25)[0], 0)
        self.assertAlmostEqual(block.test_output(t=0.75)[0], 0)

        block = WaveForm(wave="sine", unit="rad/s")
        self.assertAlmostEqual(block.test_output(t=0)[0], 0)
        self.assertAlmostEqual(block.test_output(t=math.pi / 2)[0], 1)
        self.assertAlmostEqual(block.test_output(t=3 / 2 * math.pi)[0], -1)

    def test_waveform_triangle(self):

        block = WaveForm(wave="triangle")

        self.assertAlmostEqual(block.test_output(t=0)[0], 0)
        self.assertAlmostEqual(block.test_output(t=0)[0], 0)
        self.assertAlmostEqual(block.test_output(t=0.25)[0], 1)
        self.assertAlmostEqual(block.test_output(t=0.75)[0], -1)

        block = WaveForm(wave="triangle", amplitude=2)
        self.assertAlmostEqual(block.test_output(t=0)[0], 0)
        self.assertAlmostEqual(block.test_output(t=0.25)[0], 2)
        self.assertAlmostEqual(block.test_output(t=0.75)[0], -2)

        block = WaveForm(wave="triangle", offset=1)
        self.assertAlmostEqual(block.test_output(t=0)[0], 1)
        self.assertAlmostEqual(block.test_output(t=0.25)[0], 2)
        self.assertAlmostEqual(block.test_output(t=0.75)[0], 0)

        block = WaveForm(wave="triangle", amplitude=2, offset=1)
        self.assertAlmostEqual(block.test_output(t=0)[0], 1)
        self.assertAlmostEqual(block.test_output(t=0.25)[0], 3)
        self.assertAlmostEqual(block.test_output(t=0.75)[0], -1)

        block = WaveForm(wave="triangle", min=10, max=12)
        self.assertAlmostEqual(block.test_output(t=0)[0], 11)
        self.assertAlmostEqual(block.test_output(t=0.25)[0], 12)
        self.assertAlmostEqual(block.test_output(t=0.75)[0], 10)

        block = WaveForm(wave="triangle", phase=0.25)
        self.assertAlmostEqual(block.test_output(t=0)[0], -1)
        self.assertAlmostEqual(block.test_output(t=0.25)[0], 0)
        self.assertAlmostEqual(block.test_output(t=0.75)[0], 0)

        block = WaveForm(wave="triangle", unit="rad/s")
        self.assertAlmostEqual(block.test_output(t=0)[0], 0)
        self.assertAlmostEqual(block.test_output(t=math.pi / 2)[0], 1)
        self.assertAlmostEqual(block.test_output(t=3 / 2 * math.pi)[0], -1)

    def test_waveform_square(self):

        block = WaveForm(wave="square")
        self.assertAlmostEqual(block.test_output(t=0)[0], 1)
        self.assertAlmostEqual(block.test_output(t=0.25)[0], 1)
        self.assertAlmostEqual(block.test_output(t=0.75)[0], -1)

        block = WaveForm(wave="square", amplitude=2)
        self.assertAlmostEqual(block.test_output(t=0)[0], 2)
        self.assertAlmostEqual(block.test_output(t=0.25)[0], 2)
        self.assertAlmostEqual(block.test_output(t=0.75)[0], -2)

        block = WaveForm(wave="square", offset=1)
        self.assertAlmostEqual(block.test_output(t=0)[0], 2)
        self.assertAlmostEqual(block.test_output(t=0.25)[0], 2)
        self.assertAlmostEqual(block.test_output(t=0.75)[0], 0)

        block = WaveForm(wave="square", amplitude=2, offset=1)
        self.assertAlmostEqual(block.test_output(t=0)[0], 3)
        self.assertAlmostEqual(block.test_output(t=0.25)[0], 3)
        self.assertAlmostEqual(block.test_output(t=0.75)[0], -1)

        block = WaveForm(wave="square", min=10, max=12)
        self.assertAlmostEqual(block.test_output(t=0)[0], 12)
        self.assertAlmostEqual(block.test_output(t=0.25)[0], 12)
        self.assertAlmostEqual(block.test_output(t=0.75)[0], 10)

        block = WaveForm(wave="square", phase=0.25)
        self.assertAlmostEqual(block.test_output(t=0)[0], -1)
        self.assertAlmostEqual(block.test_output(t=0.25)[0], 1)
        self.assertAlmostEqual(block.test_output(t=0.75)[0], -1)

        block = WaveForm(wave="square", unit="rad/s")
        self.assertAlmostEqual(block.test_output(t=0)[0], 1)
        self.assertAlmostEqual(block.test_output(t=math.pi / 2)[0], 1)
        self.assertAlmostEqual(block.test_output(t=3 / 2 * math.pi)[0], -1)

    def test_step(self):

        block = Step()
        self.assertEqual(block.test_output(t=0)[0], 0)

        self.assertEqual(block.test_output(t=0.9)[0], 0)
        self.assertEqual(block.test_output(t=1)[0], 1)

        block = Step(off=1, on=2)
        self.assertEqual(block.test_output(t=0.9)[0], 1)
        self.assertEqual(block.test_output(t=1)[0], 2)

        block = Step(T=2)
        self.assertEqual(block.test_output(t=1.9)[0], 0)
        self.assertEqual(block.test_output(t=2.1)[0], 1)

    def test_piecewise(self):

        block = Piecewise((0, 0), (1, 1), (2, 1), (2, 0), (10, 0))
        out = block.test_output(t=0)
        self.assertIsInstance(out, list)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0], 0)

        self.assertEqual(block.test_output(t=0.5)[0], 0)
        self.assertEqual(block.test_output(t=1)[0], 1)
        self.assertEqual(block.test_output(t=1.1)[0], 1)
        self.assertEqual(block.test_output(t=1.9)[0], 1)
        self.assertEqual(block.test_output(t=2)[0], 0)
        self.assertEqual(block.test_output(t=2.1)[0], 0)
        self.assertEqual(block.test_output(t=9)[0], 0)

    def test_ramp(self):
        block = Ramp()
        self.assertAlmostEqual(block.test_output(t=0)[0], 0)
        self.assertAlmostEqual(block.test_output(t=1)[0], 0)
        self.assertAlmostEqual(block.test_output(t=2)[0], 1)

        block = Ramp(off=-1, T=2, slope=0.5)
        self.assertAlmostEqual(block.test_output(t=0)[0], -1)
        self.assertAlmostEqual(block.test_output(t=2)[0], -1)
        self.assertAlmostEqual(block.test_output(t=4)[0], 0)
        self.assertAlmostEqual(block.test_output(t=6)[0], 1)


class SourceValueTypeTest(unittest.TestCase):
    """The values a source emits all have one type, checked when it is created."""

    def test_step_promotes_numbers(self):
        block = Step(off=0, on=1.0)
        self.assertIs(type(block.test_output(t=0)[0]), float)
        self.assertIs(type(block.test_output(t=2)[0]), float)

    def test_step_keeps_ints_and_bools(self):
        self.assertIs(type(Step(off=0, on=1).test_output(t=0)[0]), int)
        self.assertIs(type(Step(off=True, on=False).test_output(t=2)[0]), bool)

    def test_step_of_any_one_type(self):
        # numeric lists become arrays, anything else is emitted as given
        out = Step(off=[0, 0], on=[1, 2]).test_output(t=2)[0]
        self.assertIsInstance(out, np.ndarray)
        nt.assert_array_equal(out, [1, 2])
        self.assertEqual(Step(off="zero", on="one").test_output(t=2)[0], "one")
        self.assertEqual(Step(off=["a"], on=["b"]).test_output(t=2)[0], ["b"])

    def test_step_asarray_false_keeps_lists(self):
        block = Step(off=[0], on=[1], asarray=False)
        self.assertEqual(block.test_output(t=0)[0], [0])
        self.assertEqual(block.test_output(t=2)[0], [1])

    def test_piecewise_asarray(self):
        out = Piecewise((0, [0, 0]), (1, [1, 2])).test_output(t=2)[0]
        self.assertIsInstance(out, np.ndarray)
        nt.assert_array_equal(out, [1, 2])
        out = Piecewise((0, [0, 0]), (1, [1, 2]), asarray=False).test_output(t=2)[0]
        self.assertEqual(out, [1, 2])

    def test_ramp_of_lists(self):
        block = Ramp(off=[0, 0], slope=[1, 2])
        nt.assert_array_equal(block.test_output(t=2)[0], [1, 2])

    def test_step_refuses_mixed_types(self):
        for off, on in [(0, [1]), (0, True), ("a", 1), (np.zeros(2), 1.0)]:
            with self.subTest(off=off, on=on), self.assertRaises(TypeError):
                Step(off=off, on=on)

    def test_step_refuses_mismatched_arrays(self):
        with self.assertRaises(ValueError):
            Step(off=np.zeros(2), on=np.ones(3))

    def test_piecewise_promotes_numbers(self):
        block = Piecewise((0, 0), (1, 2.5), (2, 1))
        for t in (0, 1.5, 2.5):
            self.assertIs(type(block.test_output(t=t)[0]), float)

    def test_piecewise_refuses_mixed_types(self):
        with self.assertRaises(TypeError):
            Piecewise((0, 0), (1, [1]))
        with self.assertRaises(ValueError):
            Piecewise((0, np.zeros(2)), (1, np.zeros(3)))

    def test_ramp_is_always_a_float(self):
        # off is an int but off + slope*(t - T) is a float
        block = Ramp(off=0, slope=1)
        self.assertIs(type(block.test_output(t=0)[0]), float)
        self.assertIs(type(block.test_output(t=3)[0]), float)

    def test_ramp_of_vectors(self):
        block = Ramp(off=np.zeros(2), slope=np.r_[1.0, 2.0])
        nt.assert_array_equal(block.test_output(t=0)[0], [0, 0])
        nt.assert_array_equal(block.test_output(t=2)[0], [1, 2])
        with self.assertRaises(ValueError):
            Ramp(off=np.zeros(2), slope=np.ones(3))


class ConstantValueTest(unittest.TestCase):
    """CONSTANT turns a list or tuple of numbers into an ndarray, unless told not to."""

    def test_list_of_numbers_becomes_an_array(self):
        out = Constant([1, 2, 3]).test_output()[0]
        self.assertIsInstance(out, np.ndarray)
        nt.assert_array_equal(out, [1, 2, 3])
        self.assertEqual(out.dtype, np.int64)

    def test_tuple_and_nested_lists(self):
        out = Constant((1.0, 2.0)).test_output()[0]
        self.assertIsInstance(out, np.ndarray)
        self.assertEqual(out.dtype, np.float64)
        out = Constant([[1, 2], [3, 4]]).test_output()[0]
        self.assertEqual(out.shape, (2, 2))

    def test_asarray_false_emits_the_list(self):
        value = [1, 2, 3]
        out = Constant(value, asarray=False).test_output()[0]
        self.assertIs(out, value)
        value = (1, 2, 3)
        self.assertIs(Constant(value, asarray=False).test_output()[0], value)

    def test_only_numbers_are_converted(self):
        for value in (["a", "b"], [1, "a"], [None, 1], [[1, 2], [3]], [], [[]]):
            with self.subTest(value=value):
                self.assertIs(Constant(value).test_output()[0], value)

    def test_other_values_are_unchanged(self):
        array = np.r_[1, 2, 3]
        self.assertIs(Constant(array).test_output()[0], array)
        for value in (5, 2.5, True, "text", None, {"a": 1}, np.float32(2)):
            with self.subTest(value=value):
                self.assertIs(Constant(value).test_output()[0], value)

    def test_explicit_dtypes_are_kept(self):
        out = Constant(np.array([1, 2], dtype=np.float32)).test_output()[0]
        self.assertEqual(out.dtype, np.float32)
        out = Constant([np.float32(1), np.float32(2)]).test_output()[0]
        self.assertEqual(out.dtype, np.float32)


# ---------------------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()
