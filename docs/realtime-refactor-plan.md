# Realtime Refactor Plan (BDRealTime)

Status: Drafted 2026-04-24

This plan captures agreed direction for a new realtime runner with sampled-only scope, portable timer backends, optional logging, and robust timing stats.

## 1. Architectural Decisions

1. Runner placement: Option B (separate realtime runner)
- Keep `BDRealTime` in `src/bdsim/run_realtime.py`.
- Do not merge realtime logic into `BDSim` offline runner internals.
- Rationale: realtime concerns (timer callbacks, queue pressure, overrun policy) are distinct and easier to isolate/test.

2. Scope
- Sampled/clocked systems only.
- No `solve_ivp`, no crossing detector complexity in realtime core.
- Fail fast if continuous states are present.

3. Clock model
- Keep a single `Clock` class.
- Add an explicit realtime tick path (no event-queue reschedule side effect).
- Keep offline event-queue scheduling logic unchanged.

4. Queue/safety model
- One timer per Clock.
- Timer callbacks only enqueue tick events.
- One worker thread performs all `bd.evaluate()` calls and clock state mutation.
- No concurrent model mutation from timer callbacks.

5. Catchup policy
- Option on `BDRealTime` API: `catchup_policy`.
- Default: `"catchup"`.
- Alternative: `"drop_old"`.

6. Logging
- Optional signal/timestamp logging (to control memory growth).
- Stats always on.
- Logging toggles only disable long `t/x` traces, not counters/stats.

7. Percentiles
- P-square percentile estimator is in roadmap, not initial implementation.

## 2. Timer Backend Abstraction

Create a backend abstraction used by `BDRealTime`:

- Linux backend: POSIX timers.
- macOS backend: GCD timers.
- Fallback backend: thread-based periodic timers (for CI/dev and portability).

Suggested backend interface:

```python
from typing import Callable, Protocol, Any

TimerCallback = Callable[[str, int, int], None]
# args: (clock_key, scheduled_ns, fired_ns)

class PeriodicTimerBackend(Protocol):
    def start_periodic(
        self,
        *,
        timer_id: str,
        period_ns: int,
        phase_ns: int,
        callback: TimerCallback,
    ) -> None: ...

    def cancel(self, timer_id: str) -> None: ...
    def start_all(self) -> None: ...
    def stop_all(self) -> None: ...
    def now_ns(self) -> int: ...
```

Notes:
- `scheduled_ns` and `fired_ns` are both monotonic times (ns).
- Keep backend deterministic and lightweight.
- Prefer no string formatting in callback path.

## 3. Lightweight Trace/Logging Schemas

Use a lightweight structured event stream for high-rate runtime events, separate from Python `logging`.

### 3.1 Event categories and ids

```python
from enum import IntEnum

class TraceCategory(IntEnum):
    SCHEDULER = 1
    CLOCK = 2
    REALTIME = 3
    CROSSING = 4
    BLOCK = 5
    SIGNAL = 6

class TraceEventId(IntEnum):
    # scheduler
    INTERVAL_START = 100
    INTERVAL_END = 101
    EVENT_DISPATCH = 102

    # clock
    TIMER_FIRE = 200
    TICK_ENQUEUED = 201
    TICK_PROCESSED = 202

    # realtime
    QUEUE_DEPTH = 300
    OVERRUN = 301
    CATCHUP_APPLIED = 302
    DROP_OLD_APPLIED = 303

    # crossing (offline tracing)
    # ACCEPTED is the reliable event boundary from solve_ivp results.
    # DETECTOR_EVAL is optional debug telemetry only.
    CROSSING_ACCEPTED = 400
    DETECTOR_EVAL = 401

    # block
    BLOCK_ERROR = 500

    # signal (LOG block)
    LOG_SAMPLE = 600
```

### 3.2 Trace event record

```python
from dataclasses import dataclass

@dataclass(slots=True)
class TraceEvent:
    t_ns: int              # monotonic timestamp at emit time
    category: int          # TraceCategory
    event_id: int          # TraceEventId
    source_id: int         # block/clock/source numeric id, -1 if N/A
    sim_t: float           # simulation time (seconds), NaN if N/A
    v0: float              # generic numeric payload field
    v1: float              # generic numeric payload field
    i0: int                # generic integer payload field
    i1: int                # generic integer payload field
```

Design intent:
- Fixed-shape, low-overhead record.
- Avoid allocations/formatting in hot loops.
- Optional adapter can map to richer dict/json for export.

### 3.3 Trace sink interface

```python
from typing import Protocol, Iterable

class TraceSink(Protocol):
    def emit(self, event: TraceEvent) -> None: ...
    def snapshot(self) -> Iterable[TraceEvent]: ...
    def clear(self) -> None: ...
```

Initial sinks:
- `NullTraceSink` (default)
- `RingTraceSink(capacity=N)` (bounded)
- Optional: `JsonlTraceSink(path)` for offline export

### 3.4 Python logging integration

Use Python `logging` for control-plane messages only:
- backend selection,
- startup/shutdown,
- warnings/errors,
- summary reports.

Do not use standard logging handlers for high-rate dataplane events.

### 3.5 Emission cadence policy

Realtime category events are not emitted on every internal operation by default.

- CLOCK events:
    - `TIMER_FIRE` and `TICK_ENQUEUED`: once per timer firing (effectively once per clock tick).
    - `TICK_PROCESSED`: once per processed tick (after worker evaluation path).
- REALTIME events:
    - `OVERRUN`, `CATCHUP_APPLIED`, `DROP_OLD_APPLIED`: on condition (event-driven), not periodic.
    - `QUEUE_DEPTH`: optional sampled telemetry, controlled by `trace_queue_depth_every` (default disabled).
- SCHEDULER events:
    - one per interval boundary / dispatch decision.

Recommended defaults:
- Keep condition-based REALTIME events enabled.
- Keep high-rate telemetry (like periodic queue depth) disabled unless explicitly requested.
- Optionally add per-category decimation to cap trace volume.

### 3.6 Crossing detected vs accepted

For solve_ivp-based runs, only accepted crossing times are reliably observable at runner level.

- `CROSSING_ACCEPTED` (canonical): root accepted as an actual event time from solver output.
- `DETECTOR_EVAL` (optional debug): raw detector function evaluation telemetry; this is heuristic and can include normal stepping and root-refinement probes.

Guidance:
- Do not treat detector-eval telemetry as a semantic crossing boundary.
- Use `source_id` for detector/block identity.
- Use payload fields (`i0`/`i1`) for detector index / sequence correlation if needed.

Note: crossings are an offline-run concern; sampled-only realtime runs typically do not emit crossing events.

## 4. RTStats Schema (v1)

Replace/extending legacy `SimpleStats` with structured stats.

```python
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class ClockStats:
    fired: int = 0
    enqueued: int = 0
    processed: int = 0
    dropped: int = 0
    lateness_sum_ns: int = 0
    lateness_max_ns: int = 0

@dataclass
class RTStats:
    eval_count: int = 0
    eval_sum_ns: int = 0
    eval_max_ns: int = 0

    queue_depth_max: int = 0
    overrun_count: int = 0
    catchup_count: int = 0
    drop_old_count: int = 0

    by_clock: dict[str, ClockStats] = field(default_factory=lambda: defaultdict(ClockStats))

    # future (not in v1): online percentiles via P-square
    # eval_p50_ns, eval_p95_ns, eval_p99_ns, lateness_p95_ns, ...
```

Derived summary fields can be produced at end-of-run:
- `eval_mean_ns`, `eval_max_ns`, etc.

## 5. LOG Block Plan

Create a LOG block for model-level signal logging (works in offline and realtime).

Functional goals:
- Accept one input signal and timestamp each sample.
- Optional metadata/tag.
- Optional decimation/filter.
- Can route through trace sink (`LOG_SAMPLE`) and/or local ring buffer.

Payload modes:
- Value mode: numeric sample (current `LOG_SAMPLE` behavior).
- Token mode: symbolic event/message token without numeric value.
- Mixed mode: token + numeric value in the same sample.

Implementation strategy for token mode:
- Use an interned token table (token string -> small integer id) to avoid high-rate string allocations.
- Emit token id in integer payload field (`i0` or `i1`).
- Keep optional side table in output metadata for token id -> token text mapping.

Suggested parameters:
- `name: str | None`
- `decimate: int = 1`
- `max_samples: int | None = None`
- `enable: bool = True`
- `mode: str = "value"` (`"value" | "token" | "mixed"`)
- `token: str | None = None` (default token for token/mixed modes)

Suggested output behavior:
- v1 as sink block (no output) for simplicity.
- Optional future pass-through variant if needed.

## 6. BDRealTime API (proposed)

```python
def run(
    self,
    bd,
    *,
    tf: float = 5.0,
    watch: list | None = None,
    catchup_policy: str = "catchup",   # "catchup" | "drop_old"
    queue_limit: int = 4096,
    log_signals: bool = False,
    log_clock_state: bool = False,
    trace_enable: bool = False,
    trace_capacity: int = 20000,
    backend: str = "auto",             # "auto" | "posix" | "gcd" | "thread"
) -> BDStruct:
    ...
```

Output (`BDStruct`) should include:
- watched outputs (`y0`, `y1`, ...), optional time arrays when enabled,
- per-clock logs when enabled,
- always-on stats under `.stats` (or similar hidden metadata field).

## 7. Implementation Phases

Phase 1: Realtime core
1. Rebuild `BDRealTime` sampled-only runner skeleton.
2. Add thread-safe event queue + single evaluation worker.
3. Add fallback thread timer backend.
4. Add RTStats v1 counters/timing.

Phase 2: Native timer backends
1. Add Linux POSIX timer backend.
2. Add macOS GCD backend.
3. Keep fallback backend for tests and unsupported environments.

Phase 3: Optional trace/logging
1. Add `TraceEvent`, `TraceSink`, and ring sink.
2. Integrate optional tracing in realtime runner.
3. Integrate optional tracing hooks in offline runner for interval/event/crossing observability.

Phase 4: LOG block and tooling
1. Add LOG block (sink) with timestamped samples.
2. Connect LOG samples to trace sink and/or block-local buffers.
3. Add examples and docs updates.

Phase 5: Advanced statistics
1. Add online percentile estimation via P-square (deferred).
2. Extend summary output with p50/p95/p99 for eval and lateness.

## 8. Testing Plan

1. Unit tests
- backend selection (`auto` on macOS/Linux)
- queue behavior and catchup/drop policy
- logging toggles and memory bounds
- LOG block sample/decimation behavior

2. Integration tests
- multi-clock sampled systems complete to `tf`
- deterministic behavior with thread fallback backend
- no regressions in offline simulation path

3. Performance/safety checks
- bounded queue behavior under overload
- stats and overrun counters increase as expected
- no concurrent mutation of model state
