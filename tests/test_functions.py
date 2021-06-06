#!/usr/bin/env python3

import numpy as np
import scipy.interpolate
import math

from bdsim.blocks.functions import *

import unittest
import numpy.testing as nt

class FunctionBlockTest(unittest.TestCase):

    def test_gain(self):

        block = Gain(2)
        self.assertEqual(block._eval(1)[0], 2)

        block = Gain(2)
        nt.assert_array_almost_equal(block._eval(np.r_[1,2,3])[0], np.r_[2,4,6])

        block = Gain(np.r_[1,2,3])
        nt.assert_array_almost_equal(block._eval(2)[0], np.r_[2,4,6])

        block = Gain(np.array([[1,2],[3,4]]))
        nt.assert_array_almost_equal(block._eval(2)[0], np.array([[2,4],[6,8]]))

        block = Gain(np.array([[1,2],[3,4]]))
        nt.assert_array_almost_equal(block._eval(np.r_[1,2])[0], np.r_[7, 10])
        
        block = Gain(np.array([[1,2],[3,4]]), premul=True)
        nt.assert_array_almost_equal(block._eval(np.r_[1,2])[0], np.r_[5, 11])

        block = Gain(np.array([[1,2],[3,4]]))
        nt.assert_array_almost_equal(block._eval(np.array([[5,6],[7,8]]))[0], np.array([[23,34],[31,46]]))
        
        block = Gain(np.array([[1,2],[3,4]]), premul=True)
        nt.assert_array_almost_equal(block._eval(np.array([[5,6],[7,8]]))[0], np.array([[19,22],[43,50]]))

        block = Gain(np.array([[1,2],[3,4]]), order='postmul')
        block.setinputs(np.array([[5,6],[7,8]]))
        out = block.output()
        nt.assert_array_almost_equal(out[0], np.array([[23,34],[31,46]]))

    def test_sum(self):

        block = Sum('++')
        self.assertEqual(block._eval(10, 5)[0], 15)

        block = Sum('+-')
        self.assertEqual(block._eval(10, 5)[0], 5)

        block = Sum('-+')
        self.assertEqual(block._eval(10, 5)[0], -5)


        block = Sum('+-', angles=True)
        self.assertEqual(block._eval(0, -5*math.pi)[0], -math.pi)
        
        self.assertEqual(block._eval(math.pi, -math.pi)[0], 0)
        
    def test_prod(self):

        block = Prod('**')
        self.assertEqual(block._eval(10, 5)[0], 50)

        block = Prod('*/')
        self.assertEqual(block._eval(10, 5)[0], 2)

        block = Prod('/*')
        self.assertEqual(block._eval(10, 5)[0], 0.5)
        
        # test matrix and np cases
        
    def test_clip(self):
        
        block = Clip(min=-1, max=1)
        self.assertEqual(block._eval(0)[0], 0)
        
        self.assertEqual(block._eval(1)[0], 1)
        
        self.assertEqual(block._eval(10)[0], 1)
        
        self.assertEqual(block._eval(-1)[0], -1)
        
        self.assertEqual(block._eval(-10)[0], -1)
        
        block = Clip(min=-2, max=3)
        block.setinputs(1)
        out = block.output()
        self.assertEqual(out[0], 1)
        self.assertEqual(block._eval(1)[0], 1)
        
        self.assertEqual(block._eval(10)[0], 3)
        
        self.assertEqual(block._eval(-1)[0], -1)
        
        self.assertEqual(block._eval(-10)[0], -2)
        
        nt.assert_array_equal(block._eval(np.r_[-10, -2, -1, 0, 1, 3, 10])[0], np.r_[-2, -2, -1, 0, 1, 3, 3])


    def test_function(self):

        def test(x, y):
            return x+y
        
        block = Function(test, nin=2)
        self.assertEqual(block._eval(1, 2)[0], 3)

        block = Function(lambda x, y: x+y, nin=2)
        self.assertEqual(block._eval(1, 2)[0], 3)

        block = Function(lambda x, y, a, b: x+y+a+b, nin=2, args=(3,4))
        self.assertEqual(block._eval(1, 2)[0], 10)

        block = Function(lambda x, y, a=0, b=0: x+y+a+b, nin=2, kwargs={'a':3, 'b':4})
        self.assertEqual(block._eval(1, 2)[0], 10)
        
    def test_interpolate(self):
        block = Interpolate(x=(0,5,10), y=(0,1,0))

        self.assertEqual(block._eval(0)[0], 0)
        
        self.assertEqual(block._eval(2.5)[0], 0.5)
        self.assertEqual(block._eval(5)[0], 1)
        self.assertEqual(block._eval(7.5)[0], 0.5)
        self.assertEqual(block._eval(10)[0], 0)
        
        block = Interpolate(x=np.r_[0,5,10], y=np.r_[0,1,0])
        self.assertEqual(block._eval(0)[0], 0)
        self.assertEqual(block._eval(2.5)[0], 0.5)
        self.assertEqual(block._eval(5)[0], 1)
        self.assertEqual(block._eval(7.5)[0], 0.5)
        self.assertEqual(block._eval(10)[0], 0)
        
        block = Interpolate(x=np.r_[0,5,10], y=np.r_[0,1,0].reshape((3,1)))
        self.assertEqual(block._eval(0)[0], 0)
        self.assertEqual(block._eval(2.5)[0], 0.5)
        self.assertEqual(block._eval(5)[0], 1)
        self.assertEqual(block._eval(7.5)[0], 0.5)
        self.assertEqual(block._eval(10)[0], 0)
        
        block = Interpolate(xy=[(0,0), (5,1), (10,0)])
        self.assertEqual(block._eval(0)[0], 0)
        self.assertEqual(block._eval(2.5)[0], 0.5)
        self.assertEqual(block._eval(5)[0], 1)
        self.assertEqual(block._eval(7.5)[0], 0.5)
        self.assertEqual(block._eval(10)[0], 0)
        
        # block = _Interpolate(xy=np.array([(0,0), (5,1), (10,0)]).T)
        # self.assertEqual(block._eval()[0], 0)
        # self.assertEqual(block._eval()[0], 0.5)
        # self.assertEqual(block._eval()[0], 1)
        # self.assertEqual(block._eval()[0], 0.5)
        # self.assertEqual(block._eval()[0], 0)
        
        
        block = Interpolate(x=(0,5,10), y=(0,1,0), time=True)
        self.assertEqual(block._eval(t=0)[0], 0)
        self.assertEqual(block._eval(t=2.5)[0], 0.5)
        self.assertEqual(block._eval(t=5)[0], 1)
        self.assertEqual(block._eval(t=7.5)[0], 0.5)
        self.assertEqual(block._eval(t=10)[0], 0)
        
        block = Interpolate(x=np.r_[0,5,10], y=np.r_[0,1,0], time=True)
        self.assertEqual(block._eval(t=0)[0], 0)
        self.assertEqual(block._eval(t=2.5)[0], 0.5)
        self.assertEqual(block._eval(t=5)[0], 1)
        self.assertEqual(block._eval(t=7.5)[0], 0.5)
        self.assertEqual(block._eval(t=10)[0], 0)
        
        block = Interpolate(xy=[(0,0), (5,1), (10,0)], time=True)

        self.assertEqual(block._eval(t=0)[0], 0)
        self.assertEqual(block._eval(t=2.5)[0], 0.5)
        self.assertEqual(block._eval(t=5)[0], 1)
        self.assertEqual(block._eval(t=7.5)[0], 0.5)
        self.assertEqual(block._eval(t=10)[0], 0)
        
        # block = _Interpolate(xy=np.array([(0,0), (5,1), (10,0)]), time=True)
        # out = block._eval(0)
        # self.assertIsInstance(out, list)
        # self.assertAlmostEqual(len(out), 1)
        # self.assertEqual(block._eval(0)[0], 0)
        # self.assertEqual(block._eval(2.5)[0], 0.5)
        # self.assertEqual(block._eval(5)[0], 1)
        # self.assertEqual(block._eval(7.5)[0], 0.)
        # self.assertEqual(block._eval(10)[0], 0)

# ---------------------------------------------------------------------------------------#
if __name__ == '__main__':

    unittest.main()
