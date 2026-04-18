"""Shared runtime support classes, options, and utilities for bdsim."""

from __future__ import annotations

import threading
import warnings
import unicodedata

import matplotlib.pyplot as plt
import numpy as np
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bdsim.blockdiagram import BlockDiagram
    from bdsim.run_context import SimulationContext


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
        # if not normalized.isidentifier():
        #     warnings.warn(
        #         f"Port name {normalized!r} is not a valid Python identifier "
        #         f"and cannot be used for attribute-style port access.",
        #         UserWarning,
        #         stacklevel=3,
        #     )
        return normalized


class BDStruct:
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
        self._name: str = name
        for key, value in kwargs.items():
            # self.__dict__[key] = value
            setattr(self, key, value)

    def add(self, name, value) -> None:
        # self.__dict__[name] = value
        setattr(self, name, value)

    def __repr__(self) -> str:
        return str(self)

    def __len__(self) -> int:
        return len([k for k in self.__dict__.keys() if not k.startswith("_")])

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value) -> None:
        setattr(self, key, value)

    def __str__(self) -> str:
        """
        Display struct as a string

        :return: struct in indented string format
        :rtype: str

        The struct is rendered with one line per element, and substructures
        are indented.
        """
        rows = []

        if len(self) == 0:
            return ""
        maxwidth: int = max([len(key) for key in self.__dict__.keys()])
        # if self.name is not None:
        #     rows.append(self.name + '::')
        for k, v in sorted(self.__dict__.items(), key=lambda x: x[0]):
            if k.startswith("_"):
                continue
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


class OptionsBase:
    """A struct like object for option handling

    Maintains an internal dict to keep options and their values.  Some of these
    values, names in the ``_priority`` list are read-only and cannot be changed.

    Values can be read/written as attributes, or the ``set`` method can take
    a sequence of ``option=value`` arguments.
    """

    def __init__(self, readonly={}, args={}) -> None:
        self._readonly = list(readonly)
        self._dict = {**args, **readonly}

    def items(self):
        return self._dict.items()

    def __getattr__(self, name):
        try:
            if name.startswith("_"):
                return self.__dict__[name]
            else:
                return self.__dict__["_dict"][name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value) -> None:
        if name.startswith("_"):
            self.__dict__[name] = value
        else:
            dict = self.__dict__["_dict"]
            if name not in self._readonly:
                dict[name] = value
                self.__dict__["_dict"] = self.sanity(dict)

    def set(self, **changes) -> None:
        changes = self.sanity(changes)
        dict = self._dict
        for name, value in changes.items():
            if name not in self._readonly:
                dict[name] = value
            elif dict[name] != value:
                print(
                    f"attempt to programmatically set option {name}={value} is"
                    f" overriden by command line option {name}={dict[name]}, ignored"
                )

        self._dict = dict

    def copy(self):
        new = self.__class__.__new__(self.__class__)
        new._readonly = list(self._readonly)
        new._dict = dict(self._dict)
        return new

    def sanity(self, options):
        return options

    def __str__(self) -> str:
        dict = self._dict
        maxwidth: int = max([len(option) for option in dict.keys()])
        options = sorted(dict.keys())
        return "\n".join(
            [f"{option.ljust(maxwidth)}: {dict[option]}" for option in options]
        )

    def __repr__(self) -> str:
        return str(self)


class TimeQ:
    """
    Time-ordered queue for events.

    The list comprises tuples of (time, block) to reflect an event associated
    with the specified block at the specified time.
    """

    def __init__(self) -> None:
        self.q: list[tuple[float, Any]] = []
        self.dirty = False

    def __len__(self) -> int:
        return len(self.q)

    def __str__(self) -> str:
        if len(self) == 0:
            return f"TimeQ: len={len(self)}"
        return f"TimeQ: len={len(self)}, first out {self.q[0]}"

    def __repr__(self) -> str:
        return "\n".join(str(t) for t in self.q)

    def push(self, value) -> None:
        self.q.append(value)
        self.dirty = True

    def pop(self, dt: float = 0.0):
        if len(self) == 0:
            return None, []

        if self.dirty:
            self.q.sort(key=lambda x: x[0])
            self.dirty = False

        qfirst: tuple[float, Any] = self.q.pop(0)
        t: float = qfirst[0]
        blocks: list[Any] = [qfirst[1]]
        while len(self.q) > 0 and self.q[0][0] < (t + dt):
            blocks.append(self.q.pop(0)[1])
        return t, blocks

    def pop_until(self, t):
        if len(self) == 0:
            return []

        if self.dirty:
            self.q.sort(key=lambda x: x[0])
            self.dirty = False

        i = 0
        while True:
            if self.q[i][0] > t:
                out: list[tuple[float, Any]] = self.q[:i]
                self.q = self.q[i:]
                return out
            i += 1


class SimulationState:
    """Base class for per-run execution state."""

    def __init__(self) -> None:
        self.x: np.ndarray | None = None
        self.T: float | None = None
        self.t: float | None = None
        self.fignum: int = 0
        self.stop = None
        self.checkfinite: bool = True
        self.debugger: bool = True
        self.t_stop: float | None = None
        self.eventq: TimeQ = TimeQ()
        self.options: OptionsBase | None = None

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
            raise RuntimeError("no active simulation context")
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

        self.x = []  # discrete state vector numpy.ndarray
        self.t = []
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
        return str(self)

    def __str__(self) -> str:
        s: str = f"{self.name}: T={self.T} sec"
        if self.offset != 0:
            s += f", offset={self.offset}"
        s += f", clocking {len(self.blocklist)} blocks"
        return s

    def getstate0(self) -> np.ndarray[tuple[Any, ...], np.dtype[Any]]:
        # get the state from each stateful block on this clock
        x0: np.ndarray[tuple[Any, ...], np.dtype[Any]] = np.array([])
        for b in self.blocklist:
            x0 = np.r_[x0, b.getstate0()]
            # print('x0', x0)
        return x0

    def getstate(self, t) -> np.ndarray[tuple[Any, ...], np.dtype[Any]]:

        x: np.ndarray[tuple[Any, ...], np.dtype[Any]] = np.array([])
        for b in self.blocklist:
            # update dstate
            xb = b.next(t, b.inputs, b._x)
            x = np.r_[x, xb.flatten()]

        return x

    def setstate(self) -> None:
        x = self._x
        for b in self.blocklist:
            x = b.setstate(x)  # send it to blocks

    def start(self, simstate: SimulationState) -> None:
        self.i = 1
        simstate.declare_event(self, self.time(self.i))
        self.i += 1

    def next_event(self, simstate: SimulationState) -> None:
        simstate.declare_event(self, self.time(self.i))
        self.i += 1

    def time(self, i):
        # return (math.floor((t - self.offset) / self.T) + 1) * self.T + self.offset
        # k = int((t - self.offset) / self.T + 0.5)
        return i * self.T + self.offset

    def savestate(self, t) -> None:
        # save clock state at time t
        self.t.append(t)
        self.x.append(self.getstate(t))


# ------------------------------------------------------------------------- #


# Block moved to bdsim.block to separate core block API from other components.
from bdsim.block import Block, BlockApiError, BlockRuntimeError  # noqa: E402, F401

# Re-export block type subclasses defined in block.py
from bdsim.block import (  # noqa: E402, F401
    SinkBlock,
    SourceBlock,
    TransferBlock,
    FunctionBlock,
    SubsystemBlock,
    ClockedBlock,
    EventSource,
)


# c = Clock(5)
# c1 = Clock(5, 2)

# print(c, c1)
# print(c.next(0), c1.next(0))

if __name__ == "__main__":
    try:
        from ._selftest import run_module_test
    except ImportError:
        from bdsim._selftest import run_module_test

    raise SystemExit(run_module_test(__file__))
