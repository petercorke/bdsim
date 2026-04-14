#!/usr/bin/env python3
"""
Tests for graphics.py to improve coverage.

Targets uncovered lines:
  45-49  start() animation-warning block (movie != None, animation=False)
  51-58  start() FFMpeg writer setup block
  61-79  step() animation canvas-draw branches
  75-79  step() movie grab_frame block
  82-87  done() body (fig is not None)
  100-110 savefig() body
  113-288 create_figure() method
"""
import io
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import matplotlib

matplotlib.use("Agg")  # headless backend – must be set before pyplot imports
import matplotlib.pyplot as plt

from bdsim.block_types import GraphicsBlock


# ---------------------------------------------------------------------------
# Minimal concrete subclass (GraphicsBlock is abstract via SinkBlock)


class MinGB(GraphicsBlock):
    """Minimal testable GraphicsBlock with nin=1, nout=0."""

    nin = 1
    nout = 0

    def output(self, t, inports, x):
        return []


def _make_simstate(graphics=True, animation=False, backend="agg"):
    ss = MagicMock()
    ss.options.graphics = graphics
    ss.options.animation = animation
    ss.backend = backend
    return ss


def _make_gstate(tiles="1x1"):
    """Return a SimpleNamespace that satisfies create_figure()'s state contract."""
    options = SimpleNamespace(backend=None, tiles=tiles, shape=None, altscreen=False)
    return SimpleNamespace(
        options=options,
        fignum=0,
        figsize=None,
        dpi=None,
        ntiles=None,
        xoffset=0,
        screensize_pix=None,
        backend=None,
    )


# ---------------------------------------------------------------------------
class StartTest(unittest.TestCase):
    """GraphicsBlock.start() coverage."""

    def test_start_no_movie(self):
        """start() with movie=None sets _enabled from simstate (lines 41-42)."""
        gb = MinGB(nin=1)
        ss = _make_simstate(graphics=True, animation=False)
        gb.start(ss)
        self.assertTrue(gb._enabled)

    def test_start_movie_animation_disabled_warning(self):
        """start() with movie set and animation=False prints warnings (lines 44-49)."""
        gb = MinGB(nin=1, movie="test.mp4")
        ss = _make_simstate(graphics=True, animation=False)
        with patch("matplotlib.animation.FFMpegWriter") as MockW:
            MockW.return_value.setup.return_value = None
            gb.start(ss)  # covers warning block (44-49) + success path (51-56)
        self.assertEqual(gb._writer, MockW.return_value)

    def test_start_movie_ffmpeg_setup_success(self):
        """start() with movie and working FFMpeg covers setup path (lines 51-56)."""
        gb = MinGB(nin=1, movie="out.mp4")
        ss = _make_simstate(graphics=True, animation=True)
        with patch("matplotlib.animation.FFMpegWriter") as MockW:
            MockW.return_value.setup.return_value = None
            gb.start(ss)
        MockW.return_value.setup.assert_called_once()

    def test_start_movie_ffmpeg_not_found(self):
        """start() catches FileNotFoundError and calls fatal (lines 57-58)."""
        gb = MinGB(nin=1, movie="out.mp4")
        ss = _make_simstate(graphics=True, animation=True)
        with patch("matplotlib.animation.FFMpegWriter") as MockW:
            MockW.return_value.setup.side_effect = FileNotFoundError("no ffmpeg")
            # fatal() is not defined on a bare block → AttributeError propagates
            with self.assertRaises(AttributeError):
                gb.start(ss)


# ---------------------------------------------------------------------------
class StepTest(unittest.TestCase):
    """GraphicsBlock.step() coverage."""

    def test_step_no_animation(self):
        """step() with animation=False skips the canvas block (line 64 check only)."""
        gb = MinGB(nin=1)
        ss = _make_simstate(animation=False)
        gb._simstate = ss
        gb.step(0.0, [1.0])  # should not raise

    def test_step_animation_agg_else_branch(self):
        """step() with animation=True and non-TkAgg/Qt5Agg backend calls draw (lines 63-73)."""
        gb = MinGB(nin=1)
        ss = _make_simstate(animation=True, backend="agg")  # not TkAgg or Qt5Agg
        gb._simstate = ss
        gb.fig = plt.figure()
        try:
            gb.step(0.0, [1.0])  # covers else: self.fig.canvas.draw()
        finally:
            plt.close("all")

    def test_step_movie_no_writer_attribute_error(self):
        """step() with movie set but no writer → AttributeError in grab_frame (lines 75-79)."""
        gb = MinGB(nin=1, movie="out.mp4")
        ss = _make_simstate(animation=False)
        gb._simstate = ss
        # self._writer never set → AttributeError from grab_frame except block → fatal() → AttributeError
        with self.assertRaises(AttributeError):
            gb.step(0.0, [1.0])


# ---------------------------------------------------------------------------
class DoneTest(unittest.TestCase):
    """GraphicsBlock.done() coverage."""

    def test_done_no_fig(self):
        """done() with fig=None is a no-op (line 82 False branch)."""
        gb = MinGB(nin=1)
        gb.done()  # fig is None → nothing happens; line 82 still reached

    def test_done_with_mock_fig(self):
        """done() with fig set enters the body (lines 83-87)."""
        gb = MinGB(nin=1)
        gb.fig = MagicMock()  # mock avoids display interaction
        gb.done()
        gb.fig.canvas.start_event_loop.assert_called_once_with(0.001)

    def test_done_with_real_fig(self):
        """done() with a real Agg figure calls start_event_loop and plt.show."""
        gb = MinGB(nin=1)
        gb.fig = plt.figure()
        try:
            gb.done(block=False)  # plt.show(block=False) is a no-op with Agg
        finally:
            plt.close("all")


# ---------------------------------------------------------------------------
class SavefigTest(unittest.TestCase):
    """GraphicsBlock.savefig() coverage (lines 100-110)."""

    def test_savefig_with_real_fig(self):
        """savefig() with a real figure writes a PDF file (lines 100-107)."""
        gb = MinGB(nin=1)
        gb.fig = plt.figure()
        gb._name = "testblock"  # set private attr so self.name returns it
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmp = f.name
        base = tmp[: -len(".pdf")]
        try:
            gb.savefig(base, format="pdf")
            self.assertTrue(os.path.isfile(tmp))
        finally:
            plt.close("all")
            if os.path.isfile(tmp):
                os.unlink(tmp)

    def test_savefig_no_fig_suppressed(self):
        """savefig() with fig=None hits the except branch and silently passes."""
        gb = MinGB(nin=1)
        gb.savefig("ignored")  # assert fires → caught by bare except → no raise


# ---------------------------------------------------------------------------
class CreateFigureTest(unittest.TestCase):
    """GraphicsBlock.create_figure() coverage (lines 113-288)."""

    def _make_gb(self):
        gb = MinGB(nin=1)
        gb._bd = MagicMock()
        gb._bd.runtime.DEBUG = lambda *a, **kw: None
        return gb

    def test_create_figure_first_call_agg(self):
        """create_figure() with fignum=0 and Agg backend covers the else-backend branch."""
        gb = self._make_gb()
        state = _make_gstate(tiles="1x1")
        f = gb.create_figure(state)
        self.assertIsInstance(f, matplotlib.figure.Figure)
        self.assertEqual(state.fignum, 1)
        plt.close("all")

    def test_create_figure_second_call(self):
        """create_figure() with fignum>0 covers the 'subsequent figures' else branch."""
        gb1 = self._make_gb()
        gb2 = self._make_gb()
        state = _make_gstate(tiles="1x1")

        f1 = gb1.create_figure(state)  # fignum 0→1; initialises state.figsize etc.
        f2 = gb2.create_figure(state)  # fignum 1→2; uses existing state (else branch)
        self.assertEqual(state.fignum, 2)
        plt.close("all")

    def test_create_figure_2x2_tiles(self):
        """create_figure() with tiles='2x2' exercises different ntiles computation."""
        gb = self._make_gb()
        state = _make_gstate(tiles="2x2")
        f = gb.create_figure(state)
        self.assertEqual(state.ntiles, [2, 2])
        plt.close("all")


if __name__ == "__main__":
    unittest.main()
