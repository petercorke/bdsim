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
