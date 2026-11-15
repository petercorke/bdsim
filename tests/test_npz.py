#!/usr/bin/env python3
"""--npz: results written as a NumPy .npz archive, readable without pickle."""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import numpy.testing as nt

import bdsim
from bdsim.components import BDStruct


def load(path):
    """Read an archive back the safe way: nothing in it may need pickle."""
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


class DumpNpzTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "results.npz")

    def dump(self, struct):
        struct.dump_npz(self.path)
        return load(self.path)

    def test_arrays_round_trip_exactly(self):
        t = np.linspace(0, 1, 11)
        x = np.arange(22.0).reshape(11, 2)
        got = self.dump(BDStruct(t=t, x=x, flags=np.array([True, False])))
        nt.assert_array_equal(got["t"], t)
        nt.assert_array_equal(got["x"], x)
        self.assertEqual(got["x"].dtype, np.float64)
        nt.assert_array_equal(got["flags"], [True, False])

    def test_names_are_string_arrays(self):
        got = self.dump(BDStruct(xnames=["plant0", "plant1"], ynames=[]))
        self.assertEqual(got["xnames"].tolist(), ["plant0", "plant1"])
        self.assertEqual(got["ynames"].size, 0)

    def test_scalars_and_strings(self):
        got = self.dump(BDStruct(n=3, rate=2.5, label="run", ok=True, z=1 + 2j))
        self.assertEqual(got["n"].item(), 3)
        self.assertEqual(got["rate"].item(), 2.5)
        self.assertEqual(got["label"].item(), "run")
        self.assertEqual(got["ok"].item(), True)
        self.assertEqual(got["z"].item(), 1 + 2j)

    def test_nested_struct_uses_slash_separated_keys(self):
        clock = BDStruct(t=np.r_[0.0, 0.1], X=np.ones((2, 1)))
        got = self.dump(BDStruct(t=np.r_[0.0], clock0=clock))
        nt.assert_array_equal(got["clock0/t"], [0.0, 0.1])
        nt.assert_array_equal(got["clock0/X"], np.ones((2, 1)))

    def test_hidden_fields_keep_their_leading_dot(self):
        stats = {"ydot_calls": 784, "events_detected_by_source": {"ball": 3}}
        got = self.dump(BDStruct(**{".stats": stats}))
        self.assertEqual(got[".stats/ydot_calls"].item(), 784)
        self.assertEqual(got[".stats/events_detected_by_source/ball"].item(), 3)

    def test_rectangular_list_is_one_array(self):
        got = self.dump(BDStruct(w=[[1.0, 2.0], [3.0, 4.0]]))
        nt.assert_array_equal(got["w"], [[1.0, 2.0], [3.0, 4.0]])

    def test_ragged_list_is_stored_element_by_element(self):
        got = self.dump(BDStruct(w=[[1.0, 2.0, 3.0], [4.0]]))
        nt.assert_array_equal(got["w/0"], [1.0, 2.0, 3.0])
        nt.assert_array_equal(got["w/1"], [4.0])

    def test_things_that_are_not_data_are_skipped_not_pickled(self):
        got = self.dump(BDStruct(t=np.r_[0.0], nothing=None, thing=object()))
        self.assertEqual(sorted(got), ["t"])

    def test_the_file_name_is_used_as_given(self):
        path = os.path.join(self.dir.name, "bd.out")
        BDStruct(t=np.r_[0.0]).dump_npz(path)
        self.assertTrue(os.path.exists(path))
        self.assertFalse(os.path.exists(path + ".npz"))
        self.assertEqual(sorted(load(path)), ["t"])


class RunNpzTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "run.npz")

    def _run(self, **options):
        sim = bdsim.BDSim(
            graphics=None, progress=False, banner=False, quiet=True, **options
        )
        bd = sim.blockdiagram()
        step = bd.STEP(T=0.5)
        plant = bd.LTI_SISO(1, [1, 1], name="plant")
        scope = bd.NULL(1)
        bd.connect(step, plant)
        bd.connect(plant, scope)
        bd.compile(verbose=False)
        return sim.run(bd, T=2.0, watch=[plant])

    def test_option_writes_the_results_of_the_run(self):
        out = self._run(npzfile=self.path)
        got = load(self.path)
        nt.assert_array_equal(got["t"], out.t)
        nt.assert_array_equal(got["x"], out.x)
        self.assertEqual(got["xnames"].tolist(), list(out.xnames))
        self.assertGreater(got[".stats/ydot_calls"].item(), 0)

    def test_no_file_unless_asked(self):
        self._run()
        self.assertFalse(os.path.exists(self.path))


class CommandLineTest(unittest.TestCase):
    def _options(self, *argv):
        with patch.object(sys, "argv", ["prog", *argv]):
            return bdsim.BDSim(graphics=None, progress=False, banner=False).options

    def test_default_is_off(self):
        self.assertIsNone(self._options().npzfile)

    def test_with_a_file_name(self):
        self.assertEqual(self._options("--npz", "r.npz").npzfile, "r.npz")

    def test_without_a_file_name(self):
        self.assertEqual(self._options("--npz").npzfile, "bd.npz")

    def test_keyword_option(self):
        sim = bdsim.BDSim(graphics=None, progress=False, banner=False, npzfile="k.npz")
        self.assertEqual(sim.options.npzfile, "k.npz")


if __name__ == "__main__":
    unittest.main()
