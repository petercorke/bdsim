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
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

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


# decorator for debugging implicit block creation with operator overloading
def oodebug(func):
    def wrapper(*args, **kwargs):
        ret = func(*args, **kwargs)
        # print(f"{func.__qualname__}{args} --> {ret}")
        return ret

    return wrapper


# remove LaTeX characters from names for use in port names, etc.
_latex_remove: dict[int, str] = str.maketrans(
    {"$": "", "\\": "", "{": "", "}": "", "^": ""}
)


def _fixname(s):
    if isinstance(s, (tuple, list)):
        return [_fixname(x) for x in s]
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

    def __init__(self, name="BDStruct2", **kwargs) -> None:
        super().__init__()
        object.__setattr__(self, "_name", str(name))
        for key, value in kwargs.items():
            self.data[key] = value

    def add(self, name, value) -> None:
        self.data[name] = value

    def __repr__(self) -> str:
        return str(self)

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value) -> None:
        self.data[key] = value

    def __getattr__(self, name):
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

    def __setattr__(self, name, value) -> None:
        if name.startswith("_") or name == "data":
            object.__setattr__(self, name, value)
        else:
            self.data[name] = value

    def __repr__(self) -> str:
        visible = [k for k in self.data.keys() if not k.startswith(".")]
        return f"BDStruct({self._name}, fields: {', '.join(visible)})"

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
                rows.append("{:s}.{:s}::".format(k.ljust(maxwidth), v._name))
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

    def dump(self, outfile) -> None:
        import pickle

        with open(outfile, "wb") as f:
            pickle.dump(self, f)

    def dump_json(self, outfile) -> None:
        import json
        import numpy as np

        class _Encoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                if isinstance(obj, np.generic):
                    return obj.item()
                return super().default(obj)

        def _to_dict(v):
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

    def __init__(self, readonly=None, args=None) -> None:
        readonly = readonly or {}
        args = args or {}
        super().__init__({**args, **readonly})
        object.__setattr__(self, "_readonly", list(readonly))

    def items(self):
        return self.data.items()

    def __getattr__(self, name):
        try:
            if name.startswith("_"):
                return self.__dict__[name]
            else:
                return self.data[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value) -> None:
        if name.startswith("_") or name == "data":
            object.__setattr__(self, name, value)
        else:
            if name not in self._readonly:
                updated = dict(self.data)
                updated[name] = value
                self.data = self.sanity(updated)

    def set(self, **changes) -> None:
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

    def copy(self):
        new = self.__class__.__new__(self.__class__)
        object.__setattr__(new, "_readonly", list(self._readonly))
        UserDict.__init__(new, dict(self.data))
        return new

    def sanity(self, options):
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
        items = [(t, block) for t, _, block in sorted(self._heap)]
        return "\n".join(f"{t:10.6f}: {block}" for t, block in items)

    def push(self, value) -> None:
        t, block = value
        heapq.heappush(self._heap, (t, next(self._seq), block))

    def pop(self, dt: float = 0.0):
        if len(self) == 0:
            return None, []

        first_t, _, first_block = heapq.heappop(self._heap)
        t = first_t
        blocks: list[Any] = [first_block]
        while len(self._heap) > 0 and self._heap[0][0] < (t + dt):
            _, _, block = heapq.heappop(self._heap)
            blocks.append(block)
        return t, blocks

    def pop_until(self, t):
        if len(self) == 0:
            return []

        out: list[tuple[float, Any]] = []
        while len(self._heap) > 0 and self._heap[0][0] <= t:
            tt, _, block = heapq.heappop(self._heap)
            out.append((tt, block))
        return out


class SimulationState:
    """Base class for per-run execution state."""

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
        self.clock_state: dict[Any, np.ndarray] = {}
        self.clock_ticks: dict[Any, int] = {}
        self.clock_tlog: dict[Any, list[float]] = {}
        self.clock_xlog: dict[Any, list[np.ndarray]] = {}

    def declare_event(self, block, t) -> None:
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

    def DEBUG(self, debug, fmt, *args) -> None:
        context = self._get_context()
        options = context.options if context is not None else self.options
        if options is not None and debug[0] in options.debug:
            print(f"DEBUG.{debug:s}: " + fmt.format(*args))

    def done(self, bd, block=False) -> None:
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

    def report(self, bd, type="summary", **kwargs) -> None:
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

clocklist = []


class Clock:
    def __init__(self, arg, unit="s", offset=0, name=None) -> None:
        global clocklist
        if unit == "s":
            self.T = arg
        elif unit == "ms":
            self.T = arg / 1000
        elif unit == "Hz":
            self.T = 1 / arg
        else:
            raise ValueError("unknown clock unit", unit)

        self.offset: int = offset

        self.blocklist = []
        self.bd: BlockDiagram | None = None

        self.x = []  # deprecated runtime log storage (kept for compatibility)
        self.t = []  # deprecated runtime log storage (kept for compatibility)
        self.tick = 0
        self.timer = None
        self._x = np.array([])

        if name is None:
            self.name: str = "clock." + str(len(clocklist))
        else:
            self.name = name

        clocklist.append(self)

        # events happen at time t = kT + offset

    def add_block(self, block) -> None:
        self.blocklist.append(block)

    def __repr__(self) -> str:
        s = f"Clock(name={self.name}, T={self.T}"
        if self.offset != 0:
            s += f", offset={self.offset}"
        s += f", blocks={len(self.blocklist)})"
        return s

    def getstate0(self) -> np.ndarray[tuple[Any, ...], np.dtype[Any]]:
        # get the state from each stateful block on this clock
        x0: np.ndarray[tuple[Any, ...], np.dtype[Any]] = np.array([])
        for b in self.blocklist:
            x0 = np.r_[x0, b.getstate0()]
            # print('x0', x0)
        return x0

    def _ensure_runtime(self, simstate: SimulationState) -> None:
        if self not in simstate.clock_state:
            simstate.clock_state[self] = self.getstate0()
        if self not in simstate.clock_ticks:
            simstate.clock_ticks[self] = 1
        simstate.clock_tlog.setdefault(self, [])
        simstate.clock_xlog.setdefault(self, [])

    def _set_runtime_state(
        self,
        x: np.ndarray[tuple[Any, ...], np.dtype[Any]],
        simstate: SimulationState | None = None,
    ) -> None:
        if simstate is not None:
            self._ensure_runtime(simstate)
            simstate.clock_state[self] = np.array(x)
        else:
            # Compile-time/evaluation fallback where no SimulationState is available.
            self._x = np.array(x)

    def _get_runtime_state(
        self, simstate: SimulationState | None = None
    ) -> np.ndarray[tuple[Any, ...], np.dtype[Any]]:
        if simstate is not None:
            self._ensure_runtime(simstate)
            return simstate.clock_state[self]
        return self.getstate0()

    def getlog(self, simstate: SimulationState | None = None) -> tuple[list, list]:
        if simstate is None:
            return self.t, self.x
        self._ensure_runtime(simstate)
        return simstate.clock_tlog[self], simstate.clock_xlog[self]

    def getstate(self, t) -> np.ndarray[tuple[Any, ...], np.dtype[Any]]:

        x: np.ndarray[tuple[Any, ...], np.dtype[Any]] = np.array([])
        for b in self.blocklist:
            # update dstate
            xb = b.next(t, b.inport_values, b.x)
            x = np.r_[x, xb.flatten()]

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
        self.savestate(t, simstate)
        self._set_runtime_state(self.getstate(t), simstate)
        self.next_event(simstate)

    def start(self, simstate: SimulationState) -> None:
        self._ensure_runtime(simstate)
        k = simstate.clock_ticks[self]
        simstate.declare_event(self, self.time(k))
        simstate.clock_ticks[self] = k + 1

    def next_event(self, simstate: SimulationState) -> None:
        self._ensure_runtime(simstate)
        k = simstate.clock_ticks[self]
        simstate.declare_event(self, self.time(k))
        simstate.clock_ticks[self] = k + 1

    def time(self, k):
        return k * self.T + self.offset

    def savestate(self, t, simstate: SimulationState | None = None) -> None:
        # save clock state at time t
        x = self.getstate(t)
        if simstate is not None:
            self._ensure_runtime(simstate)
            simstate.clock_tlog[self].append(t)
            simstate.clock_xlog[self].append(x)
            simstate.clock_state[self] = np.array(x)
        else:
            self.t.append(t)
            self.x.append(x)
            self._x = np.array(x)


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
