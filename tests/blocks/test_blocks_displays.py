#!/usr/bin/env python3

import unittest

import matplotlib.pyplot as plt

from bdsim import BDSim


class ScopeWatchTest(unittest.TestCase):
    def tearDown(self) -> None:
        # Scope.start() creates a real matplotlib figure; close it so it
        # doesn't leak into other tests' global figure state.
        plt.close("all")

    def test_watch_adds_input_source_to_watchlist(self):
        sim = BDSim()  # create simulator
        bd = sim.blockdiagram()
        source = bd.CONSTANT(2)
        scope = bd.SCOPE(watch=True)
        bd.connect(source, scope)
        bd.compile()

        simstate = scope.test_start()

        expected_plug = scope._input_wires[0].start
        self.assertEqual(len(simstate.watchlist), 1)
        self.assertIs(simstate.watchlist[0], expected_plug)
        self.assertEqual(simstate.watchnamelist, [str(expected_plug)])

    def test_no_watch_leaves_watchlist_empty(self):
        sim = BDSim()
        bd = sim.blockdiagram()
        source = bd.CONSTANT(3)
        scope = bd.SCOPE()  # watch defaults to False
        bd.connect(source, scope)
        bd.compile()

        simstate = scope.test_start()

        self.assertEqual(simstate.watchlist, [])
        self.assertEqual(simstate.watchnamelist, [])


# ---------------------------------------------------------------------------------------#
if __name__ == "__main__":

    unittest.main()
