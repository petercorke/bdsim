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


class ScopeLineStyleTest(unittest.TestCase):
    def tearDown(self) -> None:
        plt.close("all")

    def _started_scope(self, styles, labels=None):
        sim = BDSim()
        bd = sim.blockdiagram()
        scope = bd.SCOPE(styles=styles, labels=labels)
        for i in range(len(styles)):
            bd.connect(bd.CONSTANT(i), scope[i])
        bd.compile()
        scope.test_start()
        return scope

    def test_dict_style_with_several_keys(self):
        # A style dict is passed to plot() as keyword arguments.  It must not
        # also be handed to matplotlib as the line's label: matplotlib reads a
        # dict as a sequence of labels, one per dataset, so a dict with more
        # than one key is rejected as "label must be scalar or have the same
        # length as the input data".
        scope = self._started_scope(
            [dict(color="b"), dict(color="r", drawstyle="steps")]
        )

        self.assertEqual(scope.line[0].get_color(), "b")
        self.assertEqual(scope.line[1].get_color(), "r")
        self.assertEqual(scope.line[1].get_drawstyle(), "steps")

    def test_style_is_not_the_legend_label(self):
        scope = self._started_scope(["r--", dict(color="b")], labels=["x", "y"])

        legend_texts = [t.get_text() for t in scope.ax.get_legend().get_texts()]
        self.assertEqual(legend_texts, ["x", "y"])
        for line in scope.line:
            self.assertNotIn(line.get_label(), ("r--", "{'color': 'b'}", "color"))


class ScopeXYStyleTest(unittest.TestCase):
    def tearDown(self) -> None:
        # ScopeXY.start() creates a real matplotlib figure; close it so it
        # doesn't leak into other tests' global figure state.
        plt.close("all")

    def test_dict_style_passed_through_to_plot(self):
        sim = BDSim()
        bd = sim.blockdiagram()
        x = bd.CONSTANT(1)
        y = bd.CONSTANT(2)
        scopexy = bd.SCOPEXY(style={"color": "red", "linewidth": 3})
        bd.connect(x, scopexy[0])
        bd.connect(y, scopexy[1])
        bd.compile()

        scopexy.test_start()

        self.assertEqual(scopexy.line.get_color(), "red")
        self.assertEqual(scopexy.line.get_linewidth(), 3)


# ---------------------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()
