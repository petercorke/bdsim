"""Timer backends for realtime execution.

The initial implementation provides a portable thread-based periodic backend
used for development/testing and as the default fallback. Native POSIX/GCD
backends are scaffolded for later implementation.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import platform
import threading
import time
import warnings
from dataclasses import dataclass
from typing import Callable, Protocol

TimerCallback = Callable[[str, int, int], None]


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


@dataclass
class _PeriodicTimerSpec:
    timer_id: str
    period_ns: int
    phase_ns: int
    callback: TimerCallback


class ThreadPeriodicTimerBackend:
    """Portable periodic timer backend using one thread per timer."""

    def __init__(self) -> None:
        self._specs: dict[str, _PeriodicTimerSpec] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._stop = threading.Event()
        self._started = False

    def now_ns(self) -> int:
        return time.perf_counter_ns()

    def start_periodic(
        self,
        *,
        timer_id: str,
        period_ns: int,
        phase_ns: int,
        callback: TimerCallback,
    ) -> None:
        if period_ns <= 0:
            raise ValueError("period_ns must be > 0")
        if timer_id in self._specs:
            raise ValueError(f"duplicate timer id: {timer_id}")

        self._specs[timer_id] = _PeriodicTimerSpec(
            timer_id=timer_id,
            period_ns=period_ns,
            phase_ns=max(0, phase_ns),
            callback=callback,
        )
        if self._started:
            self._start_one(timer_id, self._specs[timer_id])

    def _start_one(self, timer_id: str, spec: _PeriodicTimerSpec) -> None:
        if timer_id in self._threads and self._threads[timer_id].is_alive():
            return

        def _run() -> None:
            t0 = self.now_ns()
            next_ns = t0 + spec.phase_ns
            while not self._stop.is_set():
                now = self.now_ns()
                sleep_ns = next_ns - now
                if sleep_ns > 0:
                    time.sleep(sleep_ns / 1e9)
                fired_ns = self.now_ns()
                spec.callback(spec.timer_id, next_ns, fired_ns)
                next_ns += spec.period_ns

        thread = threading.Thread(target=_run, name=f"rt-timer-{timer_id}", daemon=True)
        self._threads[timer_id] = thread
        thread.start()

    def cancel(self, timer_id: str) -> None:
        # Coarse-grained cancellation via stop_all in v1.
        # Fine-grained per-timer cancellation can be added later.
        if timer_id not in self._specs:
            return
        del self._specs[timer_id]

    def start_all(self) -> None:
        self._started = True
        for timer_id, spec in list(self._specs.items()):
            self._start_one(timer_id, spec)

    def stop_all(self) -> None:
        self._stop.set()
        for thread in list(self._threads.values()):
            thread.join(timeout=0.5)


class PosixTimerBackend:
    """Scaffold for Linux POSIX timer backend (to be implemented)."""

    def now_ns(self) -> int:
        return time.perf_counter_ns()

    def start_periodic(
        self,
        *,
        timer_id: str,
        period_ns: int,
        phase_ns: int,
        callback: TimerCallback,
    ) -> None:
        raise NotImplementedError("POSIX timer backend not implemented yet")

    def cancel(self, timer_id: str) -> None:
        raise NotImplementedError("POSIX timer backend not implemented yet")

    def start_all(self) -> None:
        raise NotImplementedError("POSIX timer backend not implemented yet")

    def stop_all(self) -> None:
        raise NotImplementedError("POSIX timer backend not implemented yet")


class GCDTimerBackend:
    """macOS periodic timer backend using Grand Central Dispatch.

    Uses dispatch source timers from libSystem via ctypes. Callbacks execute on
    a global dispatch queue and invoke the registered Python callback with
    scheduled/fired timestamps.
    """

    _DISPATCH_TIME_NOW = 0

    def __init__(self) -> None:
        if platform.system().lower() != "darwin":
            raise RuntimeError("GCDTimerBackend is only available on macOS")

        lib_path = ctypes.util.find_library("System") or "/usr/lib/libSystem.dylib"
        self._lib = ctypes.CDLL(lib_path, use_errno=True)

        # Function signatures.
        self._lib.dispatch_get_global_queue.argtypes = [ctypes.c_long, ctypes.c_ulong]
        self._lib.dispatch_get_global_queue.restype = ctypes.c_void_p

        self._lib.dispatch_source_create.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_void_p,
        ]
        self._lib.dispatch_source_create.restype = ctypes.c_void_p

        self._lib.dispatch_set_context.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self._lib.dispatch_set_context.restype = None

        self._handler_type = ctypes.CFUNCTYPE(None, ctypes.c_void_p)
        self._lib.dispatch_source_set_event_handler_f.argtypes = [
            ctypes.c_void_p,
            self._handler_type,
        ]
        self._lib.dispatch_source_set_event_handler_f.restype = None

        self._lib.dispatch_time.argtypes = [ctypes.c_ulonglong, ctypes.c_longlong]
        self._lib.dispatch_time.restype = ctypes.c_ulonglong

        self._lib.dispatch_source_set_timer.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulonglong,
            ctypes.c_ulonglong,
            ctypes.c_ulonglong,
        ]
        self._lib.dispatch_source_set_timer.restype = None

        self._lib.dispatch_resume.argtypes = [ctypes.c_void_p]
        self._lib.dispatch_resume.restype = None

        self._lib.dispatch_source_cancel.argtypes = [ctypes.c_void_p]
        self._lib.dispatch_source_cancel.restype = None

        # dispatch_release may be unavailable when ObjC-managed objects are used;
        # treat it as optional.
        self._dispatch_release = getattr(self._lib, "dispatch_release", None)
        if self._dispatch_release is not None:
            self._dispatch_release.argtypes = [ctypes.c_void_p]
            self._dispatch_release.restype = None

        # Timer source type symbol.
        try:
            # DISPATCH_SOURCE_TYPE_TIMER is the *address* of this symbol.
            source_sym = ctypes.c_char.in_dll(self._lib, "_dispatch_source_type_timer")
            self._source_type_timer = ctypes.c_void_p(ctypes.addressof(source_sym))
        except ValueError as err:
            raise RuntimeError("failed to load GCD timer source symbol") from err

        # Keep references alive.
        self._specs: dict[str, _PeriodicTimerSpec] = {}
        self._sources: dict[str, ctypes.c_void_p] = {}
        self._context_tokens: dict[str, int] = {}
        self._token_to_timer: dict[int, str] = {}
        self._next_token = 1
        self._state: dict[str, dict[str, int]] = {}
        self._started = False
        self._lock = threading.Lock()

        self._event_handler = self._handler_type(self._on_timer_fire)

    def _on_timer_fire(self, ctx: ctypes.c_void_p) -> None:
        token = ctypes.cast(ctx, ctypes.c_void_p).value
        if token is None:
            return
        token_i = int(token)

        with self._lock:
            timer_id = self._token_to_timer.get(token_i)
        if timer_id is None:
            return

        with self._lock:
            spec = self._specs.get(timer_id)
            st = self._state.get(timer_id)
            if spec is None or st is None:
                return
            scheduled_ns = st["next_ns"]
            st["next_ns"] = scheduled_ns + st["period_ns"]

        fired_ns = self.now_ns()
        spec.callback(timer_id, scheduled_ns, fired_ns)

    def _create_source(self, timer_id: str, spec: _PeriodicTimerSpec) -> None:
        queue = self._lib.dispatch_get_global_queue(0, 0)
        if not queue:
            raise RuntimeError("dispatch_get_global_queue failed")

        source = self._lib.dispatch_source_create(
            self._source_type_timer,
            0,
            0,
            queue,
        )
        if not source:
            raise RuntimeError(f"dispatch_source_create failed for timer {timer_id}")

        # Store a stable integer token as context.
        token = self._next_token
        self._next_token += 1
        self._context_tokens[timer_id] = token
        self._token_to_timer[token] = timer_id
        self._lib.dispatch_set_context(source, ctypes.c_void_p(token))
        self._lib.dispatch_source_set_event_handler_f(source, self._event_handler)

        # Use dispatch_time(DISPATCH_TIME_NOW, phase_ns) for first fire.
        start = self._lib.dispatch_time(self._DISPATCH_TIME_NOW, int(spec.phase_ns))
        self._lib.dispatch_source_set_timer(source, start, int(spec.period_ns), 0)

        now_ns = self.now_ns()
        self._state[timer_id] = {
            "period_ns": int(spec.period_ns),
            "next_ns": now_ns + int(spec.phase_ns),
        }
        self._sources[timer_id] = ctypes.c_void_p(source)

    def now_ns(self) -> int:
        return time.perf_counter_ns()

    def now_ns(self) -> int:
        return time.perf_counter_ns()

    def start_periodic(
        self,
        *,
        timer_id: str,
        period_ns: int,
        phase_ns: int,
        callback: TimerCallback,
    ) -> None:
        if period_ns <= 0:
            raise ValueError("period_ns must be > 0")
        with self._lock:
            if timer_id in self._specs:
                raise ValueError(f"duplicate timer id: {timer_id}")

            self._specs[timer_id] = _PeriodicTimerSpec(
                timer_id=timer_id,
                period_ns=int(period_ns),
                phase_ns=max(0, int(phase_ns)),
                callback=callback,
            )

            if self._started:
                self._create_source(timer_id, self._specs[timer_id])
                self._lib.dispatch_resume(self._sources[timer_id])

    def cancel(self, timer_id: str) -> None:
        with self._lock:
            source = self._sources.pop(timer_id, None)
            self._specs.pop(timer_id, None)
            self._state.pop(timer_id, None)
            token = self._context_tokens.pop(timer_id, None)
            if token is not None:
                self._token_to_timer.pop(token, None)

        if source is not None:
            self._lib.dispatch_source_cancel(source)
            if self._dispatch_release is not None:
                self._dispatch_release(source)

    def start_all(self) -> None:
        with self._lock:
            self._started = True
            to_start: list[tuple[str, _PeriodicTimerSpec]] = list(self._specs.items())

        for timer_id, spec in to_start:
            with self._lock:
                if timer_id in self._sources:
                    continue
                self._create_source(timer_id, spec)
                source = self._sources[timer_id]
            self._lib.dispatch_resume(source)

    def stop_all(self) -> None:
        with self._lock:
            ids = list(self._sources.keys())
        for timer_id in ids:
            self.cancel(timer_id)


def create_timer_backend(backend: str = "auto") -> PeriodicTimerBackend:
    """Factory for realtime timer backends."""

    backend = backend.lower()
    if backend == "thread":
        return ThreadPeriodicTimerBackend()
    if backend == "posix":
        return PosixTimerBackend()
    if backend == "gcd":
        return GCDTimerBackend()
    if backend != "auto":
        raise ValueError(f"unknown timer backend: {backend}")

    system = platform.system().lower()
    if system == "darwin":
        try:
            return GCDTimerBackend()
        except Exception as err:
            warnings.warn(
                f"GCD backend unavailable ({err}); using thread timer backend",
                RuntimeWarning,
                stacklevel=2,
            )
            return ThreadPeriodicTimerBackend()
    if system == "linux":
        warnings.warn(
            "POSIX backend not implemented yet; using thread timer backend",
            RuntimeWarning,
            stacklevel=2,
        )
        return ThreadPeriodicTimerBackend()
    return ThreadPeriodicTimerBackend()
