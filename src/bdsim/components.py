"""Shared runtime support classes, options, and utilities for bdsim."""

from __future__ import annotations

import threading
import warnings
import unicodedata
import heapq
import itertools
from collections import UserDict

import matplotlib.pyplot as plt

import numpy as np
from typing import TYPE_CHECKING, Any, Callable, Protocol, TypeVar, runtime_checkable

from bdsim.exceptions import BlockApiError, BlockRuntimeError, SimulationContextError

if TYPE_CHECKING:
    from bdsim.blockdiagram import BlockDiagram
    from bdsim.run_context import SimulationContext


@runtime_checkable
class ScheduledEvent(Protocol):
    """Protocol for objects that can be placed on the simulation event queue.

    Any callable with the signature ``(t: float, simstate: SimulationState) -> None``
    satisfies this protocol.  :class:`Clock` implements it via ``__call__``;
    animation-frame lambdas satisfy it structurally.
    """

    def __call__(self, t: float, simstate: SimulationState) -> None: ...


_F = TypeVar("_F", bound=Callable[..., Any])


# decorator for debugging implicit block creation with operator overloading
def oodebug(func: _F) -> _F:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        ret = func(*args, **kwargs)
        # print(f"{func.__qualname__}{args} --> {ret}")
        return ret

    return wrapper  # type: ignore[return-value]


# remove LaTeX characters from names for use in port names, etc.
_latex_remove: dict[int, str] = str.maketrans(
    {"$": "", "\\": "", "{": "", "}": "", "^": ""}
)


def _fixname(s: str | list[str] | tuple[str, ...]) -> str | list[str]:
    if isinstance(s, (tuple, list)):
        return [str(_fixname(x)) for x in s]
    else:
        s = s.translate(_latex_remove)
        # PEP 3131: Python normalizes all identifiers to NFKC at parse time.
        # Port names used as attributes must round-trip through that normalization
        # or lookups via __setattr__/__getattr__ will silently fail.
        normalized = unicodedata.normalize("NFKC", s)
        if normalized != s:
            warnings.warn(
                f"Port name {s!r} contains Unicode compatibility characters "
                f"(e.g. U+{ord(next(c for c in s if unicodedata.normalize('NFKC', c) != c)):04X}); "
                f"Python identifiers are NFKC-normalized, so attribute access will use {normalized!r} instead.",
                UnicodeWarning,
                stacklevel=3,
            )
        return normalized


class BDStruct(UserDict):
    """
    A simple data container object that allows items to be added by attribute or by
    index.

    For example::

        >>> d = BDStruct('thing')
        >>> d.foo = 1
        >>> d.foo
        1
        >>> d["foo"]
        ]
        >>> d["bar"] = 2
        >>> d.bar
        >>> d
        bar   = 2 (int)
        foo   = 1 (int)
    """

    def __init__(self, name: str = "BDStruct2", **kwargs: Any) -> None:
        super().__init__()
        object.__setattr__(self, "_name", str(name))
        for key, value in kwargs.items():
            self.data[key] = value

    def add(self, name: str, value: Any) -> None:
        self.data[name] = value

    def __repr__(self) -> str:
        return self.__str__()

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.data[key] = value

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self.data[name]
        except KeyError:
            pass
        # Allow attribute access to dot-prefixed hidden fields, e.g. out.stats → out[".stats"]
        try:
            return self.data["." + name]
        except KeyError as err:
            raise AttributeError(name) from err

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "data":
            object.__setattr__(self, name, value)
        else:
            self.data[name] = value

    def __str__(self) -> str:
        """
        Display struct as a string

        :return: struct in indented string format
        :rtype: str

        The struct is rendered with one line per element, and substructures
        are indented.  Keys whose names start with '.' are hidden (internal
        metadata fields).
        """
        rows = []

        visible = {k: v for k, v in self.data.items() if not k.startswith(".")}
        if len(visible) == 0:
            return ""
        maxwidth: int = max([len("_name")] + [len(key) for key in visible.keys()])
        for k, v in sorted(visible.items(), key=lambda x: x[0]):
            if isinstance(v, BDStruct):
                rows.append("{:s}::".format(v._name.ljust(maxwidth)))
                rows.append(
                    "\n".join(
                        [" " * (maxwidth + 3) + line for line in str(v).split("\n")]
                    )
                )
            elif isinstance(v, str):
                rows.append(
                    '{:s} = "{:s}" ({:s})'.format(
                        k.ljust(maxwidth), str(v), type(v).__name__
                    )
                )
            elif isinstance(v, np.ndarray):
                rows.append(
                    "{:s} = ndarray:{:s} {:s}".format(
                        k.ljust(maxwidth), v.dtype.type.__name__, str(v.shape)
                    )
                )
            else:
                rows.append(
                    "{:s} = {:s} ({:s})".format(
                        k.ljust(maxwidth), str(v), type(v).__name__
                    )
                )

        return "\n".join(rows)

    def dump(self, outfile: str) -> None:
        """Pickle the struct to a file.

        :param outfile: path to the output file
        :type outfile: str
        """
        import pickle

        with open(outfile, "wb") as f:
            pickle.dump(self, f)

    def dump_json(self, outfile: str) -> None:
        """Serialise the struct to a JSON file.

        NumPy arrays are converted to nested lists and NumPy scalars are
        unwrapped to their Python equivalents.  Nested :class:`BDStruct`
        instances are recursively converted to plain dicts.

        :param outfile: path to the output file
        :type outfile: str
        """
        import json
        import numpy as np

        class _Encoder(json.JSONEncoder):
            def default(self, obj: Any) -> Any:
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                if isinstance(obj, np.generic):
                    return obj.item()
                return super().default(obj)

        def _to_dict(v: Any) -> Any:
            if isinstance(v, BDStruct):
                return {k: _to_dict(val) for k, val in v.items()}
            return v

        with open(outfile, "w") as f:
            json.dump(_to_dict(self), f, cls=_Encoder, indent=2)


class OptionsBase(UserDict):
    """A struct like object for option handling

    Maintains an internal dict to keep options and their values.  Some of these
    values, names in the ``_priority`` list are read-only and cannot be changed.

    Values can be read/written as attributes, or the ``set`` method can take
    a sequence of ``option=value`` arguments.
    """

    def __init__(
        self, readonly: dict[str, Any] | None = None, args: dict[str, Any] | None = None
    ) -> None:
        readonly = readonly or {}
        args = args or {}
        super().__init__({**args, **readonly})
        object.__setattr__(self, "_readonly", list(readonly))

    def items(self) -> Any:
        return self.data.items()

    def __getattr__(self, name: str) -> Any:
        try:
            if name.startswith("_"):
                return self.__dict__[name]
            else:
                return self.data[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "data":
            object.__setattr__(self, name, value)
        else:
            if name not in self._readonly:
                updated = dict(self.data)
                updated[name] = value
                self.data = self.sanity(updated)

    def set(self, **changes: Any) -> None:
        changes = self.sanity(dict(changes))
        current = dict(self.data)
        for name, value in changes.items():
            if name not in self._readonly:
                current[name] = value
            elif current[name] != value:
                print(
                    f"attempt to programmatically set option {name}={value} is"
                    f" overriden by command line option {name}={current[name]}, ignored"
                )

        self.data = current

    def copy(self) -> OptionsBase:
        new = self.__class__.__new__(self.__class__)
        object.__setattr__(new, "_readonly", list(self._readonly))
        UserDict.__init__(new, dict(self.data))
        return new

    def sanity(self, options: dict[str, Any]) -> dict[str, Any]:
        return options

    def __str__(self) -> str:
        values = self.data
        maxwidth: int = max([len(option) for option in values.keys()])
        options = sorted(values.keys())
        return "\n".join(
            [f"{option.ljust(maxwidth)}: {values[option]}" for option in options]
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({', '.join(f'{k}={v}' for k, v in self.data.items())})"


class TimeQ:
    """
    Time-ordered queue for events.

    The list comprises tuples of (time, seq, block) to reflect an event associated with
    the specified block at the specified time.  seq is a monotonic counter used as a tie-breaker to ensure a
    deterministic order of events with the same time, and is generated by an internal
    counter.
    """

    def __init__(self) -> None:
        self._heap: list[tuple[float, int, Any]] = []
        self._seq = itertools.count()

    def __len__(self) -> int:
        return len(self._heap)

    def __repr__(self) -> str:
        if len(self) == 0:
            return f"TimeQ(len=0)"
        first = self._heap[0]
        return f"TimeQ(len={len(self)}, nextout={first[2]} @ t={first[0]})"

    def __str__(self) -> str:
        if len(self) == 0:
            return ""

        # Historical formatting differed by call-site. Preserve the legacy
        # one-line summary for integer-timestamp queues used in older tests,
        # and retain tabular float formatting used by run_sim diagnostics.
        if all(isinstance(item[0], int) for item in self._heap):
            t, _, block = self._heap[0]
            return f"TimeQ: len={len(self)}, first out ({t}, {block!r})"

        items = [(t, block) for t, _, block in sorted(self._heap)]
        return "\n".join(f"{t:10.6f}: {block}" for t, block in items)

    def push(self, value: tuple[float, Any]) -> None:
        t, block = value
        heapq.heappush(self._heap, (t, next(self._seq), block))

    def pop(self, dt: float = 0.0) -> tuple[float | None, list[Any]]:
        if len(self) == 0:
            return None, []

        first_t, _, first_block = heapq.heappop(self._heap)
        t = first_t
        blocks: list[Any] = [first_block]
        while len(self._heap) > 0 and self._heap[0][0] < (t + dt):
            _, _, block = heapq.heappop(self._heap)
            blocks.append(block)
        return t, blocks

    def pop_until(self, t: float) -> list[tuple[float, Any]]:
        if len(self) == 0:
            return []

        out: list[tuple[float, Any]] = []
        while len(self._heap) > 0 and self._heap[0][0] <= t:
            tt, _, block = heapq.heappop(self._heap)
            out.append((tt, block))
        return out


class ClockState:
    """Runtime state for a single Clock during simulation."""

    def __init__(self, state: np.ndarray) -> None:
        self.state: np.ndarray = np.array(state)  # current state vector
        self.tlog: list[float] = []  # time series
        self.xlog: list[np.ndarray] = []  # output series
        self.tick: int = 1  # tick counter (next tick index to schedule)


class SimulationState:
    """Base class for per-run execution state.

    Attributes
    ----------
    x
        Current continuous-state vector view used by the active runner path.
    tf
        Requested simulation horizon for the current run.
    t
        Current simulation time.
    fignum
        Count of open/allocated graphics figures.
    stop
        Stop-request source (typically a block instance) or ``None``.
    checkfinite
        If ``True``, fail fast on NaN/Inf signal values when supported.
    debugger
        Legacy debugger enable flag used by some runner/debug paths.
    t_stop
        Optional pending stop time marker.
    eventq
        Time-ordered queue of scheduled events/callbacks.
    options
        Effective per-run options object.
    clock_states
        Per-clock sampled runtime states keyed by ``Clock`` instance.
    """

    def __init__(self) -> None:
        self.x: np.ndarray | None = None
        self.tf: float | None = None
        self.t: float | None = None
        self.fignum: int = 0
        self.stop = None
        self.checkfinite: bool = True
        self.debugger: bool = True
        self.t_stop: float | None = None
        self.eventq: TimeQ = TimeQ()
        self.options: OptionsBase | None = None
        # Per-run discrete clock runtime state, keyed by Clock instance.
        self.clock_states: dict[Any, ClockState] = {}

    def isdebug(self, flag: str) -> bool:
        """Return True if *flag* appears in the debug option string."""
        if self.options is None:
            return False
        return flag in (getattr(self.options, "debug", "") or "")

    def hasdebug(self) -> bool:
        """Return True if any debug flags are set."""
        if self.options is None:
            return False
        return bool(getattr(self.options, "debug", ""))

    def declare_event(self, block: Any, t: float) -> None:
        self.eventq.push((t, block))


class Runner:
    """Base class for simulation runners (offline, realtime, etc.)."""

    def __init__(self) -> None:
        self._context_local = threading.local()
        self.options: OptionsBase | None = None

    def _get_context(self) -> SimulationContext | None:
        return getattr(self._context_local, "current", None)

    def _require_context(self) -> SimulationContext:
        context = self._get_context()
        if context is None:
            raise SimulationContextError("no active simulation context")
        return context

    def _set_context(self, context: SimulationContext | None) -> None:
        self._context_local.current = context

    def DEBUG(self, debug: str, fmt: str, *args: Any) -> None:
        context = self._get_context()
        options = context.options if context is not None else self.options
        if options is not None and debug[0] in options.debug:
            print(f"DEBUG.{debug:s}: " + fmt.format(*args))

    def done(self, bd: BlockDiagram, block: bool = False) -> None:
        context = self._require_context()
        if context.options.hold:
            block = context.options.hold

        try:
            plt.show(block=block)
        except KeyboardInterrupt:
            print("bdsim: closing all windows")
            plt.close("all")
            return
        bd.done()
        plt.close("all")
        plt.pause(0.5)

    def closefigs(self) -> None:
        context = self._require_context()
        for i in range(context.simstate.fignum):
            print("close", i + 1)
            plt.close(i + 1)
            plt.pause(0.1)
        context.simstate.fignum = 0

    def report(self, bd: BlockDiagram, type: str = "summary", **kwargs: Any) -> None:
        context = self._get_context()
        options = context.options if context is not None else self.options
        if options is not None and options.quiet:
            return

        if type == "lists":
            bd.report_lists(**kwargs)
        elif type == "summary":
            bd.report_summary(**kwargs)
        elif type == "schedule":
            bd.report_schedule(**kwargs)


from bdsim.connect import EndPlug, Plug, Port, StartPlug, Wire

# ------------------------------------------------------------------------- #

clocklist: list[Clock] = []


class Clock:
    def __init__(
        self, arg: float, unit: str = "s", offset: float = 0, name: str | None = None
    ) -> None:
        global clocklist
        if unit == "s":
            self.T = arg
        elif unit == "ms":
            self.T = arg / 1000.0
        elif unit == "Hz":
            self.T = 1.0 / arg
        else:
            raise ValueError("unknown clock unit", unit)

        self.offset: float = offset

        self.blocklist: list[Block] = []
        self.bd: BlockDiagram | None = None
        self.statenames: list[str] = []

        # Compile-time fallback state (used when simstate=None during block.compile())
        self._compile_state: np.ndarray = np.array([])
        self._compile_tlog: list[float] = []
        self._compile_xlog: list[np.ndarray] = []
        self._compile_fallback_hits: dict[str, int] = {}

        if name is None:
            self.name: str = "clock." + str(len(clocklist))
        else:
            self.name = name

        clocklist.append(self)

        # events happen at time t = kT + offset

    def add_block(self, block: Block) -> None:
        self.blocklist.append(block)

    def __repr__(self) -> str:
        s = f"Clock(name={self.name}, T={self.T}"
        if self.offset != 0:
            s += f", offset={self.offset}"
        s += f", blocks=[{', '.join(b.name for b in self.blocklist if b.name is not None)}])"
        return s

    def __str__(self) -> str:
        s = f"Clock {self.name}:\n  T = {self.T}"
        if self.offset != 0:
            s += f"\n  offset = {self.offset}"
        s += f"\n  blocks:\n"
        for b in self.blocklist:
            s += f"    {b.name}\n"
        return s

    def getstate0(self) -> np.ndarray[tuple[Any, ...], np.dtype[Any]]:
        # get the state from each stateful block on this clock
        x0: np.ndarray[tuple[Any, ...], np.dtype[Any]] = np.array([])
        for b in self.blocklist:
            x0 = np.r_[x0, b.getstate0()]
            # print('x0', x0)
        return x0

    def _ensure_runtime(self, simstate: SimulationState) -> None:
        if self not in simstate.clock_states:
            simstate.clock_states[self] = ClockState(self.getstate0())

    def _log_compile_fallback(self, location: str) -> None:
        hits = self._compile_fallback_hits.get(location, 0) + 1
        self._compile_fallback_hits[location] = hits
        print(
            "\n"
            "!!! CLOCK SIMSTATE FALLBACK TRIGGERED !!!\n"
            f"clock={self.name} location={location} hit={hits}\n"
            "this path should only happen when simstate=None (compile-time fallback)\n"
        )

    def _set_runtime_state(
        self,
        x: np.ndarray[tuple[Any, ...], np.dtype[Any]],
        simstate: SimulationState | None = None,
    ) -> None:
        if simstate is not None:
            self._ensure_runtime(simstate)
            simstate.clock_states[self].state = np.array(x)
        else:
            # Compile-time fallback when no SimulationState is available.
            self._log_compile_fallback("_set_runtime_state")
            assert simstate is not None or True, "compile-time state tracking"
            self._compile_state = np.array(x)

    def _get_runtime_state(
        self, simstate: SimulationState | None = None
    ) -> np.ndarray[tuple[Any, ...], np.dtype[Any]]:
        if simstate is not None:
            self._ensure_runtime(simstate)
            return simstate.clock_states[self].state
        # Compile-time fallback
        self._log_compile_fallback("_get_runtime_state")
        assert simstate is not None or True, "compile-time state tracking"
        return self._compile_state if len(self._compile_state) > 0 else self.getstate0()

    def getlog(self, simstate: SimulationState | None = None) -> tuple[list, list]:
        if simstate is None:
            # Compile-time fallback
            self._log_compile_fallback("getlog")
            return self._compile_tlog, self._compile_xlog
        self._ensure_runtime(simstate)
        return (
            simstate.clock_states[self].tlog,
            simstate.clock_states[self].xlog,
        )

    def getstate(self, t: float) -> np.ndarray[tuple[Any, ...], np.dtype[Any]]:
        if self.bd is not None and hasattr(self.bd, "next"):
            try:
                next_by_clock = self.bd.next(t)
                if self in next_by_clock:
                    return next_by_clock[self]
            except Exception:
                # Fall back to per-block computation if next-state aggregation fails.
                pass

        state = (
            self._compile_state if len(self._compile_state) > 0 else self.getstate0()
        )
        x: np.ndarray[tuple[Any, ...], np.dtype[Any]] = np.array([])
        offset = 0
        for b in self.blocklist:
            width = b.ndstates
            xb = state[offset : offset + width]
            offset += width
            x = np.r_[x, b.next(t, b.inport_values, xb).flatten()]

        return x

    def setstate(self, simstate: SimulationState | None = None) -> None:
        x = self._get_runtime_state(simstate)
        for b in self.blocklist:
            x = b.setstate(x)  # bind _x_view and advance x

    def __call__(self, t: float, simstate: SimulationState) -> None:
        """Dispatch a clock tick at time *t*: save state, set runtime state, schedule next.

        This makes ``Clock`` a :class:`ScheduledEvent` so the outer loop can
        dispatch all event sources uniformly as ``source(t, simstate)`` without
        any ``isinstance`` check.
        """
        x = self.getstate(t)
        self.savestate(t, simstate, x=x)
        self._set_runtime_state(x, simstate)
        self.next_event(simstate)

    def tick_realtime(self, t: float, simstate: SimulationState) -> None:
        """Handle one realtime clock tick without event-queue rescheduling.

        Realtime scheduling is owned by timer backends; unlike ``__call__`` this
        method does not enqueue the next event in ``simstate.eventq``.
        """
        x = self.getstate(t)
        self.savestate(t, simstate, x=x)
        self._set_runtime_state(x, simstate)

    def start(self, simstate: SimulationState) -> None:
        self.next_event(simstate)

    def next_event(self, simstate: SimulationState) -> None:
        """Schedule the next event

        :param simstate: _description_
        :type simstate:

        The time of the k'th clock tick is

            $t_k = k*T + t_o$

        where 'k', the clock index, is part of the clock state within
        the `Simstate` object.
        """
        self._ensure_runtime(simstate)
        k = simstate.clock_states[self].tick
        simstate.declare_event(self, self.time(k))
        simstate.clock_states[self].tick = k + 1

    def time(self, k: int) -> float:
        return k * self.T + self.offset

    def savestate(
        self,
        t: float,
        simstate: SimulationState | None = None,
        x: np.ndarray | None = None,
    ) -> None:
        # save clock state at time t
        if x is None:
            x = self.getstate(t)
        if simstate is not None:
            self._ensure_runtime(simstate)
            clock_state = simstate.clock_states[self]
            clock_state.tlog.append(t)
            clock_state.xlog.append(x)
            clock_state.state = np.array(x)
        else:
            # Compile-time fallback when no SimulationState is available.
            self._log_compile_fallback("savestate")
            assert simstate is not None or True, "compile-time state tracking"
            self._compile_tlog.append(t)
            self._compile_xlog.append(x)
            self._compile_state = np.array(x)


# ------------------------------------------------------------------------- #


# Block moved to bdsim.block to separate core block API from other components.
from bdsim.block import Block  # noqa: E402, F401

# Re-export block type subclasses defined in block.py
from bdsim.block import (  # noqa: E402, F401
    SinkBlock,
    SourceBlock,
    ContinuousBlock,
    TransferBlock,
    FunctionBlock,
    SubsystemBlock,
    SampledBlock,
    ClockedBlock,
    EventSource,
    deprecated_block,
)

if __name__ == "__main__":
    try:
        from ._selftest import run_module_test
    except ImportError:
        from bdsim._selftest import run_module_test

    raise SystemExit(run_module_test(__file__))
