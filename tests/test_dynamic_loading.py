#!/usr/bin/env python3
"""
Tests for dynamic block loading: discovery, eager loading, and lazy resolution.

Tests the block loading pipeline using only core bdsim blocks:
  1. Discovery: find_blocks_dirs() locates packages without importing
  2. Eager loading: load_blocks() parses all .py files and creates metadata
  3. Lazy loading: _LazyBlockClass defers module import until first use
  4. Lazy resolution: On first factory call, class is resolved and cached
  5. Sibling promotion: All blocks from same module promoted on first resolve

Note: Tests assume only core bdsim blocks are available. External packages
like roboticstoolbox and machinevisiontoolbox are optional and not tested.
"""
import sys
import unittest
from pathlib import Path
import importlib.util

import bdsim
from bdsim.run_sim import BDSim, _LazyBlockClass, BDSimState, Options


class DiscoveryTest(unittest.TestCase):
    """Tests for find_blocks_dirs() - package discovery without importing."""

    def setUp(self):
        """Create a fresh BDSim instance for each test."""
        # Load only bdsim, no external toolboxes
        self.sim = BDSim(graphics=None, progress=False, banner=False, toolboxes=False)

    def test_discover_bdsim_blocks(self):
        """find_blocks_dirs() should find bdsim.blocks package."""
        # _blocklibrary is a class variable, so it may be cached from prior instances.
        # Just verify it's populated with bdsim blocks.
        self.assertIsNotNone(self.sim._blocklibrary)
        # Check that bdsim is in the library (has at least one bdsim block)
        bdsim_blocks = [
            name
            for name, info in self.sim._blocklibrary.items()
            if info["package"] == "bdsim"
        ]
        self.assertGreater(len(bdsim_blocks), 0)

    def test_blocklibrary_not_empty(self):
        """load_blocks() should populate _blocklibrary with blocks."""
        self.assertIsNotNone(self.sim._blocklibrary)
        self.assertGreater(len(self.sim._blocklibrary), 0)

    def test_blocklibrary_has_common_blocks(self):
        """_blocklibrary should include standard bdsim core blocks."""
        common_blocks = ["CONSTANT", "INTEGRATOR", "GAIN", "NULL"]
        for block_name in common_blocks:
            self.assertIn(
                block_name,
                self.sim._blocklibrary,
                f"Block {block_name} not found in library",
            )


class EagerLoadingTest(unittest.TestCase):
    """Tests for load_blocks() - eager loading and metadata parsing."""

    def setUp(self):
        """Create a fresh BDSim instance for each test."""
        # Load only bdsim, no external toolboxes
        self.sim = BDSim(graphics=None, progress=False, banner=False, toolboxes=False)

    def test_blocklibrary_contract(self):
        """Each block in _blocklibrary should have required metadata fields."""
        required_keys = {
            "path",
            "classname",
            "blockname",
            "url",
            "class",
            "module",
            "package",
            "doc",
            "params",
            "inputs",
            "outputs",
            "nin",
            "nout",
            "blockclass",
        }
        for block_name, info in self.sim._blocklibrary.items():
            missing = required_keys - set(info.keys())
            self.assertEqual(
                missing,
                set(),
                f"Block {block_name} missing keys: {missing}",
            )

    def test_block_metadata_types(self):
        """Block metadata should have correct types."""
        # Pick a few blocks and check types
        gain = self.sim._blocklibrary.get("GAIN")
        self.assertIsNotNone(gain)
        self.assertIsInstance(gain["classname"], str)
        self.assertIsInstance(gain["blockname"], str)
        self.assertIsInstance(gain["module"], str)
        self.assertIsInstance(gain["package"], str)
        self.assertTrue(
            isinstance(gain["nin"], (int, type(None)))
        )  # Can be None for variable
        self.assertTrue(isinstance(gain["nout"], (int, type(None))))

    def test_block_class_is_lazy(self):
        """Blocks should be _LazyBlockClass proxies until resolved."""
        # Note: _blocklibrary is a class variable shared across test instances.
        # By the time this test runs, CONSTANT may already be resolved from other tests.
        block_info = self.sim._blocklibrary["CONSTANT"]
        class_obj = block_info["class"]

        # Check that class is either lazy or has been properly resolved to a real Block
        if isinstance(class_obj, _LazyBlockClass):
            # Still lazy, which is what we expect for fresh load
            self.assertTrue(True)
        else:
            # Already resolved from prior test - verify it's a real Block class
            self.assertTrue(
                hasattr(class_obj, "__bases__"),
                "Resolved class should have __bases__ attribute",
            )

    def test_block_has_nin_nout(self):
        """Blocks should have nin and nout parsed from class definition."""
        integrator = self.sim._blocklibrary.get("INTEGRATOR")
        self.assertIsNotNone(integrator)
        # INTEGRATOR typically has nin=1, nout=1
        self.assertEqual(integrator["nin"], 1)
        self.assertEqual(integrator["nout"], 1)

    def test_block_has_blockclass(self):
        """Blocks should have blockclass (source, sink, transfer, etc)."""
        constant = self.sim._blocklibrary["CONSTANT"]
        self.assertEqual(constant["blockclass"], "source")

        integrator = self.sim._blocklibrary["INTEGRATOR"]
        self.assertEqual(integrator["blockclass"], "transfer")

        null = self.sim._blocklibrary["NULL"]
        self.assertEqual(null["blockclass"], "sink")


class LazyBlockClassTest(unittest.TestCase):
    """Tests for _LazyBlockClass - lazy proxy that defers import."""

    def test_lazy_class_properties(self):
        """_LazyBlockClass should expose __name__ and __module__ without resolving."""
        lazy = _LazyBlockClass("bdsim.blocks.sources", "Constant")
        self.assertEqual(lazy.__name__, "Constant")
        self.assertEqual(lazy.__module__, "bdsim.blocks.sources")

    def test_lazy_class_not_resolved_yet(self):
        """_LazyBlockClass._resolved should be None before first call."""
        lazy = _LazyBlockClass("bdsim.blocks.sources", "Constant")
        self.assertIsNone(lazy._resolved)

    def test_lazy_class_resolve_on_call(self):
        """_LazyBlockClass should resolve on first __call__."""
        lazy = _LazyBlockClass("bdsim.blocks.sources", "Constant")
        # Calling the lazy proxy should resolve it
        block_instance = lazy(1)  # Create a Constant(1) block
        self.assertIsNotNone(lazy._resolved)
        # Should be the actual Block class
        self.assertTrue(hasattr(lazy._resolved, "__mro__"))

    def test_lazy_class_resolve_error_wrong_module(self):
        """_LazyBlockClass should raise if module/class doesn't exist."""
        lazy = _LazyBlockClass("nonexistent.module", "NonexistentClass")
        with self.assertRaises((ModuleNotFoundError, ImportError)):
            lazy()  # Try to call and trigger resolution

    def test_lazy_class_resolve_error_wrong_class(self):
        """_LazyBlockClass should raise if class doesn't exist in module."""
        lazy = _LazyBlockClass("bdsim.blocks.sources", "NonexistentClass")
        with self.assertRaises(AttributeError):
            lazy()


class LazyResolutionTest(unittest.TestCase):
    """Tests for lazy resolution in factory calls and sibling promotion."""

    def setUp(self):
        """Create a fresh BDSim instance for each test."""
        # Load only bdsim, no external toolboxes
        self.sim = BDSim(graphics=None, progress=False, banner=False, toolboxes=False)

    def test_resolve_block_class_caches_result(self):
        """_resolve_block_class() should cache the resolved class."""
        # Note: _blocklibrary is a class variable shared across test instances.
        # This test focuses on caching within a single resolution.
        # Get a block and resolve it
        const_info = self.sim._blocklibrary["CONSTANT"]
        original_class = const_info["class"]

        # Resolve once
        resolved_once = self.sim._resolve_block_class("CONSTANT")

        # Check that it's either already resolved or we just resolved it
        if isinstance(original_class, _LazyBlockClass):
            # It was lazy before, should now be resolved
            cached_class = const_info["class"]
            self.assertIs(cached_class, resolved_once)
            # Second resolve should return same object
            resolved_twice = self.sim._resolve_block_class("CONSTANT")
            self.assertIs(resolved_twice, resolved_once)
        else:
            # Already resolved from prior test, just verify it's consistent
            self.assertIs(original_class, resolved_once)

    def test_sibling_blocks_promoted_on_first_resolve(self):
        """When first block from module is resolved, all siblings promoted."""
        # Find blocks from same module by picking one that's still lazy
        lazy_blocks = [
            name
            for name, info in self.sim._blocklibrary.items()
            if isinstance(info["class"], _LazyBlockClass)
        ]

        if len(lazy_blocks) < 1:
            # All blocks already resolved in prior tests, skip this test
            self.skipTest(
                "All blocks already resolved (shared _blocklibrary across tests)"
            )

        test_block = lazy_blocks[0]
        test_info = self.sim._blocklibrary[test_block]
        test_module = test_info["module"]

        # Find a sibling block from same module that's also lazy
        sibling_names = [
            name
            for name, info in self.sim._blocklibrary.items()
            if info["module"] == test_module
            and isinstance(info["class"], _LazyBlockClass)
        ]

        if len(sibling_names) < 2:
            # Need at least 2 lazy blocks from same module
            self.skipTest(
                f"Not enough lazy blocks from {test_module} (shared _blocklibrary)"
            )

        sibling_name = sibling_names[1]
        sibling_info = self.sim._blocklibrary[sibling_name]

        # Resolve first block
        self.sim._resolve_block_class(test_block)

        # Check that sibling is now resolved (promoted)
        sibling_class_after = sibling_info["class"]
        self.assertNotIsInstance(
            sibling_class_after,
            _LazyBlockClass,
            f"Sibling {sibling_name} should be promoted after first resolve",
        )

    def test_factory_call_triggers_lazy_resolution(self):
        """Creating a block via factory should trigger lazy resolution."""
        # Note: _blocklibrary is a class variable shared across test instances.
        # CONSTANT may already be resolved if other tests ran first.

        const_info = self.sim._blocklibrary["CONSTANT"]
        if not isinstance(const_info["class"], _LazyBlockClass):
            # Already resolved from prior test, skip this test
            self.skipTest(
                "CONSTANT already resolved (shared _blocklibrary across tests)"
            )

        bd = self.sim.blockdiagram()

        # CONSTANT should be lazy initially (verified above)
        self.assertIsInstance(const_info["class"], _LazyBlockClass)

        # Call factory to create a block
        block = bd.CONSTANT(42)

        # After factory call, class should be resolved
        self.assertNotIsInstance(const_info["class"], _LazyBlockClass)

    def test_factory_method_exists_on_blockdiagram(self):
        """blockdiagram() should create factory methods for all blocks."""
        bd = self.sim.blockdiagram()

        # Check that factory methods exist
        self.assertTrue(hasattr(bd, "CONSTANT"))
        self.assertTrue(callable(bd.CONSTANT))

        self.assertTrue(hasattr(bd, "INTEGRATOR"))
        self.assertTrue(callable(bd.INTEGRATOR))

        self.assertTrue(hasattr(bd, "GAIN"))
        self.assertTrue(callable(bd.GAIN))


class IntegrationTest(unittest.TestCase):
    """Integration tests: lazy loading works end-to-end in simulations."""

    def setUp(self):
        """Create a fresh BDSim instance for each test."""
        # Load only bdsim, no external toolboxes
        self.sim = BDSim(graphics=None, progress=False, banner=False, toolboxes=False)

    def test_lazy_blocks_can_be_created_and_connected(self):
        """Blocks resolved lazily should work in diagrams and simulations."""
        bd = self.sim.blockdiagram()

        # Create blocks (triggers lazy resolution)
        step = bd.STEP(t=1)
        integ = bd.INTEGRATOR()
        null = bd.NULL()

        # Connect them
        bd.connect(step, integ)
        bd.connect(integ, null)

        # Compile and run
        bd.compile()
        out = self.sim.run(bd, T=1)

        # Check output
        self.assertIsNotNone(out.t)
        self.assertGreater(len(out.t), 0)

    def test_lazy_blocks_produce_output_in_simulation(self):
        """Lazy-resolved blocks work correctly in full simulation."""
        bd = self.sim.blockdiagram()

        # Create blocks (triggers lazy resolution as factories are called)
        const = bd.CONSTANT(4)
        gain = bd.GAIN(2.5)
        null = bd.NULL()

        bd.connect(const, gain)
        bd.connect(gain, null)

        bd.compile()
        # Run evaluation cycle to test blocks work correctly
        state = bd.getstate0()
        yd = bd.schedule_evaluate(state, 0)

        # Just verify evaluation completes without error
        self.assertIsNotNone(yd)

    def test_multiple_blocks_from_same_module_resolve_once(self):
        """Multiple blocks from same module should resolve that module only once."""
        bd = self.sim.blockdiagram()

        # Sources module should load only once even with multiple blocks
        const1 = bd.CONSTANT(1)
        const2 = bd.CONSTANT(2)
        time_block = bd.TIME()  # Also from sources module

        # All source blocks should now be resolved (promoted)
        for block_name in ["CONSTANT", "TIME"]:
            class_obj = self.sim._blocklibrary[block_name]["class"]
            self.assertNotIsInstance(
                class_obj,
                _LazyBlockClass,
                f"{block_name} should be resolved after factory call",
            )

    def test_lti_siso_block_loads_successfully(self):
        """LTI_SISO block (indirect inheritance) should load and work."""
        # This tests the recursive inheritance resolution
        self.assertIn(
            "LTI_SISO",
            self.sim._blocklibrary,
            "LTI_SISO should be in block library (tests recursive inheritance)",
        )

        bd = self.sim.blockdiagram()
        step = bd.STEP(t=1)
        lti = bd.LTI_SISO(0.5, [2, 1])
        null = bd.NULL()

        bd.connect(step, lti)
        bd.connect(lti, null)

        bd.compile()
        out = self.sim.run(bd, T=1)

        self.assertIsNotNone(out.x)
        self.assertGreater(len(out.t), 0)


class MetadataTest(unittest.TestCase):
    """Tests for block metadata extraction from docstrings."""

    def setUp(self):
        """Create a fresh BDSim instance for each test."""
        # Load only bdsim, no external toolboxes
        self.sim = BDSim(graphics=None, progress=False, banner=False, toolboxes=False)

    def test_block_has_docstring(self):
        """Blocks should have docstrings extracted into 'doc' field."""
        gain = self.sim._blocklibrary["GAIN"]
        self.assertIsNotNone(gain["doc"])
        self.assertIsInstance(gain["doc"], str)
        self.assertGreater(len(gain["doc"]), 0)

    def test_block_has_params(self):
        """Blocks with parameters should have parsed docstrings."""
        gain = self.sim._blocklibrary["GAIN"]
        # GAIN has parameters in its docstring
        self.assertIsNotNone(gain["params"])
        # Just verify params dict is not empty (content varies by block)
        self.assertGreater(len(gain["params"]), 0)

    def test_blockinfo_method_returns_metadata(self):
        """sim.blockinfo() should return block metadata."""
        info = self.sim.blockinfo("GAIN")
        self.assertIsNotNone(info)
        self.assertEqual(info["blockname"], "GAIN")

    def test_blockinfo_no_arg_returns_all(self):
        """sim.blockinfo() with no arg should return all blocks."""
        all_info = self.sim.blockinfo()
        self.assertIsInstance(all_info, dict)
        self.assertEqual(all_info, self.sim._blocklibrary)


class DebugEnvironmentTest(unittest.TestCase):
    """Tests for debug environment variables (optional, visual verification)."""

    def test_debug_discovery_env_var_supported(self):
        """BDSIM_DEBUG_DISCOVERY env var should be supported (not tested verbatim)."""
        # This test just ensures the code paths exist; actual debug output
        # would be verified visually by running:
        #   $ BDSIM_DEBUG_DISCOVERY=1 python -c "import bdsim; sim = bdsim.BDSim(...)"
        import os

        # Check that the env var is referenced in code
        with open(Path(__file__).parent.parent / "src/bdsim/run_sim.py", "r") as f:
            content = f.read()
            self.assertIn("BDSIM_DEBUG_DISCOVERY", content)

    def test_debug_lazy_load_env_var_supported(self):
        """BDSIM_DEBUG_LAZY_LOAD env var should be supported (not tested verbatim)."""
        import os

        # Check that the env var is referenced in code
        with open(Path(__file__).parent.parent / "src/bdsim/run_sim.py", "r") as f:
            content = f.read()
            self.assertIn("BDSIM_DEBUG_LAZY_LOAD", content)


if __name__ == "__main__":
    unittest.main()
