from __future__ import annotations

import json
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

from bdweb.backend import server


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(server, "_FS_ROOT", tmp_path)
    monkeypatch.setattr(server, "_sim", None)
    with TestClient(server.app) as client:
        yield client


@pytest.fixture
def diagram() -> dict[str, Any]:
    return {
        "scene_width": 2400.0,
        "scene_height": 1200.0,
        "blocks": [
            {
                "id": "source",
                "block_type": "CONSTANT",
                "title": "Input",
                "pos_x": -120.5,
                "pos_y": 30.0,
                "width": 100,
                "height": 100,
                "flipped": False,
                "inputsNum": 0,
                "outputsNum": 1,
                "parameters": [["value", 3]],
            },
            {
                "id": "sum",
                "block_type": "SUM",
                "title": "Sum",
                "pos_x": 200.0,
                "pos_y": -40.0,
                "width": 120,
                "height": 80,
                "flipped": True,
                "inputsNum": 2,
                "outputsNum": 1,
                "parameters": [["signs", "+-"]],
            },
        ],
        "wires": [
            {
                "id": "wire-0",
                "start_node": "source",
                "start_port": 0,
                "end_node": "sum",
                "end_port": 0,
            },
            {
                "id": "wire-1",
                "start_node": "source",
                "start_port": 0,
                "end_node": "sum",
                "end_port": 1,
            },
        ],
    }


def test_blocks_groups_and_serialises_metadata(client: TestClient) -> None:
    response = client.get("/api/blocks")

    assert response.status_code == 200
    library = response.json()
    gain = next(block for block in library["Function"] if block["name"] == "GAIN")
    assert gain["classname"] == "Gain"
    assert gain["nin"] == gain["nout"] == 1
    assert gain["params"]["K"] == {"type": "number", "default": 1}
    assert gain["url"].endswith("/bdsim.blocks.html#bdsim.blocks.functions.Gain")
    for group, blocks in library.items():
        for block in blocks:
            assert block["blockclass"].capitalize() == group
            assert {"class", "path", "doc"}.isdisjoint(block)
            assert {"self", "args", "kwargs", "bd", "blockargs"}.isdisjoint(
                block["params"]
            )
            for param in block["params"].values():
                assert param["type"] in {"bool", "number", "str", "list"}
                assert "default" in param


@pytest.mark.parametrize("name", ["GAIN", "gain", "GaIn"])
def test_blockinfo_is_case_insensitive(client: TestClient, name: str) -> None:
    response = client.get(f"/api/blockinfo/{name}")

    assert response.status_code == 200
    info = response.json()
    assert info["blockname"] == "GAIN"
    assert info["params"]["K"] == {"type": "number", "default": 1}
    assert info["params"]["premul"] == {"type": "bool", "default": False}
    assert "class" not in info


@pytest.mark.parametrize(
    ("name", "param", "expected"),
    [
        ("SUM", "signs", {"type": "str", "default": "++"}),
        ("FUNCTION", "fargs", {"type": "list", "default": None}),
        ("LTI_SISO", "D", {"type": "list", "default": [1, 1]}),
    ],
)
def test_blockinfo_introspects_params(
    client: TestClient, name: str, param: str, expected: dict[str, Any]
) -> None:
    response = client.get(f"/api/blockinfo/{name}")

    assert response.status_code == 200
    assert response.json()["params"][param] == expected


def test_blockinfo_unknown_block(client: TestClient) -> None:
    response = client.get("/api/blockinfo/unknown")

    assert response.status_code == 404
    assert response.json() == {"detail": "Block 'unknown' not found"}


def test_load_bdedit_socket_ids(client: TestClient, tmp_path: Path) -> None:
    blocks = [
        {"id": 41, "outputs": [{"id": 101, "index": 0}]},
        {"id": 53, "inputs": [{"id": 202, "index": 1}]},
    ]
    path = tmp_path / "diagram.bd"
    path.write_text(
        json.dumps(
            {
                "blocks": blocks,
                "wires": [{"id": 77, "start_socket": 101, "end_socket": 202}],
                "scene_width": 2000.0,
                "scene_height": 1000.0,
            }
        ),
        encoding="utf-8",
    )

    response = client.post("/api/load", json={"path": str(path)})

    assert response.status_code == 200
    assert response.json() == {
        "blocks": blocks,
        "wires": [
            {
                "id": 77,
                "start_node": 41,
                "start_port": 0,
                "end_node": 53,
                "end_port": 1,
            }
        ],
        "scene_width": 2000.0,
        "scene_height": 1000.0,
    }


def test_load_missing_file(client: TestClient, tmp_path: Path) -> None:
    path = tmp_path / "missing.bd"

    response = client.post("/api/load", json={"path": str(path)})

    assert response.status_code == 404
    assert response.json() == {"detail": f"File not found: {path}"}


def test_load_rejects_other_file_types(client: TestClient, tmp_path: Path) -> None:
    path = tmp_path / "diagram.json"
    path.write_text("{}", encoding="utf-8")

    response = client.post("/api/load", json={"path": str(path)})

    assert response.status_code == 400
    assert response.json() == {"detail": "Only .bd files are supported"}


def test_save_round_trip(
    client: TestClient, tmp_path: Path, diagram: dict[str, Any]
) -> None:
    path = tmp_path / "nested" / "diagram.bd"

    response = client.post("/api/save", json={"path": str(path), "diagram": diagram})

    assert response.status_code == 200
    assert response.json() == {"saved": str(path)}
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["created_by"] == "bdweb"
    assert isinstance(saved["creation_time"], int)
    assert saved["scene_width"] == diagram["scene_width"]
    assert saved["scene_height"] == diagram["scene_height"]
    assert len(saved["blocks"]) == len(diagram["blocks"])
    for original, block in zip(diagram["blocks"], saved["blocks"]):
        for key, value in original.items():
            if key != "id":
                assert block[key] == value
        for direction, count, socket_type in (
            ("inputs", "inputsNum", 1),
            ("outputs", "outputsNum", 2),
        ):
            assert len(block[direction]) == block[count]
            assert [socket["index"] for socket in block[direction]] == list(
                range(block[count])
            )
            assert all(
                socket["socket_type"] == socket_type for socket in block[direction]
            )
    sockets = [
        socket["id"]
        for block in saved["blocks"]
        for direction in ("inputs", "outputs")
        for socket in block[direction]
    ]
    assert len(sockets) == len(set(sockets))
    source, target = saved["blocks"]
    assert len(saved["wires"]) == 2
    for port, wire in enumerate(saved["wires"]):
        assert wire["start_socket"] == source["outputs"][0]["id"]
        assert wire["end_socket"] == target["inputs"][port]["id"]

    loaded_response = client.post("/api/load", json={"path": str(path)})

    assert loaded_response.status_code == 200
    loaded = loaded_response.json()
    assert loaded["blocks"] == saved["blocks"]
    assert loaded["scene_width"] == diagram["scene_width"]
    assert loaded["scene_height"] == diagram["scene_height"]
    assert loaded["wires"] == [
        {
            "id": wire["id"],
            "start_node": source["id"],
            "start_port": 0,
            "end_node": target["id"],
            "end_port": port,
        }
        for port, wire in enumerate(saved["wires"])
    ]


@pytest.mark.parametrize("overwrite", [False, True])
def test_save_empty_diagram(
    client: TestClient, tmp_path: Path, overwrite: bool
) -> None:
    path = tmp_path / "empty.bd"
    if overwrite:
        path.write_text("old contents", encoding="utf-8")

    response = client.post("/api/save", json={"path": str(path), "diagram": {}})

    assert response.status_code == 200
    assert response.json() == {"saved": str(path)}
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["blocks"] == saved["wires"] == []
    assert saved["scene_width"] == 7200.0
    assert saved["scene_height"] == 3600.0


@pytest.mark.parametrize(
    ("endpoint", "body"),
    [
        ("load", {}),
        ("load", {"path": None}),
        ("load", {"path": []}),
        ("save", {}),
        ("save", {"path": "diagram.bd"}),
        ("save", {"diagram": {}}),
        ("save", {"path": None, "diagram": {}}),
        ("save", {"path": "diagram.bd", "diagram": "invalid"}),
    ],
)
def test_load_save_invalid_request(
    client: TestClient, tmp_path: Path, endpoint: str, body: dict[str, Any]
) -> None:
    response = client.post(f"/api/{endpoint}", json=body)

    assert response.status_code == 422
    assert response.json()["detail"]
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("endpoint", ["load", "save"])
def test_load_save_invalid_json(client: TestClient, endpoint: str) -> None:
    response = client.post(
        f"/api/{endpoint}",
        content="{",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]


def test_ls_filters_and_sorts_entries(client: TestClient, tmp_path: Path) -> None:
    for name in ("zebra", "Alpha", ".hidden"):
        (tmp_path / name).mkdir()
    for name in ("z.bd", "A.bd", ".hidden.bd", "notes.txt"):
        (tmp_path / name).touch()

    response = client.get("/api/ls")

    assert response.status_code == 200
    assert response.json() == {
        "dir": "",
        "abs": str(tmp_path),
        "entries": [
            {"name": "Alpha", "type": "dir"},
            {"name": "zebra", "type": "dir"},
            {"name": "A.bd", "type": "file", "abs": str(tmp_path / "A.bd")},
            {"name": "z.bd", "type": "file", "abs": str(tmp_path / "z.bd")},
        ],
    }


def test_ls_nested_directory(client: TestClient, tmp_path: Path) -> None:
    (tmp_path / "models").mkdir()

    response = client.get("/api/ls", params={"dir": "models/../models"})

    assert response.status_code == 200
    assert response.json() == {
        "dir": "models",
        "abs": str(tmp_path / "models"),
        "entries": [],
    }


@pytest.mark.parametrize("name", ["missing", "diagram.bd"])
def test_ls_requires_directory(client: TestClient, tmp_path: Path, name: str) -> None:
    (tmp_path / "diagram.bd").touch()

    response = client.get("/api/ls", params={"dir": name})

    assert response.status_code == 400
    assert response.json() == {"detail": "Not a directory"}


@pytest.mark.parametrize("absolute", [False, True])
def test_ls_rejects_paths_outside_root(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    absolute: bool,
) -> None:
    root = tmp_path / "home"
    root.mkdir()
    outside = tmp_path / "home-other"
    outside.mkdir()
    monkeypatch.setattr(server, "_FS_ROOT", root)

    response = client.get(
        "/api/ls", params={"dir": str(outside) if absolute else "../home-other"}
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Path outside home directory"}


def test_ls_permission_denied(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "iterdir", Mock(side_effect=PermissionError))

    response = client.get("/api/ls")

    assert response.status_code == 403
    assert response.json() == {"detail": "Permission denied"}


@pytest.mark.parametrize("exists", [False, True])
def test_exists(client: TestClient, tmp_path: Path, exists: bool) -> None:
    path = tmp_path / "diagram.bd"
    if exists:
        path.touch()

    response = client.get("/api/exists", params={"path": str(path)})

    assert response.status_code == 200
    assert response.json() == {"exists": exists}


def test_exists_requires_path(client: TestClient) -> None:
    response = client.get("/api/exists")

    assert response.status_code == 422
    assert response.json()["detail"]


@pytest.fixture
def run_process(monkeypatch: pytest.MonkeyPatch) -> Mock:
    process = Mock(
        return_value=subprocess.CompletedProcess([], 0, stdout="", stderr="")
    )
    monkeypatch.setattr(subprocess, "run", process)
    return process


@pytest.mark.parametrize("returncode", [0, 1])
@pytest.mark.parametrize("timeout", [None, 2.5])
def test_run_invokes_bdrun_and_returns_output(
    client: TestClient,
    tmp_path: Path,
    run_process: Mock,
    returncode: int,
    timeout: float | None,
) -> None:
    path = tmp_path / "model with spaces.bd"
    path.touch()
    run_process.return_value = subprocess.CompletedProcess(
        [], returncode, stdout="simulation output\n", stderr="diagnostic\n"
    )
    body: dict[str, Any] = {"path": path.name}
    if timeout is not None:
        body["timeout"] = timeout

    response = client.post("/api/run", json=body)

    assert response.status_code == 200
    assert response.json() == {
        "stdout": "simulation output\n",
        "stderr": "diagnostic\n",
        "returncode": returncode,
    }
    run_process.assert_called_once_with(
        [sys.executable, "-m", "bdsim.bin.bdrun", str(path)],
        capture_output=True,
        text=True,
        timeout=120.0 if timeout is None else timeout,
    )


@pytest.mark.parametrize(
    ("filename", "exists", "status", "detail"),
    [
        ("missing.bd", False, 404, None),
        ("diagram.json", True, 400, "Only .bd files are supported"),
    ],
)
def test_run_rejects_invalid_files_before_execution(
    client: TestClient,
    tmp_path: Path,
    run_process: Mock,
    filename: str,
    exists: bool,
    status: int,
    detail: str | None,
) -> None:
    path = tmp_path / filename
    if exists:
        path.touch()

    response = client.post("/api/run", json={"path": str(path)})

    assert response.status_code == status
    assert response.json() == {"detail": detail or f"File not found: {path}"}
    run_process.assert_not_called()


@pytest.mark.parametrize(
    ("error", "status", "detail"),
    [
        (
            subprocess.TimeoutExpired("bdrun", 0.25),
            504,
            "bdrun timed out after 0.25s",
        ),
        (OSError("Cannot start bdrun"), 500, "Cannot start bdrun"),
    ],
)
def test_run_subprocess_errors(
    client: TestClient,
    tmp_path: Path,
    run_process: Mock,
    error: Exception,
    status: int,
    detail: str,
) -> None:
    path = tmp_path / "diagram.bd"
    path.touch()
    run_process.side_effect = error

    response = client.post("/api/run", json={"path": str(path), "timeout": 0.25})

    assert response.status_code == status
    assert response.json() == {"detail": detail}
    run_process.assert_called_once()


@pytest.mark.parametrize(
    "body",
    [{}, {"path": None}, {"path": []}, {"path": "model.bd", "timeout": "invalid"}],
)
def test_run_invalid_request(
    client: TestClient, run_process: Mock, body: dict[str, Any]
) -> None:
    response = client.post("/api/run", json=body)

    assert response.status_code == 422
    assert response.json()["detail"]
    run_process.assert_not_called()
