import os
import sys


def pytest_configure(config):
    """
    Strip pytest's own arguments from sys.argv before any test code runs.

    Without this, any code that calls argparse.parse_known_args() during
    import or __init__ (e.g. BDSim()) chokes on pytest flags like
    -s, -v, --tb=short, etc.
    """
    sys.argv = sys.argv[:1]

    # Force a non-interactive matplotlib backend for all in-process tests so
    # that simulation runs don't open GUI windows or block on plt.show().
    os.environ.setdefault("MPLBACKEND", "Agg")
