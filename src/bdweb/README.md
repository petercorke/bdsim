# bdweb — Web-based Block Diagram Editor

> **Status: work in progress.** The frontend does not build yet: `frontend/src/lib/` and
> `package.json` are not committed, so some files listed under Structure below do not exist
> on this branch. See [#118](https://github.com/petercorke/bdsim/issues/118) for what remains.

Modern web UI for bdsim using SvelteKit 5 and FastAPI.

## Structure

- `backend/` — Python FastAPI server
  - `server.py` — Main API: block library, metadata introspection, load/save, simulation runner
  - `__main__.py` — Entry point; launches Vite dev server + uvicorn, handles shutdown
  
- `frontend/` — SvelteKit web application
  - `src/routes/+page.svelte` — Main editor canvas
  - `src/lib/BlockNode.svelte` — Custom xyflow node component
  - `src/lib/Palette.svelte` — Block palette sidebar
  - `src/lib/PropsCard.svelte` — Floating properties panel (anchored near selected block)
  - `src/lib/PropsPanel.svelte` — Parameter editing form (used inside PropsCard)
  - `src/lib/FileBrowser.svelte` — Server-side filesystem browser modal
  - `src/lib/ContextMenu.svelte` — Right-click context menu
  - `src/lib/FlowRef.svelte` — SvelteFlow context bridge (fitView, updateNodeInternals)
  - `src/lib/api.ts` — Typed API client
  - `src/lib/types.ts` — Shared TypeScript types

## Development

### Prerequisites
- Python 3.10+
- Node.js 18+ (only needed to build the frontend or run the dev server)

### Running bdweb

After `pip install bdsim[bdweb]`:

```bash
bdweb                        # open empty canvas
bdweb path/to/diagram.bd     # open with a diagram pre-loaded
```

`bdweb` auto-detects which mode to use:

- **Production mode** — if `frontend/build/` exists (i.e. the frontend was pre-built),
  the backend serves everything at a single port (`http://localhost:8000`). No Node.js needed.
- **Dev mode** — if `frontend/build/` is absent, `bdweb` starts a Vite dev server
  (requires Node.js + `npm install`) and proxies `/api` to the FastAPI backend.

### Building the frontend (required for distribution)

```bash
make -C src/bdweb build      # or: cd src/bdweb/frontend && npm install && npm run build
```

`make dist` at the top level runs this automatically before `python -m build`, so
the wheel includes the pre-built frontend and end users need only Python.

### Full development workflow (live reload)

```bash
# Terminal 1 — backend
python -m bdweb              # starts Vite automatically if node_modules present

# OR manually:
cd src/bdweb/frontend && npm install && npm run dev   # Vite on :5173
python -m bdweb                                       # FastAPI on :8000
```

## Interaction Model

### Canvas navigation

| Action | How |
|---|---|
| Pan | Hold **Alt** + drag, or **Alt** + scroll |
| Zoom | Hold **Alt** + scroll |
| Scroll canvas | Scroll (without Alt) |

### Selection

| Action | How |
|---|---|
| Select a block | Click it |
| Deselect / close props | Click the canvas background |
| Multi-select (lasso) | Drag on empty canvas |
| Add/remove block from selection | **Cmd** + click |

### Blocks

| Action | How |
|---|---|
| Add a block | Drag from the palette onto the canvas |
| Move block(s) | Drag selected block(s) |
| Open properties | Click a block — props card appears anchored next to it |
| Close properties | Click the canvas background or the **✕** on the card |
| Edit a parameter | Modify value in the props card, then click **Apply** |
| Rename a block | Edit the Name field in the props card, then click **Apply** |
| Delete selected | **Delete** or **Backspace** |
| Flip selected (swap inputs/outputs L↔R) | **F** or right-click → **Flip** |

### Wiring

| Action | How |
|---|---|
| Draw a wire | Drag from an output handle to an input handle |
| Delete a wire | Click the wire to select it, then **Delete** |
| Multi-wire (fan-out) | Multiple wires can leave one output handle |

Handles are displayed as small triangles: output handles point **right**, input handles point **left** (reversed when the block is flipped). Wiring always goes **output → input**.

### Toolbar

| Button | Action |
|---|---|
| **New** | Clear the canvas (prompts if unsaved) |
| **Browse…** | Open the filesystem browser to pick a `.bd` file |
| **Load** | Load the currently-selected file path |
| **Save** | Save to the current path (prompts before overwrite) |
| **▶ Run** | Execute the diagram via bdsim and show results / plots |

## Key Features

- **Live block palette** with search and package filtering
- **Floating properties card** anchored near the selected block; repositions on pan/zoom
- **Hover tooltip** showing block parameters without cluttering the block body
- **Block flip** — swap input/output sides; connected wires follow
- **Multi-select** with lasso drag or Cmd+click; move or delete multiple blocks at once
- **bdedit-compatible `.bd` format** — files round-trip cleanly with bdedit
- **Overwrite guard** — confirms before overwriting an existing file
- **Browser history** — the file browser remembers the last visited directory

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/blocks` | Full block library, grouped by block class (Source, Sink, Function, ...), with introspected parameters |
| `GET` | `/api/blockinfo/{name}` | Metadata for a single block (docs URL, params); name is case-insensitive, 404 if unknown |
| `GET` | `/api/ls?dir=…` | List directories and `.bd` files; `dir` is relative to `~` and cannot escape it (403) |
| `GET` | `/api/exists?path=…` | Check whether a file path exists |
| `POST` | `/api/load` | Load a `.bd` file (`{"path": ...}`); returns diagram JSON |
| `POST` | `/api/save` | Save diagram JSON (`{"path": ..., "diagram": ...}`) as a `.bd` file, creating parent directories |
| `POST` | `/api/run` | Run a saved `.bd` file with `bdrun` in a subprocess (`{"path": ..., "timeout": 120}`); returns `stdout`, `stderr`, `returncode`. Matplotlib windows open natively on the server |

> **Security: not safe to expose to a network yet.** Only `/api/ls` is confined to `~`.
> `/api/load`, `/api/save`, `/api/exists` and `/api/run` accept any path the server process
> can reach, and `bdweb` currently binds to `0.0.0.0` (all interfaces). Run it only on a
> machine and network you trust until this is addressed. Tracked in
> [#118](https://github.com/petercorke/bdsim/issues/118).

See [BDFILE.md](BDFILE.md) for the `.bd` file format specification.

## Testing

The backend tests use FastAPI's `TestClient`, which calls the app in-process (no server or
browser needed). They skip automatically if `fastapi` or `httpx` is not installed:

```bash
pip install fastapi httpx
pytest tests/test_bdweb.py
```

They cover every route: the block library and block info, `.bd` load/save (round trips,
error cases), `/api/ls`, `/api/exists` and `/api/run` (with the subprocess mocked). A
separate test in `tests/test_bdrun.py` runs `python -m bdsim.bin.bdrun` on a real diagram,
which is what `/api/run` invokes.


## Manual End-to-End Verification

The following browser workflow was manually tested on a Windows environment.

### Environment used for verification

| Component | Version |
|---|---|
| OS | Windows (PowerShell) |
| Python | 3.11.4 |
| Node.js | 24.12.0 |
| npm | 11.6.2 |
| Browser | Brave 1.99.57 (64-bit) |
| Chromium | 157.0.8103.79 |

### Installation and build

From the repository root, install the bdweb dependencies:

```bash
pip install -e ".[bdweb]"
```

Build the frontend:

```bash
make -C src/bdweb build
```

On Windows environments where `make` is unavailable, run the equivalent frontend commands:

```powershell
cd src/bdweb/frontend
npm install
npm run build
```

Return to the repository root and launch the editor:

```powershell
bdweb
```

The production frontend should be available at:

```text
http://localhost:8000
```

### Browser workflow verification

The following workflow was successfully tested:

1. Open `http://localhost:8000` in a browser.
2. Load an example `.bd` diagram.
3. Drag a block from the palette onto the canvas.
4. Connect two blocks using their input and output handles.
5. Select a block and modify one of its parameters.
6. Save the diagram.
7. Refresh the browser and reload the saved diagram.
8. Verify that the saved blocks and connections are retained.
9. Press **Run** to execute the diagram.
10. Verify that the simulation produces its Matplotlib graph and reports.

### Verification results

| Feature | Result |
|---|---|
| Frontend build | Passed |
| Backend startup | Passed |
| Example diagram loading | Passed |
| Adding blocks from palette | Passed |
| Connecting blocks | Passed |
| Editing block parameters | Passed |
| Saving diagrams | Passed |
| Reloading saved diagrams | Passed |
| Running simulations | Passed |
| Matplotlib graph and reports | Passed |

The following API endpoints were also checked and returned HTTP 200:

- `GET /`
- `GET /docs`
- `GET /api/blocks`

### Notes

- The Make-based build command may require GNU Make on Windows. The npm commands above provide an equivalent frontend build path.
- Node.js is required for building the frontend or running the development server. A pre-built frontend is served by the production backend.
- Run bdweb only on a trusted machine and network. See the security warning above regarding network exposure and filesystem access.


## Technology

- **Frontend:** Svelte 5 runes, `@xyflow/svelte` for graph rendering, Vite for bundling
- **Backend:** FastAPI + uvicorn, CORS-enabled for dev, introspection-based block metadata
- **Python metadata:** Runtime introspection of block `__init__` signatures (not Sphinx parsing)

## Notes

- bdweb depends on `bdsim` core; cannot be used standalone.
- The Vite dev server proxies `/api` to `http://localhost:8000`.
- Block coordinates use bdedit scene units, compatible with xyflow's canvas coordinate system.

