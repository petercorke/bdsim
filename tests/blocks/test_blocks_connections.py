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
        nt.assert_array_equal(block.test_output(1, 2)[0], np.r_[1, 2])

        block = Mux(3)
        nt.assert_array_equal(block.test_output(1, 2, 3)[0], np.r_[1, 2, 3])

        block = Mux(2)
        nt.assert_array_equal(block.test_output(1, np.r_[2, 3])[0], np.r_[1, 2, 3])

    def test_demux(self):
        block = DeMux(2)
        self.assertEqual(block.test_output(np.r_[1, 2])[0], 1)
        self.assertEqual(block.test_output(np.r_[1, 2])[1], 2)

    def test_item(self):
        block = Item("sig2")
        sig = {"sig1": 1, "sig2": 2, "sig3": 3}
        self.assertEqual(block.test_output(sig)[0], 2)

    def test_dict_multi_input_nin(self):
        """DICT with N keys must expose N inputs (regression: nin wasn't
        propagated from len(keys), so wiring more than 1 input failed)."""
        block = Dict(["a", "b", "c"])
        self.assertEqual(block.nin, 3)
        out = block.test_output(1, 2, 3)
        self.assertEqual(out[0], {"a": 1, "b": 2, "c": 3})

    def test_dict_output_is_list_wrapped(self):
        """DICT.output() must return a single-element list per the Block
        contract (regression: it returned a bare dict)."""
        block = Dict(["x"])
        out = block.test_output(5)
        self.assertEqual(out[0], {"x": 5})

    # subsystems are tested by test_blockdiagram


# ---------------------------------------------------------------------------------------#
if __name__ == "__main__":

    unittest.main()
