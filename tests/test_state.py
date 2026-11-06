"""Tests for the STATE and STATE_S blocks, which output the state of the diagram."""

import unittest

import numpy as np

import bdsim
from bdsim.blockdiagram import BlockDiagram


def new_sim() -> bdsim.BDSim:
    return bdsim.BDSim(
        sysargs=False, graphics=False, progress=False, banner=False, quiet=True
    )


def chain_diagram():
    """Two integrators in a chain, vel -> pos, and a three-state LTI_SS."""
    bd = new_sim().blockdiagram()
    vel = bd.INTEGRATOR(x0=2.0, name="vel")
    pos = bd.INTEGRATOR(x0=5.0, name="pos")
    plant = bd.LTI_SS(
        A=np.array([[0, 1.0], [-2, -3]]),
        B=np.array([[0.0], [1.0]]),
        C=np.array([[1.0, 0.0]]),
        x0=[0.1, 0.2],
        name="plant",
    )
    bd.connect(bd.CONSTANT(1.0, name="u"), vel, plant)
    bd.connect(vel, pos)
    return bd, vel, pos, plant


def read(bd: BlockDiagram, state, x) -> np.ndarray:
    """What a STATE block outputs when the diagram is at state x."""
    sink = bd.NULL(1, name="probe")
    bd.connect(state, sink)
    bd.compile(verbose=False)
    bd.evaluate(bd.state_map(np.asarray(x, dtype=float)), 0.0, sinks=False)
    return np.asarray(sink.inport_values[0])


class StateTest(unittest.TestCase):
    def test_the_default_is_every_continuous_state_in_the_diagram_order(self):
        bd, vel, pos, plant = chain_diagram()
        st = bd.STATE(name="st")
        y = read(bd, st, [1.0, 2.0, 3.0, 4.0])
        np.testing.assert_array_equal(y, [1.0, 2.0, 3.0, 4.0])
        # the order of bd.statenames: vel, pos, then the two states of plant
        self.assertEqual(st.statenames, ["vel", "pos", "plant[0]", "plant[1]"])
        self.assertEqual(len(bd.statenames), 4)

    def test_it_follows_the_state_it_is_evaluated_at(self):
        bd, vel, pos, plant = chain_diagram()
        st = bd.STATE(name="st")
        sink = bd.NULL(1, name="probe")
        bd.connect(st, sink)
        bd.compile(verbose=False)
        for x in ([0.0, 0.0, 0.0, 0.0], [9.0, -8.0, 7.0, -6.0]):
            bd.evaluate(bd.state_map(np.array(x)), 0.0, sinks=False)
            np.testing.assert_array_equal(sink.inport_values[0], x)

    def test_blocks_are_chosen_and_ordered_by_the_list(self):
        bd, vel, pos, plant = chain_diagram()
        st = bd.STATE([plant, pos], name="st")
        y = read(bd, st, [1.0, 2.0, 3.0, 4.0])
        np.testing.assert_array_equal(y, [3.0, 4.0, 2.0])
        self.assertEqual(st.statenames, ["plant[0]", "plant[1]", "pos"])

    def test_blocks_can_be_named(self):
        bd, vel, pos, plant = chain_diagram()
        st = bd.STATE(["pos", "vel"], name="st")
        np.testing.assert_array_equal(read(bd, st, [1.0, 2.0, 3.0, 4.0]), [2.0, 1.0])

    def test_one_block_alone_and_a_scalar_state(self):
        bd, vel, pos, plant = chain_diagram()
        st = bd.STATE(pos, name="st")
        self.assertEqual(read(bd, st, [1.0, 2.0, 3.0, 4.0]), 2.0)
        self.assertEqual(st.statenames, ["pos"])

    def test_a_block_named_later_is_found(self):
        # the name is resolved when it is needed, not when the block is created
        bd = new_sim().blockdiagram()
        st = bd.STATE(["later"], name="st")
        later = bd.INTEGRATOR(x0=4.0, name="later")
        bd.connect(bd.CONSTANT(0.0), later)
        self.assertEqual(read(bd, st, [4.0]), 4.0)

    def test_index_says_which_elements_belong_to_which_block(self):
        bd, vel, pos, plant = chain_diagram()
        st = bd.STATE([plant, vel], name="st")
        bd.connect(st, bd.NULL(1))
        bd.compile(verbose=False)
        index = st.index
        self.assertEqual(index["plant"], slice(0, 2))
        self.assertEqual(index["vel"], slice(2, 3))
        self.assertEqual(len(index), 3)

    def test_it_matches_the_states_of_functions_and_linearize(self):
        bd, vel, pos, plant = chain_diagram()
        st = bd.STATE(name="st")
        bd.connect(st, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        self.assertEqual(st.statenames, bd.functions().xindex.names)

    def test_errors_name_the_block_and_the_problem(self):
        bd, vel, pos, plant = chain_diagram()
        gain = bd.GAIN(2.0, name="gain")
        bd.connect(vel, gain)
        for i, (blocks, message) in enumerate(
            (
                ([gain], "'gain' has no continuous state"),
                (["nothing"], "no block named 'nothing'"),
                ([vel, "vel"], "'vel' is given twice"),
                ([3], "has no continuous state"),
            )
        ):
            st = bd.STATE(blocks, name=f"bad{i}")
            with self.assertRaisesRegex(ValueError, message):
                _ = st.index

    def test_a_diagram_without_state_is_an_error(self):
        bd = new_sim().blockdiagram()
        st = bd.STATE(name="st")
        bd.connect(bd.CONSTANT(1.0), bd.GAIN(2.0))
        with self.assertRaisesRegex(ValueError, "no continuous state"):
            _ = st.index

    def test_a_cached_choice_is_forgotten_at_reset(self):
        bd, vel, pos, plant = chain_diagram()
        st = bd.STATE(name="st")
        _ = st.index
        self.assertIsNotNone(st._selected)
        bd.reset()
        self.assertIsNone(st._selected)

    def test_the_blocks_are_not_a_parameter(self):
        bd, vel, pos, plant = chain_diagram()
        st = bd.STATE([vel], name="st")
        self.assertNotIn("blocks", [p for p in dir(st) if not p.startswith("_")])


class StateFeedbackTest(unittest.TestCase):
    """x'' = u with u = -K x and K = [3, 2] (on vel, pos) has poles at -1 and -2."""

    K = np.array([[3.0, 2.0]])

    def closed_loop(self):
        bd = new_sim().blockdiagram()
        disturbance = bd.CONSTANT(0.0, name="disturbance")
        vel = bd.INTEGRATOR(x0=0.0, name="vel")
        pos = bd.INTEGRATOR(x0=1.0, name="pos")
        force = disturbance + (-self.K) * bd.STATE(name="state")
        bd.connect(force, vel)
        bd.connect(vel, pos)
        bd.connect(pos, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        return bd

    def test_state_feedback_with_a_gain_matrix_stabilises(self):
        bd = self.closed_loop()
        out = new_sim().run(bd, T=3.0, dt=0.01)
        # x'' + 3x' + 2x = 0, x(0) = 1, x'(0) = 0
        expected = 2 * np.exp(-out.t) - np.exp(-2 * out.t)
        np.testing.assert_allclose(out.x[:, 1], expected, atol=1e-4)

    def test_the_closed_loop_poles_are_at_minus_one_and_two(self):
        bd = self.closed_loop()
        lin = bd.linearize(full=True)
        np.testing.assert_allclose(lin.poles, [-2.0, -1.0], atol=1e-6)

    def test_the_closed_loop_is_a_minus_b_k(self):
        # open loop: the same plant with the force as an input
        bd = new_sim().blockdiagram()
        force = bd.CONSTANT(0.0, name="force")
        vel = bd.INTEGRATOR(x0=0.0, name="vel")
        pos = bd.INTEGRATOR(x0=1.0, name="pos")
        bd.connect(force, vel)
        bd.connect(vel, pos)
        bd.connect(pos, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        A, B, C, D = bd.linearize()

        Acl, Bcl, Ccl, Dcl = self.closed_loop().linearize()
        np.testing.assert_allclose(Acl, A - B @ self.K, atol=1e-6)
        np.testing.assert_allclose(Bcl, B, atol=1e-6)

    def test_the_state_is_not_an_input(self):
        bd = self.closed_loop()
        sysf = bd.functions()
        self.assertEqual(sysf.uindex.names, ["disturbance"])
        with self.assertRaisesRegex(ValueError, "STATE is not an input"):
            bd.functions(inputs=[bd["state"]])

    def test_a_signal_made_from_the_state_cannot_be_an_input_and_says_so(self):
        bd = self.closed_loop()
        feedback = [b for b in bd.blocklist if b.type == "gain"][0]
        with self.assertRaisesRegex(TypeError, "depends on the state"):
            bd.functions(inputs=[feedback])


class StateSTest(unittest.TestCase):
    def sampled_diagram(self):
        bd = new_sim().blockdiagram()
        clock = bd.clock(0.1)
        first = bd.ZOH(clock, x0=3.0, name="first")
        second = bd.ZOH(clock, x0=[4.0, 5.0], name="second")
        bd.connect(bd.TIME(name="time"), first)
        bd.connect(bd.CONSTANT(np.array([1.0, 2.0]), name="v"), second)
        bd.connect(first, bd.NULL(1, name="y1"))
        bd.connect(second, bd.NULL(1, name="y2"))
        return bd, clock, first, second

    def test_it_is_the_discrete_state_of_the_blocks_on_the_clock(self):
        bd, clock, first, second = self.sampled_diagram()
        X = bd.STATE_S(clock, name="X")
        bd.connect(X, bd.NULL(1, name="y3"))
        bd.compile(verbose=False)
        self.assertEqual(X.statenames, ["first", "second[0]", "second[1]"])
        self.assertEqual(X.index["second"], slice(1, 3))

    def test_it_equals_the_state_the_clock_holds_between_ticks(self):
        bd = new_sim().blockdiagram()
        clock = bd.clock(0.1)
        zoh = bd.ZOH(clock, x0=3.0, name="zoh")
        X = bd.STATE_S(clock, name="X")
        bd.connect(bd.TIME(name="time"), zoh)
        bd.connect(zoh, bd.NULL(1, name="y1"))
        bd.connect(X, bd.NULL(1, name="y2"))
        bd.compile(verbose=False)
        out = new_sim().run(bd, T=0.45, dt=0.05, watch=[zoh, X])
        # a ZOH outputs its state: the two columns agree at every logged time
        np.testing.assert_array_equal(out.y[:, 0], out.y[:, 1])
        # the initial state is held through the first period, then it follows time
        np.testing.assert_allclose(out.y[:, 0], [3.0, 3.0, 0.1, 0.2, 0.3, 0.4])

    def test_blocks_are_chosen_and_ordered_by_the_list(self):
        bd, clock, first, second = self.sampled_diagram()
        X = bd.STATE_S(clock, [second, "first"], name="X")
        bd.connect(X, bd.NULL(1, name="y3"))
        bd.compile(verbose=False)
        self.assertEqual(X.statenames, ["second[0]", "second[1]", "first"])

    def test_a_block_not_on_the_clock_is_an_error(self):
        bd, clock, first, second = self.sampled_diagram()
        other = bd.ZOH(bd.clock(0.2), x0=1.0, name="other")
        bd.connect(first, other)
        X = bd.STATE_S(clock, [other], name="X")
        with self.assertRaisesRegex(
            ValueError, "'other' has no discrete state on clock"
        ):
            _ = X.index
        # a continuous block is not on a clock either
        integrator = bd.INTEGRATOR(name="integrator")
        with self.assertRaisesRegex(ValueError, "'integrator' has no discrete state"):
            _ = bd.STATE_S(clock, [integrator], name="Y").index

    def test_a_clock_with_no_blocks_is_an_error(self):
        bd = new_sim().blockdiagram()
        with self.assertRaisesRegex(ValueError, "no discrete state on clock"):
            _ = bd.STATE_S(bd.clock(0.1), name="X").index

    def test_the_clock_is_a_fixed_parameter(self):
        bd, clock, first, second = self.sampled_diagram()
        X = bd.STATE_S(clock, name="X")
        self.assertIs(X.clock, clock)
        with self.assertRaises((ValueError, TypeError, AttributeError)):
            X.set_param("clock", bd.clock(0.2))

    def test_it_is_not_an_input_and_a_sampled_diagram_is_refused(self):
        bd, clock, first, second = self.sampled_diagram()
        X = bd.STATE_S(clock, name="X")
        bd.connect(X, bd.NULL(1, name="y3"))
        bd.compile(verbose=False)
        with self.assertRaisesRegex(NotImplementedError, "sampled"):
            bd.functions()


if __name__ == "__main__":
    unittest.main()
