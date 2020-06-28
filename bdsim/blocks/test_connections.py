#!/usr/bin/env python3

import numpy as np
import scipy.interpolate
import math

from bdsim.blocks.connections import *

import unittest
import numpy.testing as nt

class ConnectionsTest(unittest.TestCase):

    def test_mux(self):
        
        block = Mux(2)
        nt.assert_array_equal(block._eval(1, 2)[0], np.r_[1,2])
        
        block = Mux(3)
        nt.assert_array_equal(block._eval(1, 2, 3)[0], np.r_[1,2, 3])
        
        block = Mux(2)
        nt.assert_array_equal(block._eval(1, np.r_[2, 3])[0], np.r_[1,2, 3])
        
        
    def test_demux(self):
        block = DeMux(2)
        self.assertEqual(block._eval(np.r_[1,2])[0], 1)
        self.assertEqual(block._eval(np.r_[1,2])[1], 2)
        
    def test_item(self):
        block = Item('sig2')
        sig = {'sig1':1, 'sig2':2, 'sig3':3}
        self.assertEqual(block._eval(sig)[0], 2)
    
    # subsystems are tested by test_blockdiagram


# ---------------------------------------------------------------------------------------#
if __name__ == '__main__':

    unittest.main()
