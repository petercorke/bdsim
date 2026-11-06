"""Tests for bin/stubgen.py, which generates the typing-only block factory stubs."""

import subprocess  # nosec B404
import sys
import tempfile
import unittest
from pathlib import Path

from bdsim.bin import stubgen

HAVE_RUFF = (
    subprocess.run(  # nosec B603  # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit.dangerous-subprocess-use-audit
        [sys.executable, "-m", "ruff", "--version"], capture_output=True
    ).returncode
    == 0
)


@unittest.skipUnless(HAVE_RUFF, "stubgen formats its output with ruff")
class StubgenTest(unittest.TestCase):
    def test_committed_stubs_are_current(self):
        # the same check CI runs; fails when a block signature changed without
        # regenerating, with the diff and the regenerate command in the output
        self.assertEqual(stubgen.main(["--check"]), 0)

    def test_check_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "stubs.py"
            out.write_text("stale\n", encoding="utf-8")
            # a stale file fails the check and is left alone; writing fixes it
            self.assertEqual(
                stubgen.main(["--check", "--package", "bdsim", "--out", str(out)]), 1
            )
            self.assertEqual(out.read_text(encoding="utf-8"), "stale\n")
            self.assertEqual(stubgen.main(["--package", "bdsim", "--out", str(out)]), 0)
            self.assertEqual(
                stubgen.main(["--check", "--package", "bdsim", "--out", str(out)]), 0
            )

    def test_own_stubs_hold_only_bdsim_blocks(self):
        text = stubgen.generate("bdsim", "BlockFactoryStubs", "cmd")
        self.assertIn("def GAIN(", text)
        # per-block comments name the defining module
        self.assertNotIn("# roboticstoolbox.", text)
        self.assertNotIn("# machinevisiontoolbox.", text)

    def test_unknown_package_is_an_error(self):
        with self.assertRaises(RuntimeError):
            stubgen.generate("no_such_package", "NoStubs", "cmd")

    def test_package_requires_out(self):
        with self.assertRaises(SystemExit):
            stubgen.main(["--package", "roboticstoolbox"])

    def test_generated_text_is_valid_python(self):
        compile(stubgen.generate("bdsim", "BlockFactoryStubs", "cmd"), "stubs", "exec")


if __name__ == "__main__":
    unittest.main()
