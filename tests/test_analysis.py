"""Tests for BlockDiagram.functions() and linearize() (src/bdsim/analysis.py)."""

import subprocess  # nosec B404
import sys
import unittest
import unittest.mock
import warnings

import numpy as np

import bdsim
from bdsim.analysis import AnalysisMixin, Index, Linearization
from bdsim.blockdiagram import BlockDiagram


def new_diagram() -> BlockDiagram:
    return bdsim.BDSim(sysargs=False, graphics=False).blockdiagram()


def lti_diagram():
    """Two states, two inputs, one output, with a nonzero D."""
    A = np.array([[0, 1], [-2, -3.0]])
    B = np.array([[0, 1], [1, 0.0]])
    C = np.array([[1, 2.0]])
    D = np.array([[0.5, -1.0]])
    bd = new_diagram()
    u1 = bd.CONSTANT(1.0, name="u1")
    u2 = bd.CONSTANT(2.0, name="u2")
    system = bd.LTI_SS(A=A, B=B, C=C, D=D, x0=[1, 2], name="system")
    bd.connect(u1, system[0])
    bd.connect(u2, system[1])
    bd.connect(system, bd.NULL(1, name="y"))
    bd.compile(verbose=False)
    return bd, (A, B, C, D)


G_OVER_L = 9.81
DAMPING = 0.4


def pendulum_diagram(torque=0.3, theta0=0.5, omega0=0.2):
    r"""theta'' = u - (g/l) sin(theta) - b theta', the output is theta."""
    bd = new_diagram()
    u = bd.CONSTANT(torque, name="u")
    acc = bd.SUM("+--", name="acc")
    omega = bd.INTEGRATOR(x0=omega0, name="omega")
    theta = bd.INTEGRATOR(x0=theta0, name="theta")
    sin = bd.FUNCTION(lambda th: np.sin(th), name="sin")
    stiffness = bd.GAIN(G_OVER_L, name="stiffness")
    damper = bd.GAIN(DAMPING, name="damper")
    bd.connect(u, acc[0])
    bd.connect(stiffness, acc[1])
    bd.connect(damper, acc[2])
    bd.connect(acc, omega)
    bd.connect(omega, theta, damper)
    bd.connect(theta, sin)
    bd.connect(sin, stiffness)
    bd.connect(theta, bd.NULL(1, name="y"))
    bd.compile(verbose=False)
    return bd


class FunctionsTest(unittest.TestCase):
    def test_f_and_g_of_a_linear_system(self):
        bd, (A, B, C, D) = lti_diagram()
        f, g = bd.functions()
        x = np.array([0.3, -0.7])
        u = np.array([1.5, 0.25])
        np.testing.assert_allclose(f(x, u, 0.0), A @ x + B @ u, atol=1e-12)
        np.testing.assert_allclose(g(x, u, 0.0), C @ x + D @ u, atol=1e-12)

    def test_fg_equals_f_and_g(self):
        bd, _ = lti_diagram()
        sysf = bd.functions()
        x, u = np.array([0.3, -0.7]), np.array([1.5, 0.25])
        xdot, y = sysf.fg(x, u, 0.0)
        np.testing.assert_array_equal(xdot, sysf.f(x, u))
        np.testing.assert_array_equal(y, sysf.g(x, u))

    def test_sizes_and_initial_state(self):
        bd, _ = lti_diagram()
        sysf = bd.functions()
        self.assertEqual((sysf.nx, sysf.nu, sysf.ny), (2, 2, 1))
        np.testing.assert_array_equal(sysf.x0, [1, 2])

    def test_u_at_is_the_natural_input(self):
        bd, _ = lti_diagram()
        np.testing.assert_array_equal(bd.functions().u_at(0.0), [1.0, 2.0])

    def test_the_sources_are_replaced_by_u(self):
        # the CONSTANTs are 1 and 2, but f and g follow the u given
        bd, (A, B, C, D) = lti_diagram()
        f, g = bd.functions()
        u = np.array([-4.0, 7.0])
        np.testing.assert_allclose(f([0.0, 0.0], u), B @ u, atol=1e-12)
        np.testing.assert_allclose(g([0.0, 0.0], u), D @ u, atol=1e-12)

    def test_time_is_the_t_argument_not_an_input(self):
        bd = new_diagram()
        time = bd.TIME(name="time")
        integrator = bd.INTEGRATOR(x0=0, name="integrator")
        bd.connect(time, integrator)
        bd.connect(integrator, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        sysf = bd.functions()
        self.assertEqual(sysf.nu, 0)
        self.assertEqual(sysf.f([0.0], [], t=3.5)[0], 3.5)

    def test_the_wrong_sizes_are_errors(self):
        bd, _ = lti_diagram()
        f, g = bd.functions()
        with self.assertRaisesRegex(ValueError, "x has 3 elements, expected 2"):
            f([1, 2, 3], [1, 2])
        with self.assertRaisesRegex(ValueError, "u has 1 elements, expected 2"):
            g([1, 2], [1])

    def test_a_diagram_that_is_not_compiled_is_an_error(self):
        bd = new_diagram()
        bd.connect(bd.CONSTANT(1.0), bd.NULL(1))
        with self.assertRaisesRegex(RuntimeError, "not been compiled"):
            bd.functions()

    def test_sampled_blocks_are_not_supported(self):
        bd = new_diagram()
        zoh = bd.ZOH(bd.clock(0.1), name="zoh")
        bd.connect(bd.CONSTANT(1.0), zoh)
        bd.connect(zoh, bd.NULL(1))
        bd.compile(verbose=False)
        with self.assertRaisesRegex(NotImplementedError, "zoh"):
            bd.functions()
        with self.assertRaises(NotImplementedError):
            bd.linearize()

    def test_the_sinks_are_not_stepped(self):
        bd, _ = lti_diagram()
        calls = []
        sink = bd["y"]
        sink.step = lambda t, u: calls.append(t)
        f, g = bd.functions()
        f([0.0, 0.0], [1.0, 2.0])
        g([0.0, 0.0], [1.0, 2.0])
        self.assertEqual(calls, [])

    def test_a_non_numeric_signal_is_an_error_naming_the_port(self):
        bd = new_diagram()
        text = bd.CONSTANT("hello", name="text")
        bd.connect(text, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        with self.assertRaisesRegex(TypeError, r"input text\[0\].*str"):
            bd.functions()
        # the output is the signal from "text", whatever receives it
        with self.assertRaisesRegex(TypeError, r"output text\[0\].*str"):
            bd.functions(inputs=[])


class SelectionTest(unittest.TestCase):
    def two_source_diagram(self):
        bd = new_diagram()
        a = bd.CONSTANT(3.0, name="a")
        b = bd.CONSTANT(5.0, name="b")
        total = bd.SUM("++", name="total")
        bd.connect(a, total[0])
        bd.connect(b, total[1])
        bd.connect(total, bd.NULL(1, name="y1"))
        bd.connect(b, bd.NULL(1, name="y2"))
        bd.compile(verbose=False)
        return bd, a, b

    def test_default_is_every_source_and_the_signal_into_every_sink(self):
        bd, a, b = self.two_source_diagram()
        sysf = bd.functions()
        self.assertEqual((sysf.nu, sysf.ny), (2, 2))
        self.assertEqual(sysf.uindex.names, ["a", "b"])
        # y1 receives total and y2 receives b: named by the block that produces
        # them, in the order the blocks were added (a, b, total)
        self.assertEqual(sysf.yindex.names, ["b", "total"])
        np.testing.assert_allclose(sysf.g([], [10.0, 20.0]), [20.0, 30.0])

    def test_inputs_select_sources_and_the_rest_keep_their_value(self):
        bd, a, b = self.two_source_diagram()
        sysf = bd.functions(inputs=[a])
        self.assertEqual(sysf.nu, 1)
        # b is not an input: it still outputs its own 5
        np.testing.assert_allclose(sysf.g([], [10.0]), [5.0, 15.0])

    def test_a_plug_selects_a_sink_port(self):
        bd, a, b = self.two_source_diagram()
        sysf = bd.functions(outputs=[bd["y2"]])
        self.assertEqual(sysf.ny, 1)
        np.testing.assert_allclose(sysf.g([], [10.0, 20.0]), [20.0])

    def test_a_plug_selects_one_port_of_a_sink_with_several(self):
        bd = new_diagram()
        a = bd.CONSTANT(3.0, name="a")
        b = bd.CONSTANT(5.0, name="b")
        sink = bd.NULL(2, name="sink")
        bd.connect(a, sink[0])
        bd.connect(b, sink[1])
        bd.compile(verbose=False)
        both = bd.functions()
        self.assertEqual(both.ny, 2)
        np.testing.assert_allclose(both.g([], [10.0, 20.0]), [10.0, 20.0])
        second = bd.functions(outputs=[sink[1]])
        self.assertEqual(second.ny, 1)
        np.testing.assert_allclose(second.g([], [10.0, 20.0]), [20.0])
        first = bd.functions(outputs=[sink[0]])
        np.testing.assert_allclose(first.g([], [10.0, 20.0]), [10.0])

    def test_a_number_in_an_expression_is_a_parameter_not_an_input(self):
        # "+ 1.0" makes a CONSTANT block named _const.0(1) behind the scenes
        bd = new_diagram()
        step = bd.STEP(1, name="demand")
        offset = step + 1.0
        bd.connect(offset, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        implicit = [b for b in bd.blocklist if b.type == "constant"]
        self.assertEqual(len(implicit), 1)
        self.assertTrue(implicit[0]._implicit)
        sysf = bd.functions()
        self.assertEqual(sysf.uindex.names, ["demand"])
        # y = u + 1 holds for any u: the 1 is not available to be changed
        np.testing.assert_allclose(sysf.g([], [5.0]), [6.0])
        # but it can still be chosen on purpose
        both = bd.functions(inputs=[step, implicit[0].name])
        self.assertEqual(both.nu, 2)

    def test_a_constant_made_by_the_user_is_an_input(self):
        bd = new_diagram()
        gain = bd.CONSTANT(2.0, name="mine")
        bd.connect(gain, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        self.assertFalse(bd["mine"]._implicit)
        self.assertEqual(bd.functions().uindex.names, ["mine"])

    def test_time_cannot_be_an_input(self):
        bd = new_diagram()
        time = bd.TIME(name="time")
        bd.connect(time, bd.NULL(1))
        bd.compile(verbose=False)
        with self.assertRaisesRegex(ValueError, "TIME is not an input"):
            bd.functions(inputs=[time])

    def test_inputs_must_be_sources(self):
        bd, a, b = self.two_source_diagram()
        with self.assertRaisesRegex(TypeError, "total is not a source"):
            bd.functions(inputs=[bd["total"]])

    def test_the_error_for_an_expression_names_the_sources_it_is_made_of(self):
        # step1 - step2 is a SUM block with a generated name, not a source
        bd = new_diagram()
        pulse = bd.STEP(1, name="on") - bd.STEP(1.2, name="off")
        bd.connect(pulse, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        with self.assertRaises(TypeError) as caught:
            bd.functions(inputs=[pulse])
        message = str(caught.exception)
        self.assertIn(f"input {pulse.name} is not a source block", message)
        self.assertIn("sum block", message)
        self.assertIn("on, off", message)

    def test_the_error_follows_the_expression_back_through_several_blocks(self):
        # ((on - off) * 3) + time: the sources are found two blocks back, and
        # TIME, which is not an input, is not offered as one
        bd = new_diagram()
        force = (bd.STEP(1, name="on") - bd.STEP(1.2, name="off")) * 3.0 + bd.TIME(
            name="time"
        )
        bd.connect(force, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        with self.assertRaises(TypeError) as caught:
            bd.functions(inputs=[force])
        message = str(caught.exception)
        self.assertIn("source blocks on, off:", message)
        self.assertNotIn("time", message.split("computed from")[-1])

    def test_the_error_for_an_expression_of_time_alone(self):
        bd = new_diagram()
        ramp = bd.TIME(name="time") * 2.0
        bd.connect(ramp, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        with self.assertRaisesRegex(TypeError, "Make the signal a single source block"):
            bd.functions(inputs=[ramp])

    def test_the_error_for_a_signal_from_the_state_says_so(self):
        bd = new_diagram()
        integrator = bd.INTEGRATOR(x0=0, name="integrator")
        scaled = integrator * 2.0
        bd.connect(bd.CONSTANT(1.0, name="u"), integrator)
        bd.connect(scaled, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        with self.assertRaisesRegex(TypeError, "depends on the state"):
            bd.functions(inputs=[scaled])

    def test_an_entry_must_be_a_block_a_plug_or_a_name(self):
        bd, a, b = self.two_source_diagram()
        with self.assertRaisesRegex(
            TypeError, "expected a block, a plug or a block name"
        ):
            bd.functions(outputs=[42])
        with self.assertRaises(KeyError):
            bd.functions(outputs=["nothing"])

    def test_a_vector_source_is_flattened(self):
        bd = new_diagram()
        v = bd.CONSTANT(np.array([1.0, 2.0, 3.0]), name="v")
        bd.connect(v, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        sysf = bd.functions()
        self.assertEqual((sysf.nu, sysf.ny), (3, 3))
        self.assertEqual(sysf.uindex.names, ["v[0]", "v[1]", "v[2]"])
        np.testing.assert_allclose(sysf.g([], [7, 8, 9]), [7, 8, 9])


def eg1_diagram():
    """The diagram of examples/eg1.py: a unity feedback loop, scope on two signals."""
    bd = new_diagram()
    demand = bd.STEP(T=1, name="demand")
    total = bd.SUM("+-")
    gain = bd.GAIN(20)
    plant = bd.LTI_SISO(0.5, [2, 1], name="plant")
    scope = bd.SCOPE(nin=2, name="scope")
    bd.connect(demand, total[0], scope[1])
    bd.connect(plant, total[1])
    bd.connect(total, gain)
    bd.connect(gain, plant)
    bd.connect(plant, scope[0])
    bd.compile(verbose=False)
    return bd, demand, plant, scope


class OutputSignalTest(unittest.TestCase):
    """An output is a signal, named by the block that produces it."""

    def test_the_default_is_the_signals_the_scope_receives(self):
        bd, demand, plant, scope = eg1_diagram()
        sysf = bd.functions()
        self.assertEqual((sysf.nu, sysf.ny), (1, 2))
        self.assertEqual(sysf.yindex.names, ["demand", "plant"])

    def test_a_block_is_its_output(self):
        bd, demand, plant, scope = eg1_diagram()
        sysf = bd.functions(inputs=[demand], outputs=[plant])
        self.assertEqual((sysf.nu, sysf.ny), (1, 1))
        self.assertEqual(sysf.yindex.names, ["plant"])

    def test_all_the_ways_to_name_the_same_signal_agree(self):
        bd, demand, plant, scope = eg1_diagram()
        results = []
        for outputs in (
            [plant],
            ["plant"],
            [plant[0]],
            [scope[0]],
            [plant, "plant", plant[0], scope[0]],
        ):
            sysf = bd.functions(inputs=[demand], outputs=outputs)
            self.assertEqual((sysf.ny, sysf.yindex.names), (1, ["plant"]), outputs)
            results.append(sysf.g([0.3], [1.0]))
        for r in results:
            np.testing.assert_array_equal(r, results[0])

    def test_a_sink_means_the_signals_it_receives(self):
        bd, demand, plant, scope = eg1_diagram()
        both = bd.functions(outputs=[scope])
        self.assertEqual(both.yindex.names, ["demand", "plant"])
        # scope[1] receives the demand
        one = bd.functions(outputs=[scope[1]])
        self.assertEqual(one.yindex.names, ["demand"])
        np.testing.assert_allclose(one.g([0.0], [4.0]), [4.0])

    def test_the_inputs_can_be_named_too(self):
        bd, demand, plant, scope = eg1_diagram()
        for inputs in ([demand], ["demand"], [demand[0]]):
            self.assertEqual(bd.functions(inputs=inputs).uindex.names, ["demand"])

    def demux_diagram(self):
        bd = new_diagram()
        v = bd.CONSTANT(np.array([1.0, 2.0]), name="v")
        demux = bd.DEMUX(2, name="demux")
        bd.connect(v, demux)
        bd.connect(demux[0], bd.NULL(1, name="y0"))
        bd.connect(demux[1], bd.NULL(1, name="y1"))
        bd.compile(verbose=False)
        return bd, demux

    def test_a_block_with_several_outputs_gives_one_signal_per_port(self):
        bd, demux = self.demux_diagram()
        u = [7.0, 8.0]
        for outputs in (None, [demux], ["demux"], [bd["y0"], bd["y1"]]):
            sysf = bd.functions(outputs=outputs)
            self.assertEqual(sysf.yindex.names, ["demux[0]", "demux[1]"], outputs)
            np.testing.assert_allclose(sysf.g([], u), [7.0, 8.0], err_msg=str(outputs))

    def test_a_port_selects_that_output_and_the_sink_it_feeds(self):
        bd, demux = self.demux_diagram()
        u = [7.0, 8.0]
        for outputs in ([demux[1]], [bd["y1"]], ["y1"]):
            sysf = bd.functions(outputs=outputs)
            self.assertEqual(sysf.ny, 1, outputs)
            np.testing.assert_allclose(sysf.g([], u), [8.0], err_msg=str(outputs))

    def test_the_ports_are_ordered_whatever_the_order_asked_for(self):
        bd, demux = self.demux_diagram()
        sysf = bd.functions(outputs=[demux[1], demux[0]])
        self.assertEqual(sysf.yindex.names, ["demux[0]", "demux[1]"])
        np.testing.assert_allclose(sysf.g([], [7.0, 8.0]), [7.0, 8.0])

    def test_a_signal_into_several_sinks_is_included_once(self):
        bd = new_diagram()
        source = bd.CONSTANT(2.0, name="source")
        bd.connect(source, bd.NULL(1, name="first"), bd.NULL(1, name="second"))
        bd.compile(verbose=False)
        sysf = bd.functions()
        self.assertEqual((sysf.ny, sysf.yindex.names), (1, ["source"]))

    def test_the_input_can_be_seen_in_the_output(self):
        # the output is the demand itself, so y = u and D = 1
        bd, demand, plant, scope = eg1_diagram()
        A, B, C, D = bd.linearize(inputs=[demand], outputs=[demand])
        np.testing.assert_allclose(D, [[1.0]], atol=1e-8)
        np.testing.assert_allclose(C, [[0.0]], atol=1e-8)

    def test_the_closed_loop_of_eg1(self):
        # 20 * 0.5/(2s+1) in a unity feedback loop: 10 / (2s + 11)
        bd, demand, plant, scope = eg1_diagram()
        A, B, C, D = bd.linearize(x=[0.0], u=[0.0], outputs=[plant])
        self.assertEqual((A.shape, B.shape, C.shape, D.shape), ((1, 1),) * 4)
        np.testing.assert_allclose(A, [[-5.5]], atol=1e-7)
        np.testing.assert_allclose(
            C @ B, [[5.0]], atol=1e-7
        )  # independent of the realization
        np.testing.assert_allclose(D, [[0.0]], atol=1e-8)
        # the same system named through the scope
        again = bd.linearize(x=[0.0], u=[0.0], outputs=[scope[0]])
        for a, b in zip((A, B, C, D), again):
            np.testing.assert_array_equal(a, b)


class IndexTest(unittest.TestCase):
    def test_slices_labels_and_lookup_by_name(self):
        bd = pendulum_diagram()
        sysf = bd.functions()
        # integrators in creation order: omega, then theta
        self.assertEqual(sysf.xindex.names, ["omega", "theta"])
        self.assertEqual(sysf.xindex["omega"], slice(0, 1))
        self.assertEqual(sysf.xindex[bd["theta"]], slice(1, 2))
        self.assertEqual(sysf.xindex.labels, [(bd["omega"], 0), (bd["theta"], 0)])
        self.assertEqual(len(sysf.xindex), 2)
        self.assertIn("theta", sysf.xindex)
        self.assertEqual(list(sysf.xindex), [bd["omega"], bd["theta"]])

    def test_a_block_with_several_elements_gets_one_slice(self):
        bd, _ = lti_diagram()
        sysf = bd.functions()
        self.assertEqual(sysf.xindex["system"], slice(0, 2))
        self.assertEqual(sysf.xindex.names, ["system[0]", "system[1]"])

    def test_missing_blocks(self):
        bd, _ = lti_diagram()
        sysf = bd.functions()
        with self.assertRaisesRegex(KeyError, "no block named"):
            sysf.xindex["nothing"]
        with self.assertRaisesRegex(KeyError, "no elements"):
            sysf.xindex[bd["u1"]]

    def test_the_order_is_the_order_of_addition_not_of_selection(self):
        bd = new_diagram()
        a = bd.CONSTANT(1.0, name="a")
        b = bd.CONSTANT(2.0, name="b")
        bd.connect(a, bd.NULL(1, name="ya"))
        bd.connect(b, bd.NULL(1, name="yb"))
        bd.compile(verbose=False)
        sysf = bd.functions(inputs=[b, a], outputs=[bd["yb"], bd["ya"]])
        self.assertEqual(sysf.uindex.names, ["a", "b"])
        # ya and yb receive a and b
        self.assertEqual(sysf.yindex.names, ["a", "b"])
        np.testing.assert_allclose(sysf.g([], [10.0, 20.0]), [10.0, 20.0])

    def test_repr(self):
        bd = pendulum_diagram()
        self.assertEqual(repr(bd.functions().xindex), "Index(2 elements: omega, theta)")


class LinearizeTest(unittest.TestCase):
    def test_a_linear_system_is_recovered(self):
        bd, (A, B, C, D) = lti_diagram()
        a, b, c, d = bd.linearize()
        np.testing.assert_allclose(a, A, atol=1e-8)
        np.testing.assert_allclose(b, B, atol=1e-8)
        np.testing.assert_allclose(c, C, atol=1e-8)
        np.testing.assert_allclose(d, D, atol=1e-8)
        self.assertEqual(
            (a.shape, b.shape, c.shape, d.shape), ((2, 2), (2, 2), (1, 2), (1, 2))
        )

    def test_a_nonlinear_system_against_the_analytic_jacobian(self):
        theta, omega, torque = 0.7, -0.3, 0.3
        bd = pendulum_diagram()
        # states are in the order omega, theta
        A, B, C, D = bd.linearize(x=[omega, theta], u=[torque])
        np.testing.assert_allclose(
            A,
            [[-DAMPING, -G_OVER_L * np.cos(theta)], [1.0, 0.0]],
            atol=1e-7,
        )
        np.testing.assert_allclose(B, [[1.0], [0.0]], atol=1e-8)
        np.testing.assert_allclose(C, [[0.0, 1.0]], atol=1e-8)
        np.testing.assert_allclose(D, [[0.0]], atol=1e-8)

    def test_the_operating_point_defaults_to_the_initial_state_and_natural_input(self):
        bd = pendulum_diagram(theta0=0.9)
        A, *_ = bd.linearize()
        self.assertAlmostEqual(A[0, 1], -G_OVER_L * np.cos(0.9), places=6)

    def test_u_defaults_to_the_value_of_the_sources_at_t(self):
        bd = new_diagram()
        step = bd.STEP(T=1, name="demand")  # 0 before t = 1, 1 after
        gain = bd.GAIN(2.0, name="gain")
        bd.connect(step, gain)
        bd.connect(gain, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        for t, u in ((0.0, 0.0), (0.5, 0.0), (1.0, 1.0), (2.0, 1.0)):
            lin = bd.linearize(t=t, full=True)
            np.testing.assert_array_equal(lin.u, [u], err_msg=f"t={t}")
            np.testing.assert_allclose(lin.y0, [2.0 * u], err_msg=f"t={t}")
        # a u that is given wins
        np.testing.assert_array_equal(bd.linearize(u=[9.0], t=2.0, full=True).u, [9.0])

    def test_the_result_is_not_a_function_of_the_input_given_to_a_linear_system(self):
        bd, (A, B, C, D) = lti_diagram()
        a, b, c, d = bd.linearize(x=[5.0, -4.0], u=[100.0, -100.0])
        np.testing.assert_allclose(a, A, atol=1e-7)
        np.testing.assert_allclose(d, D, atol=1e-7)

    def test_full_returns_the_operating_point_and_unpacks(self):
        bd, (A, B, C, D) = lti_diagram()
        lin = bd.linearize(x=[1.0, 2.0], u=[1.0, 2.0], full=True)
        self.assertIsInstance(lin, Linearization)
        np.testing.assert_allclose(lin.f0, A @ [1.0, 2.0] + B @ [1.0, 2.0], atol=1e-12)
        np.testing.assert_allclose(lin.y0, C @ [1.0, 2.0] + D @ [1.0, 2.0], atol=1e-12)
        np.testing.assert_array_equal(lin.x, [1.0, 2.0])
        np.testing.assert_array_equal(lin.u, [1.0, 2.0])
        self.assertEqual(lin.t, 0.0)
        self.assertIsNone(lin.error)
        self.assertEqual(lin.xindex.names, ["system[0]", "system[1]"])
        self.assertEqual(lin.uindex.names, ["u1", "u2"])
        self.assertEqual(lin.yindex.names, ["system"])
        a, b, c, d = lin
        np.testing.assert_array_equal(a, lin.A)

    def test_the_default_is_just_the_four_matrices(self):
        bd, _ = lti_diagram()
        result = bd.linearize()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 4)

    def test_estimate_error(self):
        bd = pendulum_diagram()
        lin = bd.linearize(estimate_error=True, full=True)
        self.assertEqual(set(lin.error), {"A", "B", "C", "D"})
        self.assertEqual(lin.error["A"].shape, lin.A.shape)
        self.assertLess(max(e.max() for e in lin.error.values()), 1e-8)

    def test_a_smooth_system_does_not_warn(self):
        bd = pendulum_diagram()
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            bd.linearize(estimate_error=True)

    def test_a_corner_within_the_step_warns(self):
        bd = new_diagram()
        u = bd.CONSTANT(0.95, name="u")
        clip = bd.CLIP(min=-1.0, max=1.0, name="clip")
        integrator = bd.INTEGRATOR(x0=0, name="integrator")
        bd.connect(u, clip)
        bd.connect(clip, integrator)
        bd.connect(integrator, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        # the corner at 1 is within one step (0.1) of u = 0.95, so the slope
        # across the step depends on the step
        with self.assertWarnsRegex(UserWarning, "changes with the step size"):
            bd.linearize(h=0.1, estimate_error=True)
        # and without asking for the estimate there is nothing to say
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            bd.linearize(h=0.1)

    def test_scale_gives_a_step_for_a_variable_that_is_zero(self):
        bd, (A, B, C, D) = lti_diagram()
        a, *_ = bd.linearize(x=[0.0, 0.0], u=[0.0, 0.0], scale=1e-3)
        np.testing.assert_allclose(a, A, atol=1e-5)
        with self.assertRaisesRegex(ValueError, "scale must be positive"):
            bd.linearize(scale=0.0)

    def test_the_sizes_of_x_and_u_are_checked(self):
        bd, _ = lti_diagram()
        with self.assertRaisesRegex(ValueError, "x has 1 elements, expected 2"):
            bd.linearize(x=[1.0])
        with self.assertRaisesRegex(ValueError, "u has 1 elements, expected 2"):
            bd.linearize(u=[1.0])

    def test_inputs_and_outputs_can_be_selected(self):
        bd, (A, B, C, D) = lti_diagram()
        a, b, c, d = bd.linearize(inputs=[bd["u2"]])
        np.testing.assert_allclose(b, B[:, 1:], atol=1e-8)
        np.testing.assert_allclose(d, D[:, 1:], atol=1e-8)


class LinearizationDisplayTest(unittest.TestCase):
    def lin(self, **kwargs):
        bd, _ = lti_diagram()
        return bd.linearize(x=[1.0, 2.0], u=[1.0, 2.0], full=True, **kwargs)

    def test_each_matrix_is_labelled_with_the_names_of_its_signals(self):
        text = str(self.lin())
        self.assertIn("states  x (2): system[0], system[1]", text)
        self.assertIn("inputs  u (2): u1, u2", text)
        self.assertIn("outputs y (1): system", text)
        self.assertIn("A = df/dx  (2x2)", text)
        self.assertIn("rows and columns: system[0], system[1]", text)
        self.assertIn("B = df/du  (2x2)", text)
        self.assertIn("columns: u1, u2", text)
        self.assertIn("C = dg/dx  (1x2)", text)
        self.assertIn("D = dg/du  (1x2)", text)

    def test_rows_and_columns_are_named_correctly_for_every_matrix(self):
        # distinct names for the states (vel, pos), the input (force) and the
        # outputs (amp, vel), so that a swapped label is visible
        bd = new_diagram()
        force = bd.CONSTANT(1.0, name="force")
        amp = bd.GAIN(2.0, name="amp")
        vel = bd.INTEGRATOR(x0=0.0, name="vel")
        pos = bd.INTEGRATOR(x0=0.0, name="pos")
        bd.connect(force, amp)
        bd.connect(amp, vel)
        bd.connect(vel, pos)
        bd.connect(amp, bd.NULL(1, name="y_amp"))
        bd.connect(vel, bd.NULL(1, name="y_vel"))
        bd.compile(verbose=False)
        text = str(bd.linearize(full=True))
        lines = text.splitlines()

        def section(label):
            i = next(k for k, ln in enumerate(lines) if ln.startswith(label))
            return lines[i + 1 : i + 3]

        self.assertIn("states  x (2): vel, pos", text)
        self.assertIn("inputs  u (1): force", text)
        self.assertIn("outputs y (2): amp, vel", text)
        self.assertEqual(
            section("A = "), ["  rows and columns: vel, pos", "[[0., 0.],"]
        )
        self.assertEqual(section("B = "), ["  rows: vel, pos", "  columns: force"])
        self.assertEqual(section("C = "), ["  rows: amp, vel", "  columns: vel, pos"])
        self.assertEqual(section("D = "), ["  rows: amp, vel", "  columns: force"])

    def test_the_matrices_are_shown(self):
        text = str(self.lin())
        # A = [[0, 1], [-2, -3]]
        self.assertIn("[[ 0.,  1.],\n [-2., -3.]]", text)

    def test_the_labels_change_with_the_selection(self):
        bd, _ = lti_diagram()
        text = str(bd.linearize(inputs=["u2"], full=True))
        self.assertIn("inputs  u (1): u2", text)
        self.assertNotIn("u1", text)

    def test_the_poles_are_the_eigenvalues_of_a(self):
        lin = self.lin()
        np.testing.assert_allclose(lin.poles, [-2.0, -1.0], atol=1e-6)
        self.assertEqual(lin.poles.dtype, complex)

    def test_real_poles_are_printed_without_padding_or_zero_imaginary_parts(self):
        self.assertIn("poles: [-2, -1]", str(self.lin()))

    def test_complex_poles_are_printed_compactly(self):
        # a lightly damped oscillator: poles -0.1 +- 2j
        bd = new_diagram()
        system = bd.LTI_SS(
            A=np.array([[0, 1], [-4.01, -0.2]]),
            B=np.array([[0.0], [1.0]]),
            C=np.array([[1.0, 0.0]]),
            name="oscillator",
        )
        bd.connect(bd.CONSTANT(0.0, name="u"), system)
        bd.connect(system, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        lin = bd.linearize(full=True)
        np.testing.assert_allclose(sorted(lin.poles.imag), [-2.0, 2.0], atol=1e-6)
        line = [ln for ln in str(lin).splitlines() if ln.startswith("poles:")][0]
        self.assertRegex(line, r"-0\.1(0000)?[+-]2j")
        self.assertNotIn("  ", line)

    def test_it_says_when_the_point_is_not_an_equilibrium(self):
        self.assertIn("not an equilibrium", str(self.lin()))
        bd = pendulum_diagram(torque=0.0, theta0=0.0, omega0=0.0)
        self.assertNotIn("not an equilibrium", str(bd.linearize(full=True)))

    def test_no_inputs_or_outputs_still_prints(self):
        bd = new_diagram()
        integrator = bd.INTEGRATOR(x0=0, name="integrator")
        bd.connect(bd.CONSTANT(1.0, name="u"), integrator)
        bd.compile(verbose=False)
        text = str(bd.linearize(inputs=[], outputs=[], full=True))
        self.assertIn("inputs  u (0): ", text)
        self.assertIn("(1x0)", text)

    def test_it_can_be_printed_on_any_console(self):
        str(self.lin()).encode("ascii")

    def test_repr_is_short(self):
        self.assertEqual(repr(self.lin()), "Linearization(t=0, nx=2, nu=2, ny=1)")


class StateLayoutTest(unittest.TestCase):
    """bd.xindex is the one definition of the layout of the continuous state."""

    def named_states_diagram(self):
        bd = new_diagram()
        plain = bd.INTEGRATOR(x0=1.0, name="plain")
        pair = bd.INTEGRATOR(x0=[2.0, 3.0], snames=["pos", "vel"], name="pair")
        unnamed_pair = bd.INTEGRATOR(x0=[4.0, 5.0], name="unnamed")
        bd.connect(bd.CONSTANT(0.0, name="u"), plain)
        bd.connect(bd.CONSTANT(np.zeros(2), name="v"), pair)
        bd.connect(bd.CONSTANT(np.zeros(2), name="w"), unnamed_pair)
        bd.connect(plain, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        return bd

    def test_it_lists_the_continuous_states_in_the_order_of_the_blocks(self):
        bd = self.named_states_diagram()
        index = bd.xindex
        self.assertEqual(len(index), 5)
        self.assertEqual(list(index), [bd["plain"], bd["pair"], bd["unnamed"]])
        self.assertEqual(index["pair"], slice(1, 3))
        self.assertEqual(index["unnamed"], slice(3, 5))

    def test_names_a_block_gave_its_states_are_used(self):
        bd = self.named_states_diagram()
        self.assertEqual(
            bd.xindex.names, ["plain", "pos", "vel", "unnamed[0]", "unnamed[1]"]
        )

    def test_it_describes_the_same_elements_in_the_same_order_as_statenames(self):
        bd = self.named_states_diagram()
        index = bd.xindex
        self.assertEqual(len(bd.statenames), len(index))
        for i, name in enumerate(bd.statenames):
            block, k = index.labels[i]
            # default names are "block:x_k", and the names a block gave are as given
            given = block._state_names
            expected = given[k] if given else f"{block.name}:x_{k}"
            self.assertEqual(name, expected)

    def test_the_names_agree_where_the_block_named_its_states(self):
        bd = self.named_states_diagram()
        self.assertEqual(bd.statenames[1:3], bd.xindex.names[1:3])

    def test_it_is_the_state_of_functions_and_of_the_state_block(self):
        bd = self.named_states_diagram()
        st = bd.STATE(name="state")
        bd.connect(st, bd.NULL(1, name="y2"))
        bd.compile(verbose=False)
        self.assertEqual(bd.functions().xindex.names, bd.xindex.names)
        self.assertEqual(st.statenames, bd.xindex.names)
        self.assertEqual(st.index.slices, bd.xindex.slices)

    def test_getstate0_follows_it(self):
        bd = self.named_states_diagram()
        np.testing.assert_array_equal(bd.getstate0(), [1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertEqual(len(bd.getstate0()), len(bd.xindex))

    def test_a_diagram_with_no_state_has_an_empty_index(self):
        bd = new_diagram()
        bd.connect(bd.CONSTANT(1.0), bd.NULL(1))
        bd.compile(verbose=False)
        self.assertEqual(len(bd.xindex), 0)
        self.assertEqual(list(bd.xindex), [])
        self.assertEqual(len(bd.getstate0()), 0)

    def test_an_index_can_be_given_names(self):
        bd = self.named_states_diagram()
        entries = [(bd["plain"], 0), (bd["pair"], 0), (bd["pair"], 1)]
        index = Index(entries, ["a", None, "c"])
        self.assertEqual(index.names, ["a", "pair[0]", "c"])
        with self.assertRaisesRegex(ValueError, "2 names for 3 elements"):
            Index(entries, ["a", "b"])


try:
    import control

    HAVE_CONTROL = True
except ImportError:  # python-control is an optional dependency
    HAVE_CONTROL = False


def double_integrator(feedback_gain=None):
    """x'' = u, the states are (vel, pos); with a gain K the force is -K state."""
    bd = new_diagram()
    force = bd.CONSTANT(0.0, name="force")
    vel = bd.INTEGRATOR(x0=0.0, name="vel")
    pos = bd.INTEGRATOR(x0=1.0, name="pos")
    total = force
    if feedback_gain is not None:
        total = force + (-feedback_gain) * bd.STATE(name="state")
    bd.connect(total, vel)
    bd.connect(vel, pos)
    bd.connect(pos, bd.NULL(1, name="y"))
    bd.compile(verbose=False)
    return bd


@unittest.skipUnless(HAVE_CONTROL, "python-control is not installed")
class LinearizationSSTest(unittest.TestCase):
    def test_it_is_a_state_space_system_with_the_same_matrices(self):
        bd, (A, B, C, D) = lti_diagram()
        lin = bd.linearize(full=True)
        sys = lin.ss()
        self.assertIsInstance(sys, control.StateSpace)
        np.testing.assert_array_equal(sys.A, lin.A)
        np.testing.assert_array_equal(sys.B, lin.B)
        np.testing.assert_array_equal(sys.C, lin.C)
        np.testing.assert_array_equal(sys.D, lin.D)
        np.testing.assert_allclose(sys.A, A, atol=1e-8)
        np.testing.assert_allclose(sys.D, D, atol=1e-8)

    def test_it_is_continuous_time(self):
        bd, _ = lti_diagram()
        self.assertEqual(bd.linearize(full=True).ss().dt, 0)

    def test_the_signals_carry_the_names_of_the_diagram(self):
        bd, _ = lti_diagram()
        lin = bd.linearize(full=True)
        sys = lin.ss()
        self.assertEqual(sys.state_labels, lin.xindex.names)
        self.assertEqual(sys.input_labels, ["u1", "u2"])
        self.assertEqual(sys.output_labels, ["system"])
        self.assertEqual((sys.nstates, sys.ninputs, sys.noutputs), (2, 2, 1))

    def test_the_name_is_passed_on(self):
        bd, _ = lti_diagram()
        self.assertEqual(bd.linearize(full=True).ss(name="plant").name, "plant")

    def test_the_poles_agree(self):
        bd, _ = lti_diagram()
        lin = bd.linearize(full=True)
        np.testing.assert_allclose(
            np.sort_complex(control.poles(lin.ss())), lin.poles, atol=1e-9
        )

    def test_a_system_without_outputs(self):
        bd = new_diagram()
        integrator = bd.INTEGRATOR(x0=0.0, name="integrator")
        bd.connect(bd.CONSTANT(1.0, name="u"), integrator)
        bd.compile(verbose=False)
        sys = bd.linearize(outputs=[], full=True).ss()
        self.assertEqual((sys.ninputs, sys.noutputs, sys.nstates), (1, 0, 1))

    def test_an_autonomous_system_with_two_states(self):
        # no inputs and no outputs: python-control takes this from two states up
        bd = new_diagram()
        vel = bd.INTEGRATOR(x0=1.0, name="vel")
        pos = bd.INTEGRATOR(x0=0.0, name="pos")
        bd.connect(bd.CONSTANT(0.0, name="u"), vel)
        bd.connect(vel, pos)
        bd.compile(verbose=False)
        lin = bd.linearize(inputs=[], outputs=[], full=True)
        sys = lin.ss()
        self.assertEqual((sys.ninputs, sys.noutputs, sys.nstates), (0, 0, 2))
        np.testing.assert_allclose(sys.A, lin.A)

    def test_a_design_made_with_it_closes_the_loop(self):
        # linearize the open loop, design an LQR with python-control, and apply the
        # gain with a STATE block: the closed loop has the poles the design gave
        sys = double_integrator().linearize(full=True).ss()
        K, _, poles = control.lqr(sys.A, sys.B, np.diag([1.0, 10.0]), np.array([[1.0]]))
        closed = double_integrator(feedback_gain=K)
        np.testing.assert_allclose(
            closed.linearize(full=True).poles, np.sort_complex(poles), atol=1e-6
        )
        self.assertTrue(np.all(closed.linearize(full=True).poles.real < 0))

    def test_the_closed_loop_state_names_match_the_design(self):
        sys = double_integrator().linearize(full=True).ss()
        self.assertEqual(sys.state_labels, ["vel", "pos"])


class LinearizationSSWithoutControlTest(unittest.TestCase):
    def test_a_missing_package_is_a_clear_error(self):
        bd, _ = lti_diagram()
        lin = bd.linearize(full=True)
        with unittest.mock.patch.dict(sys.modules, {"control": None}):
            with self.assertRaisesRegex(ImportError, "pip install control"):
                lin.ss()

    def test_control_is_not_imported_until_it_is_needed(self):
        code = (
            "import sys, bdsim, bdsim.analysis;"
            "bd = bdsim.BDSim(sysargs=False, graphics=False).blockdiagram();"
            "bd.connect(bd.CONSTANT(1.0), bd.INTEGRATOR(), );"
            "assert 'control' not in sys.modules, 'imported too early'"
        )
        result = subprocess.run(  # nosec B603
            [sys.executable, "-I", "-c", code], capture_output=True, text=True
        )
        self.assertNotIn("imported too early", result.stderr)


class AfterARunTest(unittest.TestCase):
    def limited_integrator_diagram(self):
        bd = new_diagram()
        u = bd.CONSTANT(1.0, name="u")
        integrator = bd.INTEGRATOR(x0=0.0, max=0.5, name="integrator")
        bd.connect(u, integrator)
        bd.connect(integrator, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        return bd

    def test_before_a_run_the_integrator_is_free(self):
        bd = self.limited_integrator_diagram()
        A, B, C, D = bd.linearize()
        np.testing.assert_allclose(B, [[1.0]], atol=1e-8)

    def test_after_a_run_a_held_integrator_stays_held(self):
        bd = self.limited_integrator_diagram()
        sim = bdsim.BDSim(sysargs=False, graphics=False)
        out = sim.run(bd, T=2.0, dt=0.1)
        np.testing.assert_allclose(out.x[-1], [0.5])
        A, B, C, D = bd.linearize(out.x[-1])
        # at the limit with the input pushing against it, the state cannot move
        np.testing.assert_allclose(A, [[0.0]], atol=1e-12)
        np.testing.assert_allclose(B, [[0.0]], atol=1e-12)
        np.testing.assert_allclose(C, [[1.0]], atol=1e-8)

    def test_linearize_at_the_end_of_a_run(self):
        bd = pendulum_diagram()
        sim = bdsim.BDSim(sysargs=False, graphics=False)
        out = sim.run(bd, T=1.0, dt=0.05)
        omega, theta = out.x[-1]
        A, B, C, D = bd.linearize(out.x[-1])
        self.assertAlmostEqual(A[0, 1], -G_OVER_L * np.cos(theta), places=6)
        self.assertAlmostEqual(A[0, 0], -DAMPING, places=6)

    def test_the_run_can_be_repeated_after_linearizing(self):
        bd = pendulum_diagram()
        sim = bdsim.BDSim(sysargs=False, graphics=False)
        first = sim.run(bd, T=0.5, dt=0.05)
        bd.linearize(first.x[-1])
        second = sim.run(bd, T=0.5, dt=0.05)
        np.testing.assert_allclose(first.x, second.x)


class EvaluateOverridesTest(unittest.TestCase):
    def test_overrides_replace_the_output_of_a_block(self):
        bd = new_diagram()
        source = bd.CONSTANT(1.0, name="source")
        gain = bd.GAIN(10.0, name="gain")
        bd.connect(source, gain)
        bd.connect(gain, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        state_map = bd.state_map(np.array([]))
        bd.evaluate(state_map, 0.0, sinks=False, overrides={source: [4.0]})
        self.assertEqual(bd["y"].inport_values, [40.0])
        # without overrides the block is called as before
        bd.evaluate(state_map, 0.0, sinks=False)
        self.assertEqual(bd["y"].inport_values, [10.0])


class MixinTest(unittest.TestCase):
    def test_the_methods_come_from_the_mixin(self):
        self.assertTrue(issubclass(BlockDiagram, AnalysisMixin))
        for name in ("functions", "linearize"):
            self.assertIs(getattr(BlockDiagram, name), getattr(AnalysisMixin, name))

    def test_index_is_exported(self):
        self.assertTrue(callable(Index))


if __name__ == "__main__":
    unittest.main()
