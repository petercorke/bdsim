"""Centralized display policy for matplotlib figures in bdsim.

This module keeps all backend-specific display and update logic in one place so
that simulation loops and graphics blocks can stay focused on data.

Three concrete managers are provided:

``MatplotlibDisplayManager``
    Used for interactive GUI backends (Qt, Tk, macOS, …).  Calls
    ``plt.show(block=False)`` once to open windows, drives redraws via
    ``draw_idle()`` / ``flush_events()``, and optionally blocks at the end of
    a run with ``plt.show(block=True)``.

``WidgetDisplayManager``
    Used for the interactive notebook backends (``%matplotlib widget``, ipympl,
    nbagg).  Shows each figure's live canvas once and redraws it in place, and
    leaves it open at the end of the run so the toolbar, zoom and data cursors
    keep working.

``NotebookDisplayManager``
    Used when ``%matplotlib inline`` (or any non-interactive IPython backend)
    is active.  Instead of relying on matplotlib's event loop it uses IPython's
    *display-id* mechanism::

        handle = display(fig, display_id=True)   # show_initial()
        handle.update(fig)                        # refresh()

    Each ``update()`` call sends an ``update_display_data`` IOPub message that
    replaces the previously-rendered figure in the cell output without appending
    a new one.  This gives smooth in-place animation with the default
    ``%matplotlib inline`` backend — no ipywidgets or ipympl required.

    At the end of a run ``finalize()`` renders one last frame then calls
    ``plt.close()`` on every registered figure.  Closing is necessary because
    Jupyter auto-renders all *open* figures when a cell finishes executing,
    which would produce a duplicate static image after the last animated frame.

Lifecycle
---------
``BDSim.run()`` in ``run_sim.py`` creates one manager per run::

    simstate.display_manager = DisplayManager.create(
        notebook_backend=simstate.notebook_backend
    )

and calls the three lifecycle methods at the appropriate points:

1. ``show_initial()`` — called once, just before the animation loop starts,
   so figures appear between the simulation-start banner and any progress
   output.
2. ``refresh()`` — called from animation frame callbacks (and, for ArmPlot,
   directly from the patched ``step()`` method in ``notebook_patches``).
3. ``finalize(hold)`` — called at the end of the run.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Iterable

import matplotlib.pyplot as plt


def _grab_movie_frame(fig: Any) -> None:
    """Grab one frame for any MP4 writer attached to ``fig``.

    The writer is set on ``fig._bdsim_movie_writer`` by
    ``GraphicsBlock._start_movie`` when a movie path is configured. Co-locating
    the grab with the display refresh keeps the movie's frame cadence on the
    fps grid (the same hook that drives ``flush_events()`` for live windows),
    regardless of how many sink ticks the integrator emits in between.
    """
    writer = getattr(fig, "_bdsim_movie_writer", None)
    if writer is None:
        return
    try:
        writer.grab_frame()
    except AttributeError as exc:
        raise RuntimeError("cannot save movie, please install ffmpeg") from exc


def is_widget_backend(backend: str) -> bool:
    """Return True if *backend* is an interactive notebook backend.

    These keep a live canvas in the cell output (ipympl, nbagg), as opposed to
    ``inline`` which only renders PNG snapshots.  Matplotlib reports the ipympl
    backend as ``widget`` or ``module://ipympl.backend_nbagg`` depending on how
    it was selected.
    """
    name = backend.lower()
    return name == "widget" or "ipympl" in name or "nbagg" in name


class DisplayManager:
    """Abstract base class and factory for bdsim display managers.

    Subclasses implement three lifecycle methods called by the simulation
    runtime:

    * ``show_initial()`` — make figures visible before animation begins.
    * ``refresh()`` — push the current canvas state to the display.
    * ``finalize(hold)`` — handle end-of-run display (optionally blocking).

    Use ``DisplayManager.create(notebook_backend=...)`` rather than
    instantiating a subclass directly.
    """

    notebook_backend = False

    def __init__(self) -> None:
        self._shown_once = False

    @classmethod
    def create(
        cls, notebook_backend: bool = False, backend: str = ""
    ) -> DisplayManager:
        """Return the appropriate ``DisplayManager`` subclass.

        Parameters
        ----------
        notebook_backend:
            ``True`` when ``matplotlib.get_backend()`` indicates an inline or
            non-interactive IPython backend (detected in ``run_sim.py``).
            Returns a ``NotebookDisplayManager``; otherwise returns a
            ``MatplotlibDisplayManager``.
        backend:
            The matplotlib backend name.  With ``notebook_backend`` true, an
            interactive one (ipympl, nbagg) gives a ``WidgetDisplayManager``.
        """
        if notebook_backend:
            if is_widget_backend(backend):
                return WidgetDisplayManager()
            return NotebookDisplayManager()
        return MatplotlibDisplayManager()

    @staticmethod
    def _iter_figures() -> Iterable[Any]:
        for num in plt.get_fignums():
            yield plt.figure(num)

    @classmethod
    def _iter_display_figures(cls) -> Iterable[Any]:
        figs = list(cls._iter_figures())
        figs_with_axes = [fig for fig in figs if len(getattr(fig, "axes", [])) > 0]
        for fig in figs_with_axes:
            yield fig

    def show_initial(self) -> None:
        """Make existing figures visible before frame updates begin."""
        raise NotImplementedError()

    def refresh(self) -> None:
        """Refresh all current figures according to backend policy."""
        raise NotImplementedError()

    def finalize(self, hold: bool = False) -> None:
        """Perform final display update at end-of-run."""
        raise NotImplementedError()

    def pace(self, t: float) -> None:
        """Called after each animation frame, at simulation time *t* (s).

        A manager can block here to slow the simulation down to a speed that can
        be watched.  The default does nothing.
        """

    def refresh_figure(self, fig: Any) -> None:
        """Refresh a specific figure according to backend policy."""
        raise NotImplementedError()


class NotebookDisplayManager(DisplayManager):
    """Display policy for ``%matplotlib inline`` and similar notebook backends.

    Uses IPython's *display-id* mechanism to stream animated figure updates
    into a single cell output slot without requiring ipywidgets or ipympl.

    How it works
    ~~~~~~~~~~~~
    ``show_initial()`` calls ``display(fig, display_id=True)`` for each open
    figure.  IPython emits a ``display_data`` IOPub message and returns a
    ``DisplayHandle`` whose ``update()`` method sends a subsequent
    ``update_display_data`` message that *replaces* the earlier PNG blob in
    the frontend rather than appending a new one.

    ``refresh()`` calls ``fig.canvas.draw()`` to force a rasterisation pass,
    then ``handle.update(fig)`` to push the result to the output slot.

    ``finalize()`` renders a final frame then closes all registered figures.
    Closing is required because Jupyter auto-renders every *open* figure when
    a cell finishes executing, which would produce a duplicate static image
    after the last animated frame.

    Compatibility
    ~~~~~~~~~~~~~
    Works in VS Code Jupyter, classic Jupyter Notebook, JupyterLab, and
    JupyterLite.  The ``%matplotlib inline`` magic (default in all of the
    above) is sufficient — no extra setup is required.
    """

    notebook_backend = True

    def __init__(self) -> None:
        super().__init__()
        # Maps id(fig) → IPython DisplayHandle (has .update(obj) method).
        # Figure numbers are not stable identities in notebook backends:
        # a closed figure can be replaced by a new figure with the same number.
        self._display_handles: dict[int, Any] = {}
        self._warned_missing_handle: set[int] = set()

    @staticmethod
    def _figure_key(fig: Any) -> int:
        return id(fig)

    @staticmethod
    def _display_figure(fig: Any) -> Any:
        """Return an IPython display handle for *fig*, or None if unavailable."""
        try:
            from IPython.display import display
        except ImportError:
            return None
        return display(fig, display_id=True)

    def _ensure_handle(self, fig: Any) -> Any:
        """Get or lazily create a display handle for *fig*."""
        key = self._figure_key(fig)
        handle = self._display_handles.get(key)
        if handle is not None:
            return handle

        try:
            fig.canvas.draw()
            handle = self._display_figure(fig)
        except Exception:
            handle = None

        if handle is not None:
            self._display_handles[key] = handle
            self._warned_missing_handle.discard(key)
        return handle

    def show_initial(self) -> None:
        """Register each open figure with a ``display_id`` and show it.

        Must be called exactly once, before ``refresh()`` is invoked.
        Calling it a second time is a no-op (``_shown_once`` guard).

        The call is placed between the simulation-start banner and the main
        loop so that the figure slot appears at the correct vertical position
        in the cell output.
        """
        if self._shown_once:
            return
        for fig in self._iter_display_figures():
            self._ensure_handle(fig)
        self._shown_once = True

    def refresh(self) -> None:
        """Push the current canvas state to the registered display slot.

        Calls ``fig.canvas.draw()`` to rasterise pending artist updates, then
        ``handle.update(fig)`` which sends an ``update_display_data`` IOPub
        message.  The Jupyter frontend replaces the earlier PNG blob in-place,
        producing the animation effect.

        Figures that were never registered by ``show_initial()`` are silently
        skipped (e.g. figures created after the initial call).
        """
        for fig in self._iter_display_figures():
            handle = self._ensure_handle(fig)
            if handle is None:
                key = self._figure_key(fig)
                if key not in self._warned_missing_handle:
                    self._warned_missing_handle.add(key)
                continue
            try:
                fig.canvas.draw()
                handle.update(fig)
            except Exception:
                pass
            _grab_movie_frame(fig)

    def refresh_figure(self, fig: Any) -> None:
        """Refresh one figure, including figures not listed by pyplot."""
        handle = self._ensure_handle(fig)
        if handle is None:
            key = self._figure_key(fig)
            if key not in self._warned_missing_handle:
                self._warned_missing_handle.add(key)
            return
        try:
            fig.canvas.draw()
            handle.update(fig)
        except Exception:
            pass
        _grab_movie_frame(fig)

    def finalize(self, hold: bool = False) -> None:
        """Render a final frame and close all registered figures.

        The ``hold`` parameter is ignored for notebook backends (there is no
        blocking event loop to enter).  Closing figures prevents Jupyter from
        auto-rendering them again at cell-end, which would append a redundant
        static image after the last animated frame.
        """
        self.refresh()
        for fig in list(self._iter_display_figures()):
            try:
                plt.close(fig)
            except Exception:
                pass


class WidgetDisplayManager(DisplayManager):
    """Display policy for the interactive notebook backends, ``%matplotlib widget``.

    With ipympl a figure is a live widget: it has a toolbar, zoom, pan and data
    cursors.  So unlike :class:`NotebookDisplayManager` there are no snapshots
    and no ``display_id``; the canvas is displayed once and redrawn in place.

    * ``show_initial()`` displays each figure's canvas, once.
    * ``refresh()`` calls ``canvas.draw()``, which renders and sends the frame to
      the browser immediately.  ``draw_idle()`` is not used: with ipympl it only
      asks the browser to request a draw, and the kernel cannot answer that
      while it is busy running the simulation.
    * ``finalize()`` draws the last frame and leaves the figures open, since
      closing them would discard the live canvas.

    A manager draws only the figures it first saw, since earlier runs' figures
    are still open.

    Each frame is a full raw RGBA image, over a megabyte for a default figure, and
    nothing slows the sender down: ipympl's acknowledgements cannot be processed while
    the kernel is busy running the simulation.  A simulation that runs faster than
    real time would flood the browser, which then falls behind and shows only the
    first frames until the end of the run.  So frames are pushed at most every
    :attr:`min_interval` seconds of wall-clock time; the final frame always is.  The
    animation is paced to play at :attr:`speed` times real time.
    """

    notebook_backend = True

    #: shortest wall-clock time between pushed frames (s)
    min_interval: float = 0.04

    #: simulated seconds per second of wall-clock time while animating, 1 is real
    #: time, ``None`` runs as fast as the frames can be drawn
    speed: float | None = 1.0

    #: delay before the final redraw that follows a run (s)
    settle_delay: float = 1.0

    def __init__(self) -> None:
        super().__init__()
        self._last_push: float | None = None
        self._wall_start: float | None = None

    def _figures(self) -> Iterable[Any]:
        """The figures of this run.

        Figures are left open at the end of a run, so earlier runs' figures are
        still open.  A figure belongs to the first manager that sees it, and a
        manager only draws its own.
        """
        for fig in self._iter_display_figures():
            owner = getattr(fig, "_bdsim_widget_owner", None)
            if owner is None:
                fig._bdsim_widget_owner = self
                owner = self
            if owner is self:
                yield fig

    @staticmethod
    def _show(fig: Any) -> None:
        """Display the canvas of *fig* in the cell output, once."""
        if getattr(fig, "_bdsim_widget_shown", False):
            return
        fig._bdsim_widget_shown = True
        manager = fig.canvas.manager
        if manager is None:
            return
        manager.show()  # ipympl: displays the canvas the first time it is called
        try:
            # ipympl also queues a new figure to be displayed when the cell ends,
            # which would give a second view of the same figure
            from ipympl.backend_nbagg import _Backend_ipympl

            _Backend_ipympl._to_show.remove(fig)
        except (ImportError, AttributeError, ValueError):
            pass

    def show_initial(self) -> None:
        if self._shown_once:
            return
        for fig in self._figures():
            self._show(fig)
        self._shown_once = True

    def _draw(self, fig: Any) -> None:
        self._show(fig)  # a no-op, unless the figure was created after show_initial()
        fig.canvas.draw()
        _grab_movie_frame(fig)

    def pace(self, t: float) -> None:
        """Sleep so that the animation plays at :attr:`speed`.

        Simulation is usually far faster than real time, so without this the frames
        of an animation are all sent within a fraction of a second.
        """
        if self.speed is None:
            return
        now = time.monotonic()
        if self._wall_start is None:
            self._wall_start = now - t / self.speed  # the first frame sets the origin
        delay = self._wall_start + t / self.speed - now
        if delay > 0:
            time.sleep(delay)

    def _due(self) -> bool:
        """True if enough wall-clock time has passed to push another frame."""
        now = time.monotonic()
        if self._last_push is not None and now - self._last_push < self.min_interval:
            return False
        self._last_push = now
        return True

    def refresh(self) -> None:
        if not self._due():
            return
        for fig in self._figures():
            self._draw(fig)

    def refresh_figure(self, fig: Any) -> None:
        if self._due():
            self._draw(fig)

    def finalize(self, hold: bool = False) -> None:
        figs = list(self._figures())
        for fig in figs:
            self._draw(fig)
        for fig in figs:
            # The draw above was made while the kernel was busy, possibly before the
            # browser had created and sized the view.  Ask the browser for a fresh
            # draw, which it can answer now that the kernel is about to be idle.
            fig.canvas.draw_idle()
        self._schedule_final_redraw(figs)

    def _schedule_final_redraw(self, figs: list[Any]) -> None:
        """Redraw the figures once, after the cell has finished.

        A figure is displayed while the kernel is busy running the simulation, so the
        browser's start-up handshake (device pixel ratio, size, a request for the
        image) is queued behind the run and is only answered when the cell ends.  The
        frames sent in the meantime can be drawn at the wrong size, or lost, and a
        slow browser may be left with a blank or partly drawn figure.  A full redraw
        scheduled on the kernel's event loop runs after the queued handshake has been
        answered.  Without an event loop (not in a kernel) there is nothing to do.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                return

        def redraw() -> None:
            for fig in figs:
                if fig.number not in plt.get_fignums():
                    continue  # closed in the meantime
                # the browser may have changed the size: send the whole image
                fig.canvas._force_full = True  # type: ignore[attr-defined]
                fig.canvas.draw()

        loop.call_later(self.settle_delay, redraw)


class MatplotlibDisplayManager(DisplayManager):
    """Display policy for interactive matplotlib GUI backends (Qt, Tk, macOS, …)."""

    notebook_backend = False

    def show_initial(self) -> None:
        if self._shown_once:
            return
        plt.show(block=False)
        for fig in self._iter_figures():
            try:
                fig.canvas.flush_events()
            except Exception:
                pass
        self._shown_once = True

    def refresh(self) -> None:
        for fig in self._iter_figures():
            fig.canvas.draw_idle()
            fig.canvas.flush_events()
            _grab_movie_frame(fig)

    def refresh_figure(self, fig: Any) -> None:
        fig.canvas.draw_idle()
        fig.canvas.flush_events()
        _grab_movie_frame(fig)

    def finalize(self, hold: bool = False) -> None:
        if hold:
            plt.show(block=True)
