# Telemetry and Remote Control Design Notes

Date: 2026-05-14
Status: Draft architecture notes

## Context and current plan

The active plan now has two coordinated tracks:

1. Untangle realtime runtime from offline runner internals so realtime startup avoids heavyweight imports and GUI dependencies.
2. Add a telemetry framework now, designed so future remote parameter control can be added without protocol breakage.

Compatibility requirement:

- `examples/eg1.py` must continue to work unchanged.

## Design goals

- Keep realtime runtime lean: no implicit matplotlib dependency in realtime execution path.
- Ensure `bdsim.realtime` is the preferred import path for realtime users.
- Support headless realtime execution on devices (Raspberry Pi etc.).
- Provide remote visualization without requiring plotting libraries in realtime process.
- Reserve protocol and runtime hooks for future bidirectional control (remote parameter setting).

## Non-goals for phase 1

- No full remote control API yet.
- No guaranteed delivery requirements for live plotting data.
- No requirement for browser/JavaScript UI in phase 1.

## Package/import direction

- Keep core `bdsim` import surface for existing examples and workflows.
- Prefer new realtime-facing entry point under `bdsim.realtime`.
- Keep graphics-only blocks and mpl-heavy code out of realtime import path.

Planned boundary:

- Core modeling/runtime primitives: no GUI assumptions.
- Realtime runner + hardware I/O: no matplotlib requirement.
- Viewer tooling: separate process and separate module/package.

## Telemetry architecture (phase 1)

Use an explicit producer-consumer split:

- Producer: TELEMETRY block (or sink-style telemetry primitive) in realtime graph.
- Transport: socket-based datagrams.
- Consumer: external viewer process that handles plotting/UI.

### Data flow

1. Realtime graph samples signals.
2. TELEMETRY emits framed messages.
3. Remote viewer receives and plots.

### Why this split

- Realtime process stays deterministic and headless.
- Plotting stack can evolve independently (matplotlib, Tk, Qt, pyqtgraph, etc.).
- Enables future control channel reuse.

## Control architecture (future)

Future counterpart to TELEMETRY: remote parameter set/get.

Needed runtime pieces:

- Parameter registry for tunables:
  - stable id/path (for example `block:param`)
  - type metadata
  - bounds/options
  - mutability flags
- Validation and safe apply semantics:
  - type checks
  - bounds checks
  - deterministic apply policy (for example apply at next clock tick)

## Protocol envelope design

Even in phase 1 telemetry-only mode, use a versioned envelope to avoid future breaking changes.

Recommended top-level fields:

- `version`
- `type` (message kind)
- `source`
- `seq`
- `t` (timestamp)
- `payload`

Candidate message kinds:

- `telemetry.sample`
- `registry.snapshot` (future)
- `param.set` (future)
- `param.ack` (future)
- `error`

## Wire format choice (phase 1)

Recommended now: JSON over UDP.

Reasons:

- very low integration friction
- easy to inspect/debug during bring-up
- schema can evolve quickly

Future path:

- keep same logical schema
- allow pluggable codecs (MessagePack/CBOR/Protobuf) if throughput/latency demands it

## Transport tradeoff summary

UDP:

- Pros: simple, lightweight, low overhead, good for lossy live plots.
- Cons: no delivery guarantee, no built-in backpressure, custom handling for drops/ordering.

ZeroMQ:

- Pros: stronger pub/sub ergonomics, better framing/patterns, easier multi-subscriber growth.
- Cons: extra dependency and operational complexity.

Phase 1 recommendation:

- Start with UDP telemetry for remote viewer MVP.
- Keep transport abstraction so ZeroMQ can be introduced later if needed.

## Realtime block-loader constraints

- Realtime loader should not import graphics blocks.
- Realtime loader should avoid mpl-heavy modules.
- Any graphics-specific functionality should live in viewer-side tooling or explicitly optional modules.

## Phased implementation plan

### Phase A: untangle and isolate realtime path

- Continue reducing realtime imports to minimal required modules.
- Keep `examples/eg1.py` behavior unchanged.

### Phase B: telemetry MVP

- Implement telemetry sink block or equivalent runtime publisher.
- Implement UDP message emitter with sequence and timestamp.
- Implement minimal standalone viewer process for plotting/inspection.

### Phase C: control-ready foundation

- Add tunable parameter registry abstraction.
- Define but do not yet require control message handlers.

### Phase D: remote parameter control

- Implement `param.set` request/ack flow.
- Add safe apply semantics and audit logging.

## Open questions

- exact tunable parameter naming convention (`block:param` vs hierarchical path)
- canonical timestamp source (`perf_counter`-derived vs wall clock)
- whether phase-1 viewer should be terminal/simple plot first or richer GUI first
- whether to reserve telemetry channels/topics now for control traffic separation
