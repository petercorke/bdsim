"""Notebook-specific compatibility patches for roboticstoolbox backends.

Problem context
---------------
The ``%matplotlib inline`` backend (the standard Jupyter default) renders
figures eagerly: whenever matplotlib's interactive mode is on, or whenever
``plt.show()`` / ``plt.draw()`` are called, the backend captures all open
figures as PNG blobs and emits them to the cell output, then *closes* them
from ``plt.get_fignums()``.  This is incompatible with bdsim's display-id
mechanism, which needs the figure to remain open across many refresh calls
so that ``handle.update(fig)`` can stream animation frames into a single
output slot.

Solution
--------
Two idempotent monkey-patches are applied at the start of each simulated run
when a notebook backend is detected (see ``bdsim.run_sim``)::

    patch_roboticstoolbox_pyplot_launch_for_notebook()
    patch_roboticstoolbox_armplot_for_notebook()

**PyPlot launch/add patch**: wraps ``PyPlot.launch()`` to suppress
``plt.ion()``, and wraps ``PyPlot.add()`` to suppress the ``plt.draw()`` and
``plt.show()`` calls that would otherwise auto-render and close the 3-D
figure before ``NotebookDisplayManager.show_initial()`` registers it with a
``display_id``.

**ArmPlot step patch**: replaces ``ArmPlot.step()`` with a notebook-aware
version that (a) mirrors the joint-angle vector into the backend robot object,
(b) suppresses ``plt.pause()``, ``plt.draw()``, and ``time.sleep()`` inside
``env.step()``, and (c) calls ``display_manager.refresh()`` to push the
updated 3-D frame to the registered display slot.

Desktop behavior is entirely unaffected: both patches check
``simstate.notebook_backend`` and delegate to the original implementation
when it is ``False``.

Version stamps
--------------
- ``PyPlot._bdsim_launch_patch_version`` — incremented when the launch/add
  patch contract changes.
- ``ArmPlot._bdsim_notebook_patch_version`` — incremented when the step
  patch contract changes.
"""

from __future__ import annotations

from typing import Any


def patch_roboticstoolbox_pyplot_launch_for_notebook() -> None:
    """Prevent ``PyPlot.launch()`` / ``PyPlot.add()`` from auto-displaying figures.

    Background
    ~~~~~~~~~~
    ``PyPlot.launch()`` calls ``plt.ion()`` unconditionally.  In the
    ``%matplotlib inline`` backend, interactive mode causes every subsequent
    canvas draw to invoke ``draw_if_interactive()`` → ``flush_figures()``,
    which renders all open figures as PNG output blobs and then *closes* them
    (removes from ``plt.get_fignums()``).

    ``PyPlot.add()`` also ends with an explicit ``plt.draw()`` +
    ``plt.show(block=False)``, which has the same flush-and-close effect.

    Both events happen *before* ``NotebookDisplayManager.show_initial()``
    gets to register the figure with ``display(fig, display_id=True)``.  The
    result: no display handle exists, ``handle.update(fig)`` is never called,
    and the robot arm is frozen at its initial pose for the entire simulation.

    What this patch does
    ~~~~~~~~~~~~~~~~~~~~
    * Wraps ``PyPlot.launch()``: calls ``plt.ioff()`` before entering the
      original body, and suppresses the ``plt.ion()`` call inside it.
    * Wraps ``PyPlot.add()``: suppresses the ``plt.draw()`` and
      ``plt.show()`` calls at the end of the original body.

    Both wrappers restore all original callables in a ``finally`` block so
    that any exception path leaves matplotlib in a predictable state.

    The patch is idempotent (version-guarded via
    ``PyPlot._bdsim_launch_patch_version``) and silently skips if
    ``roboticstoolbox`` is not installed.
    """
    try:
        from roboticstoolbox.backends.PyPlot.PyPlot import PyPlot
    except Exception:
        return

    patch_version = 1
    if getattr(PyPlot, "_bdsim_launch_patch_version", 0) >= patch_version:
        return

    original_launch = PyPlot.launch
    original_add = PyPlot.add

    def patched_launch(self: Any, name=None, fig=None, limits=None, **kwargs):
        import matplotlib.pyplot as _plt

        # Explicitly disable interactive mode BEFORE launch so that
        # canvas.draw() and artist-creation calls inside launch/add do not
        # trigger draw_if_interactive() → flush_figures() which would
        # auto-display and close the figure.
        _plt.ioff()
        _orig_ion = _plt.ion
        # Also suppress plt.ion() so the launch body cannot re-enable it.
        _plt.ion = lambda: None
        try:
            original_launch(self, name=name, fig=fig, limits=limits, **kwargs)
        finally:
            _plt.ion = _orig_ion
        # Keep non-interactive after launch so that env.add() artist
        # creation is also protected.
        _plt.ioff()

    def patched_add(self: Any, ob, **kwargs):
        import matplotlib.pyplot as _plt

        # PyPlot.add() ends with plt.draw() + plt.show(block=False).
        # In the inline backend plt.show() renders all pending figures and
        # removes them from plt.get_fignums(), destroying our display_id slot
        # before show_initial() has a chance to register it.
        _orig_show = _plt.show
        _orig_draw = _plt.draw
        _plt.show = lambda block=None: None
        _plt.draw = lambda: None
        try:
            return original_add(self, ob, **kwargs)
        finally:
            _plt.show = _orig_show
            _plt.draw = _orig_draw

    PyPlot.launch = patched_launch
    PyPlot.add = patched_add
    setattr(PyPlot, "_bdsim_launch_patch_version", patch_version)


def patch_roboticstoolbox_armplot_for_notebook() -> None:
    """Replace ``ArmPlot.step()`` with a notebook-compatible implementation.

    Background
    ~~~~~~~~~~
    The original ``ArmPlot.step()`` delegates to ``PyPlot.step()``, which
    ends with one of:

    * ``plt.draw(); plt.pause(dt)`` — GUI path (drives the event loop)
    * ``plt.draw(); fig.canvas.draw(); time.sleep(dt)`` — notebook path
      (detected by ``_isnotebook()`` inside roboticstoolbox)

    Both paths call ``plt.draw()``.  In the inline backend that triggers
    ``flush_figures()``, which closes the figure from ``plt.get_fignums()``
    and writes a new PNG output blob — creating a rogue second figure below
    the registered display slot instead of updating it in place.

    What this patch does
    ~~~~~~~~~~~~~~~~~~~~
    When ``simstate.notebook_backend`` is ``True``:

    1. Copies ``inports[0]`` (the joint-angle vector) into both
       ``self.robot.q`` and every ``env.robots[i].robot.q`` to keep the
       backend robot in sync with the block's state.
    2. Computes ``dt`` from the current vs. previous simulation timestamp so
       ``env.step()`` can update the robot's internal kinematic state.
    3. Suppresses ``plt.pause()``, ``plt.draw()``, and ``time.sleep()``
       inside the ``env.step()`` call, then restores them in a ``finally``
       block.
    4. Calls ``display_manager.refresh()`` to push the updated canvas via
       ``handle.update(fig)`` to the registered IPython display slot.

    When ``simstate.notebook_backend`` is ``False`` the original
    ``ArmPlot.step()`` is called unmodified, preserving all desktop behavior.

    The patch is idempotent (version-guarded via
    ``ArmPlot._bdsim_notebook_patch_version``) and silently skips if
    ``roboticstoolbox`` is not installed.
    """
    try:
        import numpy as np
        from roboticstoolbox.blocks.arm import ArmPlot
    except Exception:
        return

    patch_version = 5
    if getattr(ArmPlot, "_bdsim_notebook_patch_version", 0) >= patch_version:
        return

    original_step = getattr(ArmPlot, "_bdsim_original_step", ArmPlot.step)

    def patched_step(self: Any, t: float, inports: list[Any]) -> Any:
        simstate = getattr(self, "_simstate", None)
        if simstate is None:
            simstate = getattr(self, "simstate", None)

        notebook_backend = bool(getattr(simstate, "notebook_backend", False))
        if not notebook_backend:
            # Preserve desktop/MPL behavior exactly.
            return original_step(self, t, inports)

        # Notebook-only step path: keep backend robot reference synchronized,
        # drive env with explicit dt, then force canvas/output refresh.
        q = np.array(inports[0], copy=True)
        self.robot.q = q

        env = getattr(self, "env", None)
        robots = getattr(env, "robots", None)
        if robots:
            for robot_wrapper in robots:
                backend_robot = getattr(robot_wrapper, "robot", None)
                if backend_robot is not None:
                    backend_robot.q = q

        prev_t = getattr(self, "_bdsim_nb_prev_t", None)
        if prev_t is None:
            dt = 0.0
        else:
            dt = max(float(t) - float(prev_t), 0.0)
        self._bdsim_nb_prev_t = float(t)

        # Suppress plt.pause(), plt.draw(), and time.sleep() during env.step().
        # plt.pause() / plt.draw(): in a notebook the PyPlot backend's calls
        #   route through draw_if_interactive() which auto-displays and closes
        #   the figure, breaking our display_id handle mechanism.
        # time.sleep(): real-time pacing is unnecessary in a notebook; the
        #   display_manager.refresh() call already throttles by doing real I/O.
        import matplotlib.pyplot as _plt
        import time as _time

        _orig_pause = _plt.pause
        _orig_draw = _plt.draw
        _orig_sleep = _time.sleep
        _plt.pause = lambda _dt=None: None
        _plt.draw = lambda: None
        _time.sleep = lambda _dt=None: None
        try:
            try:
                self.env.step(dt)
            except TypeError:
                self.env.step()
        finally:
            _plt.pause = _orig_pause
            _plt.draw = _orig_draw
            _time.sleep = _orig_sleep

        # Ensure visible run time in notebook snapshots even when the backend
        # itself does not render a persistent timer text artist.
        ax = getattr(env, "ax", None)
        if ax is not None:
            try:
                ax.set_title(f"t={float(t):.2f}")
            except Exception:
                pass

        # Push the updated 3D figure directly to the notebook output slot.
        # This is tightly coupled to each ArmPlot step rather than relying
        # on the animation frame callback timing.
        display_manager = getattr(simstate, "display_manager", None)
        if display_manager is not None:
            display_manager.refresh()

        return None

    setattr(ArmPlot, "_bdsim_original_step", original_step)
    ArmPlot.step = patched_step
    setattr(ArmPlot, "_bdsim_notebook_patch_applied", True)
    setattr(ArmPlot, "_bdsim_notebook_patch_version", patch_version)
