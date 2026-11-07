"""The number of frames of a live animation is bounded, and is reported.

animation_rate is per second of simulated time, so a long simulation of a slow system
used to show T * animation_rate frames, each of which ended an integration interval
and redrew the figures: 12,000 of them for a 600 s run.  max_frames bounds that.
"""

import contextlib
import io
import os
import unittest
from unittest import mock

os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np

import bdsim


def run(T: float = 10, *, animation: bool = True, quiet: bool = True, **options):
    """A ramp, integrated, run with the given options; returns the output."""
    sim = bdsim.BDSim(
        sysargs=False,
        animation=animation,
        graphics=animation,
        banner=False,
        quiet=quiet,
        progress=False,
        **options,
    )
    bd = sim.blockdiagram()
    integrator = bd.INTEGRATOR(x0=0.0, name="i")
    bd.connect(bd.CONSTANT(1.0), integrator)
    bd.connect(integrator, bd.NULL(1))
    bd.compile(verbose=False)
    return sim.run(bd, T=T)


class FrameBudgetTest(unittest.TestCase):
    def test_a_short_run_is_unchanged(self):
        # 10 s at 20 Hz is 200 frames, under the default limit; plus the first frame
        stats = run(10)[".stats"]
        self.assertEqual(stats.animation_frames, 201)
        self.assertEqual(stats.run_interval_calls, 200)

    def test_a_long_run_is_limited(self):
        stats = run(10, animation_rate=100, max_frames=20)[".stats"]
        self.assertEqual(stats.animation_frames, 21)
        self.assertEqual(stats.run_interval_calls, 20)

    def test_the_default_limit_is_1000_frames(self):
        stats = run(100, animation_rate=100)[".stats"]  # 10000 frames wanted
        self.assertEqual(stats.animation_frames, 1001)
        self.assertEqual(stats.run_interval_calls, 1000)

    def test_zero_means_no_limit(self):
        stats = run(10, animation_rate=100, max_frames=0)[".stats"]
        self.assertEqual(stats.animation_frames, 1001)

    def test_exactly_the_limit_is_not_changed(self):
        stats = run(10, animation_rate=10, max_frames=100)[".stats"]
        self.assertEqual(stats.run_interval_calls, 100)

    def test_the_limit_does_not_change_the_result(self):
        # a ramp: the final value is the time, however few frames were shown
        for max_frames in (0, 5, 20):
            out = run(10, animation_rate=100, max_frames=max_frames)
            np.testing.assert_allclose(out.t[-1], 10.0)

    def test_there_are_no_frames_without_animation(self):
        self.assertEqual(run(10, animation=False)[".stats"].animation_frames, 0)


class ExemptionsTest(unittest.TestCase):
    """The limit is only for a live animation of a diagram with state.

    A diagram with no state and no clock is evaluated at the frames, so the frame grid
    is the grid its results are sampled on.  A movie and the interactive debugger are
    also left alone, but neither can be run here (ffmpeg, and a keyboard).
    """

    def stateless_points(self, max_frames: int) -> int:
        sim = bdsim.BDSim(
            sysargs=False,
            animation=True,
            animation_rate=100,
            max_frames=max_frames,
            banner=False,
            quiet=True,
            progress=False,
        )
        bd = sim.blockdiagram()
        bd.connect(bd.WAVEFORM(wave="sine", freq=1), bd.NULL(1))
        bd.compile(verbose=False)
        return len(sim.run(bd, T=10).t)

    def test_a_stateless_diagram_keeps_its_frame_grid(self):
        # the same points however small max_frames is: about 100 Hz for 10 s
        unlimited = self.stateless_points(0)
        self.assertGreaterEqual(unlimited, 1001)
        self.assertEqual(self.stateless_points(20), unlimited)


class FrameStatisticsTest(unittest.TestCase):
    def test_the_frames_are_in_the_stats_and_are_what_was_drawn(self):
        stats = run(10, animation_rate=100, max_frames=50)[".stats"]
        self.assertIn("animation_frames", stats.keys())
        self.assertEqual(stats.animation_frames, 51)


class ReportTest(unittest.TestCase):
    def report(self, **options) -> str:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            run(10, quiet=False, **options)
        return out.getvalue()

    def test_a_limited_run_says_so(self):
        text = self.report(animation_rate=100, max_frames=20)
        self.assertIn("animation: limiting to 20 frames", text)
        self.assertIn("100 Hz would be 1000 frames", text)

    def test_an_unlimited_run_does_not(self):
        self.assertNotIn("limiting to", self.report(animation_rate=10))

    def test_the_frames_are_in_the_summary(self):
        text = self.report(animation_rate=100, max_frames=20)
        self.assertIn("animation frames:", text)
        self.assertIn("(scheduled every 0.5s of simulated time)", text)


class NotebookBackendTest(unittest.TestCase):
    def test_frames_are_counted_when_refreshes_are_rate_limited(self):
        # a notebook backend redraws at most every 1/6 s of simulated time, however
        # often the frame callback runs, and only the redraws are counted
        with mock.patch("matplotlib.get_backend", return_value="widget"):
            stats = run(10, animation_rate=100, max_frames=0)[".stats"]
        self.assertGreater(stats.animation_frames, 0)
        self.assertLess(stats.animation_frames, 100)


if __name__ == "__main__":
    unittest.main()
