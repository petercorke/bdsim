# bdweb — Web-based Block Diagram Editor

Modern web UI for bdsim using SvelteKit 5 and FastAPI.

## Structure

- `backend/` — Python FastAPI server
  - `server.py` — Main API: block library, metadata introspection, simulation runner
  - `__main__.py` — Entry point; launches browser on startup
  
- `frontend/` — SvelteKit web application
  - `src/routes/+page.svelte` — Main editor canvas
  - `src/lib/` — Components: Palette, PropsPanel, BlockNode, etc.
  - `vite.config.ts` — Build config

## Development

### Prerequisites
- Python 3.10+
- Node.js 18+

### Setup

1. **Backend only** (serves block metadata, no UI):
   ```bash
   pip install -e ".[bdweb]"
   python -m bdweb  # http://localhost:8000
   ```

2. **Full development** (backend + live frontend):
   ```bash
   # Terminal 1: frontend dev server
   cd src/bdweb/frontend
   npm install
   npm run dev  # http://localhost:5173
   
   # Terminal 2: backend server
   python -m bdweb  # http://localhost:8000
   ```

### Frontend only (served from backend in production)

After production build:
```bash
cd src/bdweb/frontend
npm run build  # Creates build/
```

The backend serves the built frontend from `frontend/build/`.

## Key Features

- **Live block palette** with search and package filtering
- **Editable parameter panel** with type-aware inputs
- **Auto-layout handles** from `nin`/`nout` edits
- **Block documentation links** with computed URLs
- **Block naming** with auto-indexing (e.g., `constant.0`, `integrator.1`)

## API Endpoints

- `GET /api/library` — All block types with introspected parameters
- `GET /api/info/{block_type}` — Metadata for a single block (docs URL, params)
- `POST /api/run` — Execute block diagram (not yet fully integrated)

## Technology

- **Frontend:** Svelte 5 runes, xyflow for graph rendering, Vite for bundling
- **Backend:** FastAPI with CORS, introspection-based metadata
- **Python metadata:** Runtime introspection of block `__init__` signatures (not Sphinx parsing)

## Notes

- bdweb depends on `bdsim` core; cannot be used standalone.
- Frontend styling uses Tailwind (utilities only, no component deps).
- Block metadata is computed from Python type hints and defaults at runtime.
