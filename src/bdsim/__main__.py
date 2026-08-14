"""Command-line entry point for bdsim.

Supports ``python -m bdsim`` and the ``bdsim`` console script. No diagram
is built here, so introspection flags handled during :class:`BDSim`
construction -- such as ``--blocks`` -- have nothing further to run and
behave as print-and-exit.
"""

from __future__ import annotations

import sys

from bdsim import BDSim


def main() -> None:
    BDSim(sysargs=sys.argv[1:])


if __name__ == "__main__":
    main()
