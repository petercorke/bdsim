from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock

import pytest

pytest.importorskip("uvicorn")

from bdweb.backend import __main__ as entry


@pytest.fixture
def run_main(monkeypatch: pytest.MonkeyPatch) -> Iterator[Mock]:
    """Run entry.main() with all side effects stubbed; capture uvicorn.run."""
    monkeypatch.setattr(entry, "_free_port", lambda preferred: preferred)
    monkeypatch.setattr(entry, "_start_vite", lambda port: None)
    monkeypatch.setattr(entry.threading, "Thread", Mock())
    monkeypatch.delenv("BDWEB_API_PORT", raising=False)
    monkeypatch.delenv("BDWEB_VITE_PORT", raising=False)
    run = Mock()
    monkeypatch.setattr(entry.uvicorn, "run", run)
    yield run


def _argv(monkeypatch: pytest.MonkeyPatch, *args: str) -> None:
    monkeypatch.setattr(sys, "argv", ["bdweb", *args])


def test_default_host_is_loopback(
    run_main: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    _argv(monkeypatch)

    entry.main()

    assert run_main.call_args.kwargs["host"] == "127.0.0.1"


def test_host_option_is_honoured(
    run_main: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    _argv(monkeypatch, "--host", "0.0.0.0")

    entry.main()

    assert run_main.call_args.kwargs["host"] == "0.0.0.0"


def test_non_loopback_host_warns(
    run_main: Mock, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _argv(monkeypatch, "--host", "0.0.0.0")

    entry.main()

    assert "exposes the editor to the network" in capsys.readouterr().err


def test_loopback_host_does_not_warn(
    run_main: Mock, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _argv(monkeypatch)

    entry.main()

    assert "exposes the editor" not in capsys.readouterr().err


def test_help_mentions_host_security(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _argv(monkeypatch, "--help")

    with pytest.raises(SystemExit) as exc:
        entry.main()

    assert exc.value.code == 0
    out = " ".join(capsys.readouterr().out.split())
    assert "--host" in out
    assert "NOT SAFE" in out


def test_diagram_argument_is_loaded(
    run_main: Mock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    diagram = tmp_path / "diagram.bd"
    diagram.write_text("{}", encoding="utf-8")
    _argv(monkeypatch, str(diagram))

    entry.main()

    assert run_main.called


def test_missing_diagram_exits(
    run_main: Mock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _argv(monkeypatch, str(tmp_path / "missing.bd"))

    with pytest.raises(SystemExit) as exc:
        entry.main()

    assert exc.value.code == 1
    assert not run_main.called


def test_non_bd_argument_exits(
    run_main: Mock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    other = tmp_path / "diagram.json"
    other.write_text("{}", encoding="utf-8")
    _argv(monkeypatch, str(other))

    with pytest.raises(SystemExit) as exc:
        entry.main()

    assert exc.value.code == 1
    assert not run_main.called
