"""Helpers for running module-mapped tests from ``__main__`` guards."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


_MODULE_TEST_OVERRIDES: dict[str, str] = {
    "__init__": "bdsim",
    "_blockdiagram_mixin": "blockdiagram",
    "block": "blockdiagram",
    "block_types": "graphics",
    "connect": "blockdiagram",
    "run_context": "run_sim",
    "run_realtime": "run_sim",
}


def run_module_test(module_file: str, test_stem: str | None = None) -> int:
    """Run the pytest module corresponding to a source module file.

    Returns the pytest process exit code. If no test file exists, returns 0.
    """
    module_path = Path(module_file).resolve()
    repo_root = module_path.parents[2]
    stem = test_stem or _MODULE_TEST_OVERRIDES.get(module_path.stem, module_path.stem)
    test_file = repo_root / "tests" / f"test_{stem}.py"

    if not test_file.exists():
        print(f"no mapped test file found for module {module_path.stem}: {test_file}")
        return 0

    cmd = [sys.executable, "-m", "pytest", "-q", str(test_file)]
    return subprocess.call(cmd, cwd=str(repo_root))
