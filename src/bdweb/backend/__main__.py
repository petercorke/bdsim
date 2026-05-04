"""
bdweb — start backend + frontend dev server and open the browser.

Usage:
    bdweb                  # empty canvas
    bdweb path/to/file.bd  # canvas pre-loaded with the given diagram
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import quote

import uvicorn


# ---------------------------------------------------------------------------
# Port helpers
# ---------------------------------------------------------------------------

def _free_port(preferred: int) -> int:
    """Return *preferred* if it is free, otherwise the next free port."""
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found near {preferred}")


def _wait_for_port(port: int, timeout: float = 20.0) -> bool:
    """Poll until *port* accepts connections or *timeout* seconds elapse."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return True
        except OSError:
            time.sleep(0.15)
    return False


# ---------------------------------------------------------------------------
# Vite dev server
# ---------------------------------------------------------------------------

_FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


def _start_vite(vite_port: int) -> "subprocess.Popen[str] | None":
    """Launch `npm run dev -- --port <vite_port> --strictPort` in frontend/.

    Returns the Popen object, or None if npm / node_modules are unavailable.
    """
    if not (_FRONTEND_DIR / "node_modules").exists():
        print(
            f"[bdweb] WARNING: {_FRONTEND_DIR}/node_modules not found.\n"
            f"        Run:  cd {_FRONTEND_DIR} && npm install",
            file=sys.stderr,
        )
        return None

    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    try:
        proc = subprocess.Popen(
            [npm, "run", "dev", "--", "--port", str(vite_port), "--strictPort"],
            cwd=_FRONTEND_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,  # own process group so killpg cleans up all children
        )
    except FileNotFoundError:
        print(
            "[bdweb] ERROR: 'npm' not found.  Install Node.js to use the dev server.",
            file=sys.stderr,
        )
        return None

    # Forward Vite output to our stdout in a background thread
    def _forward() -> None:
        assert proc.stdout
        for line in proc.stdout:
            sys.stdout.write(f"  [vite] {line}")
            sys.stdout.flush()

    threading.Thread(target=_forward, daemon=True).start()
    return proc


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    # ── Parse arguments ────────────────────────────────────────────────────
    bd_file: str | None = None
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.suffix == ".bd":
            if not p.exists():
                print(f"[bdweb] ERROR: file not found: {p}", file=sys.stderr)
                sys.exit(1)
            bd_file = str(p.expanduser().resolve())
        else:
            print(f"[bdweb] WARNING: ignoring unknown argument '{arg}'", file=sys.stderr)

    # ── Decide: production build or Vite dev server ────────────────────────
    _frontend_build = Path(__file__).parent.parent / "frontend" / "build"
    use_production = _frontend_build.exists()

    try:
        api_port = _free_port(8000)
        vite_port = _free_port(5173) if not use_production else api_port
    except RuntimeError as exc:
        print(f"[bdweb] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    os.environ["BDWEB_API_PORT"] = str(api_port)
    os.environ["BDWEB_VITE_PORT"] = str(vite_port)

    if use_production:
        frontend_url = f"http://localhost:{api_port}"
        print(f"[bdweb] Serving built frontend + API at http://localhost:{api_port}")
    else:
        frontend_url = f"http://localhost:{vite_port}"
        print(f"[bdweb] Backend API : http://localhost:{api_port}")
        print(f"[bdweb] Frontend    : http://localhost:{vite_port}  (Vite dev)")

    if bd_file:
        frontend_url += f"?load={quote(bd_file, safe='')}"
        print(f"[bdweb] Auto-loading: {bd_file}")

    # ── Start Vite dev server (dev mode only) ─────────────────────────────
    vite_proc = None if use_production else _start_vite(vite_port)

    # ── Open browser once frontend is up ───────────────────────────────────
    def _open_browser() -> None:
        wait_port = api_port if use_production else vite_port
        if not _wait_for_port(wait_port, timeout=20):
            print(
                f"[bdweb] WARNING: frontend never became available on port {wait_port}",
                file=sys.stderr,
            )
            return
        webbrowser.open(frontend_url)

    threading.Thread(target=_open_browser, daemon=True).start()

    # ── Start uvicorn (blocks until Ctrl-C) ───────────────────────────────
    try:
        uvicorn.run(
            "bdweb.backend.server:app",
            host="0.0.0.0",
            port=api_port,
            reload=False,
            log_level="warning",  # suppress per-request noise; errors still shown
        )
    finally:
        if vite_proc and vite_proc.poll() is None:
            try:
                os.killpg(os.getpgid(vite_proc.pid), signal.SIGTERM)
                vite_proc.wait(timeout=4)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(os.getpgid(vite_proc.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
        print("[bdweb] stopped.", file=sys.stderr)


if __name__ == "__main__":
    main()
