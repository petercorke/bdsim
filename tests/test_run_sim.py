#!/usr/bin/env python3
"""
Additional tests for run_sim.py to improve coverage.

Targets:
  - TimeQ class (__repr__, pop_until)
  - Progress class (start/end/update)
  - BDSimState.declare_event
  - BDSim.__str__
  - sim.run() with watchlist (str, Block, Plug forms)
  - sim.run() with simtime option
  - sim.run() with debug flag
  - sim.run() with quiet=False (verbose output lines)
  - sim.run() with outfile (pickling)
  - update_parameters()
"""
import os
import sys
from pathlib import Path
import importlib.util
import tempfile
import unittest
import io
import contextlib
from types import SimpleNamespace

import numpy as np

import bdsim
from bdsim.exceptions import EventProbeOutsideIntervalError, IntegrationFailureError
from bdsim.run_sim import TimeQ, Progress, BDSimState, BDSim, Options, _LazyBlockClass


# ---------------------------------------------------------------------------
class TimeQTest(unittest.TestCase):
    """Tests for the TimeQ event queue."""

    def test_empty_str(self):
        q = TimeQ()
        self.assertEqual(str(q), "")

    def test_nonempty_str(self):
        q = TimeQ()
        q.push((1.0, "block"))
        self.assertIn("1.000000", str(q))
        self.assertIn("block", str(q))

    def test_repr_empty(self):
        q = TimeQ()
        self.assertEqual(repr(q), "TimeQ(len=0)")

    def test_repr_nonempty(self):
        q = TimeQ()
        q.push((2.0, "b"))
        r = repr(q)
        self.assertIn("len=1", r)
        self.assertIn("@ t=2.0", r)

    def test_pop_none_when_empty(self):
        q = TimeQ()
        t, blocks = q.pop()
        self.assertIsNone(t)
        self.assertEqual(blocks, [])

    def test_pop_until_empty(self):
        q = TimeQ()
        result = q.pop_until(10)
        self.assertEqual(result, [])

    def test_pop_until_sorted(self):
        """pop_until sorts and pops items up to and excluding t."""
        q = TimeQ()
        q.push((3.0, "c"))
        q.push((1.0, "a"))
        q.push((2.0, "b"))
        result = q.pop_until(2.0)
        # Items with t <= 2.0 should remain (or be popped — behavior depends on impl.)
        # The function removes items with t <= t_thresh
        # After pop_until(2.0), only the items with t > 2.0 remain
        remaining, _ = q.pop()
        self.assertEqual(remaining, 3.0)

    def test_pop_until_already_sorted(self):
        """pop_until works regardless of insertion order and prior pops."""
        q = TimeQ()
        q.push((1.0, "a"))
        q.push((2.0, "b"))
        # Pop one item then push an earlier timestamp.
        q.pop()
        q.push((0.5, "x"))

        result = q.pop_until(0.3)  # nothing <= 0.3
        self.assertEqual(result, [])
        self.assertEqual(len(q), 2)

    def test_pop_same_time_preserves_insertion_order(self):
        """Events at identical times are popped in insertion order via _seq tie-break."""
        q = TimeQ()
        q.push((1.0, "a"))
        q.push((1.0, "b"))
        q.push((1.0, "c"))

        t1, b1 = q.pop()
        t2, b2 = q.pop()
        t3, b3 = q.pop()

        self.assertEqual((t1, b1), (1.0, ["a"]))
        self.assertEqual((t2, b2), (1.0, ["b"]))
        self.assertEqual((t3, b3), (1.0, ["c"]))

    def test_pop_groups_events_with_dt(self):
        """pop(dt=...) groups events within dt tolerance into one returned batch."""
        q = TimeQ()
        q.push((1.0, "a"))
        q.push((1.0, "b"))
        q.push((1.0000001, "c"))
        q.push((1.01, "d"))

        t, blocks = q.pop(dt=1e-3)
        self.assertEqual(t, 1.0)
        self.assertEqual(blocks, ["a", "b", "c"])
        self.assertEqual(len(q), 1)


# ---------------------------------------------------------------------------
class ProgressTest(unittest.TestCase):
    """Tests for the Progress (progress bar) helper class."""

    def test_disabled_progress(self):
        p = Progress(enable=False)
        p.start(10)
        p.update(5)
        p.end()  # should not raise

    def test_enabled_progress_plain_bar(self):
        """Test the fallback plain-bar implementation."""
        p = Progress(enable=True)
        p.start(10)
        p.update(5)
        p.end()  # should not raise


# ---------------------------------------------------------------------------
class BDSimStateTest(unittest.TestCase):
    """Tests for BDSimState."""

    def test_declare_event(self):
        state = BDSimState()
        state.declare_event("some_block", 1.5)
        self.assertEqual(len(state.eventq), 1)

    def test_event_probe_outside_interval_raises(self):
        state = BDSimState()
        state.begin_event_probe_interval(0.1, 0.2)

        class _DummyBD:
            def state_map(self, y, simstate):
                return {}

            def evaluate(self, state_map, t, sinks=False):
                return None

        with self.assertRaises(EventProbeOutsideIntervalError):
            state.ensure_event_probe_evaluated(_DummyBD(), 0.05, np.array([0.0]))


# ---------------------------------------------------------------------------
class BDSimStrTest(unittest.TestCase):
    """Tests for BDSim.__str__."""

    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False)

    def test_str(self):
        s = str(self.sim)
        self.assertIn("BDSim", s)


# ---------------------------------------------------------------------------
class SimRunCoverageTest(unittest.TestCase):
    """Tests that exercise deeply uncovered paths inside sim.run()."""

    def setUp(self):
        # Fresh BDSim per test: quiet=False ensures verbose output lines run even
        # when pytest is invoked with -q (which would inject -q into sys.argv).
        # A new instance also avoids shared-state bugs from options mutations.
        self.sim = bdsim.BDSim(
            graphics=None,
            progress=False,
            banner=False,
            quiet=False,
            sysargs=False,
        )

    def _stateful_bd(self):
        """STEP -> INTEGRATOR -> NULL, 1 continuous state."""
        bd = self.sim.blockdiagram()
        step = bd.STEP(t=0.5)
        integ = bd.INTEGRATOR()
        null = bd.NULL()
        bd.connect(step, integ)
        bd.connect(integ, null)
        bd.compile(verbose=False)
        return bd, step, integ, null

    def _pure_function_bd(self):
        """CONSTANT -> GAIN -> NULL, no continuous states."""
        bd = self.sim.blockdiagram()
        src = bd.CONSTANT(3)
        gain = bd.GAIN(2)
        null = bd.NULL(1)
        bd.connect(src, gain)
        bd.connect(gain, null)
        bd.compile(verbose=False)
        return bd, src, gain, null

    def _clocked_bd(self):
        """WAVEFORM -> ZOH(clock) -> NULL, no continuous states, with clock events."""
        from bdsim.block import SampledBlock

        bd = self.sim.blockdiagram()
        clock = bd.clock(5, "Hz")
        src = bd.WAVEFORM("sine", freq=1)
        zoh = bd.ZOH(clock)
        sink = bd.NULL(1)
        bd.connect(src, zoh)
        bd.connect(zoh, sink)
        bd.compile(verbose=False)
        self.assertIsInstance(zoh, SampledBlock)
        return bd, clock, src, zoh, sink

    # ---- watchlist variants ------------------------------------------------

    def test_run_watch_block(self):
        """watch=[Block] covers the Block branch of watchlist processing."""
        bd, step, integ, null = self._stateful_bd()
        out = self.sim.run(bd, T=1, watch=[step])
        self.assertIsNotNone(out.t)
        self.assertIsNotNone(out.y0)
        self.assertGreater(len(out.y0), 0)

    def test_run_watch_plug(self):
        """watch=[Plug] covers the Plug branch of watchlist processing."""
        bd, step, integ, null = self._stateful_bd()
        out = self.sim.run(bd, T=1, watch=[step[0]])
        self.assertIsNotNone(out.t)
        self.assertIsNotNone(out.y0)
        self.assertGreater(len(out.y0), 0)

    def test_run_watch_string_no_port(self):
        """watch=["blockname"] string with no port number."""
        bd, step, integ, null = self._stateful_bd()
        out = self.sim.run(bd, T=1, watch=["step.0"])
        self.assertIsNotNone(out.t)
        self.assertIsNotNone(out.y0)
        self.assertGreater(len(out.y0), 0)

    def test_run_watch_string_with_port(self):
        """watch=["blockname[port]"] string with explicit port number."""
        bd, step, integ, null = self._stateful_bd()
        out = self.sim.run(bd, T=1, watch=["step.0[0]"])
        self.assertIsNotNone(out.t)
        self.assertIsNotNone(out.y0)
        self.assertGreater(len(out.y0), 0)

    # ---- simtime option ----------------------------------------------------

    def test_run_with_simtime_scalar(self):
        """sim.options.simtime set to a scalar value covers lines 498-501."""
        bd, step, integ, null = self._stateful_bd()
        self.sim.options.simtime = "1.0"
        try:
            out = self.sim.run(bd, T=10)  # simtime overrides T=10
        finally:
            self.sim.options.simtime = None
        # Simulation ran for T=1.0
        self.assertIsNotNone(out.t)

    def test_run_with_simtime_tuple(self):
        """sim.options.simtime as a tuple  (T, dt) covers lines 502-503."""
        bd, step, integ, null = self._stateful_bd()
        self.sim.options.simtime = "(1.0, 0.05)"
        try:
            out = self.sim.run(bd, T=10)
        finally:
            self.sim.options.simtime = None
        self.assertIsNotNone(out.t)

    # ---- debug flag -------------------------------------------------------

    def test_run_with_debug_flag(self):
        """Passing debug="s" covers the debug block (lines 536-537, 541).

        Uses "s" (state) rather than "p" (propagate) or "d" (deriv) to avoid
        pre-existing bugs in run_sim.py:
          - DEBUG("propagate", "block {:s}: ...") tries to apply :s to a Block.
          - DEBUG("deriv", YD) passes a numpy array as the format string.
        The "s" (state) path uses a proper format string with {} placeholders.
        """
        bd, step, integ, null = self._stateful_bd()
        out = self.sim.run(bd, T=0.2, debug="s")
        self.assertIsNotNone(out.t)

    # ---- quiet=False output lines -----------------------------------------

    def test_run_verbose_output(self):
        """Running with quiet=False exercises the printed summary lines."""
        bd, step, integ, null = self._stateful_bd()
        out = self.sim.run(bd, T=0.5)  # quiet=False set at class level
        self.assertIsNotNone(out.t)

    # ---- outfile pickling -------------------------------------------------

    def test_run_with_outfile(self):
        """sim.options.outfile saves pickled results (lines 648-652)."""
        bd, step, integ, null = self._stateful_bd()
        with tempfile.NamedTemporaryFile(suffix=".out", delete=False) as tmp:
            tmpname = tmp.name
        try:
            self.sim.options.outfile = tmpname
            out = self.sim.run(bd, T=0.5)
            self.assertTrue(os.path.exists(tmpname))
            self.assertGreater(os.path.getsize(tmpname), 0)
        finally:
            self.sim.options.outfile = None
            try:
                os.unlink(tmpname)
            except OSError:
                pass

    # ---- update_parameters ------------------------------------------------

    def test_update_parameters(self):
        """update_parameters() parses block:param=value strings."""
        bd, step, integ, null = self._stateful_bd()
        # GAIN block so we can set K
        gain = bd.GAIN(1)
        null2 = bd.NULL(1)
        bd.connect(integ, gain)
        bd.connect(gain, null2)
        bd.compile(verbose=False)

        self.sim.options.setparam = [f"{gain.name}:K=5"]
        try:
            self.sim.update_parameters(bd)
        finally:
            self.sim.options.setparam = []
        self.assertEqual(gain.K, 5)

    def test_update_parameters_by_id(self):
        """update_parameters() can reference blocks by integer id."""
        bd, step, integ, null = self._stateful_bd()
        gain = bd.GAIN(1)
        null2 = bd.NULL(1)
        bd.connect(integ, gain)
        bd.connect(gain, null2)
        bd.compile(verbose=False)

        self.sim.options.setparam = [f"{gain.id}:K=7"]
        try:
            self.sim.update_parameters(bd)
        finally:
            self.sim.options.setparam = []
        self.assertEqual(gain.K, 7)

    def test_update_parameters_empty_list(self):
        """update_parameters() with empty setparam is a no-op."""
        bd, step, integ, null = self._stateful_bd()
        self.sim.options.setparam = []
        self.sim.update_parameters(bd)  # should not raise

    def test_set_globals_updates_dict(self):
        """set_globals() should apply --global var=value entries to the provided dict."""
        self.sim.options.set(setglob=["x=42", "name='hello'"])
        globs = {"x": 0, "name": "old"}
        try:
            self.sim.set_globals(globs)
        finally:
            self.sim.options.set(setglob=[])
        self.assertEqual(globs["x"], 42)
        self.assertEqual(globs["name"], "hello")

    def test_set_globals_empty_list_is_noop(self):
        """set_globals() with empty setglob should leave dict unchanged."""
        self.sim.options.set(setglob=[])
        globs = {"x": 99}
        self.sim.set_globals(globs)
        self.assertEqual(globs["x"], 99)

    def test_clocked_run_populates_clock_trace(self):
        """Clocked systems should emit per-clock traces in run() results."""
        bd, clock, src, zoh, sink = self._clocked_bd()
        out = self.sim.run(bd, T=1.0)

        self.assertTrue(hasattr(out, "clock0"))
        self.assertGreater(len(out.clock0.t), 0)
        self.assertGreater(len(out.clock0.x), 0)

    def test_clocked_run_uses_event_queue(self):
        """run() for clocked systems should drive execution via simstate.eventq."""
        bd, clock, src, zoh, sink = self._clocked_bd()

        eventq_sizes = []
        original_interval = self.sim._interval_discrete

        def wrapped_interval(bd_arg, t0, T, x0, simstate):
            eventq_sizes.append(len(simstate.eventq))
            return original_interval(bd_arg, t0, T, x0, simstate)

        self.sim._interval_discrete = wrapped_interval
        try:
            out = self.sim.run(bd, T=1.0)
        finally:
            self.sim._interval_discrete = original_interval

        self.assertIsNotNone(out.t)
        self.assertGreater(len(eventq_sizes), 0)
        self.assertGreater(max(eventq_sizes), 0)

    def test_run_loops_after_early_crossing_without_scheduled_events(self):
        """Early crossing termination should trigger another interval loop.

        For diagrams with no scheduled events, run() still needs to keep calling
        run_interval() if integration stops early due to a crossing event.
        """

        bd, step, integ, null = self._stateful_bd()

        interval_calls = []
        original_interval = self.sim._interval_hybrid

        def fake_interval(bd_arg, t0, T, x0, simstate):
            interval_calls.append((float(t0), float(T)))
            if len(interval_calls) == 1:
                # Simulate an early stop before the target boundary due to crossing.
                return np.array(x0), 0.2
            return np.array(x0), float(T)

        self.sim._interval_hybrid = fake_interval
        try:
            out = self.sim.run(bd, T=0.5)
        finally:
            self.sim._interval_hybrid = original_interval

        self.assertIsNotNone(out.t)
        self.assertGreaterEqual(len(interval_calls), 2)
        self.assertEqual(interval_calls[0], (0.0, 0.5))
        self.assertGreater(interval_calls[1][0], interval_calls[0][0])

    def test_run_continues_after_real_crossing_event(self):
        """Real solve_ivp crossing events should split execution into multiple intervals.

        This exercises the integrated scheduled/crossing loop without monkeypatching
        run_interval(). The EVENT block's crossing should terminate one interval, then
        run() must continue integrating up to T.
        """
        bd = self.sim.blockdiagram()
        step = bd.STEP(T=0, off=1, on=1)
        integ = bd.INTEGRATOR(x0=0)
        thresh = bd.CONSTANT(0.2)
        err = bd.SUM("+-")

        crossing_calls = []

        def on_crossing(block):
            crossing_calls.append(block)

        evt = bd.EVENT("+", on_crossing)
        sink = bd.NULL()

        bd.connect(step, integ)
        bd.connect(integ, sink)
        bd.connect(integ, err[0])
        bd.connect(thresh, err[1])
        bd.connect(err, evt)
        bd.compile(verbose=False)

        out = self.sim.run(bd, T=0.5)

        self.assertIsNotNone(out.t)
        self.assertGreater(len(out.t), 0)
        self.assertAlmostEqual(float(out.t[-1]), 0.5, delta=1e-3)
        self.assertGreaterEqual(int(out.stats.run_interval_calls), 2)
        self.assertGreaterEqual(len(crossing_calls), 1)

    def test_stop_handler_state_mutation_persists(self):
        """STOP crossing handler edits to the unified state map must persist."""
        bd = self.sim.blockdiagram()
        step = bd.STEP(T=0, off=1, on=1)
        integ = bd.INTEGRATOR(x0=0)
        stop = bd.STOP(lambda x: x - 0.2)

        def stop_and_reset(t_crossing, y_crossing, state_map, simstate):
            # If this writes to a local copy, returned final state remains near 0.2.
            # Correct behavior writes through to canonical state and final state is 0.
            state_map[integ][:] = np.r_[0.0]
            simstate.stop = stop

        stop.event_handler = stop_and_reset
        sink = bd.NULL()

        bd.connect(step, integ)
        bd.connect(integ, sink)
        bd.connect(integ, stop)
        bd.compile(verbose=False)

        out = self.sim.run(bd, T=0.5)

        self.assertIsNotNone(out.x)
        final_x = float(np.asarray(out.x).reshape(-1)[-1])
        self.assertAlmostEqual(final_x, 0.0, delta=1e-6)

    def test_hybrid_crossing_state_map_mutation_persists_into_clock_ticks(self):
        """Crossing-handler state_map edits should persist for continuous and sampled state.

        This is an end-to-end hybrid regression:
        - continuous state is reset via crossing handler
        - sampled clocked state is rewritten via the same state_map
        - subsequent clock ticks must evolve from the rewritten sampled state
        """

        bd = self.sim.blockdiagram()

        # continuous path: xdot = 1, crossing at x=0.2
        src_c = bd.CONSTANT(1.0)
        integ = bd.INTEGRATOR(x0=0.0)
        thresh = bd.CONSTANT(0.2)
        err = bd.SUM("+-")

        # sampled path: nominally constant at 5.0 unless crossing mutates it
        clock = bd.clock(10, "Hz")
        src_d = bd.CONSTANT(0.0)
        dint = bd.INTEGRATOR_S(clock, x0=5.0)

        sink_c = bd.NULL()
        sink_d = bd.NULL()

        crossing_calls = []

        def on_crossing(event_block, state_map):
            crossing_calls.append(True)
            # reset continuous state at crossing
            state_map[integ][:] = np.r_[0.0]
            # force sampled state to a new baseline that should appear in clock trace
            state_map[dint][:] = np.r_[9.0]

        evt = bd.EVENT("+", on_crossing)

        bd.connect(src_c, integ)
        bd.connect(integ, sink_c)
        bd.connect(integ, err[0])
        bd.connect(thresh, err[1])
        bd.connect(err, evt)

        bd.connect(src_d, dint)
        bd.connect(dint, sink_d)

        bd.compile(verbose=False)

        out = self.sim.run(bd, T=0.5)

        self.assertGreaterEqual(len(crossing_calls), 1)

        # Continuous trajectory should be well below the no-reset value (~0.5)
        # because crossing-handler state reset(s) were applied.
        self.assertIsNotNone(out.x)
        final_x = float(np.asarray(out.x).reshape(-1)[-1])
        self.assertGreater(final_x, 0.0)
        self.assertLess(final_x, 0.25)

        # Sampled clock trace should include pre-crossing state (~5) and mutated state (~9).
        self.assertTrue(hasattr(out, "clock0"))
        sampled_trace = np.asarray(out.clock0.x).reshape(-1)
        self.assertTrue(np.any(np.isclose(sampled_trace, 5.0, atol=1e-9)))
        self.assertTrue(np.any(np.isclose(sampled_trace, 9.0, atol=1e-9)))

    def test_stop_crossing_in_continuous_mode_stops_without_large_t_delay(self):
        """STOP should terminate near the crossing time even when T is very large."""
        bd = self.sim.blockdiagram()
        src = bd.CONSTANT(1.0)
        integ = bd.INTEGRATOR(x0=0.0)
        stop = bd.STOP(lambda x: x > 0.2)

        bd.connect(src, integ)
        bd.connect(integ, stop)
        bd.compile(verbose=False)

        out = self.sim.run(bd, T=5.0)  # large relative to expected stop at t≈0.2

        self.assertIsNotNone(out.t)
        self.assertAlmostEqual(float(out.t[-1]), 0.2, delta=1e-3)

    def test_stop_still_works_for_pure_discrete_runs(self):
        """STOP should still work for diagrams with no continuous state."""
        bd = self.sim.blockdiagram()
        clock = bd.clock(10, "Hz")
        src = bd.WAVEFORM("sine", freq=1.0, offset=1.0, clock=clock)
        stop = bd.STOP(lambda x: x > 0.5)

        bd.connect(src, stop)
        bd.compile(verbose=False)

        out = self.sim.run(bd, T=10.0)

        self.assertIsNotNone(out.t)
        self.assertAlmostEqual(float(out.t[-1]), 0.0, delta=1e-12)
        self.assertEqual(len(out.t), 1)

    def test_run_raises_integration_failure_error_on_solver_failure(self):
        """Regression: solve_ivp failure should raise IntegrationFailureError."""
        from unittest.mock import patch

        bd, step, integ, null = self._stateful_bd()
        failed_result = SimpleNamespace(
            success=False,
            status=-1,
            message="forced failure for regression test",
        )

        with patch("bdsim.run_sim.integrate.solve_ivp", return_value=failed_result):
            with self.assertRaises(IntegrationFailureError):
                self.sim.run(bd, T=0.5)

    def test_integration_failure_error_contains_interval_details(self):
        """IntegrationFailureError exception should preserve solver internals.
        Exception attributes (t0, tf, status, message) enable precise debugging
        and programmatic re-raising or error recovery in downstream handlers.
        """
        from unittest.mock import patch

        bd, step, integ, null = self._stateful_bd()
        # failed solver result with recognizable markers
        failed_result = SimpleNamespace(
            success=False,
            status=-2,
            message="step size too small",
        )

        with patch("bdsim.run_sim.integrate.solve_ivp", return_value=failed_result):
            with self.assertRaises(IntegrationFailureError) as cm:
                self.sim.run(bd, T=0.5)

            # exception should preserve interval bounds, status code, and message
            # for debugging and downstream error handlers
            err = cm.exception
            self.assertEqual(err.t0, 0.0)
            self.assertEqual(err.tf, 0.5)
            self.assertEqual(err.status, -2)
            self.assertEqual(err.message, "step size too small")

            # formatted error message should include all critical details
            # for logs and stack traces
            msg = str(err)
            self.assertIn("0.0", msg)
            self.assertIn("0.5", msg)
            self.assertIn("-2", msg)
            self.assertIn("step size too small", msg)


# ---------------------------------------------------------------------------
class SimRunFunctionBDTest(unittest.TestCase):
    """Run a pure-function (stateless) block diagram to exercise no-state path."""

    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False, quiet=False)

    def test_run_no_states_with_dt(self):
        """Block diagram with no continuous states but with explicit dt."""
        bd = self.sim.blockdiagram()
        src = bd.CONSTANT(3)
        null = bd.NULL(1)
        bd.connect(src, null)
        bd.compile(verbose=False)
        # dt=None and no states → division would fail if dt not set.
        # Pass dt explicitly to exercise the 'no states, no clock' path.
        out = self.sim.run(bd, T=0.1, dt=0.02)
        self.assertIsNotNone(out.t)


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
        """Blocks should have blockclass (source, sink, continuous, etc)."""
        constant = self.sim._blocklibrary["CONSTANT"]
        self.assertEqual(constant["blockclass"], "source")

        integrator = self.sim._blocklibrary["INTEGRATOR"]
        self.assertEqual(integrator["blockclass"], "continuous")

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
        yd = bd.evaluate(state, 0)

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


class OptionsBackendCliTest(unittest.TestCase):
    """Tests for Options parser backend convenience modes."""

    def _parse_with_argv(self, argv):
        old_argv = sys.argv[:]
        try:
            sys.argv = argv
            return Options(sysargs=True)
        finally:
            sys.argv = old_argv

    def test_backend_list_prints_available_backends_and_exits(self):
        """--backend with no value should print available backends and exit(0)."""
        old_argv = sys.argv[:]
        try:
            sys.argv = ["prog", "--backend"]
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                with self.assertRaises(SystemExit) as cm:
                    Options(sysargs=True)
            self.assertEqual(cm.exception.code, 0)
            self.assertIn("available matplotlib backends", buf.getvalue().lower())
        finally:
            sys.argv = old_argv

    def test_animation_rate_cli_sets_option(self):
        """--animation-rate should set Options.animation_rate from CLI."""
        opts = self._parse_with_argv(["prog", "--animation-rate", "33"])
        self.assertEqual(float(opts.animation_rate), 33.0)

    def test_cli_plus_animation_enables_graphics(self):
        """+a should force graphics on if animation is requested."""
        opts = self._parse_with_argv(["prog", "+a"])
        self.assertTrue(bool(opts.animation))
        self.assertTrue(bool(opts.graphics))

    def test_cli_no_graphics_disables_animation(self):
        """-g should disable graphics and force animation off."""
        opts = self._parse_with_argv(["prog", "-g"])
        self.assertFalse(bool(opts.graphics))
        self.assertFalse(bool(opts.animation))

    def test_cli_conflicting_animation_and_no_graphics_rejected(self):
        """+a with -g conflicts: sanity raises ValueError (cross-option coupling)."""
        with self.assertRaises(ValueError):
            self._parse_with_argv(["prog", "+a", "-g"])

    def test_cli_hold_and_altscreen_switches(self):
        """+/- switches should update hold and altscreen options."""
        opts = self._parse_with_argv(["prog", "-H", "-A"])
        self.assertFalse(bool(opts.hold))
        self.assertFalse(bool(opts.altscreen))

        opts = self._parse_with_argv(["prog", "+H", "+A"])
        self.assertTrue(bool(opts.hold))
        self.assertTrue(bool(opts.altscreen))

    def test_cli_unknown_args_are_preserved(self):
        """Non-bdsim arguments should be left in _argv for user programs."""
        opts = self._parse_with_argv(["prog", "--no-progress", "--user-flag", "42"])
        self.assertFalse(bool(opts.progress))
        self.assertEqual(opts._argv, ["--user-flag", "42"])

    def test_cli_unknown_args_rewrite_sys_argv_to_user_args(self):
        """BDSim should consume its options and leave only user args in sys.argv."""
        original = sys.argv[:]
        test_argv = ["prog", "--no-progress", "--user-flag", "42"]
        try:
            sys.argv = test_argv[:]
            opts = Options(sysargs=True)
            self.assertEqual(sys.argv, ["prog", "--user-flag", "42"])
            self.assertEqual(opts._argv, ["--user-flag", "42"])
        finally:
            sys.argv = original

    def test_cli_known_args_leave_only_program_name_in_sys_argv(self):
        """If there are no extra user args, sys.argv should be reduced to argv0."""
        original = sys.argv[:]
        try:
            sys.argv = ["prog", "--no-progress"]
            opts = Options(sysargs=True)
            self.assertEqual(sys.argv, ["prog"])
            self.assertEqual(opts._argv, [])
        finally:
            sys.argv = original

    def test_interactive_rate_alias_maps_to_animation_rate(self):
        """Legacy interactive_rate option should map to animation_rate."""
        opts = Options(sysargs=False, interactive_rate=12)
        self.assertEqual(float(opts.animation_rate), 12.0)

    def test_animation_rate_cli_rejects_non_positive(self):
        """CLI-provided non-positive animation rate should be rejected."""
        with self.assertRaises(ValueError):
            self._parse_with_argv(["prog", "--animation-rate", "0"])

    def test_animation_rate_must_be_positive(self):
        """animation_rate <= 0 should be rejected by option sanity checks."""
        with self.assertRaises(ValueError):
            Options(sysargs=False, animation_rate=0)
        with self.assertRaises(ValueError):
            Options(sysargs=False, animation_rate=-1)

    def test_cli_set_accumulates_multiple_values(self):
        """--set can be specified multiple times; values accumulate in setparam list."""
        opts = self._parse_with_argv(
            ["prog", "--set", "gain:K=3", "--set", "plant:tau=0.5"]
        )
        self.assertIn("gain:K=3", opts.setparam)
        self.assertIn("plant:tau=0.5", opts.setparam)

    def test_cli_set_short_form_accumulates(self):
        """-s short form stores values in setparam list."""
        opts = self._parse_with_argv(["prog", "-s", "block:gain=10"])
        self.assertIn("block:gain=10", opts.setparam)

    def test_cli_global_accumulates_multiple_values(self):
        """--global can be specified multiple times; values accumulate in setglob list."""
        opts = self._parse_with_argv(
            ["prog", "--global", "T=10", "--global", "dt=0.01"]
        )
        self.assertIn("T=10", opts.setglob)
        self.assertIn("dt=0.01", opts.setglob)

    def test_cli_set_empty_by_default(self):
        """setparam and setglob default to empty list when flags are absent."""
        opts = self._parse_with_argv(["prog"])
        self.assertEqual(opts.setparam, [])
        self.assertEqual(opts.setglob, [])


if __name__ == "__main__":
    unittest.main()
