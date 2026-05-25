#!/usr/bin/env python3
"""Tests for bdsim.notebook_patches.

All tests use lightweight stubs so that roboticstoolbox is not required in the
test environment.  Each test re-imports the module after patching sys.modules
so that the version guards start from zero.
"""

from __future__ import annotations

import sys
import importlib
import types
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")  # headless — no GUI window


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fresh_nbp():
    """Return a freshly-imported copy of notebook_patches with a clean module cache."""
    mod_name = "bdsim.notebook_patches"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    import bdsim.notebook_patches as nbp

    return nbp


def _make_simstate(notebook_backend: bool = True) -> Any:
    return SimpleNamespace(notebook_backend=notebook_backend, display_manager=None)


# ---------------------------------------------------------------------------
# PyPlot launch / add patch
# ---------------------------------------------------------------------------


class _FakePyPlot:
    """Minimal stand-in for roboticstoolbox.backends.PyPlot.PyPlot."""

    launch_calls: list[dict]
    add_calls: list[Any]

    def __init__(self):
        self.launch_calls = []
        self.add_calls = []
        self._inline_is_jl = False

    def launch(self, name=None, fig=None, ax=None, limits=None, **kwargs):
        import matplotlib.pyplot as _plt

        # Mimic the real PyPlot.launch(): call plt.ion() then set _inline_is_jl
        # as the real launch does (sys.platform == "emscripten").
        _plt.ion()
        # Simulate JupyterLite: pretend platform is emscripten.
        self._inline_is_jl = True
        self.launch_calls.append({"name": name, "fig": fig, "ax": ax, "limits": limits})

    def add(self, ob, **kwargs):
        import matplotlib.pyplot as _plt

        # Mimic the real PyPlot.add(): end with plt.draw() + plt.show()
        _plt.draw()
        _plt.show(block=False)
        self.add_calls.append(ob)
        return len(self.add_calls)


def _install_fake_pyplot(monkeypatch, cls):
    """Install *cls* as roboticstoolbox.backends.PyPlot.PyPlot in sys.modules."""
    pkg = types.ModuleType("roboticstoolbox")
    backends = types.ModuleType("roboticstoolbox.backends")
    pyplot_pkg = types.ModuleType("roboticstoolbox.backends.PyPlot")
    pyplot_mod = types.ModuleType("roboticstoolbox.backends.PyPlot.PyPlot")
    pyplot_mod.PyPlot = cls
    for name, mod in [
        ("roboticstoolbox", pkg),
        ("roboticstoolbox.backends", backends),
        ("roboticstoolbox.backends.PyPlot", pyplot_pkg),
        ("roboticstoolbox.backends.PyPlot.PyPlot", pyplot_mod),
    ]:
        monkeypatch.setitem(sys.modules, name, mod)


def test_pyplot_launch_patch_suppresses_ion(monkeypatch):
    """After patching, plt.ion() inside launch() does NOT turn on interactive mode."""
    cls = type("PyPlot", (_FakePyPlot,), {})
    _install_fake_pyplot(monkeypatch, cls)

    nbp = _fresh_nbp()
    nbp.patch_roboticstoolbox_pyplot_launch_for_notebook()

    plt.ioff()
    instance = cls()
    instance.launch(name="test")

    assert not matplotlib.is_interactive(), "plt.ion() should have been suppressed"


def test_pyplot_launch_patch_reuses_existing_3d_axes(monkeypatch):
    """If the figure already has 3D axes, patched_launch passes them to original launch."""
    cls = type("PyPlot", (_FakePyPlot,), {})
    _install_fake_pyplot(monkeypatch, cls)

    nbp = _fresh_nbp()
    nbp.patch_roboticstoolbox_pyplot_launch_for_notebook()

    fig = plt.figure()
    ax3d = fig.add_subplot(111, projection="3d")
    instance = cls()
    instance.launch(name="test", fig=fig)

    assert (
        instance.launch_calls[0]["ax"] is ax3d
    ), "Existing 3D axes should have been injected into launch() call"
    plt.close("all")


def test_pyplot_launch_patch_clears_inline_is_jl(monkeypatch):
    """patched_launch forces _inline_is_jl=False even if original_launch set it True."""
    cls = type("PyPlot", (_FakePyPlot,), {})
    _install_fake_pyplot(monkeypatch, cls)

    nbp = _fresh_nbp()
    nbp.patch_roboticstoolbox_pyplot_launch_for_notebook()

    instance = cls()
    instance.launch(name="test")

    assert (
        instance._inline_is_jl is False
    ), "patched_launch must reset _inline_is_jl to False after original_launch"


def test_pyplot_add_patch_suppresses_show_and_draw(monkeypatch):
    """After patching, plt.show() and plt.draw() inside add() are suppressed."""
    cls = type("PyPlot", (_FakePyPlot,), {})
    _install_fake_pyplot(monkeypatch, cls)

    nbp = _fresh_nbp()
    nbp.patch_roboticstoolbox_pyplot_launch_for_notebook()

    fig = plt.figure()
    initial_fignums = set(plt.get_fignums())

    instance = cls()
    instance.add("robot_stub")

    # Figure must still be open — show() should not have closed it
    assert (
        set(plt.get_fignums()) >= initial_fignums
    ), "plt.show() inside add() should not have closed figures"
    plt.close("all")


def test_pyplot_launch_patch_idempotent(monkeypatch):
    """Calling the patch function twice does not double-wrap."""
    cls = type("PyPlot", (_FakePyPlot,), {})
    _install_fake_pyplot(monkeypatch, cls)

    nbp = _fresh_nbp()
    nbp.patch_roboticstoolbox_pyplot_launch_for_notebook()
    original_launch = cls.launch
    nbp.patch_roboticstoolbox_pyplot_launch_for_notebook()

    assert cls.launch is original_launch, "Second call should not re-wrap launch"


def test_pyplot_patch_skips_when_rtb_missing(monkeypatch):
    """patch_roboticstoolbox_pyplot_launch_for_notebook is a no-op if rtb absent."""
    monkeypatch.setitem(sys.modules, "roboticstoolbox", None)
    monkeypatch.setitem(sys.modules, "roboticstoolbox.backends", None)
    monkeypatch.setitem(sys.modules, "roboticstoolbox.backends.PyPlot", None)
    monkeypatch.setitem(sys.modules, "roboticstoolbox.backends.PyPlot.PyPlot", None)

    nbp = _fresh_nbp()
    # Should not raise
    nbp.patch_roboticstoolbox_pyplot_launch_for_notebook()


# ---------------------------------------------------------------------------
# ArmPlot step patch
# ---------------------------------------------------------------------------


class _FakeArmPlot:
    """Minimal stand-in for roboticstoolbox.blocks.arm.ArmPlot."""

    step_calls: list[tuple]

    def __init__(self):
        self.step_calls = []
        self.robot = SimpleNamespace(q=None)
        self.env = SimpleNamespace(
            robots=[SimpleNamespace(robot=SimpleNamespace(q=None))],
            ax=SimpleNamespace(set_title=lambda s: None),
        )
        self._simstate = None

    def step(self, t: float, inports: list) -> None:
        self.step_calls.append((t, inports))


def _install_fake_armplot(monkeypatch, cls):
    arm_mod = types.ModuleType("roboticstoolbox.blocks.arm")
    arm_mod.ArmPlot = cls
    monkeypatch.setitem(
        sys.modules, "roboticstoolbox", types.ModuleType("roboticstoolbox")
    )
    monkeypatch.setitem(
        sys.modules,
        "roboticstoolbox.blocks",
        types.ModuleType("roboticstoolbox.blocks"),
    )
    monkeypatch.setitem(sys.modules, "roboticstoolbox.blocks.arm", arm_mod)


def test_armplot_patch_desktop_delegates_to_original(monkeypatch):
    """On desktop (notebook_backend=False) the original step is called unchanged."""
    import numpy as np

    cls = type("ArmPlot", (_FakeArmPlot,), {})
    _install_fake_armplot(monkeypatch, cls)

    nbp = _fresh_nbp()
    nbp.patch_roboticstoolbox_armplot_for_notebook()

    instance = cls()
    instance._simstate = _make_simstate(notebook_backend=False)
    q = np.zeros(6)
    instance.step(0.1, [q])

    # Original step was called → step_calls populated
    assert len(instance.step_calls) == 1


def test_armplot_patch_notebook_syncs_robot_q(monkeypatch):
    """In notebook mode, patched step mirrors q into env.robots[i].robot.q."""
    import numpy as np

    cls = type("ArmPlot", (_FakeArmPlot,), {})
    _install_fake_armplot(monkeypatch, cls)

    nbp = _fresh_nbp()
    nbp.patch_roboticstoolbox_armplot_for_notebook()

    dm = SimpleNamespace(refresh=MagicMock())
    simstate = _make_simstate(notebook_backend=True)
    simstate.display_manager = dm

    instance = cls()
    instance._simstate = simstate
    # Patch env.step to avoid calling real PyPlot.step
    instance.env.step = MagicMock()

    q = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    instance.step(0.0, [q])

    assert instance.robot.q is not None
    assert np.allclose(instance.robot.q, q)
    assert np.allclose(instance.env.robots[0].robot.q, q)


def test_armplot_patch_notebook_refresh_nontiled(monkeypatch):
    """Non-tiled notebook mode: patched step calls display_manager.refresh() so
    that SCOPE and other bdsim-managed pyplot figures get updated.  RTB manages
    env.fig via its own _push_inline_frame handle, so refresh_figure is NOT called.
    """
    import numpy as np

    cls = type("ArmPlot", (_FakeArmPlot,), {})
    _install_fake_armplot(monkeypatch, cls)

    nbp = _fresh_nbp()
    nbp.patch_roboticstoolbox_armplot_for_notebook()

    dm = SimpleNamespace(refresh=MagicMock(), refresh_figure=MagicMock())
    simstate = _make_simstate(notebook_backend=True)
    simstate.display_manager = dm
    # ntiles absent (or None) → non-tiled
    simstate.ntiles = None

    instance = cls()
    instance._simstate = simstate
    instance.env.step = MagicMock()
    instance.env.fig = object()

    instance.step(0.0, [np.zeros(6)])

    dm.refresh.assert_called_once()
    dm.refresh_figure.assert_not_called()


def test_armplot_patch_notebook_refresh_figure_tiled(monkeypatch):
    """Tiled notebook mode: patched step calls display_manager.refresh_figure(env.fig)
    to update the shared figure containing ArmPlot and SCOPE subplots.
    refresh() must NOT be called (env.fig is not in pyplot registry).
    """
    import numpy as np

    cls = type("ArmPlot", (_FakeArmPlot,), {})
    _install_fake_armplot(monkeypatch, cls)

    nbp = _fresh_nbp()
    nbp.patch_roboticstoolbox_armplot_for_notebook()

    dm = SimpleNamespace(refresh=MagicMock(), refresh_figure=MagicMock())
    simstate = _make_simstate(notebook_backend=True)
    simstate.display_manager = dm
    simstate.ntiles = [2, 2]  # tiled → shared figure

    instance = cls()
    instance._simstate = simstate
    instance.env.step = MagicMock()
    fig = object()
    instance.env.fig = fig

    instance.step(0.0, [np.zeros(6)])

    dm.refresh_figure.assert_called_once_with(fig)
    dm.refresh.assert_not_called()


def test_armplot_patch_notebook_clears_jl_flag_nontiled(monkeypatch):
    """Non-tiled notebook mode: env._inline_is_jl is forced to False so that
    RTB uses display-id animation instead of clear_output(), which would destroy
    other blocks' (e.g. SCOPE's) output display slots.
    """
    import numpy as np

    cls = type("ArmPlot", (_FakeArmPlot,), {})
    _install_fake_armplot(monkeypatch, cls)

    nbp = _fresh_nbp()
    nbp.patch_roboticstoolbox_armplot_for_notebook()

    dm = SimpleNamespace(refresh=MagicMock(), refresh_figure=MagicMock())
    simstate = _make_simstate(notebook_backend=True)
    simstate.display_manager = dm
    simstate.ntiles = None

    instance = cls()
    instance._simstate = simstate
    instance.env.step = MagicMock()
    instance.env._inline_is_jl = True  # simulate JupyterLite

    instance.step(0.0, [np.zeros(6)])

    assert (
        instance.env._inline_is_jl is False
    ), "patched_step must clear _inline_is_jl so RTB uses display-id, not clear_output()"


def test_armplot_patch_notebook_suppresses_push_inline_frame_tiled(monkeypatch):
    """Tiled notebook mode: env._push_inline_frame is suppressed during env.step()
    and restored afterwards, so RTB does not create a competing display slot for
    the shared figure that bdsim drives via display_manager.refresh_figure().
    """
    import numpy as np

    cls = type("ArmPlot", (_FakeArmPlot,), {})
    _install_fake_armplot(monkeypatch, cls)

    nbp = _fresh_nbp()
    nbp.patch_roboticstoolbox_armplot_for_notebook()

    original_push = MagicMock()
    push_seen_during_step: list[Any] = []

    def recording_step(dt=None):
        # Capture whatever _push_inline_frame is at call time
        push_seen_during_step.append(instance.env._push_inline_frame)

    dm = SimpleNamespace(refresh=MagicMock(), refresh_figure=MagicMock())
    simstate = _make_simstate(notebook_backend=True)
    simstate.display_manager = dm
    simstate.ntiles = [2, 2]

    instance = cls()
    instance._simstate = simstate
    instance.env.step = recording_step
    instance.env._push_inline_frame = original_push
    instance.env.fig = object()

    instance.step(0.0, [np.zeros(6)])

    # During env.step(), _push_inline_frame must have been replaced (not the original)
    assert len(push_seen_during_step) == 1
    assert (
        push_seen_during_step[0] is not original_push
    ), "_push_inline_frame should be suppressed during env.step() in tiled mode"
    # After step(), _push_inline_frame must be restored
    assert (
        instance.env._push_inline_frame is original_push
    ), "_push_inline_frame must be restored after patched_step()"


def test_armplot_patch_notebook_suppresses_plt_draw(monkeypatch):
    """plt.draw() is suppressed during env.step() and restored afterwards."""
    import numpy as np

    cls = type("ArmPlot", (_FakeArmPlot,), {})
    _install_fake_armplot(monkeypatch, cls)

    nbp = _fresh_nbp()
    nbp.patch_roboticstoolbox_armplot_for_notebook()

    draw_during_step: list[bool] = []
    plt_draw_was_suppressed: list[bool] = []

    real_draw = plt.draw

    def recording_env_step(dt=None):
        # Record whether plt.draw is suppressed at call-time
        plt_draw_was_suppressed.append(plt.draw is not real_draw)

    dm = SimpleNamespace(refresh=MagicMock())
    simstate = _make_simstate(notebook_backend=True)
    simstate.display_manager = dm

    instance = cls()
    instance._simstate = simstate
    instance.env.step = recording_env_step

    instance.step(0.0, [np.zeros(6)])

    assert plt_draw_was_suppressed == [
        True
    ], "plt.draw should be suppressed inside env.step()"
    assert plt.draw is real_draw, "plt.draw should be restored after step()"


def test_armplot_patch_notebook_suppresses_time_sleep(monkeypatch):
    """time.sleep() is suppressed during env.step() and restored afterwards."""
    import numpy as np
    import time as _time

    cls = type("ArmPlot", (_FakeArmPlot,), {})
    _install_fake_armplot(monkeypatch, cls)

    nbp = _fresh_nbp()
    nbp.patch_roboticstoolbox_armplot_for_notebook()

    real_sleep = _time.sleep
    sleep_was_suppressed: list[bool] = []

    def recording_env_step(dt=None):
        sleep_was_suppressed.append(_time.sleep is not real_sleep)

    dm = SimpleNamespace(refresh=MagicMock())
    simstate = _make_simstate(notebook_backend=True)
    simstate.display_manager = dm

    instance = cls()
    instance._simstate = simstate
    instance.env.step = recording_env_step

    instance.step(0.0, [np.zeros(6)])

    assert sleep_was_suppressed == [
        True
    ], "time.sleep should be suppressed inside env.step()"
    assert _time.sleep is real_sleep, "time.sleep should be restored after step()"


def test_armplot_patch_idempotent(monkeypatch):
    """Calling the patch function twice does not double-wrap step."""
    cls = type("ArmPlot", (_FakeArmPlot,), {})
    _install_fake_armplot(monkeypatch, cls)

    nbp = _fresh_nbp()
    nbp.patch_roboticstoolbox_armplot_for_notebook()
    first_step = cls.step
    nbp.patch_roboticstoolbox_armplot_for_notebook()

    assert cls.step is first_step, "Second call should not re-wrap step"


def test_armplot_patch_skips_when_rtb_missing(monkeypatch):
    """patch_roboticstoolbox_armplot_for_notebook is a no-op if rtb absent."""
    monkeypatch.setitem(sys.modules, "roboticstoolbox", None)
    monkeypatch.setitem(sys.modules, "roboticstoolbox.blocks", None)
    monkeypatch.setitem(sys.modules, "roboticstoolbox.blocks.arm", None)

    nbp = _fresh_nbp()
    # Should not raise
    nbp.patch_roboticstoolbox_armplot_for_notebook()


def test_armplot_patch_restores_plt_draw_on_exception(monkeypatch):
    """plt.draw() is restored even when env.step() raises."""
    import numpy as np

    cls = type("ArmPlot", (_FakeArmPlot,), {})
    _install_fake_armplot(monkeypatch, cls)

    nbp = _fresh_nbp()
    nbp.patch_roboticstoolbox_armplot_for_notebook()

    real_draw = plt.draw

    dm = SimpleNamespace(refresh=MagicMock())
    simstate = _make_simstate(notebook_backend=True)
    simstate.display_manager = dm

    instance = cls()
    instance._simstate = simstate
    instance.env.step = MagicMock(side_effect=RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        instance.step(0.0, [np.zeros(6)])

    assert (
        plt.draw is real_draw
    ), "plt.draw must be restored even after env.step() raises"
