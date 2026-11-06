"""Names of the discrete states: bd.dstatenames, clock.statenames and clock.index.

The continuous states have bd.statenames and bd.xindex.  The discrete state is held
clock by clock, so it is named clock by clock, and these tests are for the names
being the same wherever they appear, see issue #205.
"""

import unittest

import numpy as np

import bdsim
from bdsim.exceptions import BlockCreationError


def new_sim() -> bdsim.BDSim:
    return bdsim.BDSim(
        sysargs=False, graphics=False, progress=False, banner=False, quiet=True
    )


def sampled_diagram(**zoh_args):
    bd = new_sim().blockdiagram()
    clock = bd.clock(0.1)
    zoh = bd.ZOH(clock, name="zoh", **zoh_args)
    size = np.size(zoh_args.get("x0", 0.0))
    bd.connect(bd.CONSTANT(np.ones(size) if size > 1 else 1.0), zoh)
    bd.connect(zoh, bd.NULL(1, name="y"))
    return bd, clock, zoh


class DefaultNamesTest(unittest.TestCase):
    def test_bd_dstatenames_is_not_empty_when_there_is_discrete_state(self):
        bd, clock, zoh = sampled_diagram(x0=3.0)
        bd.compile(verbose=False)
        self.assertEqual(bd.ndstates, 1)
        self.assertEqual(bd.dstatenames, ["zoh:X_0"])

    def test_the_clock_has_the_same_names(self):
        bd, clock, zoh = sampled_diagram(x0=3.0)
        bd.compile(verbose=False)
        self.assertEqual(clock.statenames, bd.dstatenames)

    def test_there_is_a_name_for_every_discrete_state(self):
        bd = new_sim().blockdiagram()
        clock = bd.clock(0.1)
        a = bd.ZOH(clock, x0=[1.0, 2.0, 3.0], name="a")
        b = bd.ZOH(clock, x0=4.0, name="b")
        bd.connect(bd.CONSTANT(np.ones(3)), a)
        bd.connect(bd.CONSTANT(1.0), b)
        bd.connect(a, bd.NULL(1))
        bd.connect(b, bd.NULL(1))
        bd.compile(verbose=False)
        self.assertEqual(len(bd.dstatenames), bd.ndstates)
        self.assertEqual(bd.dstatenames, ["a:X_0", "a:X_1", "a:X_2", "b:X_0"])

    def test_a_diagram_without_discrete_state_has_none(self):
        bd = new_sim().blockdiagram()
        bd.connect(bd.CONSTANT(1.0), bd.NULL(1))
        bd.compile(verbose=False)
        self.assertEqual((bd.ndstates, bd.dstatenames), (0, []))

    def test_compiling_again_does_not_repeat_the_names(self):
        bd, clock, zoh = sampled_diagram(x0=3.0)
        bd.compile(verbose=False)
        bd.compile(verbose=False)
        self.assertEqual(clock.statenames, ["zoh:X_0"])
        self.assertEqual(bd.dstatenames, ["zoh:X_0"])

    def test_the_continuous_names_are_unchanged(self):
        bd = new_sim().blockdiagram()
        i = bd.INTEGRATOR(x0=[1.0, 2.0], name="i")
        bd.connect(bd.CONSTANT(np.zeros(2)), i)
        bd.connect(i, bd.NULL(1))
        bd.compile(verbose=False)
        self.assertEqual(bd.statenames, ["i:x_0", "i:x_1"])
        self.assertEqual(bd.dstatenames, [])


class GivenNamesTest(unittest.TestCase):
    def test_a_sampled_block_can_name_its_states(self):
        bd, clock, zoh = sampled_diagram(x0=[3.0, 4.0], snames=["a", "b"])
        bd.compile(verbose=False)
        self.assertEqual(bd.dstatenames, ["a", "b"])
        self.assertEqual(clock.statenames, ["a", "b"])

    def test_the_names_reach_the_index_and_the_state_block(self):
        bd, clock, zoh = sampled_diagram(x0=[3.0, 4.0], snames=["a", "b"])
        X = bd.STATE_S(clock, name="X")
        bd.connect(X, bd.NULL(1, name="y2"))
        bd.compile(verbose=False)
        self.assertEqual(clock.index.names, ["a", "b"])
        self.assertEqual(X.statenames, ["a", "b"])

    def test_the_names_reach_the_results(self):
        bd, clock, zoh = sampled_diagram(x0=[3.0, 4.0], snames=["a", "b"])
        bd.compile(verbose=False)
        out = new_sim().run(bd, T=0.3, dt=0.1)
        # one entry for the clock, whose key depends on how many clocks exist
        clocks = [out[k] for k in out.keys() if k.startswith("clock")]
        self.assertEqual(len(clocks), 1)
        self.assertEqual(list(clocks[0].Xnames), ["a", "b"])

    def test_names_and_default_names_can_be_mixed_on_one_clock(self):
        bd = new_sim().blockdiagram()
        clock = bd.clock(0.1)
        named = bd.ZOH(clock, x0=[1.0, 2.0], snames=["p", "q"], name="named")
        plain = bd.ZOH(clock, x0=3.0, name="plain")
        bd.connect(bd.CONSTANT(np.ones(2)), named)
        bd.connect(bd.CONSTANT(1.0), plain)
        bd.connect(named, bd.NULL(1))
        bd.connect(plain, bd.NULL(1))
        bd.compile(verbose=False)
        self.assertEqual(bd.dstatenames, ["p", "q", "plain:X_0"])
        self.assertEqual(clock.index.names, ["p", "q", "plain"])

    def test_the_wrong_number_of_names_is_an_error(self):
        bd = new_sim().blockdiagram()
        clock = bd.clock(0.1)
        # the block's constructor says "number of state names (3) must match number of
        # states (2)", which the diagram reports as a failure to create the block
        with self.assertRaises(BlockCreationError):
            bd.ZOH(clock, x0=[1.0, 2.0], snames=["a", "b", "c"], name="zoh")

    def test_a_block_with_several_states_and_names_given_later(self):
        # state_names() is the older way to name the states, checked at compile
        bd, clock, zoh = sampled_diagram(x0=[3.0, 4.0], snames=["a", "b"])
        zoh.state_names(["only one"])
        with self.assertRaisesRegex(ValueError, "1 state names for 2 states"):
            bd.compile(verbose=False)

    def test_continuous_names_still_work(self):
        bd = new_sim().blockdiagram()
        i = bd.INTEGRATOR(x0=[1.0, 2.0], snames=["pos", "vel"], name="i")
        bd.connect(bd.CONSTANT(np.zeros(2)), i)
        bd.connect(i, bd.NULL(1))
        bd.compile(verbose=False)
        self.assertEqual(bd.statenames, ["pos", "vel"])
        self.assertEqual(bd.xindex.names, ["pos", "vel"])


class SeveralClocksTest(unittest.TestCase):
    def diagram(self):
        """Blocks on two clocks, created interleaved, with distinct initial states."""
        bd = new_sim().blockdiagram()
        fast = bd.clock(0.1)
        slow = bd.clock(0.5)
        blocks = [
            bd.ZOH(fast, x0=1.0, name="f1"),
            bd.ZOH(slow, x0=[10.0, 11.0], snames=["s1a", "s1b"], name="s1"),
            bd.ZOH(fast, x0=2.0, name="f2"),
            bd.ZOH(slow, x0=12.0, name="s2"),
        ]
        for b in blocks:
            size = b.ndstates
            bd.connect(bd.CONSTANT(np.ones(size) if size > 1 else 1.0), b)
            bd.connect(b, bd.NULL(1))
        bd.compile(verbose=False)
        return bd, fast, slow

    def test_each_clock_names_its_own_blocks_in_order(self):
        bd, fast, slow = self.diagram()
        self.assertEqual(fast.statenames, ["f1:X_0", "f2:X_0"])
        self.assertEqual(slow.statenames, ["s1a", "s1b", "s2:X_0"])

    def test_bd_dstatenames_follows_the_clocks_in_turn(self):
        bd, fast, slow = self.diagram()
        self.assertEqual(bd.dstatenames, ["f1:X_0", "f2:X_0", "s1a", "s1b", "s2:X_0"])

    def test_the_names_are_in_the_order_of_the_state_vectors(self):
        # the names are of the elements of the clocks' state vectors, in order
        bd, fast, slow = self.diagram()
        np.testing.assert_array_equal(fast.getstate0(), [1.0, 2.0])
        np.testing.assert_array_equal(slow.getstate0(), [10.0, 11.0, 12.0])
        self.assertEqual(len(fast.statenames), len(fast.getstate0()))
        self.assertEqual(len(slow.statenames), len(slow.getstate0()))
        self.assertEqual(fast.index.slices[bd["f2"]], slice(1, 2))
        self.assertEqual(slow.index.slices[bd["s2"]], slice(2, 3))

    def test_clock_index_matches_clock_statenames_in_length_and_blocks(self):
        bd, fast, slow = self.diagram()
        for clock in (fast, slow):
            self.assertEqual(len(clock.index), len(clock.statenames))
            self.assertEqual(
                list(clock.index), [b for b in clock.blocklist if b.ndstates]
            )


if __name__ == "__main__":
    unittest.main()
