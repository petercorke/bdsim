from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from bdweb.backend import __main__ as entry
from bdweb.backend import server

DIAGRAM: dict[str, Any] = {"blocks": [], "wires": []}


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setattr(server, "_FS_ROOT", root)
    return root


@pytest.fixture
def client(root: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(server, "_sim", None)
    with TestClient(server.app) as client:
        yield client


def _request(client: TestClient, endpoint: str, path: str) -> Any:
    if endpoint == "exists":
        return client.get("/api/exists", params={"path": path})
    body: dict[str, Any] = {"path": path}
    if endpoint == "save":
        body["diagram"] = DIAGRAM
    return client.post(f"/api/{endpoint}", json=body)


@pytest.mark.parametrize("endpoint", ["load", "save", "exists", "run"])
def test_inside_root_is_allowed(
    client: TestClient, root: Path, endpoint: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    diagram = root / "diagram.bd"
    diagram.write_text(json.dumps({"blocks": [], "wires": []}), encoding="utf-8")
    if endpoint == "run":
        completed = Mock(stdout="", stderr="", returncode=0)
        monkeypatch.setattr(subprocess, "run", Mock(return_value=completed))

    response = _request(client, endpoint, str(diagram))

    assert response.status_code == 200


@pytest.mark.parametrize("endpoint", ["load", "save", "exists", "run"])
@pytest.mark.parametrize("escape", ["dotdot", "absolute", "symlink", "tilde"])
def test_outside_root_is_rejected(
    client: TestClient,
    root: Path,
    tmp_path: Path,
    endpoint: str,
    escape: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outside = tmp_path / "outside.bd"
    outside.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path))
    if escape == "dotdot":
        path = "../outside.bd"
    elif escape == "absolute":
        path = str(outside)
    elif escape == "symlink":
        link = root / "link.bd"
        link.symlink_to(outside)
        path = str(link)
    else:
        path = "~/outside.bd"
    run = Mock()
    monkeypatch.setattr(subprocess, "run", run)

    response = _request(client, endpoint, path)

    assert response.status_code == 403
    assert response.json() == {"detail": "Path outside the root directory"}
    assert not run.called


@pytest.mark.parametrize("endpoint", ["load", "save", "exists", "run"])
def test_relative_path_is_root_relative(
    client: TestClient, root: Path, endpoint: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    diagram = root / "diagram.bd"
    diagram.write_text(json.dumps({"blocks": [], "wires": []}), encoding="utf-8")
    if endpoint == "run":
        completed = Mock(stdout="", stderr="", returncode=0)
        monkeypatch.setattr(subprocess, "run", Mock(return_value=completed))

    response = _request(client, endpoint, "diagram.bd")

    assert response.status_code == 200


def test_save_cannot_create_dirs_outside_root(
    client: TestClient, root: Path, tmp_path: Path
) -> None:
    response = _request(client, "save", "../new-dir/diagram.bd")

    assert response.status_code == 403
    assert not (tmp_path / "new-dir").exists()


def test_fs_root_defaults_to_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BDWEB_ROOT", raising=False)
    assert server._FS_ROOT == Path.home()


def test_root_option_sets_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(entry, "_free_port", lambda preferred: preferred)
    monkeypatch.setattr(entry, "_start_vite", lambda port: None)
    monkeypatch.setattr(entry.threading, "Thread", Mock())
    monkeypatch.setattr(entry.uvicorn, "run", Mock())
    monkeypatch.setattr(sys, "argv", ["bdweb", "--root", str(tmp_path)])
    monkeypatch.delenv("BDWEB_ROOT", raising=False)

    entry.main()

    assert os.environ["BDWEB_ROOT"] == str(tmp_path.resolve())


def test_root_option_rejects_non_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sys, "argv", ["bdweb", "--root", str(tmp_path / "missing")])

    with pytest.raises(SystemExit) as exc:
        entry.main()

    assert exc.value.code == 1
