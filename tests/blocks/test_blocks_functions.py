#!/usr/bin/env python3

import numpy as np
import math

from bdsim.blocks.functions import (
    Abs,
    Anoise,
    Clip,
    Deadband,
    Function,
    Gain,
    Interpolate,
    Mnoise,
    Pow,
    Prod,
    Sign,
    Sqrt,
    Sum,
)

import unittest
import numpy.testing as nt


class FunctionBlockTest(unittest.TestCase):
    def test_gain(self):

        block = Gain(2)
        self.assertEqual(block.test_output(1)[0], 2)

        block = Gain(2)
        nt.assert_array_almost_equal(
            block.test_output(np.r_[1, 2, 3])[0], np.r_[2, 4, 6]
        )

        block = Gain(np.r_[1, 2, 3])
        nt.assert_array_almost_equal(block.test_output(2)[0], np.r_[2, 4, 6])

        block = Gain(np.array([[1, 2], [3, 4]]))
        nt.assert_array_almost_equal(
            block.test_output(2)[0], np.array([[2, 4], [6, 8]])
        )

        block = Gain(np.array([[1, 2], [3, 4]]))
        nt.assert_array_almost_equal(block.test_output(np.r_[1, 2])[0], np.r_[7, 10])

        block = Gain(np.array([[1, 2], [3, 4]]), premul=True)
        nt.assert_array_almost_equal(block.test_output(np.r_[1, 2])[0], np.r_[5, 11])

        block = Gain(np.array([[1, 2], [3, 4]]))
        nt.assert_array_almost_equal(
            block.test_output(np.array([[5, 6], [7, 8]]))[0],
            np.array([[23, 34], [31, 46]]),
        )

        block = Gain(np.array([[1, 2], [3, 4]]), premul=True)
        nt.assert_array_almost_equal(
            block.test_output(np.array([[5, 6], [7, 8]]))[0],
            np.array([[19, 22], [43, 50]]),
        )

        block = Gain(np.array([[1, 2], [3, 4]]), premul=False)
        out = block.test_output(np.array([[5, 6], [7, 8]]))
        nt.assert_array_almost_equal(out[0], np.array([[23, 34], [31, 46]]))

    def test_pow(self):

        block = Pow(3)
        self.assertEqual(block.test_output(2)[0], 8)

        block = Pow(2)
        nt.assert_array_almost_equal(block.test_output(np.r_[2, 3])[0], np.r_[4, 9])

        block = Pow(3, matrix=True)
        nt.assert_array_almost_equal(
            block.test_output(np.array([[2, 0], [0, 3]]))[0],
            np.array([[8, 0], [0, 27]]),
        )

    def test_pow_matrix_float_integer_exponent(self):
        # 2.0 is integral, so must take the matrix_power path, same as 2
        m = np.array([[1, 2], [3, 4]])
        nt.assert_array_almost_equal(
            Pow(2.0, matrix=True).test_output(m)[0],
            Pow(2, matrix=True).test_output(m)[0],
        )
        nt.assert_array_almost_equal(Pow(2.0, matrix=True).test_output(m)[0], m @ m)

    def test_sqrt(self):
        block = Sqrt()
        self.assertEqual(block.test_output(4)[0], 2)
        self.assertEqual(block.test_output(0)[0], 0)

        # signed: sgn(x) * sqrt(|x|)
        self.assertEqual(block.test_output(-9)[0], -3)

        nt.assert_array_almost_equal(
            block.test_output(np.r_[4, -9, 0, 2.25])[0], np.r_[2, -3, 0, 1.5]
        )
        nt.assert_array_almost_equal(
            block.test_output(np.array([[1, -4], [-16, 25]]))[0],
            np.array([[1, -2], [-4, 5]]),
        )

    def test_sign(self):
        block = Sign()
        self.assertEqual(block.test_output(3.5)[0], 1)
        self.assertEqual(block.test_output(-0.1)[0], -1)
        self.assertEqual(block.test_output(0)[0], 0)
        self.assertEqual(block.test_output(-7)[0], -1)

        nt.assert_array_equal(
            block.test_output(np.r_[-2.5, 0, 4, -0.0])[0], np.r_[-1, 0, 1, 0]
        )
        nt.assert_array_equal(
            block.test_output(np.array([[1, -2], [0, 5]]))[0],
            np.array([[1, -1], [0, 1]]),
        )

    def test_abs(self):
        block = Abs()
        self.assertEqual(block.test_output(3.5)[0], 3.5)
        self.assertEqual(block.test_output(-3.5)[0], 3.5)
        self.assertEqual(block.test_output(0)[0], 0)
        self.assertEqual(block.test_output(-7)[0], 7)

        nt.assert_array_equal(
            block.test_output(np.r_[-2.5, 0, 4, -0.0])[0], np.r_[2.5, 0, 4, 0]
        )
        nt.assert_array_equal(
            block.test_output(np.array([[1, -2], [0, -5]]))[0],
            np.array([[1, 2], [0, 5]]),
        )

    def test_anoise(self):
        # scalar in -> scalar out, array in -> same shape out
        block = Anoise(sigma=0.5, seed=1)
        self.assertEqual(np.shape(block.test_output(1.0)[0]), ())
        self.assertEqual(np.shape(block.test_output(np.zeros(3))[0]), (3,))
        self.assertEqual(np.shape(block.test_output(np.zeros((2, 3)))[0]), (2, 3))

        # zero sigma is the identity
        nt.assert_array_equal(Anoise(sigma=0).test_output(np.r_[1, 2, 3])[0], [1, 2, 3])

        # seeded blocks are reproducible
        x = np.zeros(5)
        nt.assert_array_equal(
            Anoise(sigma=1, seed=42).test_output(x)[0],
            Anoise(sigma=1, seed=42).test_output(x)[0],
        )

        # statistics: mean and std of added noise
        out = Anoise(sigma=2.0, seed=3).test_output(np.full(100000, 10.0))[0]
        self.assertAlmostEqual(out.mean(), 10.0, delta=0.05)
        self.assertAlmostEqual(out.std(), 2.0, delta=0.05)

        # per-element sigma
        out = Anoise(sigma=np.r_[0.0, 1000.0], seed=4).test_output(np.zeros((5000, 2)))[0]
        self.assertTrue(np.all(out[:, 0] == 0))
        self.assertAlmostEqual(out[:, 1].std(), 1000.0, delta=50)

        # incompatible sigma shape
        with self.assertRaises(ValueError):
            Anoise(sigma=np.r_[1, 2, 3]).test_output(np.zeros(2))

    def test_mnoise(self):
        block = Mnoise(sigma=0.5, seed=1)
        self.assertEqual(np.shape(block.test_output(1.0)[0]), ())
        self.assertEqual(np.shape(block.test_output(np.zeros(3))[0]), (3,))
        self.assertEqual(np.shape(block.test_output(np.zeros((2, 3)))[0]), (2, 3))

        # zero sigma is the identity
        nt.assert_array_equal(Mnoise(sigma=0).test_output(np.r_[1, 2, 3])[0], [1, 2, 3])

        # zero input stays zero, whatever the noise
        nt.assert_array_equal(Mnoise(sigma=1, seed=1).test_output(np.zeros(4))[0], 0)

        # seeded blocks are reproducible
        x = np.ones(5)
        nt.assert_array_equal(
            Mnoise(sigma=1, seed=42).test_output(x)[0],
            Mnoise(sigma=1, seed=42).test_output(x)[0],
        )

        # statistics: x * N(1, sigma^2) has mean x and std |x| * sigma
        out = Mnoise(sigma=0.1, seed=3).test_output(np.full(100000, 10.0))[0]
        self.assertAlmostEqual(out.mean(), 10.0, delta=0.05)
        self.assertAlmostEqual(out.std(), 1.0, delta=0.02)

        # incompatible sigma shape
        with self.assertRaises(ValueError):
            Mnoise(sigma=np.r_[1, 2, 3]).test_output(np.zeros(2))

    def test_sum(self):

        block = Sum("++")
        self.assertEqual(block.test_output(10, 5)[0], 15)

        block = Sum("+-")
        self.assertEqual(block.test_output(10, 5)[0], 5)

        block = Sum("-+")
        self.assertEqual(block.test_output(10, 5)[0], -5)

        block = Sum("-+", mode="r")
        self.assertEqual(block.test_output(10, 5)[0], -5)

        block = Sum("+-", mode="c")
        self.assertEqual(block.test_output(0, -5 * math.pi)[0], -math.pi)
        self.assertEqual(block.test_output(math.pi, -math.pi)[0], 0)

        block = Sum("+-", mode="C")
        self.assertEqual(block.test_output(0, -5 * math.pi)[0], math.pi)
        self.assertEqual(block.test_output(math.pi, -math.pi)[0], 0)

        block = Sum("++", mode="l")
        self.assertEqual(block.test_output(math.pi / 2, math.pi)[0], math.pi / 2)
        self.assertEqual(block.test_output(math.pi, -math.pi)[0], 0)

        block = Sum("++", mode="rc")
        x = np.r_[math.pi, math.pi]
        nt.assert_array_almost_equal(block.test_output(x, x)[0], [2 * math.pi, 0])
        x = np.ones((2, 4)) * math.pi
        y = np.vstack((np.ones((4,)) * 2 * math.pi, np.zeros((4,))))
        nt.assert_array_almost_equal(block.test_output(x, x)[0], y)

    def test_prod(self):

        block = Prod("**")
        self.assertEqual(block.test_output(10, 5)[0], 50)

        block = Prod("*/")
        self.assertEqual(block.test_output(10, 5)[0], 2)

        block = Prod("/*")
        self.assertEqual(block.test_output(10, 5)[0], 0.5)

        # test matrix and np cases

    def test_clip(self):

        block = Clip(min=-1, max=1)
        self.assertEqual(block.test_output(0)[0], 0)

        self.assertEqual(block.test_output(1)[0], 1)

        self.assertEqual(block.test_output(10)[0], 1)

        self.assertEqual(block.test_output(-1)[0], -1)

        self.assertEqual(block.test_output(-10)[0], -1)

        block = Clip(min=-2, max=3)
        out = block.test_output(1)
        self.assertEqual(out[0], 1)
        self.assertEqual(block.test_output(1)[0], 1)

        self.assertEqual(block.test_output(10)[0], 3)

        self.assertEqual(block.test_output(-1)[0], -1)

        self.assertEqual(block.test_output(-10)[0], -2)

        nt.assert_array_equal(
            block.test_output(np.r_[-10, -2, -1, 0, 1, 3, 10])[0],
            np.r_[-2, -2, -1, 0, 1, 3, 3],
        )

    def test_clip_array_bounds(self):
        # elementwise bounds
        block = Clip(min=np.r_[-1, -2], max=np.r_[1, 2])
        nt.assert_array_equal(block.test_output(np.r_[-5, 5])[0], np.r_[-1, 2])
        nt.assert_array_equal(block.test_output(np.r_[0.5, -0.5])[0], np.r_[0.5, -0.5])

        # scalar bounds applied to every element
        block = Clip(min=-1, max=1)
        nt.assert_array_equal(block.test_output(np.r_[-5, 0, 5])[0], np.r_[-1, 0, 1])

        # defaults are unbounded
        block = Clip()
        self.assertEqual(block.test_output(1e9)[0], 1e9)
        self.assertEqual(block.test_output(-1e9)[0], -1e9)

    def test_deadband_symmetric(self):
        block = Deadband(2)
        self.assertEqual(block.test_output(0)[0], 0)
        self.assertEqual(block.test_output(1.5)[0], 0)
        self.assertEqual(block.test_output(-1.5)[0], 0)

        # edges are inside the band, output continuous across them
        self.assertEqual(block.test_output(2)[0], 0)
        self.assertEqual(block.test_output(-2)[0], 0)

        # outside: distance from nearest edge
        self.assertEqual(block.test_output(5)[0], 3)
        self.assertEqual(block.test_output(-5)[0], -3)

        nt.assert_array_almost_equal(
            block.test_output(np.r_[-5, -2, -1, 0, 1, 2, 5])[0],
            np.r_[-3, 0, 0, 0, 0, 0, 3],
        )

    def test_deadband_asymmetric(self):
        for d in ([-1, 3], (-1, 3), np.r_[-1, 3]):
            block = Deadband(d)
            self.assertEqual(block.test_output(0)[0], 0)
            self.assertEqual(block.test_output(3)[0], 0)
            self.assertEqual(block.test_output(-1)[0], 0)
            self.assertEqual(block.test_output(5)[0], 2)
            self.assertEqual(block.test_output(-4)[0], -3)

        # the band need not contain zero
        block = Deadband([1, 3])
        self.assertEqual(block.test_output(0)[0], -1)
        self.assertEqual(block.test_output(2)[0], 0)
        self.assertEqual(block.test_output(4)[0], 1)

        # array input, same band for every element
        block = Deadband([-1, 3])
        nt.assert_array_almost_equal(
            block.test_output(np.array([[-4, 0], [3.5, 5]]))[0],
            np.array([[-3, 0], [0.5, 2]]),
        )

    def test_deadband_zero_width(self):
        block = Deadband(0)
        self.assertEqual(block.test_output(0)[0], 0)
        self.assertEqual(block.test_output(2)[0], 2)
        self.assertEqual(block.test_output(-2)[0], -2)

    def test_deadband_errors(self):
        with self.assertRaises(ValueError):
            Deadband(-1)
        with self.assertRaises(ValueError):
            Deadband([3, -1])
        with self.assertRaises(ValueError):
            Deadband([1, 2, 3])
        with self.assertRaises(ValueError):
            Deadband([[1, 2], [3, 4]])

    def test_function(self):

        def test(x, y):
            return x + y

        block = Function(test, nin=2)
        self.assertEqual(block.test_output(1, 2)[0], 3)

        block = Function(lambda x, y: x + y, nin=2)
        self.assertEqual(block.test_output(1, 2)[0], 3)

        block = Function(lambda x, y, a, b: x + y + a + b, nin=2, fargs=(3, 4))
        self.assertEqual(block.test_output(1, 2)[0], 10)

        block = Function(
            lambda x, y, a=0, b=0: x + y + a + b, nin=2, fkwargs={"a": 3, "b": 4}
        )
        self.assertEqual(block.test_output(1, 2)[0], 10)

    def test_interpolate(self):
        block = Interpolate(x=(0, 5, 10), y=(0, 1, 0))

        self.assertEqual(block.test_output(0)[0], 0)

        self.assertEqual(block.test_output(2.5)[0], 0.5)
        self.assertEqual(block.test_output(5)[0], 1)
        self.assertEqual(block.test_output(7.5)[0], 0.5)
        self.assertEqual(block.test_output(10)[0], 0)

        block = Interpolate(x=np.r_[0, 5, 10], y=np.r_[0, 1, 0])
        self.assertEqual(block.test_output(0)[0], 0)
        self.assertEqual(block.test_output(2.5)[0], 0.5)
        self.assertEqual(block.test_output(5)[0], 1)
        self.assertEqual(block.test_output(7.5)[0], 0.5)
        self.assertEqual(block.test_output(10)[0], 0)

        block = Interpolate(x=np.r_[0, 5, 10], y=np.r_[0, 1, 0].reshape((3, 1)))
        self.assertEqual(block.test_output(0)[0], 0)
        self.assertEqual(block.test_output(2.5)[0], 0.5)
        self.assertEqual(block.test_output(5)[0], 1)
        self.assertEqual(block.test_output(7.5)[0], 0.5)
        self.assertEqual(block.test_output(10)[0], 0)

        block = Interpolate(xy=[(0, 0), (5, 1), (10, 0)])
        self.assertEqual(block.test_output(0)[0], 0)
        self.assertEqual(block.test_output(2.5)[0], 0.5)
        self.assertEqual(block.test_output(5)[0], 1)
        self.assertEqual(block.test_output(7.5)[0], 0.5)
        self.assertEqual(block.test_output(10)[0], 0)

        # block = _Interpolate(xy=np.array([(0,0), (5,1), (10,0)]).T)
        # self.assertEqual(block.test_output()[0], 0)
        # self.assertEqual(block.test_output()[0], 0.5)
        # self.assertEqual(block.test_output()[0], 1)
        # self.assertEqual(block.test_output()[0], 0.5)
        # self.assertEqual(block.test_output()[0], 0)

        block = Interpolate(x=(0, 5, 10), y=(0, 1, 0), time=True)
        self.assertEqual(block.test_output(t=0)[0], 0)
        self.assertEqual(block.test_output(t=2.5)[0], 0.5)
        self.assertEqual(block.test_output(t=5)[0], 1)
        self.assertEqual(block.test_output(t=7.5)[0], 0.5)
        self.assertEqual(block.test_output(t=10)[0], 0)

        block = Interpolate(x=np.r_[0, 5, 10], y=np.r_[0, 1, 0], time=True)
        self.assertEqual(block.test_output(t=0)[0], 0)
        self.assertEqual(block.test_output(t=2.5)[0], 0.5)
        self.assertEqual(block.test_output(t=5)[0], 1)
        self.assertEqual(block.test_output(t=7.5)[0], 0.5)
        self.assertEqual(block.test_output(t=10)[0], 0)

        block = Interpolate(xy=[(0, 0), (5, 1), (10, 0)], time=True)

        self.assertEqual(block.test_output(t=0)[0], 0)
        self.assertEqual(block.test_output(t=2.5)[0], 0.5)
        self.assertEqual(block.test_output(t=5)[0], 1)
        self.assertEqual(block.test_output(t=7.5)[0], 0.5)
        self.assertEqual(block.test_output(t=10)[0], 0)

        # block = _Interpolate(xy=np.array([(0,0), (5,1), (10,0)]), time=True)
        # out = block.test_output(0)
        # self.assertIsInstance(out, list)
        # self.assertAlmostEqual(len(out), 1)
        # self.assertEqual(block.test_output(0)[0], 0)
        # self.assertEqual(block.test_output(2.5)[0], 0.5)
        # self.assertEqual(block.test_output(5)[0], 1)
        # self.assertEqual(block.test_output(7.5)[0], 0.)
        # self.assertEqual(block.test_output(10)[0], 0)


# ---------------------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()
