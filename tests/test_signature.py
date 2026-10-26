#!/usr/bin/env python3

import io
import unittest
from contextlib import redirect_stdout

import numpy as np
from spatialmath import SE3

import bdsim
from bdsim.block_types import FunctionBlock, SourceBlock
from bdsim.signature import Signature


class Emit(SourceBlock):
    """A source that emits its value exactly as given, whatever the type.

    CONSTANT converts some values, for example a list becomes an ndarray.
    """

    nin = 0
    nout = 1

    def __init__(self, value, **blockargs):
        super().__init__(**blockargs)
        self.value = value

    def output(self, t, inputs, x):
        return [self.value]


class SignatureOfTest(unittest.TestCase):
    """A signature is the type of a value, plus shape and dtype for an ndarray."""

    def test_python_scalars(self):
        for value, kind in [(1, int), (2.5, float), (True, bool), (1j, complex)]:
            with self.subTest(value=value):
                sig = Signature.of(value)
                self.assertIs(sig.type, kind)
                self.assertIsNone(sig.shape)
                self.assertIsNone(sig.dtype)

    def test_numpy_scalar_is_not_an_array(self):
        sig = Signature.of(np.float64(1.5))
        self.assertIs(sig.type, np.float64)
        self.assertIsNone(sig.shape)
        self.assertIsNone(sig.dtype)

    def test_any_python_type(self):
        # a wire can carry any Python object, so nothing here is numeric
        for value in ([1, 2, 3], "text", None, {"a": 1}, (1, 2), object(), SE3()):
            with self.subTest(type=type(value).__name__):
                sig = Signature.of(value)
                self.assertIs(sig.type, type(value))
                self.assertIsNone(sig.shape)
                self.assertIsNone(sig.dtype)

    def test_list_records_no_length(self):
        self.assertEqual(Signature.of([1, 2, 3]), Signature.of([4]))

    def test_ndarray_records_shape_and_dtype(self):
        sig = Signature.of(np.zeros((2, 3)))
        self.assertIs(sig.type, np.ndarray)
        self.assertEqual(sig.shape, (2, 3))
        self.assertEqual(sig.dtype, np.dtype("float64"))

        sig = Signature.of(np.array([1, 2, 3]))
        self.assertEqual(sig.shape, (3,))
        self.assertEqual(sig.dtype, np.dtype("int64"))

    def test_equality(self):
        self.assertEqual(Signature.of(np.zeros(3)), Signature.of(np.ones(3)))
        self.assertNotEqual(Signature.of(np.zeros(3)), Signature.of(np.zeros(4)))
        self.assertNotEqual(Signature.of(np.zeros(3)), Signature.of(np.zeros(3, int)))
        self.assertNotEqual(Signature.of(1), Signature.of(1.0))
        self.assertNotEqual(Signature.of([1]), Signature.of((1,)))

    def test_immutable_and_hashable(self):
        sig = Signature.of(np.zeros(3))
        with self.assertRaises(Exception):
            sig.shape = (4,)  # type: ignore[misc]
        self.assertEqual(len({sig, Signature.of(np.ones(3))}), 1)

    def test_str(self):
        self.assertEqual(str(Signature.of(1.5)), "float")
        self.assertEqual(str(Signature.of([1])), "list")
        self.assertEqual(str(Signature.of(np.zeros((2, 3)))), "ndarray(2, 3) float64")


class ScalarCollapseTest(unittest.TestCase):
    """A 1-D ndarray of size 1 is presented as a scalar, once, when published."""

    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False)

    def _publish(self, value):
        bd = self.sim.blockdiagram()
        block = bd.CONSTANT(0)
        block.compile()  # creates the port slots
        block._publish_output_values([value])
        return block, block.outport_slot(0).value

    def test_size_one_vector_becomes_a_scalar(self):
        _, out = self._publish(np.array([2.5]))
        self.assertNotIsInstance(out, np.ndarray)
        self.assertEqual(out, 2.5)

    def test_numpy_scalar_type_is_preserved(self):
        _, out = self._publish(np.array([2.5]))
        self.assertIsInstance(out, np.float64)
        _, out = self._publish(np.array([3]))
        self.assertIsInstance(out, np.integer)
        _, out = self._publish(np.array([True]))
        self.assertIsInstance(out, np.bool_)

    def test_one_by_one_matrix_stays_a_matrix(self):
        _, out = self._publish(np.array([[2.5]]))
        self.assertIsInstance(out, np.ndarray)
        self.assertEqual(out.shape, (1, 1))

    def test_longer_vectors_and_matrices_are_unchanged(self):
        value = np.array([1.0, 2.0])
        _, out = self._publish(value)
        self.assertIs(out, value)
        value = np.eye(2)
        _, out = self._publish(value)
        self.assertIs(out, value)

    def test_only_ndarrays_collapse(self):
        for value in ([1.0], (1.0,), "x", None, 1.0, 3):
            with self.subTest(value=value):
                _, out = self._publish(value)
                self.assertIs(out, value)

    def test_cached_output_value_is_collapsed_too(self):
        block, out = self._publish(np.array([2.5]))
        self.assertEqual(block.outport_value(0), out)
        self.assertNotIsInstance(block.outport_value(0), np.ndarray)


class DiagramSignatureTest(unittest.TestCase):
    """compile() records the signature of every wire from the trial evaluation."""

    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False)

    def _source_to_sink(self, value):
        bd = self.sim.blockdiagram()
        src = Emit(value, bd=bd)
        sink = bd.NULL(1)
        bd.connect(src, sink)
        bd.compile(verbose=False)
        return src, sink

    def test_unknown_before_compile(self):
        bd = self.sim.blockdiagram()
        src = bd.CONSTANT(1)
        sink = bd.NULL(1)
        bd.connect(src, sink)
        self.assertEqual(src.outsig, [None])
        self.assertEqual(sink.insig, [None])

    def test_types_of_wires(self):
        cases = [
            (1, Signature(int)),
            (2.5, Signature(float)),
            (True, Signature(bool)),
            ("hello", Signature(str)),
            ([1, 2, 3], Signature(list)),
            (np.array([1.0, 2.0, 3.0]), Signature(np.ndarray, (3,), np.dtype(float))),
            (np.eye(2), Signature(np.ndarray, (2, 2), np.dtype(float))),
            (np.array([[5.0]]), Signature(np.ndarray, (1, 1), np.dtype(float))),
            (np.array([1, 2]), Signature(np.ndarray, (2,), np.dtype(int))),
        ]
        for value, expected in cases:
            with self.subTest(value=repr(value)):
                src, sink = self._source_to_sink(value)
                self.assertEqual(src.outsig, [expected])
                self.assertEqual(sink.insig, [expected])

    def test_size_one_vector_wire_is_a_scalar(self):
        src, sink = self._source_to_sink(np.array([5.0]))
        self.assertIs(src.outsig[0].type, np.float64)
        self.assertIsNone(src.outsig[0].shape)

    def test_input_signature_is_the_parents_output_signature(self):
        # an input port is bound to the producer's own slot, so there is one
        # record per wire and the two views cannot disagree
        bd = self.sim.blockdiagram()
        src = bd.CONSTANT(np.zeros(3))
        a = bd.NULL(1)
        b = bd.NULL(1)
        bd.connect(src, a, b)  # fan-out
        bd.compile(verbose=False)
        self.assertIs(a.insig[0], src.outsig[0])
        self.assertIs(b.insig[0], src.outsig[0])

    def test_sinks_have_input_signatures(self):
        _, sink = self._source_to_sink(np.zeros(4))
        self.assertEqual(sink.insig, [Signature(np.ndarray, (4,), np.dtype(float))])
        self.assertEqual(sink.outsig, [])

    def test_through_blocks(self):
        bd = self.sim.blockdiagram()
        scalar = bd.CONSTANT(2.0)
        vector = bd.CONSTANT(np.ones(3))
        g1 = bd.GAIN(3)
        g2 = bd.GAIN(3)
        bd.connect(scalar, g1)
        bd.connect(vector, g2)
        bd.connect(g1, bd.NULL(1))
        bd.connect(g2, bd.NULL(1))
        bd.compile(verbose=False)
        self.assertIs(g1.outsig[0].type, float)
        self.assertEqual(g2.outsig[0], Signature(np.ndarray, (3,), np.dtype(float)))

    def test_state_vector_of_size_one_is_a_scalar(self):
        bd = self.sim.blockdiagram()
        integrator = bd.INTEGRATOR(x0=0.0)
        bd.connect(bd.CONSTANT(1.0), integrator)
        bd.connect(integrator, bd.NULL(1))
        bd.compile(verbose=False)
        sig = integrator.outsig[0]
        self.assertIsNone(sig.shape)
        self.assertNotIn(sig.type, (np.ndarray, list))

    def test_not_recorded_without_the_trial_evaluation(self):
        bd = self.sim.blockdiagram()
        src = bd.CONSTANT(1)
        sink = bd.NULL(1)
        bd.connect(src, sink)
        bd.compile(evaluate=False, verbose=False)
        self.assertEqual(src.outsig, [None])
        self.assertEqual(sink.insig, [None])

    def test_signatures_survive_further_evaluations(self):
        src, sink = self._source_to_sink(np.zeros(3))
        before = src.outsig[0]
        bd = src._bd
        bd.evaluate(bd.initial_state_map(), 0.0)
        self.assertIs(src.outsig[0], before)
        self.assertIs(sink.insig[0], before)

    def test_reset_does_not_clear_signatures(self):
        src, sink = self._source_to_sink(np.zeros(3))
        before = src.outsig[0]
        src._bd.reset()
        self.assertIs(src.outsig[0], before)


class ReportTest(unittest.TestCase):
    """The reports show each wire's type from its signature."""

    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False)

    def _diagram(self, **compile_args):
        bd = self.sim.blockdiagram()
        vec = Emit(np.zeros(3), bd=bd)
        word = Emit("hello", bd=bd)
        bd.connect(vec, bd.NULL(1))
        bd.connect(word, bd.NULL(1))
        bd.compile(verbose=False, **compile_args)
        return bd

    def _printed(self, method):
        buf = io.StringIO()
        with redirect_stdout(buf):
            method()
        return buf.getvalue()

    def test_summary_shows_signatures(self):
        bd = self._diagram()
        text = self._printed(bd.report_summary)
        self.assertIn("ndarray(3,) float64", text)
        self.assertIn("str", text)

    def test_wire_table_shows_signatures(self):
        bd = self._diagram()
        text = self._printed(bd.report_lists)
        self.assertIn("ndarray(3,) float64", text)
        self.assertIn("str", text)

    def test_reports_agree_with_the_signatures(self):
        bd = self._diagram()
        for b in bd.blocklist:
            for sig in b.insig:
                self.assertIn(str(sig), self._printed(bd.report_summary))
                self.assertIn(str(sig), self._printed(bd.report_lists))

    def test_unobserved_wires_are_marked_unknown(self):
        # no trial evaluation, so no signatures: the reports must still work
        bd = self._diagram(evaluate=False)
        for method in (bd.report_summary, bd.report_lists):
            self.assertIn("?", self._printed(method))

    def test_report_does_not_read_the_live_values(self):
        # the signature is what was observed at compile time, whatever the
        # wire carries afterwards
        bd = self._diagram()
        for b in bd.blocklist:
            for slot in b._outport_slots:
                slot.value = None
        self.assertIn("ndarray(3,) float64", self._printed(bd.report_summary))


class ConfigureTest(unittest.TestCase):
    """configure() runs once per run, after reset() and before start()."""

    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False)

    def _diagram(self, fail=False):
        calls, seen = [], {}

        class Probe(FunctionBlock):
            nin = 1
            nout = 1

            def output(self, t, inputs, x):
                return [inputs[0]]

            def reset(self):
                calls.append("reset")

            def configure(self):
                calls.append("configure")
                if fail:
                    raise ValueError("cannot configure")
                seen["insig"] = self.insig
                seen["outsig"] = self.outsig

            def start(self, simstate):
                calls.append("start")

        bd = self.sim.blockdiagram()
        probe = Probe(bd=bd)
        bd.connect(Emit(np.zeros(3), bd=bd), probe)
        bd.connect(probe, bd.NULL(1))
        bd.compile(verbose=False)
        return bd, probe, calls, seen

    def test_default_is_a_no_op(self):
        bd = self.sim.blockdiagram()
        block = bd.GAIN(2)
        self.assertIsNone(block.configure())

    def test_compile_does_not_configure(self):
        bd, probe, calls, seen = self._diagram()
        self.assertEqual(calls, [])

    def test_order_within_a_run(self):
        bd, probe, calls, seen = self._diagram()
        self.sim.run(bd, T=0.1)
        self.assertEqual(calls, ["reset", "configure", "start"])
        calls.clear()
        self.sim.run(bd, T=0.1)  # every run configures again
        self.assertEqual(calls, ["reset", "configure", "start"])

    def test_configure_sees_the_signatures(self):
        bd, probe, calls, seen = self._diagram()
        self.sim.run(bd, T=0.1)
        expected = [Signature(np.ndarray, (3,), np.dtype(float))]
        self.assertEqual(seen["insig"], expected)
        self.assertEqual(seen["outsig"], expected)

    def test_error_in_configure_names_the_block(self):
        bd, probe, calls, seen = self._diagram(fail=True)
        buf = io.StringIO()
        with redirect_stdout(buf), self.assertRaises(RuntimeError):
            self.sim.run(bd, T=0.1)
        self.assertIn(probe.name, buf.getvalue())
        self.assertIn("configure", buf.getvalue())
        self.assertIn("cannot configure", buf.getvalue())
        self.assertNotIn("start", calls)  # no block was started


if __name__ == "__main__":
    unittest.main()
