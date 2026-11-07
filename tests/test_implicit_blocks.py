"""Blocks that bdsim makes for an expression, such as ``3 * x + 1``.

Their names are ``_gain.0``, ``_const.0`` and so on: a counter, and nothing that can
change, so that ``bd["_gain.0"]`` and ``--set _gain.0:K=3`` can find them.  The value
that makes one recognizable in a report is in its label, and is the current value.
"""

import contextlib
import io
import unittest

import numpy as np

import bdsim


def sim():
    return bdsim.BDSim(
        sysargs=False, banner=False, quiet=True, progress=False, graphics=False
    )


def captured(function, *args, **kwargs) -> str:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        function(*args, **kwargs)
    return out.getvalue()


class NamesTest(unittest.TestCase):
    def test_the_name_is_a_counter_and_not_the_value(self):
        bd = sim().blockdiagram()
        x = bd.STEP(1, name="x")
        y = 3 * x + 1
        z = (y**2) * np.array([[1.0, 2.0]])
        names = [b.name for b in bd.blocklist]
        self.assertIn("_gain.0", names)
        self.assertIn("_const.0", names)
        self.assertIn("_pow.0", names)
        self.assertIn("_gain.1", names)
        self.assertIn("_sum.0", names)
        self.assertFalse([n for n in names if "(" in n or "<" in n or " " in n])

    def test_a_block_is_found_by_its_name_and_can_be_changed(self):
        s = sim()
        bd = s.blockdiagram()
        x = bd.STEP(1, name="x")
        bd.connect(3 * x, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        self.assertEqual(bd["_gain.0"].K, 3)
        bd["_gain.0"].K = 5
        self.assertEqual(bd["_gain.0"].K, 5)
        bd["_gain.0"].set_param("K", 7)
        self.assertEqual(bd.blocknames["_gain.0"].K, 7)

    def test_set_on_the_command_line_and_in_options_reaches_it(self):
        s = bdsim.BDSim(
            sysargs=False,
            banner=False,
            quiet=True,
            progress=False,
            graphics=False,
            setparam=["_gain.0:K=4"],
        )
        bd = s.blockdiagram()
        bd.connect(3 * bd.STEP(1, name="x"), bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        s.update_parameters(bd)
        self.assertEqual(bd["_gain.0"].K, 4)

    def test_a_name_the_user_gives_is_not_changed(self):
        bd = sim().blockdiagram()
        gain = bd.GAIN(2, name="lqr")
        self.assertEqual(gain.name, "lqr")
        self.assertEqual(gain.label, "lqr")
        self.assertFalse(gain.implicit)


class ImplicitTest(unittest.TestCase):
    def test_a_leading_underscore_is_private(self):
        bd = sim().blockdiagram()
        self.assertTrue(bd.GAIN(1, name="_helper").implicit)
        self.assertFalse(bd.GAIN(1, name="helper").implicit)
        self.assertFalse(bd.GAIN(1).implicit)  # gain.0

    def test_all_the_blocks_bdsim_makes_are_implicit(self):
        bd = sim().blockdiagram()
        x = bd.STEP(1, name="x")
        y = -((3 * x + 1) ** 2) / 4
        bd.connect(y, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        made = [b for b in bd.blocklist if b.name.startswith("_")]
        self.assertGreaterEqual(len(made), 4)
        self.assertTrue(all(b.implicit for b in made))
        self.assertFalse(any(b.implicit for b in bd.blocklist if b not in made))

    def test_a_block_in_a_subsystem_is_implicit_by_the_end_of_its_name(self):
        s = sim()
        inner = s.blockdiagram(name="inner")
        i, o = inner.INPORT(1), inner.OUTPORT(1)
        inner.connect(i * 3, o)
        bd = s.blockdiagram()
        sub = bd.SUBSYSTEM(inner, name="sub")
        bd.connect(bd.CONSTANT(1.0, name="c"), sub)
        bd.connect(sub, bd.NULL(1, name="n"))
        bd.compile(verbose=False)
        self.assertIn("sub/_gain.0", bd.blocknames)
        self.assertTrue(bd["sub/_gain.0"].implicit)
        out = captured(bd.report_summary, implicit=False)
        rows = [
            line.split("\u2502")[1].strip()
            for line in out.splitlines()
            if line.startswith("\u2502")
        ]
        # it is not a row of its own, though it is still the source of "n"
        self.assertEqual(rows[1:], ["c", "n"])

    def test_an_implicit_constant_is_not_a_default_input_of_functions(self):
        bd = sim().blockdiagram()
        x = bd.STEP(1, name="demand")
        bd.connect(x + 1.0, bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        self.assertEqual(bd.functions(full=True).uindex.names, ["demand"])


class LabelTest(unittest.TestCase):
    def labels(self, expr) -> dict[str, str]:
        bd = sim().blockdiagram()
        x = bd.STEP(1, name="x")
        bd.connect(expr(bd, x), bd.NULL(1, name="y"))
        return {b.name: b.label for b in bd.blocklist}

    def test_a_scalar_is_shown_to_three_figures(self):
        labels = self.labels(lambda bd, x: 3.14159 * x)
        self.assertEqual(labels["_gain.0"], "_gain.0(3.14)")

    def test_constant_and_power(self):
        labels = self.labels(lambda bd, x: (x + 2) ** 3)
        self.assertEqual(labels["_const.0"], "_const.0(2)")
        self.assertEqual(labels["_pow.0"], "_pow.0(3)")

    def test_a_small_array_is_on_one_line(self):
        labels = self.labels(lambda bd, x: np.array([[1.0, 2.0, 3.0]]) * x)
        text = labels["_gain.0"]
        self.assertTrue(text.startswith("_gain.0([["), text)
        self.assertNotIn("\n", text)

    def test_a_large_array_is_described(self):
        labels = self.labels(lambda bd, x: np.eye(6) * x)
        self.assertEqual(labels["_gain.0"], "_gain.0<float64 6x6>")

    def test_the_label_follows_the_value(self):
        bd = sim().blockdiagram()
        bd.connect(3 * bd.STEP(1, name="x"), bd.NULL(1, name="y"))
        gain = bd["_gain.0"]
        self.assertEqual(gain.label, "_gain.0(3)")
        gain.set_param("K", 5)
        self.assertEqual(gain.label, "_gain.0(5)")
        self.assertEqual(gain.name, "_gain.0")  # the identity does not change

    def test_a_private_block_of_the_users_has_no_value_in_its_label(self):
        bd = sim().blockdiagram()
        self.assertEqual(bd.GAIN(2, name="_mine").label, "_mine(2)")
        self.assertEqual(bd.SUM("++", name="_total").label, "_total")


class OutputTest(unittest.TestCase):
    @staticmethod
    def diagram():
        bd = sim().blockdiagram()
        bd.connect(3 * bd.STEP(1, name="x"), bd.NULL(1, name="y"))
        bd.compile(verbose=False)
        return bd

    def test_the_report_shows_the_label(self):
        bd = self.diagram()
        self.assertIn("_gain.0(3)", captured(bd.report))
        self.assertIn("_gain.0(3)", captured(bd.report_summary))

    def test_the_report_follows_a_changed_value(self):
        bd = self.diagram()
        bd["_gain.0"].K = 9
        out = captured(bd.report)
        self.assertIn("_gain.0(9)", out)
        self.assertNotIn("_gain.0(3)", out)

    def test_the_parameter_table_has_the_name_that_set_wants(self):
        out = captured(self.diagram().report_params)
        self.assertIn("_gain.0:K", out)
        self.assertNotIn("_gain.0(", out)

    def test_the_dot_file_has_the_name_as_the_node_and_the_value_as_its_label(self):
        bd = self.diagram()
        dot = io.StringIO()
        bd.dotfile(dot)
        text = dot.getvalue()
        self.assertIn('"_gain.0" -> ', text)
        self.assertIn('"_gain.0" [', text)
        self.assertIn('label="_gain.0(3)"', text)


if __name__ == "__main__":
    unittest.main()
