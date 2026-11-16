#!/usr/bin/env python3
"""Smoke test that executes Jupyter notebooks in docs/notebooks.

Each notebook is its own test, so a failure or timeout names the notebook, and a slow
shared CI runner is judged per notebook, not on the total.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

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


# The CI-wide limit is 50 s (``--timeout=50`` in ci.yml), too tight for a kernel
# start plus a simulation on a loaded shared runner.  This is above the 130 s
# subprocess limit below, so that limit fires first and says which notebook.
@pytest.mark.timeout(300, method="thread")
@pytest.mark.parametrize("notebook", NOTEBOOK_FILES)
def test_notebook_runs(notebook: str, tmp_path: Path) -> None:
    """Execute one notebook in docs/notebooks via nbconvert.

    nbconvert --execute returns non-zero if any cell raises an exception.
    """
    pytest.importorskip("nbconvert")

    skip = dict(SKIP_NOTEBOOKS)
    # icra2026 uses robotics-toolbox-python, which is not a bdsim dependency
    if importlib.util.find_spec("roboticstoolbox") is None:
        skip["icra2026.ipynb"] = "needs roboticstoolbox-python, which is not installed"
    if notebook in skip:
        pytest.skip(skip[notebook])

    env = os.environ.copy()
    # Force a headless backend so plots do not require an interactive display,
    # and turn graphics off in bdsim, which is faster: nothing is drawn.
    env["MPLBACKEND"] = "Agg"
    env["BDSIM_NO_GRAPHICS"] = "1"

    # nbconvert always writes the executed notebook, so give it a directory to
    # throw away (it adds .ipynb to the name, so it cannot be os.devnull)
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
                str(tmp_path),
                str(NOTEBOOKS_DIR / notebook),
            ],
            cwd=str(NOTEBOOKS_DIR),
            env=env,
            text=True,
            capture_output=True,
            timeout=130,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.fail(f"{notebook} timed out after {exc.timeout}s")

    if result.returncode != 0:
        pytest.fail(
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
