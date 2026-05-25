#!/usr/bin/env python3

from types import SimpleNamespace

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

from bdsim.display import (
    DisplayManager,
    MatplotlibDisplayManager,
    NotebookDisplayManager,
)


def test_factory_returns_notebook_manager() -> None:
    manager = DisplayManager.create(notebook_backend=True)
    assert isinstance(manager, NotebookDisplayManager)
    assert manager.notebook_backend is True


def test_factory_returns_matplotlib_manager() -> None:
    manager = DisplayManager.create(notebook_backend=False)
    assert isinstance(manager, MatplotlibDisplayManager)
    assert manager.notebook_backend is False


def test_notebook_show_initial_and_refresh(monkeypatch) -> None:
    manager = NotebookDisplayManager()
    fig, _ax = plt.subplots()  # must have axes or _iter_display_figures() skips it

    display_calls: list[tuple[int, bool]] = []
    update_calls: list[int] = []

    # The handle returned by display() must have an update() method; that is
    # what refresh() calls on subsequent frames.
    def fake_display(obj, display_id=False):
        display_calls.append((obj.number, bool(display_id)))
        handle = SimpleNamespace(
            display_id=f"disp-{obj.number}",
            update=lambda o: update_calls.append(o.number),
        )
        return handle

    # show_initial() imports display at call time from IPython.display
    monkeypatch.setattr("IPython.display.display", fake_display)

    try:
        manager.show_initial()
        manager.refresh()
    finally:
        plt.close("all")

    assert display_calls == [(fig.number, True)]
    assert update_calls == [fig.number]


def test_notebook_show_initial_idempotent(monkeypatch) -> None:
    manager = NotebookDisplayManager()
    fig, _ax = plt.subplots()

    display_calls: list[int] = []

    def fake_display(obj, display_id=False):
        display_calls.append(obj.number)
        return SimpleNamespace(
            display_id=f"disp-{obj.number}",
            update=lambda o: None,
        )

    monkeypatch.setattr("IPython.display.display", fake_display)

    try:
        manager.show_initial()
        manager.show_initial()  # second call must be a no-op
    finally:
        plt.close("all")

    assert len(display_calls) == 1, "show_initial() must not call display() twice"


def test_notebook_finalize_refreshes_and_closes(monkeypatch) -> None:
    manager = NotebookDisplayManager()
    fig, _ax = plt.subplots()

    update_calls: list[int] = []

    def fake_display(obj, display_id=False):
        return SimpleNamespace(
            display_id=f"disp-{obj.number}",
            update=lambda o: update_calls.append(o.number),
        )

    monkeypatch.setattr("IPython.display.display", fake_display)

    manager.show_initial()
    manager.finalize()

    assert update_calls == [fig.number], "finalize() must call refresh() once"
    assert fig.number not in plt.get_fignums(), "finalize() must close the figure"


def test_notebook_refresh_lazy_registers_without_show_initial(monkeypatch) -> None:
    manager = NotebookDisplayManager()
    fig, _ax = plt.subplots()

    display_calls: list[tuple[int, bool]] = []
    update_calls: list[int] = []

    def fake_display(obj, display_id=False):
        display_calls.append((obj.number, bool(display_id)))
        return SimpleNamespace(
            display_id=f"disp-{obj.number}",
            update=lambda o: update_calls.append(o.number),
        )

    monkeypatch.setattr("IPython.display.display", fake_display)

    try:
        manager.refresh()
    finally:
        plt.close("all")

    assert display_calls == [(fig.number, True)]
    assert update_calls == [fig.number]


def test_notebook_refresh_registers_figures_created_after_show_initial(
    monkeypatch,
) -> None:
    manager = NotebookDisplayManager()
    fig1, _ax1 = plt.subplots()

    display_calls: list[int] = []
    update_calls: list[int] = []

    def fake_display(obj, display_id=False):
        display_calls.append(obj.number)
        return SimpleNamespace(
            display_id=f"disp-{obj.number}",
            update=lambda o: update_calls.append(o.number),
        )

    monkeypatch.setattr("IPython.display.display", fake_display)

    try:
        manager.show_initial()
        fig2, _ax2 = plt.subplots()
        manager.refresh()
    finally:
        plt.close("all")

    assert display_calls == [fig1.number, fig2.number]
    assert update_calls == [fig1.number, fig2.number]


def test_notebook_refresh_figure_updates_closed_pyplot_figure(monkeypatch) -> None:
    manager = NotebookDisplayManager()
    fig, _ax = plt.subplots()
    fig_number = fig.number
    plt.close(fig)

    display_calls: list[int] = []
    update_calls: list[int] = []

    def fake_display(obj, display_id=False):
        display_calls.append(obj.number)
        return SimpleNamespace(
            display_id=f"disp-{obj.number}",
            update=lambda o: update_calls.append(o.number),
        )

    monkeypatch.setattr("IPython.display.display", fake_display)

    manager.refresh_figure(fig)

    assert display_calls == [fig_number]
    assert update_calls == [fig_number]


def test_notebook_refresh_figure_does_not_reuse_handle_for_new_same_number(
    monkeypatch,
) -> None:
    manager = NotebookDisplayManager()

    fig1, _ax1 = plt.subplots(num=1)
    first_number = fig1.number

    display_calls: list[int] = []
    update_calls: list[int] = []

    def fake_display(obj, display_id=False):
        display_calls.append(obj.number)
        return SimpleNamespace(
            display_id=f"disp-{obj.number}-{len(display_calls)}",
            update=lambda o: update_calls.append(o.number),
        )

    monkeypatch.setattr("IPython.display.display", fake_display)

    manager.refresh_figure(fig1)
    plt.close(fig1)

    # New figure intentionally reuses the same matplotlib figure number.
    fig2, _ax2 = plt.subplots(num=first_number)
    manager.refresh_figure(fig2)

    plt.close("all")

    assert display_calls == [first_number, first_number]
    assert update_calls == [first_number, first_number]


def test_matplotlib_finalize_with_hold(monkeypatch) -> None:
    manager = MatplotlibDisplayManager()

    show_calls: list[bool] = []

    def fake_show(*, block=False):
        show_calls.append(bool(block))

    monkeypatch.setattr("matplotlib.pyplot.show", fake_show)

    manager.finalize(hold=True)
    manager.finalize(hold=False)

    assert show_calls == [True]
