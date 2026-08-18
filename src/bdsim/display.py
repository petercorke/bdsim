"""Centralized display policy for matplotlib figures in bdsim.

This module keeps all backend-specific display and update logic in one place so
that simulation loops and graphics blocks can stay focused on data.

Two concrete managers are provided:

``MatplotlibDisplayManager``
    Used for interactive GUI backends (Qt, Tk, macOS, …).  Calls
    ``plt.show(block=False)`` once to open windows, drives redraws via
    ``draw_idle()`` / ``flush_events()``, and optionally blocks at the end of
    a run with ``plt.show(block=True)``.

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

from typing import Any, Iterable

import matplotlib
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
    def create(cls, notebook_backend: bool = False) -> DisplayManager:
        """Return the appropriate ``DisplayManager`` subclass.

        Parameters
        ----------
        notebook_backend:
            ``True`` when ``matplotlib.get_backend()`` indicates an inline or
            non-interactive IPython backend (detected in ``run_sim.py``).
            Returns a ``NotebookDisplayManager``; otherwise returns a
            ``MatplotlibDisplayManager``.
        """
        if notebook_backend:
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
