#!/usr/bin/env python3
"""Golden-master regression tests: do the examples still produce the same numbers?

Each working example is run as a subprocess through the real command line, with
``--no-graphics --dt 0.1 --npz FILE``, and its results are compared with the
reference in ``tests/golden/<example>.npz``.

* ``--dt 0.1`` puts the results on a fixed grid, so they do not depend on the
  integrator's own step choices.
* A float result must agree to ``rtol=1e-5, atol=1e-6``, the scale of the solver's
  own default accuracy; everything else (names, event counts) must be equal.
  Tighter than that the test fails on another platform: on Windows the van der Pol
  oscillator differs by 7e-8 in two values, from floating-point differences that
  the adaptive step size control amplifies.  A change that matters is far bigger.
  Solver counts and wall time are not compared.
* ``pytest --update-golden`` rewrites the references from the current results.
  Do that only for a change that is meant to alter the numbers, and review it:
  the references are binary files, so describe the change in the commit message.

A golden test shows that results are *unchanged*, not that they are *correct*.
"""

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import numpy.testing as nt
import pytest

GOLDEN = Path(__file__).parent / "golden"
EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
SRC = Path(__file__).resolve().parents[1] / "src"
ARGS = ["-q", "--no-graphics", "--dt", "0.1"]

NAMES = [
    "bouncing-ball",
    "cartpole",
    "deriv",
    "eg1",
    "eg1_zoh",
    "eg1a",
    "pid",
    "vanderpol",
    "waveform",
    "test_deriv1",
    "test_deriv2",
    "test_deriv_s",
    "test_integrator",
    "test_integrator_s",
    "test_lti_tf",
    "test_lti_tf_s",
    "test_pid",
    "test_pid_s",
]

# the one solver statistic that is a property of the model, not of the solver
KEEP_STATS = {".stats/events_detected_total"}

pytestmark = pytest.mark.golden


def golden_view(data: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """What is stored and compared: the results, without timings or solver counts."""
    return {
        key: value
        for key, value in data.items()
        if not key.startswith(".stats/") or key in KEEP_STATS
    }


def run_example(name: str, outfile: Path) -> dict[str, np.ndarray]:
    env = dict(os.environ, MPLBACKEND="Agg", PYTHONPATH=str(SRC))
    result = subprocess.run(
        [sys.executable, f"{name}.py", *ARGS, "--npz", str(outfile)],
        cwd=EXAMPLES,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, f"{name}.py failed:\n{result.stderr[-2000:]}"
    with np.load(outfile, allow_pickle=False) as data:
        return golden_view({key: data[key] for key in data.files})


@pytest.mark.parametrize("name", NAMES)
def test_example_matches_golden(name, tmp_path, request):
    actual = run_example(name, tmp_path / f"{name}.npz")
    path = GOLDEN / f"{name}.npz"

    if request.config.getoption("--update-golden"):
        GOLDEN.mkdir(exist_ok=True)
        with open(path, "wb") as f:
            np.savez_compressed(f, **actual)
        return

    if not path.exists():
        pytest.fail(f"no reference for {name}: run pytest --update-golden")
    with np.load(path, allow_pickle=False) as data:
        expected = {key: data[key] for key in data.files}

    assert sorted(actual) == sorted(expected), (
        f"{name}: the set of results changed: "
        f"new {sorted(set(actual) - set(expected))}, "
        f"missing {sorted(set(expected) - set(actual))}"
    )
    for key in sorted(expected):
        got, want = actual[key], expected[key]
        assert got.shape == want.shape, (
            f"{name}: {key} has shape {got.shape}, reference {want.shape}"
        )
        if want.dtype.kind in "fc":
            nt.assert_allclose(
                got, want, rtol=1e-5, atol=1e-6, err_msg=f"{name}: {key} differs"
            )
        else:
            nt.assert_array_equal(got, want, err_msg=f"{name}: {key} differs")
