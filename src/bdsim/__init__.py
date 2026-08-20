"""bdsim package exports.

Set BDSIM_IMPORT_TIMING=1 to print per-symbol lazy import timings during
`import bdsim` and subsequent first access of exported symbols.
"""

from .run_sim import *
from .run_realtime import *
from .blockdiagram import *
from .blockdiagram import bdload
from .components import *

# from .block_types import GraphicsBlock
# from .blockdiagram import bdload
# from .bin.bdrun import bdrun


# from __future__ import annotations

# import importlib
# import os
# import time
# from typing import Any


# def _env_true(name: str) -> bool:
#     return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


# _IMPORT_TIMING = _env_true("BDSIM_IMPORT_TIMING")
# _IMPORT_T0 = time.perf_counter() if _IMPORT_TIMING else 0.0

# ===
# # Public package-level exports. Values are (module_name, attr_name).
# # Keep this as static metadata only: populating __all__ from this dict is cheap
# # and does not import submodules. Actual imports happen in __getattr__.
# _PUBLIC_EXPORTS: dict[str, tuple[str, str | None]] = {
#     "BDSim": ("bdsim.run_sim", "BDSim"),
#     "BDRealTime": ("bdsim.run_realtime", "BDRealTime"),
#     "BDRealTimeState": ("bdsim.run_realtime", "BDRealTimeState"),
#     "Block": ("bdsim.block", "Block"),
#     "BlockDiagram": ("bdsim.blockdiagram", "BlockDiagram"),
#     "bdload": ("bdsim.blockdiagram", "bdload"),
#     "GraphicsBlock": ("bdsim.block_types", "GraphicsBlock"),
#     "bdrun": ("bdsim.bin.bdrun", "bdrun"),
#     "components": ("bdsim.components", None),
# }

# __all__ = sorted(_PUBLIC_EXPORTS.keys())

# # Public package-level exports. Values are (module_name, attr_name).
# # Keep this as static metadata only: populating __all__ from this dict is cheap
# # and does not import submodules. Actual imports happen in __getattr__.
# _PUBLIC_EXPORTS: dict[str, tuple[str, str | None]] = {
#     "BDSim": ("bdsim.run_sim", "BDSim"),
#     "BDRealTime": ("bdsim.run_realtime", "BDRealTime"),
#     "BDRealTimeState": ("bdsim.run_realtime", "BDRealTimeState"),
#     "BlockDiagram": ("bdsim.blockdiagram", "BlockDiagram"),
#     "bdload": ("bdsim.blockdiagram", "bdload"),
#     "GraphicsBlock": ("bdsim.block_types", "GraphicsBlock"),
#     "bdrun": ("bdsim.bin.bdrun", "bdrun"),
#     "components": ("bdsim.components", None),
# }

# __all__ = sorted(_PUBLIC_EXPORTS.keys())


# def _resolve_export(name: str) -> Any:
#     # Resolve and memoize on first attribute access so later lookups are fast
#     # and do not re-import. This keeps `import bdsim` lightweight.
#     module_name, attr_name = _PUBLIC_EXPORTS[name]
#     t0 = time.perf_counter() if _IMPORT_TIMING else 0.0
#     module = importlib.import_module(module_name)
#     value = module if attr_name is None else getattr(module, attr_name)
#     globals()[name] = value
#     if _IMPORT_TIMING:
#         print(f"bdsim import: {name}={time.perf_counter() - t0:.3f}s")
#     return value


# def __getattr__(name: str) -> Any:
#     if name in _PUBLIC_EXPORTS:
#         return _resolve_export(name)
#     raise AttributeError(name)


# def __dir__() -> list[str]:
#     return sorted(list(globals().keys()) + list(_PUBLIC_EXPORTS.keys()))


# if _IMPORT_TIMING:
#     print(f"bdsim import: total={time.perf_counter() - _IMPORT_T0:.3f}s")

try:
    import importlib.metadata

    __version__ = importlib.metadata.version("bdsim")
except Exception:
    pass
