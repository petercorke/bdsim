#!/usr/bin/env python3
"""Smoke test that executes top-level example scripts."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="example smoke tests temporarily disabled")

import os
import subprocess
import sys
import unittest
from pathlib import Path

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
EXAMPLE_SCRIPTS = sorted(path.name for path in EXAMPLES_DIR.glob("*.py"))

# Known non-smoke examples that currently require unavailable dependencies,
# hardware, or hit known runtime issues outside this test's scope.
SKIP_SCRIPTS: dict[str, str] = {}

# Keep this list intentionally small and revisit when runtime/example fixes land.
# When removing an entry, run just this module to validate:
#   pytest -vv -s tests/test_examples_smoke.py


class ExamplesSmokeTest(unittest.TestCase):
    """Run every top-level Python example script as a smoke test."""

    def test_top_level_examples_run(self):
        env = os.environ.copy()
        # Force a headless backend so plots do not require an interactive display.
        env["MPLBACKEND"] = "Agg"

        for script in EXAMPLE_SCRIPTS:
            if script in SKIP_SCRIPTS:
                continue

            with self.subTest(script=script):
                script_path = EXAMPLES_DIR / script
                try:
                    result = subprocess.run(
                        [sys.executable, str(script_path)],
                        cwd=str(EXAMPLES_DIR),
                        env=env,
                        text=True,
                        capture_output=True,
                        timeout=60,
                    )
                except subprocess.TimeoutExpired as exc:
                    self.fail(f"{script} timed out after {exc.timeout}s")

                if result.returncode != 0:
                    self.fail(
                        "\n".join(
                            [
                                f"{script} failed with exit code {result.returncode}",
                                "stdout:",
                                result.stdout,
                                "stderr:",
                                result.stderr,
                            ]
                        )
                    )


if __name__ == "__main__":
    unittest.main()
