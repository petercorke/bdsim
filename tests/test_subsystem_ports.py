#!/usr/bin/env python3
"""Subsystem INPORT and OUTPORT blocks are replaced by wires when the diagram is compiled
(Issue #84), and the signals of a subsystem are still found through the subsystem block.
"""

import math
import unittest

import numpy.testing as nt

import bdsim
from bdsim.connect import Plug, StartPlug, Wire


def quiet():
    return bdsim.BDSim(graphics=False, progress=False, banner=False, quiet=True)


def run(sim, bd, **kwargs):
    bd.compile(verbose=False)
    return sim.run(bd, T=1.0, dt=0.1, **kwargs)


def ports_in(bd):
    return [b for b in bd.blocklist if b.type in ("inport", "outport")]


class Issue84Test(unittest.TestCase):
    """Port 0 goes through an integrator, port 1 is feedthrough, and out[0] is fed back."""

    def diagram(self, sim):
        ss = sim.blockdiagram("Subsystem")
        inport = ss.INPORT(1)
        outport = ss.OUTPORT(2)
        integ = ss.INTEGRATOR(1.0)
        ss.connect(inport, integ, outport[1])
        ss.connect(integ, outport[0])

        bd = sim.blockdiagram()
        block = bd.SUBSYSTEM(ss, name="block")
        bd.connect(block[0], bd.NULL(1))
        bd.connect(block[1], bd.NULL(1))
        bd.connect(block[0], block)
        return bd, block

    def test_compiles(self):
        sim = quiet()
        bd, _ = self.diagram(sim)
        bd.compile(verbose=False)
        self.assertEqual(ports_in(bd), [])

    def test_the_answer_is_right(self):
        # x' = x, x(0) = 1 and the feedthrough output is the same signal
        sim = quiet()
        bd, block = self.diagram(sim)
        out = run(sim, bd, watch=[block[0], block[1]])
        nt.assert_allclose(out.y[-1], [math.exp(1.0)] * 2, rtol=1e-4)


class ElisionTest(unittest.TestCase):
    def setUp(self):
        self.sim = quiet()

    def gain_subsystem(self, name, k):
        ss = self.sim.blockdiagram(name=name)
        inp = ss.INPORT(1)
        gain = ss.GAIN(k, name="gain")
        outp = ss.OUTPORT(1)
        ss.connect(inp, gain)
        ss.connect(gain, outp)
        return ss

    def test_no_port_blocks_remain(self):
        bd = self.sim.blockdiagram()
        sub = bd.SUBSYSTEM(self.gain_subsystem("g", 2.0), name="sub")
        bd.connect(bd.CONSTANT(3.0), sub)
        bd.connect(sub, bd.NULL(1))
        bd.compile(verbose=False)
        self.assertEqual(ports_in(bd), [])
        self.assertNotIn("sub/inport.0", bd.blocknames)
        self.assertEqual(len(bd.blocklist), 3)  # constant, gain, null
        self.assertEqual(len(bd.wirelist), 2)

    def test_a_subsystem_that_only_passes_a_signal_through(self):
        ss = self.sim.blockdiagram(name="through")
        ss.connect(ss.INPORT(1), ss.OUTPORT(1))
        bd = self.sim.blockdiagram()
        sub = bd.SUBSYSTEM(ss, name="sub")
        const = bd.CONSTANT(3.0)
        bd.connect(const, sub)
        bd.connect(sub, bd.NULL(1))
        out = run(self.sim, bd, watch=[sub])
        self.assertEqual(out.y[-1][0], 3.0)
        self.assertIs(sub.outports[0].block, const)

    def test_an_input_goes_to_several_blocks(self):
        ss = self.sim.blockdiagram(name="fan")
        inp = ss.INPORT(1)
        two = ss.GAIN(2.0, name="two")
        three = ss.GAIN(3.0, name="three")
        outp = ss.OUTPORT(2)
        ss.connect(inp, two, three)
        ss.connect(two, outp[0])
        ss.connect(three, outp[1])
        bd = self.sim.blockdiagram()
        sub = bd.SUBSYSTEM(ss, name="sub")
        bd.connect(bd.CONSTANT(1.0), sub)
        bd.connect(sub[0], bd.NULL(1))
        bd.connect(sub[1], bd.NULL(1))
        out = run(self.sim, bd, watch=[sub[0], sub[1]])
        nt.assert_array_equal(out.y[-1], [2.0, 3.0])

    def test_nested_subsystems(self):
        inner = self.gain_subsystem("inner", 2.0)
        outer = self.sim.blockdiagram(name="outer")
        inp = outer.INPORT(1)
        sub = outer.SUBSYSTEM(inner, name="inner")
        outp = outer.OUTPORT(1)
        outer.connect(inp, sub)
        outer.connect(sub, outp)

        bd = self.sim.blockdiagram()
        top = bd.SUBSYSTEM(outer, name="top")
        const = bd.CONSTANT(3.0)
        bd.connect(const, top)
        bd.connect(top, bd.NULL(1))
        out = run(self.sim, bd, watch=[top, "top/inner[0]"])

        self.assertEqual(ports_in(bd), [])
        nt.assert_array_equal(out.y[-1], [6.0, 6.0])
        # the output of each is found inside; the nested one is looked through
        gain = bd["top/inner/gain"]
        self.assertIs(top.outports[0].block, gain)
        self.assertIs(bd["top/inner"].outports[0].block, gain)
        self.assertIs(top.inports[0].block, const)
        self.assertIs(bd["top/inner"].inports[0].block, const)

    def test_watch_keeps_the_name_of_the_subsystem(self):
        bd = self.sim.blockdiagram()
        sub = bd.SUBSYSTEM(self.gain_subsystem("g", 2.0), name="sub")
        bd.connect(bd.CONSTANT(3.0), sub)
        bd.connect(sub, bd.NULL(1))
        out = run(self.sim, bd, watch=[sub])
        (name,) = out.ynames
        self.assertIn("'sub'", name)  # not the gain block that generates the value
        self.assertNotIn("gain", name)

    def test_watch_by_name_and_by_plug(self):
        bd = self.sim.blockdiagram()
        sub = bd.SUBSYSTEM(self.gain_subsystem("g", 2.0), name="sub")
        bd.connect(bd.CONSTANT(3.0), sub)
        bd.connect(sub, bd.NULL(1))
        out = run(self.sim, bd, watch=["sub[0]", sub[0], "sub"])
        nt.assert_array_equal(out.y[-1], [6.0, 6.0, 6.0])

    def test_compiling_again(self):
        bd = self.sim.blockdiagram()
        sub = bd.SUBSYSTEM(self.gain_subsystem("g", 2.0), name="sub")
        bd.connect(bd.CONSTANT(3.0), sub)
        bd.connect(sub, bd.NULL(1))
        bd.compile(verbose=False)
        out = run(self.sim, bd, watch=[sub])
        self.assertEqual(out.y[-1][0], 6.0)
        self.assertEqual(len(bd.blocklist), 3)

    def test_an_unconnected_input_is_an_error_that_names_the_subsystem(self):
        bd = self.sim.blockdiagram()
        bd.SUBSYSTEM(self.gain_subsystem("g", 2.0), name="sub")
        with self.assertRaises(ValueError):  # as for any unconnected input
            with _captured() as out:
                bd.compile(verbose=False)
        self.assertIn("input 0 of subsystem sub is not connected", out.getvalue())

    def test_ports_wired_in_a_loop_are_an_error(self):
        ss = self.sim.blockdiagram(name="through")
        ss.connect(ss.INPORT(1), ss.OUTPORT(1))
        bd = self.sim.blockdiagram()
        sub = bd.SUBSYSTEM(ss, name="sub")
        bd.connect(sub, sub)
        with self.assertRaises(RuntimeError):
            with _captured() as out:
                bd.compile(verbose=False)
        self.assertIn("loop", out.getvalue())

    def test_parameters_of_the_blocks_inside_are_still_reached(self):
        bd = self.sim.blockdiagram()
        pid = bd.PID(P=1, I=1, name="pid")
        bd.connect(bd.CONSTANT(1.0), pid[0])
        bd.connect(bd.CONSTANT(0.0), pid[1])
        bd.connect(pid, bd.NULL(1))
        bd.compile(verbose=False)
        self.assertEqual(ports_in(bd), [])
        self.assertIs(bd["pid"], pid)
        bd["pid"].set_param("P", 4)
        self.assertEqual(bd["pid/P"].K, 4)
        self.assertEqual(len(pid.outports), 1)
        self.assertEqual(len(pid.inports), 2)


class ReportTest(unittest.TestCase):
    def test_subsystem_report_lists_the_ports_with_their_sources(self):
        sim = quiet()
        inner = sim.blockdiagram(name="inner")
        i = inner.INPORT(1)
        g = inner.GAIN(2.0, name="gain")
        o = inner.OUTPORT(1)
        inner.connect(i, g)
        inner.connect(g, o)
        bd = sim.blockdiagram()
        sub = bd.SUBSYSTEM(inner, name="sub")
        bd.connect(bd.CONSTANT(3.0, name="three"), sub)
        bd.connect(sub, bd.NULL(1))
        bd.compile(verbose=False)
        with _captured() as out:
            bd.report_subsystems()
        text = out.getvalue()
        self.assertIn("sub[0]", text)
        self.assertIn("three[0]", text)  # the source of the input
        self.assertIn("sub/gain[0]", text)  # the source of the output
        self.assertIn("float", text)
        self.assertNotIn("inport", text)
        self.assertNotIn("outport", text)


class WireNewStartTest(unittest.TestCase):
    def setUp(self):
        self.bd = quiet().blockdiagram()
        self.a = self.bd.CONSTANT(1.0)
        self.b = self.bd.CONSTANT(2.0)
        self.c = self.bd.NULL(1)

    def test_the_wire_starts_somewhere_else(self):
        w = Wire(StartPlug(self.a, 0), Plug(self.c, 0, "end"))
        plug = StartPlug(self.b, 0)
        w.newstart(plug)
        self.assertIs(w.start.block, self.b)
        self.assertEqual(w.start.port, 0)
        self.assertEqual(w.start.type, "start")

    def test_it_takes_a_copy_of_the_plug(self):
        plug = StartPlug(self.b, 0)
        w1 = Wire(StartPlug(self.a, 0), Plug(self.c, 0, "end"))
        w2 = Wire(StartPlug(self.a, 0), Plug(self.c, 0, "end"))
        w1.newstart(plug)
        w2.newstart(plug)
        self.assertIsNot(w1.start, plug)
        self.assertIsNot(w1.start, w2.start)
        w1.start.block = self.a  # changing one cannot change the other
        self.assertIs(w2.start.block, self.b)
        self.assertIs(plug.block, self.b)

    def test_not_once_it_is_connected_to_its_blocks(self):
        self.bd.connect(self.a, self.c)
        self.bd.compile(verbose=False)
        w = self.bd.wirelist[0]
        with self.assertRaises(RuntimeError):
            w.newstart(StartPlug(self.b, 0))


import contextlib
import io


@contextlib.contextmanager
def _captured():
    with contextlib.redirect_stdout(io.StringIO()) as out:
        yield out


if __name__ == "__main__":
    unittest.main()
