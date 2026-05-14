"""Lazy exports for block classes.

This package avoids importing every block family module during package import,
which keeps submodule imports such as `bdsim.blocks.io_base` cheap while still
supporting `from bdsim.blocks import Gain` and `from bdsim.blocks import *`.
"""

from __future__ import annotations

import ast
import importlib
from functools import lru_cache
from pathlib import Path
from typing import Any

_BLOCKS_DIR = Path(__file__).resolve().parent
_SKIP_MODULES = {"__init__", "io_base"}


@lru_cache(maxsize=1)
def _export_map() -> dict[str, str]:
    # Build a symbol -> module map by parsing source files, not importing them.
    # This keeps package import cheap and avoids importing optional deps until
    # a concrete block class is actually requested.
    exports: dict[str, str] = {}

    for path in sorted(_BLOCKS_DIR.glob("*.py")):
        module_stem = path.stem
        if module_stem.startswith("_") or module_stem in _SKIP_MODULES:
            continue

        tree = ast.parse(path.read_text(), filename=str(path))
        module_name = f"{__name__}.{module_stem}"

        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if node.name.startswith("_") or node.name.endswith("Block"):
                continue
            exports.setdefault(node.name, module_name)

    return exports


def __getattr__(name: str) -> Any:
    # __all__ is served lazily here so that `from bdsim.blocks import *` works
    # without triggering the AST scan at package import time.
    if name == "__all__":
        value = sorted(_export_map().keys())
        globals()["__all__"] = value
        return value

    module_name = _export_map().get(name)
    if module_name is None:
        raise AttributeError(name)

    module = importlib.import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    # Introspection may trigger a one-time export map build; this is acceptable
    # because __dir__ is debugging/editor assistance, not the hot startup path.
    return sorted(list(globals().keys()) + list(_export_map().keys()))


url = "https://petercorke.github.io/bdsim/" + __package__
