# bdsim — Agent Instructions

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
  code generation, and a lightweight web-based editor.
- The current Qt-based editor is a vendored student project — kept working for now, but the
  long-term aim is to make it redundant once the web editor lands, not to invest further in it.
