# bdsim — Agent Instructions

> **Audience:** agents working on bdsim's source code. If you're helping someone *use* bdsim, read https://petercorke.github.io/bdsim/llms.txt instead (or `llms-full.txt` for the complete documentation and wiki).

Part of the RVC ecosystem. **Read [rvc-ecosystem/AGENTS.md](https://github.com/petercorke/rvc-ecosystem/blob/main/AGENTS.md) first** — it defines shared conventions: repo ownership, math invariants, dependency boundaries, git/PR workflow, code standards, tech-debt tracking. This file only adds what's specific to this repo.

| | |
|---|---|
| PyPI package | `bdsim` |
| Nickname | bdsim |
| Owner | Peter Corke (`petercorke`) |
| Default branch | `main` |
| Contribution model | Branch → PR; direct push to `main` at Peter's discretion |

## Notes specific to this repo

- Depends on `spatialmath`, `ansitable`. Integrates with `robotics-toolbox-python`
  *optionally* (notebook helpers, examples) — not a hard package dependency, don't add one
  without discussion.
- Hardware I/O blocks integrate with `arduIO` (Python client + Arduino sketch).
- Pure Python — builds with Hatch (`hatchling`) directly.
- Aspirational direction, in progress on branches, not yet merged: more real-time support,
  code generation, and a lightweight web-based editor. `feat/realtime` (hardware-target
  real-time I/O work, most recently targeting Raspberry Pi) is active. The web editor
  (`bdweb`) is on `origin/feat/bdweb` (one commit, SvelteKit + FastAPI) but is **incomplete**:
  `frontend/src/lib/` and `package.json` were never committed, because `.gitignore`'s
  `lib/` rule swallowed the former, so the frontend cannot build. `pyproject.toml` already
  scaffolds it (optional-dependency group, console script, Hatch wheel target `src/bdweb`),
  but the source is not on `main`. Tracked in
  [#118](https://github.com/petercorke/bdsim/issues/118).
- The current Qt-based editor is a vendored student project — kept working for now, but the
  long-term aim is to make it redundant once the web editor lands, not to invest further in it.
- **Block discovery is AST-based, not import-based.** `BDSim` builds its block registry
  (`sim.blocks()` / `--blocks`) by `ast.parse`-ing each `<package>/blocks/*.py` file
  directly, never importing at discovery time (`run_sim.py`, `load_blocks`/`parse_module`).
  Only *top-level* `class` statements are seen — a class nested inside a module-level
  `if`/`try` is invisible to discovery even though it still works fine if imported directly.
  This silently broke `blocks/spatial.py` for years (a now-dead `if sm:` guard, fixed in
  [PR #68](https://github.com/petercorke/bdsim/pull/68)) — keep block class definitions
  unconditional at module scope. Actual imports are deferred via a `_LazyBlockClass` proxy,
  resolved only when a block type is actually instantiated in a diagram.
- `python -m bdsim` / the `bdsim` console script (`src/bdsim/__main__.py`, added in
  [PR #69](https://github.com/petercorke/bdsim/pull/69)) build no diagram — they exist for
  introspection flags handled during `BDSim` construction, e.g. `bdsim --blocks`. `bdrun`
  remains the separate, diagram-first entry point for loading and running a saved `.bd` file.

## Before opening a pull request

Multiple agents often work on the same open issue at once, producing duplicate PRs. Before writing code for an issue:

1. Search for an existing PR for it: `gh pr list --state open --search "#<issue>"`, and check the issue's linked pull requests and assignee. If a PR already exists, or the issue is assigned to someone else, **do not open a competing PR**. Comment on the existing one instead.
2. Comment on the issue to claim it before starting.
3. Disclose AI assistance in the PR description, and state whether the change alters numerical results or public behaviour.
4. One concern per PR, matching `CONTRIBUTING.md`.
