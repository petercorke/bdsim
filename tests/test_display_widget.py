"""
The display manager for the interactive notebook backend, ``%matplotlib widget``.

The real ipympl canvas needs a Jupyter kernel and a browser, so these tests use a
stand-in canvas to check the policy: which manager is chosen, what is drawn, and that the
figure is left open at the end of a run.  The kernel side is exercised by running a
notebook, see the pull request.
"""

from __future__ import annotations

import unittest
from unittest import mock

import matplotlib
import matplotlib.pyplot as plt

from bdsim.display import (
    DisplayManager,
    MatplotlibDisplayManager,
    NotebookDisplayManager,
    WidgetDisplayManager,
    is_widget_backend,
)


class FactoryTest(unittest.TestCase):
    def test_is_widget_backend(self) -> None:
        for name in ("widget", "module://ipympl.backend_nbagg", "nbAgg"):
            self.assertTrue(is_widget_backend(name), name)
        for name in (
            "inline",
            "module://matplotlib_inline.backend_inline",
            "Agg",
            "QtAgg",
        ):
            self.assertFalse(is_widget_backend(name), name)

    def test_create_chooses_by_backend(self) -> None:
        cases = [
            (True, "widget", WidgetDisplayManager),
            (True, "module://ipympl.backend_nbagg", WidgetDisplayManager),
            (True, "inline", NotebookDisplayManager),
            (True, "", NotebookDisplayManager),
            (False, "QtAgg", MatplotlibDisplayManager),
            (
                False,
                "widget",
                MatplotlibDisplayManager,
            ),  # notebook_backend decides first
        ]
        for notebook, backend, expected in cases:
            manager = DisplayManager.create(notebook_backend=notebook, backend=backend)
            self.assertIs(type(manager), expected, (notebook, backend))


class WidgetManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        # other tests depend on the backend, so put it back afterwards
        original = matplotlib.get_backend()
        self.addCleanup(plt.switch_backend, original)
        plt.switch_backend("Agg")
        plt.close("all")
        self.fig, ax = plt.subplots()
        ax.plot([0, 1])
        # the Agg canvas has a manager but no widget to show
        self.manager_show = mock.patch.object(self.fig.canvas.manager, "show").start()
        self.draw = mock.patch.object(self.fig.canvas, "draw").start()
        # on the Agg canvas draw_idle() calls draw(), which the tests count
        mock.patch.object(self.fig.canvas, "draw_idle").start()
        self.addCleanup(mock.patch.stopall)
        self.addCleanup(plt.close, "all")

    def test_shown_once_drawn_each_refresh(self) -> None:
        wm = WidgetDisplayManager()
        wm.min_interval = 0.0  # no limit on the rate
        wm.show_initial()
        wm.show_initial()  # second call does nothing
        wm.refresh()
        wm.refresh()
        self.assertEqual(self.manager_show.call_count, 1)
        self.assertEqual(self.draw.call_count, 2)

    def test_frames_are_limited_by_wall_clock_time(self) -> None:
        wm = WidgetDisplayManager()
        wm.show_initial()
        with mock.patch("bdsim.display.time.monotonic") as clock:
            clock.return_value = 100.0
            wm.refresh()  # pushed
            clock.return_value = 100.0 + wm.min_interval / 2
            wm.refresh()  # too soon
            clock.return_value = 100.0 + 2 * wm.min_interval
            wm.refresh()  # pushed
        self.assertEqual(self.draw.call_count, 2)

    def test_finalize_always_draws(self) -> None:
        wm = WidgetDisplayManager()
        wm.show_initial()
        wm.refresh()  # starts the interval
        n = self.draw.call_count
        wm.finalize()  # well inside the interval, still drawn
        self.assertEqual(self.draw.call_count, n + 1)

    def test_earlier_runs_figures_are_not_redrawn(self) -> None:
        first = WidgetDisplayManager()
        first.show_initial()
        old_draws = self.draw.call_count
        # a second run: the first run's figure is still open
        second_fig, ax = plt.subplots()
        ax.plot([0, 1])
        with mock.patch.object(second_fig.canvas.manager, "show"):
            with mock.patch.object(second_fig.canvas, "draw") as new_draw:
                second = WidgetDisplayManager()
                second.show_initial()
                second.refresh()
        self.assertEqual(
            self.draw.call_count, old_draws
        )  # the old figure is left alone
        self.assertEqual(new_draw.call_count, 1)

    def test_pace_makes_the_animation_play_at_the_set_speed(self) -> None:
        wm = WidgetDisplayManager()
        sleeps: list[float] = []
        with (
            mock.patch("bdsim.display.time.monotonic") as clock,
            mock.patch("bdsim.display.time.sleep", side_effect=sleeps.append),
            mock.patch.object(WidgetDisplayManager, "speed", 2.0),
        ):
            clock.return_value = 50.0
            wm.pace(1.0)  # the first frame sets the origin: no sleep
            clock.return_value = 50.1
            wm.pace(2.0)  # 1 s later in simulation, 0.5 s of wall time at 2x
        self.assertEqual(len(sleeps), 1)
        self.assertAlmostEqual(sleeps[0], 0.4)

    def test_pace_does_not_sleep_when_behind_or_unpaced(self) -> None:
        with (
            mock.patch("bdsim.display.time.monotonic") as clock,
            mock.patch("bdsim.display.time.sleep") as sleep,
        ):
            wm = WidgetDisplayManager()
            clock.return_value = 0.0
            wm.pace(0.0)
            clock.return_value = 10.0  # drawing took longer than the simulated time
            wm.pace(1.0)
            sleep.assert_not_called()
            with mock.patch.object(WidgetDisplayManager, "speed", None):
                wm.pace(100.0)
            sleep.assert_not_called()

    def test_finalize_schedules_a_full_redraw_after_the_cell(self) -> None:
        wm = WidgetDisplayManager()
        wm.show_initial()
        loop = mock.Mock()
        with mock.patch("bdsim.display.asyncio.get_running_loop", return_value=loop):
            wm.finalize()
        loop.call_later.assert_called_once()
        delay, redraw = loop.call_later.call_args.args
        self.assertEqual(delay, wm.settle_delay)
        n = self.draw.call_count
        redraw()  # what the event loop will run
        self.assertEqual(self.draw.call_count, n + 1)
        self.assertTrue(self.fig.canvas._force_full)

    def test_deferred_redraw_skips_a_closed_figure(self) -> None:
        wm = WidgetDisplayManager()
        wm.show_initial()
        loop = mock.Mock()
        with mock.patch("bdsim.display.asyncio.get_running_loop", return_value=loop):
            wm.finalize()
        redraw = loop.call_later.call_args.args[1]
        n = self.draw.call_count
        plt.close(self.fig)
        redraw()
        self.assertEqual(self.draw.call_count, n)

    def test_no_event_loop_is_not_an_error(self) -> None:
        wm = WidgetDisplayManager()
        wm.show_initial()
        with (
            mock.patch(
                "bdsim.display.asyncio.get_running_loop", side_effect=RuntimeError
            ),
            mock.patch(
                "bdsim.display.asyncio.get_event_loop", side_effect=RuntimeError
            ),
        ):
            wm.finalize()  # must not raise

    def test_finalize_asks_the_browser_for_a_fresh_draw(self) -> None:
        wm = WidgetDisplayManager()
        wm.show_initial()
        with mock.patch.object(self.fig.canvas, "draw_idle") as idle:
            wm.finalize()
        idle.assert_called_once()

    def test_figure_created_later_is_shown(self) -> None:
        wm = WidgetDisplayManager()
        wm.refresh()  # no show_initial() first
        self.assertEqual(self.manager_show.call_count, 1)

    def test_finalize_leaves_figure_open(self) -> None:
        wm = WidgetDisplayManager()
        wm.show_initial()
        wm.finalize()
        self.assertIn(self.fig.number, plt.get_fignums())
        self.assertGreaterEqual(self.draw.call_count, 1)

    def test_inline_manager_closes_figure(self) -> None:
        # the contrast: this is why a widget needs its own manager
        nm = NotebookDisplayManager()
        with mock.patch.object(
            NotebookDisplayManager, "_ensure_handle", return_value=None
        ):
            nm.finalize()
        self.assertNotIn(self.fig.number, plt.get_fignums())


if __name__ == "__main__":
    unittest.main()
