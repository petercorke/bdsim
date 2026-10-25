"""Regression tests for the generated JupyterLite install cell."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ADAPT_SCRIPT = REPO_ROOT / "docs" / "lite" / "adapt_nb.py"


class TestJupyterLiteAdapter(unittest.TestCase):
    def test_bootstrap_installs_runtime_dependencies_before_no_deps_packages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            lite_dir = temp_root / "docs" / "lite"
            notebooks_dir = temp_root / "docs" / "notebooks"
            lite_dir.mkdir(parents=True)
            notebooks_dir.mkdir(parents=True)

            notebook_path = notebooks_dir / "bouncing-ball.ipynb"
            notebook_path.write_text(
                json.dumps(
                    {
                        "cells": [
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "id": "example",
                                "metadata": {},
                                "outputs": [],
                                "source": ["print('ready')\n"],
                            }
                        ],
                        "metadata": {},
                        "nbformat": 4,
                        "nbformat_minor": 5,
                    }
                ),
                encoding="utf-8",
            )

            for _ in range(2):
                subprocess.run(
                    [sys.executable, str(ADAPT_SCRIPT)],
                    cwd=lite_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                )

            adapted = json.loads(notebook_path.read_text(encoding="utf-8"))
            install_cells = [
                cell for cell in adapted["cells"] if cell.get("id") == "lite-install"
            ]
            self.assertEqual(len(install_cells), 1)

            source = "".join(install_cells[0]["source"])
            runtime_install = source.index("await piplite.install(")
            spatialmath_install = source.index(
                "await piplite.install('spatialmath-python', deps=False)"
            )
            bdsim_install = source.index("await piplite.install('bdsim', deps=False)")
            self.assertLess(runtime_install, spatialmath_install)
            self.assertLess(spatialmath_install, bdsim_install)
            for package in (
                "numpy",
                "scipy",
                "matplotlib",
                "ansitable",
                "progress",
                "typing_extensions",
            ):
                self.assertIn(f"'{package}'", source[:spatialmath_install])


if __name__ == "__main__":
    unittest.main()
