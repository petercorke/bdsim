"""Compatibility package exposing the top-level bdedit package as bdsim.bdedit."""

from importlib import import_module
from pathlib import Path

_BD_EDIT_PATH = Path(__file__).resolve().parents[2] / "bdedit"

# Route submodule imports like ``bdsim.bdedit.interface_manager`` to the
# existing editor sources under ``src/bdedit``.
__path__ = [str(_BD_EDIT_PATH)]


def main(*args, **kwargs):
    return import_module("bdedit.bdedit").main(*args, **kwargs)
