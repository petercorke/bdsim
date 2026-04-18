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


def _make_simstate(graphics=True, animation=False, backend="agg"):
    ss = MagicMock()
    ss.options.graphics = graphics
    ss.options.animation = animation
    ss.backend = backend
    return ss


def _make_gstate(tiles=None):
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
        gb._bd.blocklist = [gb]
        return gb

    def test_create_figure_first_call_agg(self):
        """create_figure() with fignum=0 and Agg backend covers the else-backend branch."""
        gb = self._make_gb()
        state = _make_gstate()
        f = gb.create_figure(state)
        self.assertIsInstance(f, matplotlib.figure.Figure)
        self.assertEqual(state.fignum, 1)
        plt.close("all")

    def test_create_figure_second_call(self):
        """create_figure() with fignum>0 covers the 'subsequent figures' else branch."""
        gb1 = self._make_gb()
        gb2 = self._make_gb()
        state = _make_gstate()

        f1 = gb1.create_figure(state)  # fignum 0→1; initialises state.figsize etc.
        f2 = gb2.create_figure(
            state
        )  # fignum 1→2; creates a new figure in untiled mode
        self.assertEqual(state.fignum, 2)
        self.assertNotEqual(f1.number, f2.number)
        plt.close("all")

    def test_create_figure_2x2_tiles(self):
        """create_figure() with tiles='2x2' exercises different ntiles computation."""
        gb = self._make_gb()
        state = _make_gstate(tiles="2x2")
        f = gb.create_figure(state)
        self.assertEqual(state.ntiles, [2, 2])
        plt.close("all")

    def test_create_figure_tiled_reuses_single_figure(self):
        """Tiled mode assigns each graphics block a subplot within one shared figure."""
        gb1 = self._make_gb()
        gb2 = self._make_gb()
        state = _make_gstate(tiles="1x2")

        f1 = gb1.create_figure(state)
        f2 = gb2.create_figure(state)

        self.assertEqual(f1.number, f2.number)
        self.assertIsNotNone(getattr(gb1, "_tile_axes", None))
        self.assertIsNotNone(getattr(gb2, "_tile_axes", None))
        plt.close("all")

    def test_create_figure_tiled_overflow_raises(self):
        """Option C: more graphics blocks than tiles should fail with ValueError."""
        gb1 = self._make_gb()
        gb2 = self._make_gb()
        state = _make_gstate(tiles="1x1")

        gb1.create_figure(state)
        with self.assertRaises(ValueError):
            gb2.create_figure(state)
        plt.close("all")

    def test_create_figure_square_tiles_keyword(self):
        """tiles='square' computes a near-square layout from graphics block count."""
        gb = self._make_gb()
        gb._bd.blocklist = [
            MagicMock(isgraphics=True),
            MagicMock(isgraphics=True),
            MagicMock(isgraphics=True),
        ]
        state = _make_gstate(tiles="square")
        f = gb.create_figure(state)
        self.assertEqual(state.ntiles, [2, 2])
        plt.close("all")

    def test_create_figure_wide_tiles_keyword(self):
        """tiles='wide' creates a single-row layout sized to graphics block count."""
        gb = self._make_gb()
        gb._bd.blocklist = [
            MagicMock(isgraphics=True),
            MagicMock(isgraphics=True),
            MagicMock(isgraphics=True),
        ]
        state = _make_gstate(tiles="wide")
        f = gb.create_figure(state)
        self.assertEqual(state.ntiles, [1, 3])
        plt.close("all")

    def test_create_figure_tall_tiles_keyword(self):
        """tiles='tall' creates a single-column layout sized to graphics block count."""
        gb = self._make_gb()
        gb._bd.blocklist = [
            MagicMock(isgraphics=True),
            MagicMock(isgraphics=True),
            MagicMock(isgraphics=True),
        ]
        state = _make_gstate(tiles="tall")
        f = gb.create_figure(state)
        self.assertEqual(state.ntiles, [3, 1])
        plt.close("all")

    def test_create_figure_invalid_backend_error_is_actionable(self):
        """Invalid backend names should raise a clear RuntimeError with guidance."""
        gb = self._make_gb()
        state = _make_gstate()
        state.options.backend = "DefinitelyNotARealBackend"

        with self.assertRaises(RuntimeError) as cm:
            gb.create_figure(state)
        self.assertIn("can't select matplotlib backend", str(cm.exception))


from bdsim.block import is_notebook_backend


# ---------------------------------------------------------------------------
class IsNotebookBackendTest(unittest.TestCase):
    """Unit tests for is_notebook_backend() helper."""

    # --- names that ARE notebook backends ---
    def test_module_prefix(self):
        self.assertTrue(
            is_notebook_backend("module://matplotlib_inline.backend_inline")
        )

    def test_module_prefix_ipympl(self):
        self.assertTrue(is_notebook_backend("module://ipympl.backend_nbagg"))

    def test_inline_lowercase(self):
        self.assertTrue(is_notebook_backend("inline"))

    def test_inline_uppercase(self):
        # matplotlib sometimes normalises to mixed case
        self.assertTrue(is_notebook_backend("Inline"))

    def test_widget(self):
        self.assertTrue(is_notebook_backend("widget"))

    def test_widget_uppercase(self):
        self.assertTrue(is_notebook_backend("Widget"))

    def test_nbagg(self):
        self.assertTrue(is_notebook_backend("nbagg"))

    def test_nbagg_uppercase(self):
        self.assertTrue(is_notebook_backend("NbAgg"))

    # --- names that are NOT notebook backends ---
    def test_qtAgg(self):
        self.assertFalse(is_notebook_backend("QtAgg"))

    def test_qt5agg(self):
        self.assertFalse(is_notebook_backend("Qt5Agg"))

    def test_tkagg(self):
        self.assertFalse(is_notebook_backend("TkAgg"))

    def test_agg(self):
        self.assertFalse(is_notebook_backend("agg"))

    def test_macosx(self):
        self.assertFalse(is_notebook_backend("MacOSX"))

    def test_empty_string(self):
        self.assertFalse(is_notebook_backend(""))


# ---------------------------------------------------------------------------
class NotebookBackendNoSwitchTest(unittest.TestCase):
    """create_figure() must not call matplotlib.use() when a notebook backend is active."""

    def _make_gb(self):
        gb = MinGB(nin=1)
        gb._bd = MagicMock()
        gb._bd.runtime.DEBUG = lambda *a, **kw: None
        gb._bd.blocklist = [gb]
        return gb

    def _run_create_figure_with_backend(self, backend_name):
        gb = self._make_gb()
        state = _make_gstate()
        with patch("matplotlib.get_backend", return_value=backend_name), patch(
            "matplotlib.use"
        ) as mock_use:
            gb.create_figure(state)
            return mock_use

    def test_inline_does_not_call_matplotlib_use(self):
        mock_use = self._run_create_figure_with_backend("inline")
        mock_use.assert_not_called()

    def test_module_inline_does_not_call_matplotlib_use(self):
        mock_use = self._run_create_figure_with_backend(
            "module://matplotlib_inline.backend_inline"
        )
        mock_use.assert_not_called()

    def test_widget_does_not_call_matplotlib_use(self):
        mock_use = self._run_create_figure_with_backend("widget")
        mock_use.assert_not_called()

    def test_nbagg_does_not_call_matplotlib_use(self):
        mock_use = self._run_create_figure_with_backend("nbagg")
        mock_use.assert_not_called()

    def test_notebook_backend_sets_gstate_flag(self):
        """gstate.notebook_backend is True when a notebook backend is active."""
        gb = self._make_gb()
        state = _make_gstate()
        with patch("matplotlib.get_backend", return_value="inline"):
            gb.create_figure(state)
        self.assertTrue(state.notebook_backend)

    def test_non_notebook_backend_gstate_flag_false(self):
        """gstate.notebook_backend is False for a regular Agg/Qt backend."""
        gb = self._make_gb()
        state = _make_gstate()
        # Agg is already active (set at module level above); no patching needed
        gb.create_figure(state)
        self.assertFalse(state.notebook_backend)
        plt.close("all")


if __name__ == "__main__":
    unittest.main()
