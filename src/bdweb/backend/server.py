"""
bdweb FastAPI backend.

Serves the block library, load/save .bd files, and runs simulations.
The SvelteKit build is served as static files from ../frontend/build/.
"""

from __future__ import annotations

import base64
import importlib
import inspect
import io
import json
import os
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")  # must be before any other matplotlib import
import matplotlib.pyplot as plt

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import bdsim
from bdsim.bdrun import bdload

# ---------------------------------------------------------------------------
# App + CORS (dev: Vite runs on :5173, backend on :8000)
# ---------------------------------------------------------------------------

app = FastAPI(title="bdweb", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:5175", "http://127.0.0.1:5175",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Block library — loaded once at startup
# ---------------------------------------------------------------------------

_sim: bdsim.BDSim | None = None


def get_sim() -> bdsim.BDSim:
    global _sim
    if _sim is None:
        _sim = bdsim.BDSim(banner=False)
    return _sim


def _normalise_docs_root(raw_url: str | None, package: str) -> str | None:
    """Normalize package/module docs URLs to a stable root URL.

    Converts GitHub blob URLs (including gh-pages branch links) to the
    corresponding GitHub Pages site URL.
    """
    if not raw_url:
        return None

    url = raw_url.rstrip("/")

    # Convert: https://github.com/<owner>/<repo>/blob/<branch>/...
    #      to: https://<owner>.github.io/<repo>/...
    m = re.match(r"^https?://github\.com/([^/]+)/([^/]+)/blob/[^/]+(?:/(.*))?$", url)
    if m:
        owner, repo, rest = m.group(1), m.group(2), m.group(3) or ""
        base = f"https://{owner}.github.io/{repo}"
        if rest.startswith("_modules/"):
            return base
        return base

    # If already pointing at a rendered module page, trim to site root.
    if "/_modules/" in url:
        return url.split("/_modules/", 1)[0]

    # URLs exported from blocks/__init__.py are often like .../<package>.blocks
    suffix = f"/{package}.blocks"
    if url.endswith(suffix):
        return url[: -len(suffix)]

    return url


@lru_cache(maxsize=16)
def _package_docs_root(package: str) -> str | None:
    """Best-effort docs root lookup from a package's blocks module."""
    try:
        blocks_mod = importlib.import_module(f"{package}.blocks")
        blocks_url = getattr(blocks_mod, "url", None)
        root = _normalise_docs_root(blocks_url, package)
        if root:
            return root
    except Exception:
        pass

    # Fallback roots for known Peter Corke packages.
    fallback_roots = {
        "bdsim": "https://petercorke.github.io/bdsim",
        "roboticstoolbox": "https://petercorke.github.io/robotics-toolbox-python",
        "machinevisiontoolbox": "https://petercorke.github.io/machinevision-toolbox-python",
        "spatialmath": "https://petercorke.github.io/spatialmath-python",
    }
    return fallback_roots.get(package)


def _block_doc_url(info: dict) -> str | None:
    """Build a docs URL anchored to the block's API class documentation entry."""
    package = info.get("package")
    module = info.get("module")
    classname = info.get("classname")

    if package and module and classname:
        root = _package_docs_root(package)
        if root:
            # Sphinx API docs aggregate block classes on <package>.blocks.html
            # with anchors of the form: <module>.<ClassName>
            anchor = f"{module}.{classname}"
            return f"{root}/{package}.blocks.html#{anchor}"

    # Fallback to any existing URL after normalization.
    fallback = _normalise_docs_root(info.get("url"), package or "")
    if fallback and classname:
        anchor = f"{module}.{classname}" if module else classname
        if fallback.endswith(".html"):
            return f"{fallback}#{anchor}"
        return f"{fallback}#{anchor}"
    return fallback


def _normalise_type(annotation: Any, default: Any) -> str:
    """Map a Python type annotation (or a default value) to a simple UI type.

    Returns one of: "bool", "number", "str", "list".
    Priority: annotation wins; fall back to type(default) when annotation absent.
    """
    ann_str = ""
    if annotation is not inspect.Parameter.empty:
        ann_str = str(annotation).lower()

    # Explicit bool check first (bool is a subclass of int in Python)
    if "bool" in ann_str:
        return "bool"

    # Lists / tuples / dicts → JSON textarea
    if re.search(r"\blist\b|\btuple\b|\bdict\b|\bsequence\b", ann_str):
        return "list"

    # Numeric types
    if re.search(r"\bint\b|\bfloat\b|\bnumber\b|\bnp\.ndarray\b|\bvector\b|\bmatrix\b", ann_str):
        return "number"

    # Fall back to the default value's type
    if isinstance(default, bool):
        return "bool"
    if isinstance(default, (int, float)):
        return "number"
    if isinstance(default, (list, tuple, dict)):
        return "list"

    return "str"


def _introspect_params(cls: type) -> dict[str, dict]:
    """Return {param_name: {type, default}} via __init__ introspection.

    Skips internal parameters: self, args, kwargs, bd, blockargs.
    The 'type' value is one of: "bool", "number", "str", "list".
    The 'default' is the Python default, JSON-serialised-safe (None for required).
    """
    skip = {"self", "args", "kwargs", "bd", "blockargs"}
    try:
        sig = inspect.signature(cls.__init__)
    except (ValueError, TypeError):
        return {}

    result: dict[str, dict] = {}
    for name, p in sig.parameters.items():
        if name in skip:
            continue
        default = None if p.default is inspect.Parameter.empty else p.default
        # Convert numpy scalars / non-JSON-safe defaults to plain Python
        try:
            json.dumps(default)
        except (TypeError, ValueError):
            default = str(default)
        result[name] = {
            "type": _normalise_type(p.annotation, default),
            "default": default,
        }
    return result


def _serialisable_block_info(info: dict) -> dict:
    """Build a JSON-safe block info dict, replacing sphinx params with introspection."""
    keep = ("classname", "blockname", "module", "package", "blockclass",
        "nin", "nout", "inputs", "outputs")
    result = {k: info[k] for k in keep if k in info}
    cls = info.get("class")
    result["params"] = _introspect_params(cls) if cls is not None else {}
    result["url"] = _block_doc_url(info)
    return result


@app.get("/api/blocks")
def get_blocks() -> dict[str, Any]:
    """Return the full block library, grouped by blockclass."""
    sim = get_sim()
    library: dict[str, list[dict]] = {}
    for name, info in sim._blocklibrary.items():
        cls = info.get("blockclass", "other").capitalize()
        entry = _serialisable_block_info(info)
        entry["name"] = name  # e.g. "GAIN"
        library.setdefault(cls, []).append(entry)
    return library


@app.get("/api/blockinfo/{name}")
def get_block_info(name: str) -> dict[str, Any]:
    """Return metadata for a single block type."""
    sim = get_sim()
    name_upper = name.upper()
    if name_upper not in sim._blocklibrary:
        raise HTTPException(status_code=404, detail=f"Block '{name}' not found")
    return _serialisable_block_info(sim._blocklibrary[name_upper])


# ---------------------------------------------------------------------------
# Filesystem browser  (rooted at ~, serves dirs + .bd files only)
# ---------------------------------------------------------------------------

_FS_ROOT = Path.home()


@app.get("/api/ls")
def list_dir(dir: str = "") -> dict:
    """List directories and .bd files under ~.

    *dir* is a path relative to ~.  Returns the resolved relative path of the
    listed directory plus its entries.  Refuses to escape ~.
    """
    target = (_FS_ROOT / dir).resolve() if dir else _FS_ROOT
    # Security: never escape the home root
    try:
        target.relative_to(_FS_ROOT)
    except ValueError:
        raise HTTPException(status_code=403, detail="Path outside home directory")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Not a directory")

    entries = []
    try:
        children = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    for p in children:
        if p.name.startswith("."):
            continue  # skip hidden
        if p.is_dir():
            entries.append({"name": p.name, "type": "dir"})
        elif p.is_file() and p.suffix == ".bd":
            entries.append({"name": p.name, "type": "file", "abs": str(p)})

    rel = str(target.relative_to(_FS_ROOT)) if target != _FS_ROOT else ""
    return {"dir": rel, "abs": str(target), "entries": entries}


# ---------------------------------------------------------------------------
# Load / Save
# ---------------------------------------------------------------------------

class LoadRequest(BaseModel):
    path: str


class SaveRequest(BaseModel):
    path: str
    diagram: dict


def _bd_to_diagram(raw: dict) -> dict:
    """Convert raw bdedit .bd JSON to the Diagram format expected by the frontend.

    The .bd wire format identifies endpoints by socket ID (a large Python
    object id stored in each block's inputs/outputs arrays).  We build a
    lookup map so wires can be expressed as (block_id, port_index) pairs
    that the frontend can match against node IDs.

    Block coordinates (pos_x, pos_y) are passed through unchanged — they are
    in bdedit scene units, which are compatible with @xyflow/svelte's canvas
    coordinate system.  fitView() re-centres on load.
    """
    # socket_id → {block_id, index}
    socket_map: dict[int, dict] = {}
    for block in raw.get("blocks", []):
        block_id = block["id"]
        for sock in block.get("inputs", []):
            socket_map[sock["id"]] = {"block_id": block_id, "index": sock["index"]}
        for sock in block.get("outputs", []):
            socket_map[sock["id"]] = {"block_id": block_id, "index": sock["index"]}

    wires: list[dict] = []
    for wire in raw.get("wires", []):
        start = socket_map.get(wire.get("start_socket"))
        end = socket_map.get(wire.get("end_socket"))
        if start is None or end is None:
            continue  # skip wires with unresolvable socket ids
        wires.append({
            "id": wire["id"],
            "start_node": start["block_id"],
            "start_port": start["index"],
            "end_node":   end["block_id"],
            "end_port":   end["index"],
        })

    return {
        "blocks":       raw.get("blocks", []),
        "wires":        wires,
        "scene_width":  raw.get("scene_width"),
        "scene_height": raw.get("scene_height"),
    }


@app.post("/api/load")
def load_file(req: LoadRequest) -> dict[str, Any]:
    p = Path(req.path).expanduser().resolve()
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {p}")
    if p.suffix != ".bd":
        raise HTTPException(status_code=400, detail="Only .bd files are supported")
    raw = json.loads(p.read_text())
    return _bd_to_diagram(raw)


@app.get("/api/exists")
def file_exists(path: str) -> dict[str, bool]:
    p = Path(path).expanduser().resolve()
    return {"exists": p.exists()}


def _diagram_to_bd(diagram: dict) -> dict:
    """Convert bdweb diagram format to bdedit-compatible .bd JSON.

    Generates sequential integer IDs for blocks and sockets so the file
    can be opened in bdedit and round-trips cleanly through _bd_to_diagram.
    """
    import time as _time

    _id = iter(range(1, 10_000_000))

    def nxt() -> int:
        return next(_id)

    # map frontend node id (str) → integer block id
    block_id_map: dict[str, int] = {}
    # map (node_id, "in"/"out", port_index) → integer socket id
    socket_id_map: dict[tuple, int] = {}

    bd_blocks = []
    for b in diagram.get("blocks", []):
        bid = nxt()
        block_id_map[str(b["id"])] = bid

        inputs = []
        for i in range(b.get("inputsNum", 0)):
            sid = nxt()
            socket_id_map[(str(b["id"]), "in", i)] = sid
            inputs.append({"id": sid, "index": i, "multi_wire": True,
                           "position": 1, "socket_type": 1})

        outputs = []
        for i in range(b.get("outputsNum", 0)):
            sid = nxt()
            socket_id_map[(str(b["id"]), "out", i)] = sid
            outputs.append({"id": sid, "index": i, "multi_wire": True,
                            "position": 3, "socket_type": 2})

        bd_blocks.append({
            "id": bid,
            "block_type": b["block_type"],
            "title": b.get("title", b["block_type"]),
            "pos_x": b.get("pos_x", 0.0),
            "pos_y": b.get("pos_y", 0.0),
            "width":  b.get("width", 100),
            "height": b.get("height", 100),
            "flipped": b.get("flipped", False),
            "inputsNum":  b.get("inputsNum", 0),
            "outputsNum": b.get("outputsNum", 0),
            "inputs":  inputs,
            "outputs": outputs,
            "parameters": b.get("parameters", []),
        })

    bd_wires = []
    for w in diagram.get("wires", []):
        start_sid = socket_id_map.get((str(w["start_node"]), "out", w["start_port"]))
        end_sid   = socket_id_map.get((str(w["end_node"]),   "in",  w["end_port"]))
        if start_sid is None or end_sid is None:
            continue
        bd_wires.append({
            "id": nxt(),
            "start_socket": start_sid,
            "end_socket":   end_sid,
            "wire_type": 3,
            "custom_routing": False,
            "wire_coordinates": [],
        })

    return {
        "id": nxt(),
        "created_by": "bdweb",
        "creation_time": int(_time.time()),
        "scene_width":  diagram.get("scene_width")  or 7200.0,
        "scene_height": diagram.get("scene_height") or 3600.0,
        "blocks": bd_blocks,
        "wires":  bd_wires,
    }


@app.post("/api/save")
def save_file(req: SaveRequest) -> dict[str, str]:
    p = Path(req.path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(_diagram_to_bd(req.diagram), indent=2))
    return {"saved": str(p)}


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    path: str
    timeout: float = 120.0


@app.post("/api/run")
def run_diagram(req: RunRequest) -> dict[str, Any]:
    """
    Save already happened on the frontend.  Run bdrun as a subprocess,
    capture its stdout+stderr, and return them for display in the UI.
    Matplotlib windows open natively and close when bdrun exits.
    """
    import subprocess
    p = Path(req.path).expanduser().resolve()
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {p}")
    if p.suffix != ".bd":
        raise HTTPException(status_code=400, detail="Only .bd files are supported")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "bdsim.bdrun", str(p)],
            capture_output=True,
            text=True,
            timeout=req.timeout,
        )
        return {
            "stdout":     result.stdout,
            "stderr":     result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail=f"bdrun timed out after {req.timeout}s")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Serve built SvelteKit app (production only — dev uses Vite)
# ---------------------------------------------------------------------------

_frontend_build = Path(__file__).parent.parent.parent / "frontend" / "build"
if _frontend_build.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_build), html=True), name="static")
