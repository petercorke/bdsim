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


if __name__ == "__main__":
    unittest.main()
