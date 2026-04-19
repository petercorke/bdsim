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
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
# Load / Save
# ---------------------------------------------------------------------------

class LoadRequest(BaseModel):
    path: str


class SaveRequest(BaseModel):
    path: str
    diagram: dict


@app.post("/api/load")
def load_file(req: LoadRequest) -> dict[str, Any]:
    p = Path(req.path).expanduser().resolve()
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {p}")
    if p.suffix != ".bd":
        raise HTTPException(status_code=400, detail="Only .bd files are supported")
    return json.loads(p.read_text())


@app.post("/api/save")
def save_file(req: SaveRequest) -> dict[str, str]:
    p = Path(req.path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(req.diagram, indent=2))
    return {"saved": str(p)}


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    diagram: dict
    T: float = 5.0


@app.post("/api/run")
def run_diagram(req: RunRequest) -> dict[str, Any]:
    """
    Run the diagram, return stdout text and any matplotlib figures as base64 PNG.
    """
    import sys
    import tempfile
    import traceback
    from io import StringIO

    # Write diagram to a temp .bd file so bdload can read it
    with tempfile.NamedTemporaryFile(mode="w", suffix=".bd", delete=False) as f:
        json.dump(req.diagram, f)
        tmp_path = f.name

    stdout_capture = StringIO()
    plots: list[str] = []
    error: str | None = None

    try:
        # Redirect stdout
        old_stdout = sys.stdout
        sys.stdout = stdout_capture

        sim = bdsim.BDSim(banner=False)
        bd = sim.blockdiagram()
        bdload(bd, tmp_path)
        bd.compile()
        out = sim.run(bd, T=req.T)

        sys.stdout = old_stdout

        # Capture all open matplotlib figures
        for fig_num in plt.get_fignums():
            fig = plt.figure(fig_num)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight")
            buf.seek(0)
            plots.append(base64.b64encode(buf.read()).decode())
        plt.close("all")

    except Exception:
        sys.stdout = old_stdout
        error = traceback.format_exc()
    finally:
        os.unlink(tmp_path)

    return {
        "stdout": stdout_capture.getvalue(),
        "plots": plots,
        "error": error,
    }


# ---------------------------------------------------------------------------
# Serve built SvelteKit app (production only — dev uses Vite)
# ---------------------------------------------------------------------------

_frontend_build = Path(__file__).parent.parent.parent / "frontend" / "build"
if _frontend_build.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_build), html=True), name="static")
