"""Backward-compatible graphics exports.

Third-party packages historically imported ``GraphicsBlock`` from
``bdsim.graphics``. The implementation now lives in ``bdsim.block_types``,
so this module preserves the old import path.
"""

from .block_types import GraphicsBlock

__all__ = ["GraphicsBlock"]


if __name__ == "__main__":
	try:
		from ._selftest import run_module_test
	except ImportError:
		from bdsim._selftest import run_module_test

	raise SystemExit(run_module_test(__file__))
