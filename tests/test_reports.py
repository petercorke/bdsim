"""The report methods of BlockDiagram live in src/bdsim/_reports.py."""

import contextlib
import io
import unittest

import bdsim
from bdsim._reports import ReportMixin
from bdsim.blockdiagram import BlockDiagram


class ReportMixinTest(unittest.TestCase):
    def test_methods_come_from_the_mixin(self):
        self.assertTrue(issubclass(BlockDiagram, ReportMixin))
        for name in (
            "report",
            "report_summary",
            "report_lists",
            "report_subsystems",
            "report_params",
            "report_schedule",
            "blockvalues",
        ):
            self.assertIs(getattr(BlockDiagram, name), getattr(ReportMixin, name))

    def test_report_names_the_blocks(self):
        bd = bdsim.BDSim(sysargs=False).blockdiagram()
        bd.connect(bd.STEP(1, name="step"), bd.NULL(name="null"))
        bd.compile(verbose=False)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            bd.report_lists()
        self.assertIn("step", out.getvalue())
        self.assertIn("null", out.getvalue())


class LsTest(unittest.TestCase):
    """ls() used to loop forever: it joined a Block, which iterates through __getitem__."""

    @staticmethod
    def ls(bd) -> list[str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            bd.ls()
        return out.getvalue().splitlines()

    def test_groups_names_by_block_type_in_order(self):
        bd = bdsim.BDSim(sysargs=False).blockdiagram()
        step = bd.STEP(1, name="s")
        g1 = bd.GAIN(2)
        g2 = bd.GAIN(3, name="mine")
        bd.connect(step, g1)
        bd.connect(g1, g2)
        bd.connect(g2, bd.NULL())
        lines = self.ls(bd)
        self.assertEqual(
            [line.split(":")[0].strip() for line in lines], ["step", "gain", "null"]
        )
        self.assertEqual(lines[1].split(":", 1)[1].strip(), "gain.0, mine")

    def test_empty_diagram(self):
        self.assertEqual(self.ls(bdsim.BDSim(sysargs=False).blockdiagram()), [])

    def test_after_compile(self):
        bd = bdsim.BDSim(sysargs=False).blockdiagram()
        bd.connect(bd.STEP(1), bd.NULL())
        bd.compile(verbose=False)
        self.assertEqual(len(self.ls(bd)), 2)


if __name__ == "__main__":
    unittest.main()


class ReportSummaryImplicitTest(unittest.TestCase):
    """Implicit blocks (names starting with _) come last, or are hidden."""

    @staticmethod
    def _diagram():
        bd = bdsim.BDSim(sysargs=False).blockdiagram()
        x = bd.STEP(1, name="zstep")
        # the 3 * x and + 1 create implicit _gain and _const/_sum blocks
        y = 3 * x + 1
        bd.connect(y, bd.NULL(name="anull"))
        bd.compile(verbose=False)
        return bd

    @staticmethod
    def _rows(bd, **kwargs):
        """Names in the first column, in order."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            bd.report_summary(**kwargs)
        names = []
        for line in out.getvalue().splitlines():
            if line.startswith("│"):
                cell = line.split("│")[1].strip().rstrip("@")
                if cell and cell != "block":
                    names.append(cell)
        return names

    def test_implicit_blocks_exist(self):
        names = self._rows(self._diagram())
        self.assertTrue(any(n.startswith("_") for n in names))

    def test_implicit_last_by_name(self):
        names = self._rows(self._diagram(), sortby="name")
        flags = [n.startswith("_") for n in names]
        self.assertEqual(flags, sorted(flags))
        explicit = [n for n in names if not n.startswith("_")]
        implicit = [n for n in names if n.startswith("_")]
        self.assertEqual(explicit, sorted(explicit))
        self.assertEqual(implicit, sorted(implicit))

    def test_implicit_last_by_type(self):
        bd = self._diagram()
        names = self._rows(bd, sortby="type")
        flags = [n.startswith("_") for n in names]
        self.assertEqual(flags, sorted(flags))
        types = [bd.blocknames[n].type for n in names if n in bd.blocknames]
        n_explicit = flags.count(False)
        self.assertEqual(types[:n_explicit], sorted(types[:n_explicit]))
        self.assertEqual(types[n_explicit:], sorted(types[n_explicit:]))

    def test_implicit_false_hides_them(self):
        for sortby in ("name", "type"):
            names = self._rows(self._diagram(), sortby=sortby, implicit=False)
            self.assertEqual(sorted(names), ["anull", "zstep"])

    def test_bad_sortby(self):
        with self.assertRaises(ValueError):
            self._diagram().report_summary(sortby="size")
