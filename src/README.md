# bdsim Monorepo

This directory contains three packages that comprise the bdsim ecosystem:

## Packages

### `bdsim/`
Core block diagram simulation engine. Provides the fundamental simulation infrastructure, block types, and solver.

**Dependencies:** NumPy, SciPy, matplotlib, spatialmath-python  
**Standalone:** Yes — can be used without editors  
**Entry point:** `bdrun`

### `bdedit/`
PyQt6-based desktop GUI for editing and running block diagrams.

**Dependencies:** PySide6, Pillow (plus `bdsim`)  
**Requires:** `bdsim` core  
**Entry points:** `bdedit`, `bdedit-app`, `bdedit-associate-windows`

### `bdweb/`
SvelteKit + FastAPI web-based editor for block diagrams (modern replacement for bdedit).

**Structure:**
- `backend/` — FastAPI server for block library introspection and simulation
- `frontend/` — SvelteKit + Svelte 5 web UI with xyflow canvas

**Dependencies:** FastAPI, uvicorn[standard] (plus `bdsim`)  
**Requires:** `bdsim` core  
**Entry point:** `bdweb`

## Installation

Install from the repository root:

```bash
# Core only
pip install -e .

# With Qt desktop editor
pip install -e ".[bdedit]"

# With web editor
pip install -e ".[bdweb]"

# With both editors
pip install -e ".[all]"
```

## Dependency Model

```
bdsim (core, standalone)
  ├─ bdedit (optional GUI)
  └─ bdweb (optional web UI)
```

The editors depend on `bdsim`, but `bdsim` has no dependencies on the editors.

## Development

### Frontend development (bdweb)
```bash
cd src/bdweb/frontend
npm install
npm run dev          # Vite dev server on :5173
```

### Backend server (bdweb)
```bash
python -m bdweb      # Runs on :8000
```

Run both concurrently during development for live-reload.

## Building

The wheel includes all three packages. Python entry points are conditional on extras being installed.
