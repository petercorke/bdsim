"""Realtime execution support for sampled/clocked block diagrams."""

from __future__ import annotations

import gc
import importlib
import queue
import re
import threading
import time
import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np


def _env_true(name: str) -> bool:
    import os

    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


_IMPORT_TIMING = _env_true("BDSIM_IMPORT_TIMING")


def _timed_module(module_name: str):
    # Realtime startup cost is dominated by imports on low-power targets.
    # Keep heavyweight modules out of module scope and import them only when
    # needed, while retaining optional timing visibility for profiling.
    t0 = time.perf_counter() if _IMPORT_TIMING else 0.0
    module = importlib.import_module(module_name)
    if _IMPORT_TIMING:
        print(
            f"bdsim import: run_realtime->{module_name}={time.perf_counter() - t0:.3f}s"
        )
    return module


_m_components = _timed_module("bdsim.components")
BDStruct = _m_components.BDStruct
OptionsBase = _m_components.OptionsBase
SimulationState = _m_components.SimulationState

IOProvider = _timed_module("bdsim.blocks.io_base").IOProvider
Plug = _timed_module("bdsim.connect").Plug
SimulationContext = _timed_module("bdsim.run_context").SimulationContext
create_timer_backend = _timed_module("bdsim.timers").create_timer_backend


class BDRealTimeState(SimulationState):
    """Realtime simulation state for a single run."""

    def __init__(self) -> None:
        super().__init__()
        self.watchlist: list[Plug] = []
        self.watchnamelist: list[str] = []
        self.tlist: list[float] = []
        self.plist: list[list[Any]] = []


@dataclass
class ClockStats:
    fired: int = 0
    enqueued: int = 0
    processed: int = 0
    dropped: int = 0
    lateness_sum_ns: int = 0
    lateness_sum_sq_ns2: int = 0
    lateness_max_ns: int = 0


@dataclass
class RTStats:
    eval_count: int = 0
    eval_sum_ns: int = 0
    eval_sum_sq_ns2: int = 0
    eval_max_ns: int = 0
    queue_depth_max: int = 0
    overrun_count: int = 0
    catchup_count: int = 0
    drop_old_count: int = 0
    by_clock: dict[str, ClockStats] = field(default_factory=dict)


@dataclass
class _TickEvent:
    timer_id: str
    scheduled_ns: int
    fired_ns: int


class BDRealTime:
    """Realtime runner for sampled/clocked systems.

    This runner currently uses a timer backend abstraction with a thread backend
    fallback and executes model evaluation from a single worker thread.
    """

    def __init__(
        self,
        *args: Any,
        io_provider: IOProvider | str | None = None,
        io_provider_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        # Realtime mode does not need block metadata/doc harvesting during
        # startup, so default to the minimal path unless explicitly overridden.
        kwargs.setdefault("block_metadata", "minimal")
        # Import BDSim on demand so `from bdsim.realtime import BDRealTime`
        # stays cheap until an instance is actually constructed.
        bdsim_cls = _timed_module("bdsim.run_sim").BDSim
        self._sim = bdsim_cls(*args, **kwargs)
        if isinstance(io_provider, str):
            self.io_provider = IOProvider.create(
                io_provider, **(io_provider_kwargs or {})
            )
        else:
            self.io_provider = io_provider

    def __getattr__(self, name: str) -> Any:
        # Delegate shared runtime API (options, blockdiagram(), context helpers,
        # done(), etc.) to the underlying BDSim instance.
        return getattr(self._sim, name)

    def blockdiagram(self, *args: Any, **kwargs: Any) -> Any:
        """Create a block diagram bound to this realtime runtime wrapper."""
        bd = self._sim.blockdiagram(*args, **kwargs)
        bd.runtime = self
        return bd

    def _process_watchlist(self, bd, watch: list[Any]) -> tuple[list[Plug], list[str]]:
        watchlist: list[Plug] = []
        watchnamelist: list[str] = []
        re_block: re.Pattern[str] = re.compile(r"(?P<name>[^[]+)(\[(?P<port>[0-9]+)\])")
        block_type: type[Any] | None = None

        for w in watch:
            if isinstance(w, str):
                m: re.Match[str] | None = re_block.match(w)
                if m is None:
                    raise ValueError("watch block[port] not found: " + w)
                name = m.group("name")
                port = int(m.group("port"))
                b = bd.blocknames[name]
                plug = b[port]
            elif isinstance(w, Plug):
                plug = w
            else:
                # Resolve Block type lazily so realtime startup doesn't import
                # the heavy bdsim.block module unless watch values require it.
                if block_type is None:
                    try:
                        block_module = _timed_module("bdsim.block")
                        block_type = getattr(block_module, "Block", None)
                    except Exception:
                        block_type = None
                if block_type is not None and isinstance(w, block_type):
                    plug = w[0]
                else:
                    raise TypeError(f"bad watch type: {type(w)}")

            if plug.block.blockclass == "subsystem":
                # subsystem blocks no longer exist in the wirelist and don't
                # have their own output values; redirect to the subsystem's
                # OUTPORT block so outport_value() succeeds.
                plug.block = plug.block.outport

            # Watchlists are always output ports.  Pointing at a block
            # with no output (e.g. a sink like ANALOGOUT) is a user error.
            if plug.port >= plug.block.nout:
                raise ValueError(
                    f"Watch {w!r}: block {plug.block.name!r} has {plug.block.nout} "
                    f"output port(s), so port {plug.port} does not exist. "
                    "Watch lists must reference output ports. "
                    "For a sink block, watch the upstream block that drives it."
                )

            watchlist.append(plug)
            watchnamelist.append(str(plug))

        return watchlist, watchnamelist

    def _clock_stats(self, stats: RTStats, timer_id: str) -> ClockStats:
        if timer_id not in stats.by_clock:
            stats.by_clock[timer_id] = ClockStats()
        return stats.by_clock[timer_id]

    def run(
        self,
        bd,
        tf: float = 5,
        dt=None,
        block=None,
        checkfinite: bool = True,
        watch=None,
        samples=True,
        T=None,
        *,
        catchup_policy: str = "catchup",
        queue_limit: int = 4096,
        log_signals: bool = False,
        log_clock_state: bool = False,
        log_gc: bool = False,
        backend: str = "auto",
    ) -> BDStruct:
        """Run sampled/clocked block diagram in realtime.

        :param tf: run horizon in seconds
        :param watch: optional list of watched ports
        :param catchup_policy: "catchup" or "drop_old"
        :param queue_limit: max realtime tick queue depth
        :param log_signals: record t/watch logs
        :param log_clock_state: include per-clock logs in output
        :param log_gc: include Python GC activity and pause stats in output
        :param backend: timer backend selector
        """

        del dt, samples  # legacy args retained for compatibility

        assert bd.compiled, "Network has not been compiled"

        # Ensure runtime-visible provider lookup resolves against the realtime
        # wrapper (not the internal BDSim helper instance).
        bd.runtime = self

        if T is not None:
            warnings.warn(
                "run(T=...) is deprecated, use run(tf=...) instead",
                DeprecationWarning,
                stacklevel=2,
            )
            tf = T

        if bd.nstates > 0:
            raise RuntimeError(
                "BDRealTime currently supports sampled/clocked systems only"
            )

        if catchup_policy not in ("catchup", "drop_old"):
            raise ValueError("catchup_policy must be 'catchup' or 'drop_old'")

        watch = [] if watch is None else list(watch)

        simstate = BDRealTimeState()
        assert self.options is not None
        options: OptionsBase = self.options.copy()

        context = SimulationContext(
            bd=bd, simstate=simstate, options=options, progress=None, threaded=False
        )
        self._set_context(context)

        gc_metrics: dict[str, Any] | None = None
        gc_cb = None
        if log_gc:
            before_stats = gc.get_stats()
            gc_metrics = {
                "collections": 0,
                "collected": 0,
                "uncollectable": 0,
                "collections_by_gen": {0: 0, 1: 0, 2: 0},
                "collected_by_gen": {0: 0, 1: 0, 2: 0},
                "uncollectable_by_gen": {0: 0, 1: 0, 2: 0},
                "pause_sum_ns": 0,
                "pause_max_ns": 0,
                "_start_ns": {},
                "count_before": gc.get_count(),
                "stats_before": before_stats,
            }

            def _gc_callback(phase: str, info: dict[str, Any]) -> None:
                if gc_metrics is None:
                    return
                gen = int(info.get("generation", 0))
                gen = 0 if gen < 0 else (2 if gen > 2 else gen)
                if phase == "start":
                    gc_metrics["_start_ns"][gen] = time.perf_counter_ns()
                    return
                if phase != "stop":
                    return

                gc_metrics["collections"] += 1
                gc_metrics["collections_by_gen"][gen] += 1
                collected = int(info.get("collected", 0))
                uncollectable = int(info.get("uncollectable", 0))
                gc_metrics["collected"] += collected
                gc_metrics["uncollectable"] += uncollectable
                gc_metrics["collected_by_gen"][gen] += collected
                gc_metrics["uncollectable_by_gen"][gen] += uncollectable

                start_ns = gc_metrics["_start_ns"].pop(gen, None)
                if start_ns is not None:
                    pause_ns = time.perf_counter_ns() - start_ns
                    gc_metrics["pause_sum_ns"] += pause_ns
                    gc_metrics["pause_max_ns"] = max(
                        gc_metrics["pause_max_ns"], pause_ns
                    )

            gc_cb = _gc_callback
            gc.callbacks.append(gc_cb)

        try:
            from colored import attr as _attr, fg as _fg

            _fg_yellow = _fg("yellow")
            _attr_reset = _attr(0)
        except Exception:
            _fg_yellow = _attr_reset = ""

        try:
            simstate.tf = tf
            simstate.options = options
            simstate.checkfinite = checkfinite

            watchlist, watchnamelist = self._process_watchlist(bd, watch)
            simstate.watchlist = watchlist
            simstate.watchnamelist = watchnamelist
            simstate.plist = [[] for _ in watchlist]

            if not options.quiet:
                print(_fg_yellow)
                print(f">>> Start realtime simulation: T = {tf}")
                s_disc = "s" if bd.ndstates != 1 else ""
                print(
                    f"  Discrete system: {bd.ndstates} discrete state variable{s_disc}"
                )
                for clock in bd.clocklist:
                    print(f"    {clock.name} (T={clock.T}s): x0 = ", clock.getstate0())
                print(_attr_reset)

            # Start blocks and initialize clock runtime state.
            bd.start(simstate)

            timer_backend = create_timer_backend(backend)
            start_ns = timer_backend.now_ns()
            deadline_ns = start_ns + int(tf * 1e9)

            tick_queue: queue.Queue[_TickEvent] = queue.Queue(maxsize=queue_limit)
            stop_event = threading.Event()
            stats = RTStats()
            stats_lock = threading.Lock()

            timer_to_clock = {c.name: c for c in bd.clocklist}

            def on_tick(timer_id: str, scheduled_ns: int, fired_ns: int) -> None:
                if scheduled_ns > deadline_ns or stop_event.is_set():
                    return

                with stats_lock:
                    cs = self._clock_stats(stats, timer_id)
                    cs.fired += 1

                try:
                    tick_queue.put_nowait(_TickEvent(timer_id, scheduled_ns, fired_ns))
                except queue.Full:
                    with stats_lock:
                        cs = self._clock_stats(stats, timer_id)
                        cs.dropped += 1
                        stats.drop_old_count += 1
                    return

                with stats_lock:
                    cs = self._clock_stats(stats, timer_id)
                    cs.enqueued += 1
                    lateness_ns = max(0, fired_ns - scheduled_ns)
                    cs.lateness_sum_ns += lateness_ns
                    cs.lateness_sum_sq_ns2 += lateness_ns * lateness_ns
                    cs.lateness_max_ns = max(cs.lateness_max_ns, lateness_ns)
                    stats.queue_depth_max = max(
                        stats.queue_depth_max, tick_queue.qsize()
                    )

            for clock in bd.clocklist:
                timer_backend.start_periodic(
                    timer_id=clock.name,
                    period_ns=int(clock.T * 1e9),
                    phase_ns=int(max(0.0, float(clock.offset)) * 1e9),
                    callback=on_tick,
                )

            timer_backend.start_all()

            def _record_watch(sim_t: float) -> None:
                if not log_signals:
                    return
                simstate.tlist.append(sim_t)
                for i, p in enumerate(simstate.watchlist):
                    b = p.block
                    output = b.outport_value(p.port)
                    simstate.plist[i].append(output)

            def worker() -> None:
                while not stop_event.is_set() or not tick_queue.empty():
                    try:
                        if catchup_policy == "catchup":
                            backlog = tick_queue.qsize()
                            if backlog > 0:
                                with stats_lock:
                                    stats.catchup_count += backlog
                        event = tick_queue.get(timeout=0.05)
                    except queue.Empty:
                        if timer_backend.now_ns() >= deadline_ns:
                            stop_event.set()
                        continue

                    events: list[_TickEvent] = [event]
                    if catchup_policy == "drop_old":
                        latest: dict[str, _TickEvent] = {event.timer_id: event}
                        dropped_by_timer: dict[str, int] = {}
                        while True:
                            try:
                                extra = tick_queue.get_nowait()
                            except queue.Empty:
                                break
                            previous = latest.get(extra.timer_id)
                            if previous is not None:
                                dropped_by_timer[extra.timer_id] = (
                                    dropped_by_timer.get(extra.timer_id, 0) + 1
                                )
                            latest[extra.timer_id] = extra
                        dropped = sum(dropped_by_timer.values())
                        if dropped > 0:
                            with stats_lock:
                                stats.drop_old_count += dropped
                                for timer_id, n in dropped_by_timer.items():
                                    cs = self._clock_stats(stats, timer_id)
                                    cs.dropped += n
                        events = list(latest.values())

                    for ev in events:
                        if ev.timer_id not in timer_to_clock:
                            continue

                        sim_t = (ev.scheduled_ns - start_ns) / 1e9
                        if sim_t > tf + 1e-12:
                            stop_event.set()
                            break

                        simstate.t = sim_t
                        clock = timer_to_clock[ev.timer_id]
                        eval_start = time.perf_counter_ns()
                        bd.evaluate(
                            bd.state_map(np.array([]), simstate),
                            sim_t,
                            checkfinite=checkfinite,
                        )
                        clock.tick_realtime(sim_t, simstate)
                        eval_ns = time.perf_counter_ns() - eval_start

                        with stats_lock:
                            stats.eval_count += 1
                            stats.eval_sum_ns += eval_ns
                            stats.eval_sum_sq_ns2 += eval_ns * eval_ns
                            stats.eval_max_ns = max(stats.eval_max_ns, eval_ns)
                            cs = self._clock_stats(stats, ev.timer_id)
                            cs.processed += 1
                            if eval_ns > int(clock.T * 1e9):
                                stats.overrun_count += 1

                        _record_watch(sim_t)

                        if simstate.stop is not None:
                            stop_event.set()
                            break

                    if timer_backend.now_ns() >= deadline_ns:
                        stop_event.set()

            worker_thread = threading.Thread(
                target=worker, name="rt-worker", daemon=True
            )
            worker_thread.start()

            while not stop_event.is_set():
                if timer_backend.now_ns() >= deadline_ns:
                    stop_event.set()
                    break
                time.sleep(0.01)

            timer_backend.stop_all()
            worker_thread.join(timeout=2.0)

            out = BDStruct(name="results")
            if log_signals:
                if simstate.plist:
                    # Trim to min recorded length in case the worker thread
                    # crashed mid-tick, leaving some channels one entry short.
                    min_len = min(len(p) for p in simstate.plist)
                    out["t"] = np.array(simstate.tlist[:min_len])
                    if min_len > 0:
                        out["y"] = np.column_stack(
                            [np.array(p[:min_len]) for p in simstate.plist]
                        )
                else:
                    out["t"] = np.array(simstate.tlist)
                out["ynames"] = [p.block.name for p in simstate.watchlist]

            if log_clock_state:
                for i, clock in enumerate(bd.clocklist):
                    name = f"clock{i}"
                    clockdata = BDStruct(name)
                    clock_t, clock_x = clock.getlog(simstate)
                    clockdata["t"] = np.array(clock_t)
                    clockdata["x"] = np.array(clock_x)
                    out.add(name, clockdata)

            s = BDStruct(name="stats")
            s["eval_count"] = stats.eval_count
            s["eval_sum_ns"] = stats.eval_sum_ns
            s["eval_sum_sq_ns2"] = stats.eval_sum_sq_ns2
            s["eval_max_ns"] = stats.eval_max_ns
            s["eval_mean_ns"] = (
                stats.eval_sum_ns / stats.eval_count if stats.eval_count > 0 else 0.0
            )
            s["eval_stddev_ns"] = (
                np.sqrt(
                    max(
                        0.0,
                        (stats.eval_sum_sq_ns2 / stats.eval_count)
                        - (s["eval_mean_ns"] * s["eval_mean_ns"]),
                    )
                )
                if stats.eval_count > 0
                else 0.0
            )
            s["queue_depth_max"] = stats.queue_depth_max
            s["overrun_count"] = stats.overrun_count
            s["catchup_count"] = stats.catchup_count
            s["drop_old_count"] = stats.drop_old_count
            s["by_clock"] = {
                name: {
                    "fired": c.fired,
                    "enqueued": c.enqueued,
                    "processed": c.processed,
                    "dropped": c.dropped,
                    "lateness_sum_ns": c.lateness_sum_ns,
                    "lateness_sum_sq_ns2": c.lateness_sum_sq_ns2,
                    "lateness_mean_ns": (
                        c.lateness_sum_ns / c.enqueued if c.enqueued > 0 else 0.0
                    ),
                    "lateness_stddev_ns": (
                        np.sqrt(
                            max(
                                0.0,
                                (c.lateness_sum_sq_ns2 / c.enqueued)
                                - (
                                    (c.lateness_sum_ns / c.enqueued)
                                    * (c.lateness_sum_ns / c.enqueued)
                                ),
                            )
                        )
                        if c.enqueued > 0
                        else 0.0
                    ),
                    "lateness_max_ns": c.lateness_max_ns,
                }
                for name, c in stats.by_clock.items()
            }

            if log_gc and gc_metrics is not None:
                after_stats = gc.get_stats()
                gc_by_gen = {}
                for i in range(min(len(after_stats), 3)):
                    before = gc_metrics["stats_before"][i]
                    after = after_stats[i]
                    gc_by_gen[str(i)] = {
                        "collections": int(after.get("collections", 0))
                        - int(before.get("collections", 0)),
                        "collected": int(after.get("collected", 0))
                        - int(before.get("collected", 0)),
                        "uncollectable": int(after.get("uncollectable", 0))
                        - int(before.get("uncollectable", 0)),
                    }

                gc_summary = {
                    "count_before": gc_metrics["count_before"],
                    "count_after": gc.get_count(),
                    "collections": gc_metrics["collections"],
                    "collected": gc_metrics["collected"],
                    "uncollectable": gc_metrics["uncollectable"],
                    "collections_by_gen": gc_metrics["collections_by_gen"],
                    "collected_by_gen": gc_metrics["collected_by_gen"],
                    "uncollectable_by_gen": gc_metrics["uncollectable_by_gen"],
                    "pause_sum_ns": gc_metrics["pause_sum_ns"],
                    "pause_max_ns": gc_metrics["pause_max_ns"],
                    "pause_mean_ns": (
                        gc_metrics["pause_sum_ns"] / gc_metrics["collections"]
                        if gc_metrics["collections"] > 0
                        else 0.0
                    ),
                    "get_stats_delta_by_gen": gc_by_gen,
                }
                s["gc"] = gc_summary
            out[".stats"] = s

            if not options.quiet:
                print(_fg_yellow)
                print("<<< Realtime simulation complete")
                print(f"  block diagram evaluations: {stats.eval_count}")
                print(f"  max eval time:             {stats.eval_max_ns / 1000:.1f} µs")
                print(f"  mean eval time:            {s['eval_mean_ns'] / 1000:.1f} µs")
                print(
                    f"  stddev eval time:          {s['eval_stddev_ns'] / 1000:.1f} µs"
                )
                print(f"  overrun count:             {stats.overrun_count}")
                print(f"  max queue depth:           {stats.queue_depth_max}")
                for name, c in stats.by_clock.items():
                    lateness_mean_ns = (
                        c.lateness_sum_ns / c.enqueued if c.enqueued > 0 else 0.0
                    )
                    lateness_stddev_ns = (
                        np.sqrt(
                            max(
                                0.0,
                                (c.lateness_sum_sq_ns2 / c.enqueued)
                                - (lateness_mean_ns * lateness_mean_ns),
                            )
                        )
                        if c.enqueued > 0
                        else 0.0
                    )
                    abandoned = c.fired - c.processed - c.dropped
                    print(
                        f"  clock {name}: fired={c.fired} processed={c.processed} "
                        f"dropped={c.dropped} abandoned={abandoned} "
                        f"lateness_mean_ns={lateness_mean_ns / 1000:.1f} µs "
                        f"lateness_stddev_ns={lateness_stddev_ns / 1000:.1f} µs "
                        f"lateness_max_ns={c.lateness_max_ns / 1000:.1f} µs"
                    )
                if log_gc and "gc" in s:
                    g = s["gc"]
                    print(
                        f"  gc: collections={g['collections']} "
                        f"collected={g['collected']} "
                        f"uncollectable={g['uncollectable']}"
                    )
                    print(
                        f"  gc pause: mean={g['pause_mean_ns'] / 1000:.1f} µs "
                        f"max={g['pause_max_ns'] / 1000:.1f} µs"
                    )
                print(_attr_reset)

            if block is not None and options.graphics:
                self.done(bd, block=block)

            if options.outfile is not None:
                out.dump(options.outfile)
                if not options.quiet:
                    print("simulation results pickled --> ", options.outfile)

            if options.jsonfile is not None:
                out.dump_json(options.jsonfile)
                if not options.quiet:
                    print("simulation results JSON --> ", options.jsonfile)

            return out
        finally:
            if gc_cb is not None:
                try:
                    gc.callbacks.remove(gc_cb)
                except ValueError:
                    pass
            provider = getattr(self, "io_provider", None)
            if provider is not None:
                provider.close()
            self._set_context(None)


if __name__ == "__main__":
    try:
        from ._selftest import run_module_test
    except ImportError:
        from bdsim._selftest import run_module_test

    raise SystemExit(run_module_test(__file__))
