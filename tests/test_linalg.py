#!/usr/bin/env python3

import numpy as np
import scipy.interpolate
import math

from bdsim.blocks.linalg import *

import unittest
import numpy.testing as nt

class LinalgBlockTest(unittest.TestCase):

    def test_inverse(self):

        block = Inverse()
        x = np.array([[2, 1], [7, 4]])
        xi = np.array([[4, -1], [-7, 2]])
        nt.assert_array_almost_equal(block._output(x)[0], xi)
        nt.assert_array_almost_equal(block._output(x)[1], np.linalg.cond(x))

        # singular matrix
        a = np.array([[1, 2], [2, 4]])
        with self.assertRaises(RuntimeError):
            x = block._output(a)[0]

        # pseudo-inverse
        block = Inverse(pinv=True)
        x = block._output(a)[0]
        # axa = a
        nt.assert_array_almost_equal(a @ x @ a - a, np.zeros((2,2)))
        
    def test_transpose(self):
        block = Transpose()
        x = np.array([[1, 2], [3, 4]])
        nt.assert_array_almost_equal(block._output(x)[0], x.T)

    def test_det(self):
        block = Det()
        x = np.array([[1, 2], [3, 4]])
        nt.assert_array_almost_equal(block._output(x)[0], -2)

    def test_cond(self):
        block = Cond()
        x = np.array([[2, 1], [7, 4]])
        nt.assert_array_almost_equal(block._output(x)[0], np.linalg.cond(x))

    def test_norm(self):
        block = Norm()
        x = np.array([3, 4])
        nt.assert_array_almost_equal(block._output(x)[0], 5)

    def test_slice1(self):
    
        x = np.arange(10) + 100
        block = Slice1([2])
        nt.assert_array_almost_equal(block._output(x)[0], 102)

        block = Slice1([4, 5, 6])
        nt.assert_array_almost_equal(block._output(x)[0], [104, 105, 106])

        block = Slice1((4, 7, 1))
        nt.assert_array_almost_equal(block._output(x)[0], [104, 105, 106])

        block = Slice1((4, 7, None))
        nt.assert_array_almost_equal(block._output(x)[0], [104, 105, 106])

        block = Slice1((6, 3, -1))
        nt.assert_array_almost_equal(block._output(x)[0], [106, 105, 104])

        with self.assertRaises(RuntimeError):
            x = block._output(np.array([[1,2], [3,4]]))[0]

        with self.assertRaises(ValueError):
            block = Slice1(index=(1,2))

    def test_slice2(self):

        x = np.arange(20).reshape((4, 5)) + 100

        block = Slice2(rows=[2], cols=None)
        nt.assert_array_almost_equal(block._output(x)[0], np.c_[np.arange(110, 115)].T)

        block = Slice2(rows=[2, 1], cols=None)
        nt.assert_array_almost_equal(block._output(x)[0], 
            np.vstack((np.arange(110, 115), np.arange(105, 110)))
            )

        block = Slice2(rows=(2,3,None), cols=None)
        nt.assert_array_almost_equal(block._output(x)[0], np.c_[np.arange(110, 115)].T)

        block = Slice2(rows=(2, 0, -1), cols=None)
        nt.assert_array_almost_equal(block._output(x)[0], 
            np.vstack((np.arange(110, 115), np.arange(105, 110)))
            )

        block = Slice2(cols=[2], rows=None)
        nt.assert_array_almost_equal(block._output(x)[0], np.c_[np.arange(102, 120, 5)])

        block = Slice2(cols=[2, 1], rows=None)
        nt.assert_array_almost_equal(block._output(x)[0], 
            np.column_stack((np.arange(102, 120, 5), np.arange(101, 120, 5)))
            )

        block = Slice2(cols=(2, 3, None), rows=None)
        nt.assert_array_almost_equal(block._output(x)[0], np.c_[np.arange(102, 120, 5)])

        block = Slice2(cols=(2, 0, -1), rows=None)
        nt.assert_array_almost_equal(block._output(x)[0], 
            np.column_stack((np.arange(102, 120, 5), np.arange(101, 120, 5)))
            )

        with self.assertRaises(RuntimeError):
            x = block._output(np.r_[1,2,3])[0]

        with self.assertRaises(ValueError):
            block = Slice2(rows=(1,2))

        with self.assertRaises(ValueError):
            block = Slice2(cols=(1,2))

    def test_flatten(self):

        x = np.arange(20).reshape((4, 5)) + 100

        block = Flatten('F')
        nt.assert_array_almost_equal(block._output(x)[0], x.flatten('F'))

        block = Flatten('C')
        nt.assert_array_almost_equal(block._output(x)[0], x.flatten('C'))

# ---------------------------------------------------------------------------------------#
if __name__ == '__main__':

    unittest.main()