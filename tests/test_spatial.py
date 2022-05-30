#!/usr/bin/env python3

import numpy as np
from spatialmath import *

from bdsim.blocks.spatial import *

import unittest
import numpy.testing as nt

class SpatialMathBlockTest(unittest.TestCase):

    def test_pose_postmul(self):

        A = SE3.Trans(1,2,3) * SE3.Rx(np.pi/2)
        block = Pose_postmul(A)
        B = SE3.Rz(np.pi/2)
        nt.assert_array_almost_equal(block._output(B)[0], B*A)

    def test_pose_premul(self):

        A = SE3.Trans(1,2,3) * SE3.Rx(np.pi/2)
        block = Pose_premul(A)
        B = SE3.Rz(np.pi/2)
        nt.assert_array_almost_equal(block._output(B)[0], A*B)

    def test_pose_inverse(self):

        block = Pose_inverse()
        A = SE3.Trans(1,2,3) * SE3.Rx(np.pi/2)

        nt.assert_array_almost_equal(block._output(A)[0], A.inv())

    def test_vector_transform(self):

        A = SE3.Trans(1,2,3) * SE3.Rx(np.pi/2)
        block = Transform_vector()
        B = np.r_[1,2,3]
        nt.assert_array_almost_equal(block._output(A,B)[0], A*B)
        

# ---------------------------------------------------------------------------------------#
if __name__ == '__main__':

    unittest.main()