# bdweb — Web-based Block Diagram Editor

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
| `GET` | `/api/library` | All block types with introspected parameters |
| `GET` | `/api/info/{block_type}` | Metadata for a single block (docs URL, params) |
| `GET` | `/api/ls?path=…` | List a directory on the server filesystem |
| `GET` | `/api/exists?path=…` | Check whether a file path exists |
| `POST` | `/api/load` | Load a `.bd` file; returns diagram JSON |
| `POST` | `/api/save` | Save a `.bd` file from diagram JSON |
| `POST` | `/api/run` | Execute the diagram and return stdout + base64 plots |

See [BDFILE.md](BDFILE.md) for the `.bd` file format specification.

## Technology

- **Frontend:** Svelte 5 runes, `@xyflow/svelte` for graph rendering, Vite for bundling
- **Backend:** FastAPI + uvicorn, CORS-enabled for dev, introspection-based block metadata
- **Python metadata:** Runtime introspection of block `__init__` signatures (not Sphinx parsing)

## Notes

- bdweb depends on `bdsim` core; cannot be used standalone.
- The Vite dev server proxies `/api` to `http://localhost:8000`.
- Block coordinates use bdedit scene units, compatible with xyflow's canvas coordinate system.

