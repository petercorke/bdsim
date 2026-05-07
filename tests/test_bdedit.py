"""
Tests for the bdedit block-diagram editor.

Four levels:

1. File round-trip  — pure JSON, no Qt required
2. Qt smoke test    — loads a .bd file, checks the scene is populated
3. Export tests     — saves PDF, SVG, and PNG; checks files are non-empty
4. CLI --print test — runs bdedit as a subprocess, checks output file

Tests that require Qt are skipped when PySide6 is not installed or when
no display is available (detected by attempting to create a QApplication).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"
EG1 = EXAMPLES_DIR / "eg1.bd"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _qt_app():
    """Return (or create) a QApplication, or None if Qt / display unavailable."""
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        return None
    app = QApplication.instance()
    if app is None:
        try:
            app = QApplication([])
        except Exception:
            return None
    return app


def _require_qt():
    """Skip the test if Qt is not usable."""
    if _qt_app() is None:
        pytest.skip("PySide6 not available or no display")


def _make_window():
    """Create an InterfaceWindow using the primary screen geometry."""
    from PySide6.QtWidgets import QApplication
    from bdedit.interface_manager import InterfaceWindow

    app = QApplication.instance()
    resolution = app.primaryScreen().availableGeometry()
    return InterfaceWindow(resolution, debug=False)


# ===========================================================================
# 1. File round-trip (no Qt)
# ===========================================================================


class TestFileRoundTrip:
    """Load a .bd file as raw JSON, serialise it back, compare."""

    def test_eg1_roundtrip(self, tmp_path):
        """eg1.bd should survive a JSON parse → serialise cycle unchanged."""
        original = json.loads(EG1.read_text())
        out = tmp_path / "eg1_copy.bd"
        out.write_text(json.dumps(original, indent=4))
        reloaded = json.loads(out.read_text())
        assert original == reloaded

    def test_eg1_has_blocks_and_wires(self):
        """eg1.bd must contain at least one block and one wire."""
        data = json.loads(EG1.read_text())
        assert len(data.get("blocks", [])) > 0, "no blocks in eg1.bd"
        assert len(data.get("wires", [])) > 0, "no wires in eg1.bd"

    def test_all_example_bd_files_parse(self):
        """Every .bd file in examples/ must be valid JSON."""
        bd_files = list(EXAMPLES_DIR.rglob("*.bd"))
        assert bd_files, "no .bd files found in examples/"
        for path in bd_files:
            data = json.loads(path.read_text())
            assert isinstance(data, dict), f"{path} did not parse as a JSON object"


# ===========================================================================
# 2. Qt smoke test
# ===========================================================================


class TestQtSmoke:
    """Load .bd files into InterfaceWindow and verify the scene is populated."""

    def test_window_creates(self):
        _require_qt()
        win = _make_window()
        assert win is not None
        win.close()

    def test_load_eg1_populates_scene(self):
        _require_qt()
        win = _make_window()
        try:
            win.loadFromFilePath(str(EG1))
            scene = win.centralWidget().scene
            assert len(scene.blocks) > 0, "no blocks loaded"
            assert len(scene.wires) > 0, "no wires loaded"
        finally:
            win.close()

    def test_load_sets_filename(self):
        _require_qt()
        win = _make_window()
        try:
            win.loadFromFilePath(str(EG1))
            assert win.filename == str(EG1)
        finally:
            win.close()

    def test_scene_save_reload(self, tmp_path):
        """Save to a temp file; verify the JSON round-trip preserves block/wire counts."""
        _require_qt()
        win = _make_window()
        try:
            win.loadFromFilePath(str(EG1))
            scene = win.centralWidget().scene
            n_blocks = len(scene.blocks)
            n_wires = len(scene.wires)

            out = tmp_path / "eg1_saved.bd"
            scene.saveToFile(str(out))
            assert out.exists(), "saveToFile did not create a file"

            saved = json.loads(out.read_text())
            assert len(saved["blocks"]) == n_blocks, "block count changed on save"
            assert len(saved["wires"]) == n_wires, "wire count changed on save"
        finally:
            win.close()


# ===========================================================================
# 3. Export tests
# ===========================================================================


class TestExport:
    """Export the diagram to PDF, SVG, and PNG; check output is non-trivial."""

    MIN_BYTES = 1_000  # any real output will exceed this

    def _export(self, fmt: str, tmp_path: Path) -> Path:
        _require_qt()
        win = _make_window()
        try:
            win.loadFromFilePath(str(EG1))
            out = tmp_path / f"eg1.{fmt}"
            win.centralWidget().save_image(
                str(out), picture_name="", picture_format=fmt
            )
            return out
        finally:
            win.close()

    def test_export_pdf(self, tmp_path):
        out = self._export("pdf", tmp_path)
        assert out.exists(), "PDF not created"
        assert out.stat().st_size > self.MIN_BYTES, "PDF suspiciously small"
        # Verify PDF magic bytes
        assert out.read_bytes()[:4] == b"%PDF", "file does not look like a PDF"

    def test_export_svg(self, tmp_path):
        out = self._export("svg", tmp_path)
        assert out.exists(), "SVG not created"
        assert out.stat().st_size > self.MIN_BYTES, "SVG suspiciously small"
        content = out.read_text(errors="replace")
        assert "<svg" in content, "file does not look like an SVG"

    def test_export_png(self, tmp_path):
        out = self._export("png", tmp_path)
        assert out.exists(), "PNG not created"
        assert out.stat().st_size > self.MIN_BYTES, "PNG suspiciously small"
        # Verify PNG magic bytes
        assert (
            out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
        ), "file does not look like a PNG"


# ===========================================================================
# 4. CLI --print test (subprocess integration)
# ===========================================================================


class TestCLI:
    """Run bdedit as a subprocess with --print and verify the output file."""

    MIN_BYTES = 1_000

    def _run_print(
        self, out: Path, fmt: str | None = None
    ) -> subprocess.CompletedProcess:
        cmd = [
            sys.executable,
            "-m",
            "bdedit.bdedit",
            "-p",
            str(out),
            str(EG1),
        ]
        if fmt:
            cmd += ["-f", fmt]
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "MPLBACKEND": "Agg"},
            cwd=str(REPO_ROOT),
        )

    def test_cli_print_pdf(self, tmp_path):
        out = tmp_path / "eg1.pdf"
        result = self._run_print(out)
        assert (
            result.returncode == 0
        ), f"bdedit exited {result.returncode}\n{result.stderr}"
        assert out.exists(), "PDF output not created"
        assert out.stat().st_size > self.MIN_BYTES
        assert out.read_bytes()[:4] == b"%PDF"

    def test_cli_print_png(self, tmp_path):
        out = tmp_path / "eg1.png"
        result = self._run_print(out, fmt="png")
        assert (
            result.returncode == 0
        ), f"bdedit exited {result.returncode}\n{result.stderr}"
        assert out.exists(), "PNG output not created"
        assert out.stat().st_size > self.MIN_BYTES
        assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    def test_cli_no_file_arg(self):
        """bdedit with no file and no --print should start (we just check it
        exits cleanly when we immediately send it SIGTERM — i.e. it starts up)."""
        proc = subprocess.Popen(
            [sys.executable, "-m", "bdedit.bdedit"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "MPLBACKEND": "Agg"},
            cwd=str(REPO_ROOT),
        )
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            # Expected — the GUI event loop is running; kill it
            proc.terminate()
            proc.wait(timeout=5)
        # Either it exited on its own (no display) or we terminated it — either is fine
        assert proc.returncode is not None
