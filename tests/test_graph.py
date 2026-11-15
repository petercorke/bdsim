"""Tests for the graph output methods of BlockDiagram (src/bdsim/_graph.py)."""

import io
import json
import unittest

import bdsim
from bdsim._graph import GraphMixin
from bdsim.blockdiagram import BlockDiagram


def make_diagram() -> BlockDiagram:
    """step -> gain -> null, compiled."""
    bd = bdsim.BDSim(sysargs=False).blockdiagram()
    step = bd.STEP(1, name="step")
    gain = bd.GAIN(2, name="gain")
    null = bd.NULL(name="null")
    bd.connect(step, gain)
    bd.connect(gain, null)
    bd.compile(verbose=False)
    return bd


class GraphTest(unittest.TestCase):
    def test_methods_come_from_the_mixin(self):
        self.assertTrue(issubclass(BlockDiagram, GraphMixin))
        for name in ("graph", "dotfile", "schedule_dotfile", "showgraph"):
            self.assertIs(getattr(BlockDiagram, name), getattr(GraphMixin, name))

    def test_dot(self):
        text = make_diagram().graph(format="dot")
        self.assertTrue(text.startswith("digraph G {"))
        self.assertIn('"step" -> "gain"', text)
        self.assertIn('"gain" -> "null"', text)

    def test_graph_dot_matches_dotfile(self):
        bd = make_diagram()
        f = io.StringIO()
        bd.dotfile(f)
        self.assertEqual(bd.graph(format="dot"), f.getvalue())

    def test_mermaid(self):
        text = make_diagram().graph(format="mermaid")
        self.assertTrue(text.startswith("flowchart LR"))
        self.assertIn('b0["step"]', text)
        self.assertIn("b0 --> b1", text)
        self.assertIn("b1 --> b2", text)

    def test_mermaid_fenced(self):
        text = make_diagram().graph(format="mermaid_fenced")
        self.assertTrue(text.startswith("```mermaid"))
        self.assertIn("flowchart LR", text)

    def test_graphml(self):
        text = make_diagram().graph(format="graphml")
        self.assertTrue(text.startswith("<?xml"))
        self.assertTrue(text.rstrip().endswith("</graphml>"))
        self.assertEqual(text.count("<node "), 3)
        self.assertEqual(text.count("<edge "), 2)

    def test_elk_is_json_with_the_right_graph(self):
        d = json.loads(make_diagram().graph(format="elk"))
        labels = [c["labels"][0]["text"] for c in d["children"]]
        self.assertEqual(labels, ["step", "gain", "null"])
        self.assertEqual(len(d["edges"]), 2)

    def test_unknown_format(self):
        with self.assertRaisesRegex(ValueError, "unsupported graph format"):
            make_diagram().graph(format="nope")

    def test_graph_writes_a_file(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "g.mmd"
            text = make_diagram().graph(format="mermaid", filename=str(path))
            self.assertEqual(path.read_text(encoding="utf-8"), text)

    def test_schedule_dotfile(self):
        f = io.StringIO()
        make_diagram().schedule_dotfile(f)
        self.assertIn("digraph", f.getvalue())
        self.assertTrue(f.getvalue().rstrip().endswith("}"))


if __name__ == "__main__":
    unittest.main()
