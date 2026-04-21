import os
import sys

# Force a non-interactive matplotlib backend before anything else is imported.
# This must happen at module level (not inside pytest_configure) because
# block.py imports matplotlib.pyplot at module level, which triggers backend
# selection before any hook has a chance to run.
os.environ["MPLBACKEND"] = "Agg"
import matplotlib

matplotlib.use("Agg")


def pytest_configure(config):
    """
    Strip pytest's own arguments from sys.argv before any test code runs.

    Without this, any code that calls argparse.parse_known_args() during
    import or __init__ (e.g. BDSim()) chokes on pytest flags like
    -s, -v, --tb=short, etc.
    """
    sys.argv = sys.argv[:1]
