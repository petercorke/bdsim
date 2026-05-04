"""Realtime execution support for sampled/clocked block diagrams."""

from __future__ import annotations

import queue
import re
import threading
import time
import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from bdsim.components import BDStruct, Block, OptionsBase, SimulationState
from bdsim.connect import Plug
from bdsim.run_context import SimulationContext
from bdsim.run_sim import BDSim
from bdsim.timers import create_timer_backend


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
    by_clock: dict[str, ClockStats] = field(default_factory=dict)


@dataclass
class _TickEvent:
    timer_id: str
    scheduled_ns: int
    fired_ns: int


class BDRealTime(BDSim):
    """Realtime runner for sampled/clocked systems.

    This runner currently uses a timer backend abstraction with a thread backend
    fallback and executes model evaluation from a single worker thread.
    """

    def _process_watchlist(self, bd, watch: list[Any]) -> tuple[list[Plug], list[str]]:
        watchlist: list[Plug] = []
        watchnamelist: list[str] = []
        re_block: re.Pattern[str] = re.compile(r"(?P<name>[^[]+)(\[(?P<port>[0-9]+)\])")

        for w in watch:
            if isinstance(w, str):
                m: re.Match[str] | None = re_block.match(w)
                if m is None:
                    raise ValueError("watch block[port] not found: " + w)
                name = m.group("name")
                port = int(m.group("port"))
                b = bd.blocknames[name]
                plug = b[port]
            elif isinstance(w, Block):
                plug = w[0]
            elif isinstance(w, Plug):
                plug = w
            else:
                raise TypeError(f"bad watch type: {type(w)}")

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
        backend: str = "auto",
    ) -> BDStruct:
        """Run sampled/clocked block diagram in realtime.

        :param tf: run horizon in seconds
        :param watch: optional list of watched ports
        :param catchup_policy: "catchup" or "drop_old"
        :param queue_limit: max realtime tick queue depth
        :param log_signals: record t/watch logs
        :param log_clock_state: include per-clock logs in output
        :param backend: timer backend selector
        """

        del dt, samples  # legacy args retained for compatibility

        assert bd.compiled, "Network has not been compiled"

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

        try:
            simstate.tf = tf
            simstate.options = options
            simstate.checkfinite = checkfinite

            watchlist, watchnamelist = self._process_watchlist(bd, watch)
            simstate.watchlist = watchlist
            simstate.watchnamelist = watchnamelist
            simstate.plist = [[] for _ in watchlist]

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
                out["t"] = np.array(simstate.tlist)
                for i, _ in enumerate(simstate.watchlist):
                    out["y" + str(i)] = np.array(simstate.plist[i])
                out["ynames"] = simstate.watchnamelist

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
            s["eval_max_ns"] = stats.eval_max_ns
            s["eval_mean_ns"] = (
                stats.eval_sum_ns / stats.eval_count if stats.eval_count > 0 else 0.0
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
                    "lateness_max_ns": c.lateness_max_ns,
                }
                for name, c in stats.by_clock.items()
            }
            out[".stats"] = s

            if block is not None and options.graphics:
                self.done(bd, block=block)

            return out
        finally:
            self._set_context(None)


if __name__ == "__main__":
    try:
        from ._selftest import run_module_test
    except ImportError:
        from bdsim._selftest import run_module_test

    raise SystemExit(run_module_test(__file__))
