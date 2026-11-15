#!/usr/bin/env python3
"""Smoke test that executes Jupyter notebooks in docs/notebooks."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

NOTEBOOKS_DIR = Path(__file__).resolve().parents[1] / "docs" / "notebooks"
NOTEBOOK_FILES = sorted(path.name for path in NOTEBOOKS_DIR.glob("*.ipynb"))

# Notebooks skipped from smoke execution.
SKIP_NOTEBOOKS: dict[str, str] = {
    "index.ipynb": "index-only notebook, not meant to be executed standalone",
    "advanced-topics.ipynb": (
        "records a movie and then displays it; with graphics off, as here, there is "
        "no movie, and a movie needs ffmpeg"
    ),
}

# Keep this list intentionally small and revisit when notebook/runtime fixes land.
# When removing an entry, run just this module to validate:
#   pytest -vv -s tests/test_notebooks_smoke.py


class NotebooksSmokeTest(unittest.TestCase):
    """Execute every notebook in docs/notebooks as a smoke test via nbconvert."""

    def test_notebooks_run(self):
        # nbconvert --execute re-runs the notebook in-place (to a temp output)
        # and returns non-zero if any cell raises an exception.
        try:
            import nbconvert  # noqa: F401
        except ImportError:
            self.skipTest("nbconvert is not installed; skipping notebook smoke tests")

        # icra2026 uses robotics-toolbox-python, which is not a bdsim dependency
        skip = dict(SKIP_NOTEBOOKS)
        if importlib.util.find_spec("roboticstoolbox") is None:
            skip["icra2026.ipynb"] = (
                "needs roboticstoolbox-python, which is not installed"
            )

        env = os.environ.copy()
        # Force a headless backend so plots do not require an interactive display,
        # and turn graphics off in bdsim, which is faster: nothing is drawn.
        env["MPLBACKEND"] = "Agg"
        env["BDSIM_NO_GRAPHICS"] = "1"

        # nbconvert always writes the executed notebook, and adds .ipynb to the output
        # name, so it cannot be sent to os.devnull: give it a directory to throw away
        outdir = tempfile.TemporaryDirectory()
        self.addCleanup(outdir.cleanup)

        for notebook in NOTEBOOK_FILES:
            if notebook in skip:
                continue

            with self.subTest(notebook=notebook):
                notebook_path = NOTEBOOKS_DIR / notebook
                try:
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "nbconvert",
                            "--to",
                            "notebook",
                            "--execute",
                            "--ExecutePreprocessor.timeout=120",
                            "--output-dir",
                            outdir.name,
                            str(notebook_path),
                        ],
                        cwd=str(NOTEBOOKS_DIR),
                        env=env,
                        text=True,
                        capture_output=True,
                        timeout=130,
                    )
                except subprocess.TimeoutExpired as exc:
                    self.fail(f"{notebook} timed out after {exc.timeout}s")

                if result.returncode != 0:
                    self.fail(
                        "\n".join(
                            [
                                f"{notebook} failed with exit code {result.returncode}",
                                "stdout:",
                                result.stdout,
                                "stderr:",
                                result.stderr,
                            ]
                        )
                    )


if __name__ == "__main__":
    unittest.main()
