"""Offline simulation runner and dynamic block-loading support."""

from __future__ import annotations

import ast
from concurrent.futures import Future, ThreadPoolExecutor
from collections import Counter, namedtuple
from dataclasses import dataclass, field
import io
import inspect
import os
from pathlib import Path
import sys
import importlib
import importlib.util
import argparse
import types
import time
import traceback
import traceback as tb
import warnings
from typing import Any, Callable, NoReturn, Sequence

import matplotlib

import matplotlib.pyplot as plt
import numpy as np
import scipy.integrate as integrate
import spatialmath.base as smb  # type: ignore[import-not-found]
from colored import attr, fg

from bdsim.components import (
    BDStruct,
    Block,
    Clock,
    OptionsBase,
    Plug,
    Runner,
    SimulationState,
    TimeQ,
)
from bdsim.exceptions import (
    BlockApiError,
    BlockCreationError,
    BlockRuntimeError,
    EventProbeOutsideIntervalError,
    IntegrationFailureError,
    SimulationContextError,
)
from bdsim.blockdiagram import BlockDiagram
from bdsim.run_context import SimulationContext, SimulationJob

import tempfile
import re
import subprocess
import webbrowser

try:
    from progress.bar import FillingCirclesBar

    _FillingCirclesBar = True
except ImportError:
    _FillingCirclesBar = False


class Progress:
    # print a progress bar
    # https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
    @staticmethod
    def printProgressBar(
        fraction: float,
        prefix: str = "",
        suffix: str = "",
        decimals: int = 1,
        length: int = 50,
        fill: str = "█",
        printEnd: str = "\r",
    ) -> None:
        percent: str = ("{0:." + str(decimals) + "f}").format(fraction * 100)
        filledLength = int(length * fraction)
        bar: str = fill * filledLength + "-" * (length - filledLength)
        print(f"\r{prefix} |{bar}| {percent}% {suffix}", end=printEnd)

    def __init__(self, enable: bool = True) -> None:
        self.enable: bool = enable
        self.length = 60
        if not enable:
            return

    def start(self, T: float) -> None:
        self.T = T

        if not self.enable:
            return

        if _FillingCirclesBar:
            self.bar = FillingCirclesBar(
                "bdsim", max=100, suffix="%(percent).1f%% - %(eta)ds"
            )
        else:
            self.printProgressBar(
                0, prefix="Progress:", suffix="complete", length=self.length
            )

    def end(self) -> None:
        """
        Clean up progress bar
        """
        if not self.enable:
            return

        if _FillingCirclesBar:
            self.bar.finish()
        else:
            print("\r" + " " * (self.length + 20) + "\r")

    def update(self, t: float) -> None:
        """
        Update progress bar

        :param t: current simulation time, defaults to None
        :type t: float, optional

        Update progress bar as a percentage of the maximum simulation time,
        given as an argument to ``run``.

        :seealso: :meth:`run` :meth:`progress_done`
        """
        if not self.enable:
            return

        if _FillingCirclesBar:
            self.bar.goto(round(t / self.T * 100))
        else:
            self.printProgressBar(
                t / self.T, prefix="Progress:", suffix="complete", length=self.length
            )


# convert class name to BLOCK name
# strip underscores and capitalize
def blockname(name: str) -> str:
    return name.upper()


class _LazyBlockClass:
    """Proxy object that resolves a block class on first use."""

    __slots__ = ("_module_name", "_class_name", "_resolved")

    def __init__(self, module_name: str, class_name: str) -> None:
        self._module_name = module_name
        self._class_name = class_name
        self._resolved: type[Block] | None = None

    @property
    def __name__(self) -> str:  # type: ignore[override]
        return self._class_name

    @property
    def __module__(self) -> str:  # type: ignore[override]
        return self._module_name

    def _resolve(self) -> type[Block]:
        if self._resolved is None:
            if os.getenv("BDSIM_DEBUG_LAZY_LOAD"):
                print(
                    f"[bdsim] lazy-resolve {self._module_name}.{self._class_name}",
                    flush=True,
                )
            module = importlib.import_module(self._module_name)
            resolved = getattr(module, self._class_name)
            if not inspect.isclass(resolved) or Block not in inspect.getmro(resolved):
                raise TypeError(
                    f"{self._module_name}.{self._class_name} is not a Block class"
                )
            self._resolved = resolved
        return self._resolved

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._resolve()(*args, **kwargs)

    def __getattribute__(self, name: str) -> Any:
        if name in {
            "_module_name",
            "_class_name",
            "_resolved",
            "_resolve",
            "__name__",
            "__module__",
            "__class__",
            "__dict__",
            "__slots__",
            "__call__",
            "__getattribute__",
            "__repr__",
        }:
            return object.__getattribute__(self, name)
        if name == "__init__":
            return self._resolve().__init__
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return getattr(self._resolve(), name)

    def __repr__(self) -> str:
        return f"<LazyBlockClass {self._module_name}.{self._class_name}>"


@dataclass
class RunIntervalStats:
    """Runtime counters and timings accumulated during simulation."""

    run_interval_calls: int = 0
    ydot_calls: int = 0
    integrator_wall_time: float = 0.0
    events_detected_total: int = 0
    events_detected_by_source: Counter[str] = field(default_factory=Counter)


class BDSimState(SimulationState):
    """
    Offline simulation state: extends SimulationState with offline-specific fields.

    Holds the mutable execution state for a single offline run, created fresh
    each time run() is called. This keeps BDSim.run() reentrant.

    Inherited attributes from ``SimulationState``:
    ``x``, ``tf``, ``t``, ``fignum``, ``stop``, ``checkfinite``, ``debugger``,
    ``t_stop``, ``eventq``, ``options``, ``clock_states``.

    Additional attributes
    ---------------------
    T
        Resolved run horizon for this offline run.
    dt
        Optional output sample interval used to build solve_ivp ``t_eval`` grids.
    max_step
        Optional maximum integration step cap for solve_ivp.
    count
        Total runtime callback/evaluation counter.
    bdtime
        Cumulative wall time spent in block-diagram evaluation.
    gtime
        Last time graphics were updated.
    solver
        Requested solver/method name.
    solver_args
        Keyword arguments forwarded to ``solve_ivp``.
    minstepsize
        Minimum step-size guard used by interval checks.
    watchlist
        Normalized watched plugs.
    watchnamelist
        Display names corresponding to ``watchlist``.
    tlist
        Logged simulation times.
    xlist
        Logged continuous state vectors.
    plist
        Logged watched signal values.
    figsize
        Figure size setting captured for run output/graphics.
    dpi
        Figure DPI setting.
    backend
        Active matplotlib backend name.
    screensize_pix
        Screen size in pixels for tiling/layout helpers.
    ntiles
        Requested figure tiling layout.
    xoffset
        Horizontal figure offset in pixels.
    crossing_detectors
        Registered solve_ivp zero-crossing detectors and owning blocks.
    _event_probe_t
        Last event-probe time cached for shared detector evaluation.
    _event_probe_y
        Last event-probe state vector cached for shared detector evaluation.
    _event_probe_interval_start
        Active interval start bound for valid event probes.
    _event_probe_interval_end
        Active interval end bound for valid event probes.
    stats
        RunIntervalStats counters for interval/solver diagnostics.
    """

    def __init__(self) -> None:
        super().__init__()
        # offline-specific fields
        self.T: float | None = None
        self.dt: float | None = None
        self.max_step: float | None = None
        self.count: int = 0
        self.bdtime: float = 0.0
        self.gtime: float = 0.0  # last graphics update
        self.solver: str = ""
        self.solver_args: dict = {}
        self.minstepsize: float | None = None
        self.watchlist: list = []
        self.watchnamelist: list = []
        self.tlist: list = []
        self.xlist: list = []
        self.plist: list = []
        self.figsize: list = []
        self.dpi: float = 100.0
        self.backend: str = ""
        self.screensize_pix: tuple = ()
        self.ntiles: list = []
        self.xoffset: int = 0
        # Crossing detectors: zero-crossing detection callbacks for solve_ivp.
        # Distinct from scheduled_events (discrete-time), these are continuous root-finding.
        self.crossing_detectors: list[tuple[Callable[[float, Any], float], Block]] = []
        # Per-probe cache for solve_ivp event detector group evaluation.
        #
        # solve_ivp may call multiple event detector callables sequentially for the
        # same probe point (t, y). We evaluate the block diagram at most once per
        # probe and let each detector read its already-updated input signal.
        self._event_probe_t: float | None = None
        self._event_probe_y: np.ndarray | None = None
        self._event_probe_interval_start: float | None = None
        self._event_probe_interval_end: float | None = None
        self.stats = RunIntervalStats()

    def __repr__(self) -> str:
        s = f"BDSimState(t={self.bdtime:.3f}, count={self.count}"
        if self.dt is not None:
            s += f", dt={self.dt:.3g}"
        if self.max_step is not None:
            s += f", max_step={self.max_step:.3g}"
        if self.solver is not None:
            s += f", solver={self.solver}"
        if len(self.watchlist) > 0:
            s += f", watchlist={self.watchnamelist}"
        return s + ")"

    def declare_crossing_event(
        self, detector: Callable[[float, Any], float], block: Block
    ) -> None:
        """Register a zero-crossing detector for continuous root-finding via solve_ivp.

        Distinct from scheduled discrete events; these are detected during integration.
        """
        self.crossing_detectors.append((detector, block))

    def reset_event_probe_cache(self) -> None:
        """Invalidate cached solve_ivp event-probe evaluation state."""
        self._event_probe_t = None
        self._event_probe_y = None

    def begin_event_probe_interval(self, t0: float, t1: float) -> None:
        """Declare the active solve_ivp interval used for event probes.

        Probes outside this interval are invalid because sampled states are not
        uniquely determined before the previous boundary or after the next one.
        """
        self._event_probe_interval_start = t0
        self._event_probe_interval_end = t1
        self.reset_event_probe_cache()

    def ensure_event_probe_evaluated(self, bd: BlockDiagram, t: float, y: Any) -> None:
        """Evaluate diagram once for the current solve_ivp event probe.

        Event detectors are expected to be pure readers of already-computed
        inputs. This helper guarantees that for a given probe `(t, y)` the
        network is propagated at most once, regardless of how many detectors
        are invoked.
        """
        t0 = self._event_probe_interval_start
        t1 = self._event_probe_interval_end
        if t0 is not None and t1 is not None:
            tol = 1e-12
            if t < (t0 - tol) or t > (t1 + tol):
                raise EventProbeOutsideIntervalError(probe_t=float(t), t0=t0, t1=t1)

        y_arr = np.asarray(y)
        if (
            self._event_probe_t == t
            and self._event_probe_y is not None
            and y_arr.shape == self._event_probe_y.shape
            and np.array_equal(y_arr, self._event_probe_y)
        ):
            return
        bd.evaluate(bd.state_map(y, self), t, sinks=False)
        self._event_probe_t = t
        self._event_probe_y = np.array(y_arr, copy=True)


class BDSim(Runner):
    _blocklibrary: dict | None = None
    _executor: ThreadPoolExecutor | None = None
    _required_blockinfo_keys: tuple[str, ...] = (
        "path",
        "classname",
        "blockname",
        "url",
        "class",
        "module",
        "package",
        "doc",
        "params",
        "inputs",
        "outputs",
        "nin",
        "nout",
        "blockclass",
    )

    @classmethod
    def _validate_blocklibrary_contract(
        cls, blocklibrary: dict[str, dict[str, Any]]
    ) -> None:
        """Ensure each block entry satisfies the historical _blocklibrary schema."""

        for block_name, info in blocklibrary.items():
            missing = [k for k in cls._required_blockinfo_keys if k not in info]
            if missing:
                raise RuntimeError(
                    "invalid block library entry for "
                    f"{block_name}: missing keys {missing}"
                )

    def _resolve_block_info(self, block_name: str) -> dict[str, Any]:
        assert self._blocklibrary is not None
        try:
            return self._blocklibrary[block_name]
        except KeyError as exc:
            raise NotImplementedError(
                f"block {block_name} is not defined in the block library: missing block definition, block path error, or syntax error in the body of the block's code."
            ) from exc

    def _resolve_block_class(self, block_name: str) -> type[Block]:
        info = self._resolve_block_info(block_name)
        cls_obj = info["class"]
        if isinstance(cls_obj, _LazyBlockClass):
            resolved = cls_obj._resolve()
            # Cache the resolved class for future calls.
            info["class"] = resolved
            # Bulk-promote all other lazy proxies from the same module: the
            # module is already imported so getattr() is essentially free.
            module_name = cls_obj._module_name
            module = sys.modules.get(module_name)
            if module is not None and self._blocklibrary is not None:
                for other_info in self._blocklibrary.values():
                    other_cls = other_info.get("class")
                    if (
                        isinstance(other_cls, _LazyBlockClass)
                        and other_cls._module_name == module_name
                    ):
                        sibling = getattr(module, other_cls._class_name, None)
                        if sibling is not None:
                            other_cls._resolved = sibling
                            other_info["class"] = sibling
            return resolved
        return cls_obj

    def __init__(
        self,
        banner: bool = True,
        packages: str | None = None,
        load: bool = True,
        toolboxes: bool = True,
        **kwargs: Any,
    ) -> None:
        """
        :param banner: display docstring banner, defaults to True
        :type banner: bool, optional
        :param packages: colon-separated list of folders to search for blocks
        :type packages: str
        :param load: dynamically load blocks from libraries, defaults to True
        :type load: bool,optional
        :param sysargs: process options from sys.argv, defaults to True
        :type sysargs: bool, optional
        :param graphics: enable graphics, defaults to True
        :type graphics: bool, optional
        :param animation: enable animation, defaults to False
        :type animation: bool, optional
        :param progress: enable progress bar, defaults to True
        :type progress: bool, optional
        :param debug: debug options, defaults to None
        :type debug: str, optional
        :param backend: matplotlib backend, defaults to 'Qt5Agg'
        :type backend: str, optional
        :param tiles: figure tile layout on monitor, defaults to None
        :type tiles: str, optional
        :raises ImportError: syntax error in block
        :return: parent object for blockdiagram simulation
        :rtype: BDSim

        If ``sysargs`` is True, process command line arguments and passed
        options.  Command line arguments have precedence.

        =================================  ===============  =========  =====================================================
        Command line switch                Argument         Default    Behaviour
        =================================  ===============  =========  =====================================================
        ``--graphics``, ``+g``             graphics         True       enable graphical display
        ``--no-graphics``, ``-g``          graphics         True       disable graphical display
        ``--animation``, ``+a``            animation        False      update graphics at each time step
        ``--no-animation``, ``-a``         animation        False      don't update graphics at each time step
        ``--hold``, ``+H``                 hold             True       hold graphics in done()
        ``--no-hold``, ``-H``              hold             True       do not hold graphics in done()
        ``--altscreen``, ``+A``            altscreen        True       display plots on second monitor
        ``--no-altscreen``, ``-A``         altscreen        True       do not display plots on second monitor
        ``--no-progress``                   progress         True       do not display simulation progress bar
        ``--backend BE``, ``-b BE``        backend          None       matplotlib backend
        ``--tiles SPEC``, ``-t SPEC``      tiles            None       arrange figure tiles as RxC or square/wide/tall
        ``--shape WxH``                    shape            None       window size (default: matplotlib default)
        ``--blocks``                       blocks           False      display block list at startup
        ``--debug F``, ``-d F``            debug            ``''``     debug flags: p/ropagate, s/tate, d/eriv, i/nteractive
        ``--animation-rate R``             animation_rate   20.0       target update rate for animation/debugger (Hz)
        ``--simtime T[,dt]``, ``-S``       simtime          None       simulation time as T or T,dt
        ``--dt DT``                        dt               None       output sample interval (build solve_ivp t_eval)
        ``--max-step DT``                  max_step         None       maximum solve_ivp integration step
        ``--atol ATOL``                    atol             None       absolute tolerance for solve_ivp
        ``--rtol RTOL``                    rtol             None       relative tolerance for solve_ivp
        ``--method NAME``                  method           None       solve_ivp method (RK45, DOP853, Radau, BDF, LSODA)
        ``--verbose``, ``-v``              verbose          False      be verbose
        ``--quiet``, ``-q``               quiet            False      suppress reports and progress bar
        ``-p [FILE]``, ``--pickle [FILE]`` outfile          None       output pickled results (default: bd.out)
        ``-o [FILE]``, ``--out [FILE]``    outfile          None       *(deprecated, use -p/--pickle)*
        ``-j [FILE]``, ``--json [FILE]``   jsonfile         None       output JSON results (default: bd.json)
        ``--set P``, ``-s P``              setparam         ``[]``     override block parameter: ``block:param=value``
        ``--global G``                     setglob          ``[]``     override global parameter: ``var=value``
        =================================  ===============  =========  =====================================================

        .. note:: ``animation`` and ``graphics`` options are coupled.  If
            ``graphics=False``, all graphics is suppressed.  If
            ``graphics=True`` then graphics are shown and the behaviour depends
            on ``animation``.  ``animation=False`` shows graphs at the end of
            the simulation, while ``animation=True`` will animate the graphs
            during simulation.

        :seealso: :meth:`set_globals()`
        """

        super().__init__()

        if os.getenv("BDSIM_NO_TOOLBOXES", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            toolboxes = False

        self.packages = packages

        # process command line and overall options
        self.options = Options(**kwargs)
        self.moduledicts: dict[str, dict[str, list[str]]] | None = None
        # self.blockdict: dict[str, Any] = {}

        # print docstring as a startup banner
        if banner and not self.options.quiet:
            current_frame: types.FrameType | None = inspect.currentframe()
            calling_frame: types.FrameType | None = (
                current_frame.f_back if current_frame is not None else None
            )
            if calling_frame is not None:
                try:
                    doc = calling_frame.f_locals["__doc__"]
                    if doc is not None:
                        for line in doc.strip().split("\n"):
                            print("* " + line)
                except KeyError:
                    pass

        # load modules from the blocks folder
        if BDSim._blocklibrary is None and load:
            BDSim._blocklibrary = self.load_blocks(
                self.options.verbose, toolboxes=toolboxes
            )
            self._validate_blocklibrary_contract(BDSim._blocklibrary)
        if self.options.blocks:
            self.blocks()

    @property
    def block_library(self) -> dict[str, dict[str, Any]]:
        """Read-only view of the loaded block registry, excluding deprecated blocks.

        Returns a dict keyed by upper-case block name (e.g. ``"GAIN"``).
        Each value is a metadata dict with keys: ``path``, ``classname``,
        ``url``, ``class``, ``module``, ``package``, ``params``, ``inputs``,
        ``outputs``, ``nin``, ``nout``, ``blockclass``.

        Deprecated blocks (decorated with :func:`deprecated_block`) are
        excluded so they don't appear in editor menus.  They remain in the
        internal registry and are still accessible as factory methods on a
        :class:`BlockDiagram`.
        """
        assert self._blocklibrary is not None, "block library not loaded"
        return {k: v for k, v in self._blocklibrary.items() if not v.get("deprecated")}

    def blockinfo(self, block: str | None = None) -> Any:
        """Return info about all blocks.

        .. deprecated::
            Use :attr:`block_library` instead.  ``sim.blockinfo()`` is
            equivalent to ``sim.block_library``; ``sim.blockinfo(name)`` is
            equivalent to ``sim.block_library[name]``.
        """
        warnings.warn(
            "blockinfo() is deprecated; use the block_library property instead",
            DeprecationWarning,
            stacklevel=2,
        )
        if block is None:
            assert self._blocklibrary is not None
            return self._blocklibrary
        else:
            assert self._blocklibrary is not None
            return self._blocklibrary[block]

    def _repr__(self) -> str:
        """
        String representation of simulation

        :return: single line summary of simulation environment
        :rtype: str
        """
        assert self._blocklibrary is not None
        s: str = f"BDSim(nblocks={len(self._blocklibrary)})\n"
        return s

    def __str__(self) -> str:
        assert self._blocklibrary is not None
        context: SimulationContext | None = self._get_context()
        assert self.options is not None
        options: OptionsBase = context.options if context is not None else self.options
        s: str = (
            f"BDSim: Block diagram simulation runtime, {len(self._blocklibrary)} blocks"
            " imported to library.\n"
        )
        s += "simulation options:\n"
        for k, v in options.items():
            s += "  {:s}: {}\n".format(k, v)
        return s

    def _get_context(self) -> SimulationContext | None:
        return getattr(self._context_local, "current", None)

    def _require_context(self) -> SimulationContext:
        context: SimulationContext | None = self._get_context()
        if context is None:
            raise SimulationContextError("no active simulation context")
        return context

    def _set_context(self, context: SimulationContext | None) -> None:
        self._context_local.current = context

    def _make_run_options(
        self, *, threaded: bool = False, **overrides: Any
    ) -> OptionsBase:
        assert self.options is not None
        options: OptionsBase = self.options.copy()
        options.set(**overrides)
        if threaded:
            options.graphics = False
            options.animation = False
            options.hold = False
        return options

    def _make_context(
        self,
        bd: BlockDiagram,
        simstate: BDSimState,
        options: OptionsBase,
        *,
        threaded: bool = False,
    ) -> SimulationContext:
        return SimulationContext(
            bd=bd, simstate=simstate, options=options, threaded=threaded
        )

    def _print_exception_red(
        self,
        message: str,
        err: Exception,
        traceback: bool = True,
        callsite: str | None = None,
    ) -> None:
        print(fg("red"))
        print(message)
        if callsite is not None:
            for line in callsite.splitlines():
                print(
                    f"  Triggered by: {line}"
                    if line == callsite.splitlines()[0]
                    else f"                {line}"
                )

        if traceback and err.__traceback__ is not None:
            # Show the full chained traceback so constructor failures include
            # the original root cause, not just the final exception line.
            trace = "".join(
                tb.format_exception(type(err), err, err.__traceback__, chain=True)
            ).rstrip()
            for line in trace.splitlines():
                print(f"  {line}")
        else:
            print("  " + "".join(tb.format_exception_only(type(err), err)).strip())
        print(attr(0))

    @staticmethod
    def _format_external_callsite() -> str | None:
        stack = tb.extract_stack()
        current_file = __file__

        for frame in reversed(stack[:-1]):
            if frame.filename == current_file and frame.name in {
                "block_init_wrapper",
                "new_method",
                "_format_external_callsite",
            }:
                continue

            line = frame.line.strip() if frame.line is not None else ""
            location = f'File "{frame.filename}", line {frame.lineno}, in {frame.name}'
            if line:
                return f"{location}\n    {line}"
            return location

        return None

    @staticmethod
    def _is_solve_ivp_alias(name: str) -> bool:
        return name.lower() in {"solve_ivp", "solver_ivp"}

    def _solve_ivp_method(self, simstate: BDSimState) -> str:
        # Single integration entry point: always use solve_ivp and derive method
        # from explicit method, legacy integrator, or solver argument.
        #
        # Priority order for backwards compatibility:
        # 1) solver_args['method']      (new explicit solve_ivp API)
        # 2) solver_args['integrator']  (legacy alias, unless it asks for solve_ivp)
        # 3) run(..., solver='RK45')    (historical bdsim solver argument)
        # 4) default to RK45 when solver is 'solve_ivp'/'solver_ivp'
        method = simstate.solver_args.get("method")
        if method is not None:
            return str(method)

        integrator = simstate.solver_args.get("integrator")
        if integrator is not None and not self._is_solve_ivp_alias(str(integrator)):
            return str(integrator)

        if self._is_solve_ivp_alias(simstate.solver):
            return "RK45"

        return str(simstate.solver)

    @staticmethod
    def _build_t_eval_grid(t0: float, t1: float, dt: float) -> np.ndarray | None:
        """Build an absolute-time t_eval grid over the closed interval [t0, t1]."""
        tol = 1e-12
        if dt <= 0:
            return None
        k0 = int(np.ceil((t0 - tol) / dt))
        k1 = int(np.floor((t1 + tol) / dt))
        if k1 < k0:
            return None
        grid = dt * np.arange(k0, k1 + 1, dtype=float)
        grid = grid[(grid >= (t0 - tol)) & (grid <= (t1 + tol))]
        if grid.size == 0:
            return None
        grid = np.clip(grid, t0, t1)
        grid = np.unique(grid)
        return grid if grid.size > 0 else None

    def _dispatch_crossing_event(
        self,
        block: Block,
        t_crossing: float,
        y_crossing: Any,
        simstate: BDSimState,
        state_map: dict[Block, np.ndarray],
    ) -> None:
        """Invoke a crossing event handler if one is defined on the block.

        Called when a zero-crossing is detected by the solver.
        """
        for handler_name in ("event_handler", "on_event", "handle_event"):
            handler = getattr(block, handler_name, None)
            if callable(handler):
                try:
                    handler(t_crossing, y_crossing, state_map, simstate)
                except TypeError:
                    # Backward-compatible fallbacks for simpler signatures.
                    try:
                        handler(t_crossing, y_crossing, simstate)
                    except TypeError:
                        try:
                            handler(t_crossing, y_crossing, state_map)
                        except TypeError:
                            try:
                                handler(t_crossing, y_crossing)
                            except TypeError:
                                handler(t_crossing)
                return

    def _record_sample_and_service_hooks(
        self,
        bd: Any,
        simstate: BDSimState,
        t: float,
        y: np.ndarray | None = None,
        *,
        stop_short_circuit: bool,
    ) -> bool:
        """Record one accepted sample and run watch/graphics/progress/debug hooks.

        :param bd: system block diagram
        :type bd: BlockDiagram
        :param simstate: per-run simulation state
        :type simstate: BDSimState
        :param t: sample time
        :type t: float
        :param y: continuous state sample (None for discrete-only paths)
        :type y: ndarray | None
        :param stop_short_circuit: if True, return immediately when stop is
            requested before the interactive debugger hook
        :type stop_short_circuit: bool
        :return: True if caller should break interval processing
        :rtype: bool
        """

        simstate.tlist.append(t)
        if y is not None:
            simstate.xlist.append(y)

        for i, p in enumerate(simstate.watchlist):
            b = p.block
            out = b.outport_value(p.port)
            simstate.plist[i].append(out)

        if simstate.options.animation or (t - simstate.gtime) > (simstate.T / 200):  # type: ignore[operator,union-attr]
            bd.step(t)
            simstate.gtime = t

        progress: Progress | None = self._require_context().progress
        assert progress is not None
        progress.update(t)

        if simstate.stop is not None:
            print(
                fg("red") + f"\n--- stop requested at t={simstate.t:.4f} by"
                f" {simstate.stop}" + attr(0)
            )
            if stop_short_circuit:
                return True

        if simstate.isdebug("i"):
            bd._debugger(simstate)

        return False

    def run(
        self,
        bd: Any,
        T: float = 5,
        dt: float | None = None,
        max_step: float | None = None,
        solver: str = "RK45",
        solver_args: dict[str, Any] | None = None,
        debug: str = "",
        block: bool | None = None,
        checkfinite: bool = True,
        minstepsize: float = 1e-12,
        watch: Any = None,
        threaded: bool = False,
    ) -> BDStruct:
        """Run a compiled block diagram.

        :param T: simulation horizon, defaults to 5
        :type T: float, optional
        :param dt: output sample interval; used to build a ``t_eval`` grid for
            ``solve_ivp`` so results are recorded at uniform steps
        :type dt: float, optional
        :param max_step: maximum integration step passed to solve_ivp
        :type max_step: float, optional
        :param solver: solve_ivp method name, defaults to ``RK45``
        :type solver: str, optional
        :param solver_args: extra keyword arguments for ``scipy.integrate.solve_ivp``
        :type solver_args: dict
        :param debug: debug flags string (see below), defaults to ``''``
        :type debug: str, optional
        :param block: matplotlib block-at-end behaviour, default False
        :type block: bool
        :param checkfinite: error if inf or nan on any wire, default True
        :type checkfinite: bool
        :param minstepsize: minimum step length guard, default 1e-12
        :type minstepsize: float
        :param watch: list of signals to log (see below)
        :type watch: list, optional
        :param threaded: run in a worker thread (disables graphics), default False
        :type threaded: bool, optional
        :return: simulation results container
        :rtype: BDStruct

        The system is simulated from time 0 to ``T``.

        The integration backend is always ``scipy.integrate.solve_ivp``.  The
        ``solver`` argument selects the method (e.g. ``RK45``, ``DOP853``,
        ``Radau``, ``BDF``, ``LSODA``).  Finer control — tolerances, first
        step, etc. — can be passed via ``solver_args``.

        The output ``dt`` controls the time resolution of logged output.  When
        given, ``solve_ivp`` is called with a matching ``t_eval`` grid so that
        ``out.t`` contains uniformly-spaced points.  If omitted, ``solve_ivp``
        chooses its own internal steps and all accepted points are recorded.

        Results are returned in a :class:`BDStruct` with attributes:

        - ``t`` — time vector: ndarray, shape=(M,)
        - ``x`` — continuous state matrix: ndarray, shape=(M,N)
        - ``xnames`` — list of state names corresponding to columns of ``x``,
          e.g. ``"plant.x0"`` (set via the block's ``snames`` argument)
        - ``clockN`` — :class:`BDStruct` for each clock (``clock0``, ``clock1``,
          …) with sub-attributes ``t`` and ``x`` holding the discrete time
          history; a legacy alias using the clock's name is also added when
          possible
        - ``yN`` — logged signal for the N-th entry in ``watch``
        - ``ynames`` — list of names of the watched ports, same order as
          ``watch``
        - ``.stats`` — :class:`BDStruct` with integration statistics:
          ``integration_time_points``, ``run_interval_calls``,
          ``ydot_calls``, ``integrator_wall_time``,
          ``events_detected_total``, ``events_detected_by_source``

        The ``watch`` argument is a list of one or more signals whose value
        during simulation will be recorded.  Each element can be:

        - a :class:`Block` reference, interpreted as output port 0
        - a :class:`Plug` reference (block with port index)
        - a string of the form ``"blockname[i]"`` — port *i* of the named block

        The ``debug`` string contains single-character flags:

        - ``'p'`` — trace network value propagation
        - ``'s'`` — trace state vector
        - ``'d'`` — trace state derivative
        - ``'i'`` — interactive step-by-step debugger

        .. note::
            Simulation stops if the step size falls below ``minstepsize``,
            which typically indicates the solver is struggling with a very
            stiff or discontinuous system.
        """

        assert bd.compiled, "Network has not been compiled"

        if solver_args is None:
            solver_args = {}
        else:
            solver_args = dict(solver_args)
        if watch is None:
            watch = []

        run_options: OptionsBase = self._make_run_options(threaded=threaded)

        # get simulation time
        #  --simtime=T  or --simtime=T,dt
        if run_options.simtime is not None:
            try:
                default_times = ast.literal_eval(run_options.simtime)
                if isinstance(default_times, (int, float)):
                    T = default_times
                elif isinstance(default_times, tuple):
                    T, dt = default_times
                else:
                    raise ValueError("bad simtime option passed " + run_options.simtime)
            except (SyntaxError, ValueError) as exc:
                raise ValueError(
                    "bad simtime option passed " + run_options.simtime
                ) from exc

        # Resolve run horizon from arguments/options once for this run.
        tf = T

        simstate = BDSimState()
        simstate.T = tf
        simstate.tf = tf

        if dt is None:
            dt = getattr(run_options, "dt", None)
        if max_step is None:
            max_step = getattr(run_options, "max_step", None)

        if dt is not None and float(dt) <= 0:
            raise ValueError("dt must be > 0")

        if max_step is None and "max_step" not in solver_args:
            max_step = tf / 100
        simstate.dt = dt
        simstate.max_step = max_step
        simstate.count = 0
        simstate.bdtime = 0.0
        simstate.gtime = 0.0  # last graphics update
        simstate.solver = solver
        simstate.solver_args = solver_args
        simstate.minstepsize = minstepsize
        simstate.stop = None  # allow any block to stop.BlockDiagram by setting this to the block's name
        simstate.checkfinite = checkfinite
        simstate.options = run_options
        simstate.t_stop = None

        context: SimulationContext = self._make_context(
            bd, simstate, run_options, threaded=threaded
        )
        previous_context: SimulationContext | None = self._get_context()
        self._set_context(context)

        try:
            if debug:
                # append debug flags
                if debug not in simstate.options.debug:
                    simstate.options.debug += debug

            # turn off progress bar if any debug options are given
            if simstate.hasdebug():
                simstate.options.progress = False
            if block is not None:
                simstate.options.hold = block

            # Compute the animation / debugger frame interval from --animation-rate.
            # Animation uses Option-A eventq callables for frame pacing.
            # The debugger also limits max_step so single-step stays responsive.
            interactive_dt: float | None = None
            if simstate.options.animation or simstate.isdebug("i"):
                interactive_rate_hz = float(simstate.options.animation_rate)
                interactive_dt = 1.0 / interactive_rate_hz
            if simstate.isdebug("i") and interactive_dt is not None and bd.nstates > 0:
                current_max_step = simstate.solver_args.get("max_step")
                if current_max_step is None or float(current_max_step) > interactive_dt:
                    simstate.solver_args["max_step"] = interactive_dt
                    if not simstate.options.quiet:
                        print(
                            f"  interactive debugger: limiting integrator max_step to"
                            f" {interactive_dt:.4f}s ({interactive_rate_hz:g} Hz)"
                        )

            # process the watchlist
            #  elements can be:
            #   - block or Plug reference
            #   - str in the form BLOCKNAME[PORT]
            watchlist = []
            watchnamelist = []
            re_block: re.Pattern[str] = re.compile(
                r"(?P<name>[^[]+)(\[(?P<port>[0-9]+)\])?"
            )
            for w in watch:
                if isinstance(w, str):
                    # a name was given, with optional port number
                    m: re.Match[str] | None = re_block.match(w)
                    if m is None:
                        raise ValueError("watch block[port] not found: " + w)
                    name: str | None = m.group("name")

                    # get optional port number
                    port_group = m.group("port")
                    port = 0 if port_group is None else int(port_group)

                    b = bd.blocknames[name]
                    plug = b[port]
                elif isinstance(w, Block):
                    # a block was given, defaults to port 0
                    plug: Plug = w[0]  # type: ignore[no-redef]
                elif isinstance(w, Plug):
                    # a plug was given
                    plug: Plug = w  # type: ignore[no-redef]

                if plug.block.blockclass == "subsystem":
                    # subsystem blocks no longer exist in the wirelist, and don't have
                    # their own outputs, so watch the corresponding port of the subsystem's
                    # OUTPORT block instead.
                    plug.block = plug.block.outport

                watchlist.append(plug)
                watchnamelist.append(str(plug))
            simstate.watchlist = watchlist
            simstate.watchnamelist = watchnamelist

            x0 = bd.getstate0()

            if not simstate.options.quiet:
                print(fg("yellow"))
                print(
                    f">>> Start simulation: T = {tf}, dt = {dt}, max_step = {max_step}"
                )
                if bd.nstates > 0:
                    s_cont = "s" if bd.nstates != 1 else ""
                    s_disc = "s" if bd.ndstates != 1 else ""
                    print(
                        f"  Hybrid system solver: {bd.nstates} continuous state variable{s_cont}, {bd.ndstates} discrete state variable{s_disc}"
                    )
                    print("    x0 = ", x0)
                else:
                    s_disc = "s" if bd.ndstates != 1 else ""
                    print(
                        f"  Discrete system solver: {bd.ndstates} discrete state variable{s_disc}"
                    )

            # get the number of discrete states from all clocks
            ndstates = 0
            for clock in bd.clocklist:
                nds = 0
                for b in clock.blocklist:
                    nds += b.ndstates
                ndstates += nds
                if not simstate.options.quiet:
                    print(f"    {clock.name}: x0 = ", clock.getstate0())

            if not simstate.options.quiet:
                print(attr(0))

            # update block parameters given on command line
            self.update_parameters(bd)

            # tell all blocks we're starting a BlockDiagram
            bd.start(simstate)

            # initialize list of time and states
            simstate.tlist = []
            simstate.xlist = []
            simstate.plist = [[] for p in simstate.watchlist]

            context.progress = Progress(enable=simstate.options.progress)
            context.progress.start(tf)

            run_start_time = time.time()

            # For pure discrete systems, evaluate at t=0 to capture initial conditions
            # (needed for STOP blocks and other immediate triggers that must fire at t=0).
            if bd.nstates == 0:
                simstate.t = 0.0
                simstate.count += 1
                eval_start = time.time()
                bd.evaluate(bd.state_map(np.array([]), simstate), 0.0)
                eval_end = time.time()
                simstate.bdtime += eval_end - eval_start
                self._record_sample_and_service_hooks(
                    bd, simstate, 0.0, None, stop_short_circuit=False
                )
                if simstate.stop is not None:
                    # Stop triggered at t=0, early exit from run loop
                    context.progress.end()
                    if not simstate.options.quiet:
                        mean_eval_ms = simstate.bdtime / max(simstate.count, 1) * 1000.0
                        print(fg("yellow"))
                        print("<<< Simulation complete")
                        print(f"  block diagram evaluations: {simstate.count}")
                        print(
                            f"    of which ydot calls:     {simstate.stats.ydot_calls}"
                            f"  (remaining are post-integration replay + sink passes)"
                        )
                        print(
                            f"  bd.evaluate() mean time:   {mean_eval_ms*1000:.1f} μs/call"
                            f"  (total {simstate.bdtime * 1000:.1f} ms)"
                        )
                        run_wall_time = time.time() - run_start_time
                        print(
                            f"  clocktime speedup:         {simstate.T / max(run_wall_time, 1e-12):.2f}x"
                            f"  (simulated {simstate.T:.3g}s in {run_wall_time*1000:.1f} ms)"
                        )
                        print(f"  integration time points:   {len(simstate.tlist)}")
                        print(f"  scheduled event intervals: 0")
                        print(attr(0))
                    # Build output struct
                    out = BDStruct(name="results")
                    out["t"] = np.array(simstate.tlist)
                    out["x"] = np.array(simstate.xlist)
                    out["xnames"] = bd.statenames
                    for i, c in enumerate(bd.clocklist):
                        name = f"clock{i}"
                        clockdata = BDStruct(name)
                        clock_t, clock_x = c.getlog(simstate)
                        clockdata["t"] = np.array(clock_t)
                        clockdata["x"] = np.array(clock_x)
                        out.add(name, clockdata)
                        legacy_name = str(c.name).replace(".", "")
                        if legacy_name != name and legacy_name not in out:
                            out.add(legacy_name, clockdata)
                    for i, p in enumerate(watchlist):
                        out["y" + str(i)] = np.array(simstate.plist[i])
                    out["ynames"] = watchnamelist
                    stats = BDStruct(name="stats")
                    stats["integration_time_points"] = len(simstate.tlist)
                    stats["run_interval_calls"] = simstate.stats.run_interval_calls
                    stats["ydot_calls"] = simstate.stats.ydot_calls
                    stats["integrator_wall_time"] = simstate.stats.integrator_wall_time
                    stats["events_detected_total"] = (
                        simstate.stats.events_detected_total
                    )
                    stats["events_detected_by_source"] = dict(
                        simstate.stats.events_detected_by_source
                    )
                    out[".stats"] = stats
                    return out

            # Unified interval loop for both scheduled and crossing events.
            simstate.declare_event(None, tf)  # terminal boundary marker
            t0 = 0.0
            simstate.eventq.pop_until(t0)
            x = x0
            nintervals = 0
            event_tol = 1e-12

            interval_handler = (
                self._interval_hybrid if bd.nstates > 0 else self._interval_discrete
            )

            # Option A: schedule animation frame events as callables in the eventq.
            # Each callback pumps the matplotlib event loop then re-schedules itself.
            if simstate.options.animation and interactive_dt is not None:
                # Show all figures now so windows are visible before the loop starts.
                # flush_events() only works on already-visible windows; plt.show() is
                # not called until after the run otherwise.
                plt.show(block=False)
                for num in plt.get_fignums():
                    plt.figure(num).canvas.flush_events()

                def _anim_frame(t: float, ss: Any, _dt: float = interactive_dt) -> None:
                    # Flush pending draw events for all open figures without
                    # entering a blocking event loop (plt.pause(0) hangs with
                    # Qt because start_event_loop(0) never installs a quit timer).
                    for num in plt.get_fignums():
                        canvas = plt.figure(num).canvas
                        canvas.draw_idle()
                        canvas.flush_events()
                    if t + _dt < tf - event_tol:
                        ss.declare_event(_anim_frame, t + _dt)

                simstate.declare_event(_anim_frame, interactive_dt)

            while t0 < tf - event_tol:
                # Next scheduled boundary (clock tick, explicit event, or terminal marker).
                tnext, sources = simstate.eventq.pop(dt=1e-6)
                if tnext is None:
                    tnext = tf
                    sources = []

                t1 = min(float(tnext), float(tf))
                if t1 <= t0 + event_tol:
                    # Nothing to integrate; process due scheduled sources and continue.
                    for source in sources:
                        if isinstance(source, Clock):
                            try:
                                x_next = bd.next(t1, bd.state_map(x, simstate))[source]
                            except BlockRuntimeError as err:
                                bd._handle_block_runtime_error(err)
                                continue
                            source.savestate(t1, simstate, x=x_next)
                            source._set_runtime_state(x_next, simstate)
                            source.next_event(simstate)
                        elif callable(source):
                            source(t1, simstate)
                    t0 = t1
                    continue

                # Pure-discrete diagrams should only evaluate at actual clock ticks
                # (and terminal boundary). Other scheduled callables such as
                # animation/debug hooks must not trigger sampled-block output().
                if bd.nstates == 0:
                    has_clock_source = any(
                        isinstance(source, Clock) for source in sources
                    )
                    has_terminal_marker = any(source is None for source in sources)
                    if not has_clock_source and not has_terminal_marker:
                        for source in sources:
                            if callable(source):
                                source(t1, simstate)
                        t0 = t1
                        continue

                # Integrate/step until the next scheduled boundary.
                interval_result = interval_handler(bd, t0, t1, x, simstate)
                if interval_result is None:
                    break
                x, treached = interval_result
                simstate.stats.run_interval_calls += 1
                nintervals += 1

                if simstate.stop is not None:
                    break

                reached_boundary = treached >= t1 - event_tol
                if reached_boundary:
                    for source in sources:
                        if isinstance(source, Clock):
                            try:
                                x_next = bd.next(t1, bd.state_map(x, simstate))[source]
                            except BlockRuntimeError as err:
                                bd._handle_block_runtime_error(err)
                                continue
                            source.savestate(t1, simstate, x=x_next)
                            source._set_runtime_state(x_next, simstate)
                            source.next_event(simstate)
                        elif callable(source):
                            source(t1, simstate)
                    t0 = t1
                else:
                    # Integration ended early (typically a crossing event). Continue from
                    # the actual stop time and revisit this scheduled boundary later.
                    if treached <= t0 + event_tol:
                        t0 = min(t1, t0 + event_tol)
                    else:
                        t0 = treached
                    for source in sources:
                        simstate.declare_event(source, float(tnext))

            # finished integration

            context.progress.end()  # cleanup the progress bar

            # print some info about the integration
            if not simstate.options.quiet:
                mean_eval_ms = simstate.bdtime / max(simstate.count, 1) * 1000.0
                print(fg("yellow"))
                print("<<< Simulation complete")
                print(f"  block diagram evaluations: {simstate.count}")
                print(
                    f"    of which ydot calls:     {simstate.stats.ydot_calls}"
                    f"  (remaining are post-integration replay + sink passes)"
                )
                print(
                    f"  bd.evaluate() mean time:   {mean_eval_ms*1000:.1f} μs/call"
                    f"  (total {simstate.bdtime * 1000:.1f} ms)"
                )
                run_wall_time = time.time() - run_start_time
                print(
                    f"  clocktime speedup:         {simstate.T / max(run_wall_time, 1e-12):.2f}x"
                    f"  (simulated {simstate.T:.3g}s in {run_wall_time*1000:.1f} ms)"
                )
                print(f"  integration time points:   {len(simstate.tlist)}")
                # Scheduled events (clock ticks, explicit declare_event calls) are
                # the interval boundaries; nintervals = number of interval-handler calls.
                print(
                    f"  scheduled event intervals: {nintervals}"
                    f"  (each bounded by a clock tick, scheduled event, or terminal marker)"
                )
                if bd.nstates > 0:
                    print(
                        "  integrator wall time:      "
                        f" {simstate.stats.integrator_wall_time:.3f} s"
                        "  (solve_ivp only; excludes post-integration replay)"
                    )
                    # Zero-crossing events are detected by solve_ivp root-finding,
                    # distinct from the scheduled (clock/discrete) event boundaries above.
                    n_crossing = simstate.stats.events_detected_total
                    print(f"  zero-crossing events:      {n_crossing}")
                    if n_crossing > 0:
                        for (
                            src,
                            cnt,
                        ) in simstate.stats.events_detected_by_source.items():
                            print(f"    {src}: {cnt}")
                print(attr(0))

            # save buffered data in a Struct
            out = BDStruct(name="results")
            out["t"] = np.array(simstate.tlist)
            out["x"] = np.array(simstate.xlist)
            out["xnames"] = bd.statenames

            # save clocked states
            for i, c in enumerate(bd.clocklist):
                # Use deterministic per-diagram naming independent of global clock
                # instance counters to keep output keys stable across runs/tests.
                name = c.name.replace(".", "")
                clockdata = BDStruct(name)
                clock_t, clock_x = c.getlog(simstate)
                clockdata["t"] = np.array(clock_t)
                clockdata["X"] = np.array(clock_x)
                clockdata["Xnames"] = c.statenames
                out.add(name, clockdata)

            # save the watchlist into variables named y0, y1 etc.
            # for i, p in enumerate(watchlist):
            #     out["y" + str(i)] = np.array(simstate.plist[i])
            if simstate.plist:
                out["y"] = np.column_stack([np.array(p) for p in simstate.plist])
                out["ynames"] = [p.block.name for p in watchlist]

            stats = BDStruct(name="stats")
            stats["integration_time_points"] = len(simstate.tlist)
            stats["run_interval_calls"] = simstate.stats.run_interval_calls
            stats["ydot_calls"] = simstate.stats.ydot_calls
            stats["integrator_wall_time"] = simstate.stats.integrator_wall_time
            stats["events_detected_total"] = simstate.stats.events_detected_total
            stats["events_detected_by_source"] = dict(
                simstate.stats.events_detected_by_source
            )
            out[".stats"] = stats

            # command line output options:
            #  -o/--out [FILE] writes pickle (default filename: bd.out)
            #  -j/--json [FILE] writes JSON (default filename: bd.json)
            #
            # we can visualize a pickle output file by
            #
            #   % python -mpickle bd.out
            #   t      = ndarray:float64 (123,)
            #   x      = ndarray:float64 (123, 1)
            #   xnames = ['plantx0'] (list)
            #   ynames = [] (list)

            if simstate.options.outfile is not None:
                out.dump(simstate.options.outfile)

                if not simstate.options.quiet:
                    print("simulation results pickled --> ", simstate.options.outfile)

            if simstate.options.jsonfile is not None:
                out.dump_json(simstate.options.jsonfile)

                if not simstate.options.quiet:
                    print("simulation results JSON --> ", simstate.options.jsonfile)

            # pause until all graphics blocks close

            if simstate.options.graphics and simstate.options.hold:
                self.done(bd, block=simstate.options.hold)
            elif simstate.options.graphics and getattr(
                simstate, "notebook_backend", False
            ):
                # In a notebook, plt.draw() flushes pending updates so the
                # inline/widget backend captures the final figure state.
                try:
                    plt.draw()
                except Exception:
                    pass
            return out
        finally:
            self._set_context(previous_context)

    def submit(self, bd: Any, **kwargs: Any) -> SimulationJob:
        if BDSim._executor is None:
            BDSim._executor = ThreadPoolExecutor()
        kwargs.setdefault("threaded", True)
        future: Future[BDStruct] = BDSim._executor.submit(self.run, bd, **kwargs)
        return SimulationJob(future)

    def update_parameters(self, bd: Any) -> None:
        """
        Set value of parameters according to command line arguments

        Command line arguments of the form:

            ``-s block:param=value``
            ``--set block:param=value``

        are stored as list items in ``options.setparam``

        ``block`` can be either:

        - the block's name as a string, either user assigned or bdsim assigned
        - the block ``id`` as displayed by the ``report`` method

        ``param`` is the name of the parameter used in the constructor

        ``value`` is the new value of the variable
        """

        context: SimulationContext | None = self._get_context()
        assert self.options is not None
        options: OptionsBase = context.options if context is not None else self.options
        re_set: re.Pattern[str] = re.compile(
            r"(?P<block>[\w\.]+):(?P<param>[\w]+)=(?P<value>.*)"
        )
        for s in options.setparam:
            m: re.Match[str] | None = re_set.match(s)
            if m is None:
                raise ValueError("bad set parameter: " + s)

            # get block reference
            blockname: str | int | None = m["block"]
            if blockname is not None:
                try:
                    blockname = int(blockname)
                except ValueError:
                    pass
            block = bd[blockname]

            param: str | Any = m["param"]
            try:
                prev_value = getattr(block, param)
            except ValueError:
                raise ValueError(f"block {block.name} has no parameter '{param}'")

            # get the parameter
            value: str | Any = m["value"]
            new_value = None

            try:
                if ";" in value:
                    new_value = smb.str2array(value)
                else:
                    try:
                        new_value = int(value)
                    except ValueError:
                        new_value = float(value)
            except ValueError:
                raise ValueError("cannot parse value " + value)

            # change the value
            setattr(block, param, new_value)
            print(
                f"changed value of {block.name}:{param} from {prev_value} ->"
                f" {new_value}"
            )

    def _interval_hybrid(
        self, bd: Any, t0: float, t1: float, x0: np.ndarray, simstate: BDSimState
    ) -> tuple[np.ndarray, float]:
        """
        Integrate one hybrid (continuous/discrete) interval.

        :param bd: system block diagram
        :type bd: BlockDiagram
        :param t0: interval start time
        :type t0: float
        :param t1: interval end time
        :type t1: float
        :param x0: continuous state at interval start
        :type x0: ndarray(n)
        :param simstate: per-run simulation state
        :type simstate: BDSimState
        :return: final continuous state and time reached
        :rtype: tuple(ndarray(n), float)

        Uses scipy.integrate.solve_ivp over [t0, t1], replays accepted points
        to update logs/watchlists/graphics, and dispatches zero-crossing handlers.
        """

        # Event detector probes are valid only within this integration interval,
        # bounded by the most recent and upcoming scheduled event boundaries.
        simstate.begin_event_probe_interval(float(t0), float(t1))

        def ydot(t: float, y: np.ndarray) -> np.ndarray:
            # Every call represents one RHS evaluation requested by the
            # integration algorithm at an internal time/state pair.
            simstate.t = t
            simstate.count += 1
            simstate.stats.ydot_calls += 1
            eval_start = time.time()
            bd.evaluate(bd.state_map(y, simstate), t, sinks=False)
            yd = bd.deriv(t)
            eval_end = time.time()
            simstate.bdtime += eval_end - eval_start
            return yd

        # Build solve_ivp kwargs from user-provided solver_args, then normalize
        # to bdsim conventions.
        ivp_args = dict(simstate.solver_args)
        # Historical alias used by older call sites; we map it to method below.
        ivp_args.pop("integrator", None)

        option_max_step = getattr(simstate.options, "max_step", None)
        option_method = getattr(simstate.options, "method", None)
        option_atol = getattr(simstate.options, "atol", None)
        option_rtol = getattr(simstate.options, "rtol", None)

        if option_max_step is not None:
            ivp_args.setdefault("max_step", float(option_max_step))
        if simstate.max_step is not None:
            # Caller-provided run(max_step=...) acts as an upper bound on solver step.
            ivp_args.setdefault("max_step", simstate.max_step)

        if option_atol is not None:
            ivp_args.setdefault("atol", float(option_atol))
        if option_rtol is not None:
            ivp_args.setdefault("rtol", float(option_rtol))

        if simstate.dt is not None:
            t_eval = self._build_t_eval_grid(float(t0), float(t1), float(simstate.dt))
            if t_eval is not None:
                ivp_args.setdefault("t_eval", t_eval)

        # Keep user-provided method if present; otherwise use option/default,
        # then finally derive from run(..., solver=...).
        if option_method is not None:
            ivp_args.setdefault("method", str(option_method))
        else:
            ivp_args.setdefault("method", self._solve_ivp_method(simstate))

        if len(simstate.crossing_detectors) > 0:
            # Crossing detectors: zero-crossing callbacks registered in start().
            # Pass to solve_ivp so root-finding is performed by SciPy.
            # Detector callbacks are read-only: each callback asks simstate to
            # ensure one shared propagation for the current probe (t, y), then
            # returns only its own scalar event metric.
            ivp_args["events"] = [
                detector for detector, _ in simstate.crossing_detectors
            ]

        # ---------------------------------------------------------------------
        # INTEGRATOR CORE (single solve_ivp call for this interval)
        #
        # About solve_ivp "vectorized" mode:
        # - "arrays of states" means y is a matrix with shape (n, k), where
        #   each column is one candidate state vector to evaluate.
        # - In vectorized mode, ydot(t, y) must return dydt with the same
        #   shape (n, k), computed for all columns at once.
        # - bdsim's evaluate path is currently scalar-state oriented:
        #   it expects one state vector at a time and mutates block instance
        #   state during evaluation.
        # - Therefore this RHS callback is intentionally non-vectorized and
        #   should be used with solve_ivp's default vectorized=False behavior.
        # ---------------------------------------------------------------------
        ivp_start = time.time()
        result = integrate.solve_ivp(ydot, (t0, t1), x0, **ivp_args)
        simstate.stats.integrator_wall_time += time.time() - ivp_start

        # check for integration failure
        if not result.success:
            raise IntegrationFailureError(
                t0=float(t0),
                tf=float(t1),
                status=int(result.status),
                message=str(result.message),
            )

        # remove time overlap between integration segments
        #
        #   solve_ivp commonly echoes the interval start in result.t.
        #   In multi-interval runs (clock/event queue), that point was already
        #   recorded by the previous interval, so we skip an initial duplicate.
        start_index = (
            1
            if len(result.t) > 0
            and np.isclose(float(result.t[0]), float(t0), rtol=0.0, atol=1e-15)
            else 0
        )

        # post-process the results for the integration segment
        #
        #  solve_ivp returns chunks of trajectory not each individual step, so
        #  we need to iterate over the segment to update block states record,
        #  watchlist ports, and dispatch eventq events.  This is necessary to
        #  ensure that block states are consistent with the final integrated
        #  state and  that events are dispatched at the correct times with the
        #  correct state, even if the solver took large steps or if events were
        #  detected between solver steps.
        for k in range(start_index, len(result.t)):
            t = float(result.t[k])
            y = result.y[:, k]
            simstate.t = t

            simstate.count += 1
            eval_start = time.time()
            bd.evaluate(bd.state_map(y, simstate), t, sinks=False)
            eval_end = time.time()
            simstate.bdtime += eval_end - eval_start

            should_break = self._record_sample_and_service_hooks(
                bd, simstate, t, y, stop_short_circuit=True
            )
            if should_break:
                break

        # Handle detected zero-crossings from continuous root-finding.
        # solve_ivp returns crossing_times and crossing_states for each registered detector.
        # We map detector index → owning block, update counters, then dispatch handlers
        # with progressively permissive call signatures.
        crossing_times_all = result.t_events if result.t_events is not None else []
        crossing_states = result.y_events if result.y_events is not None else []
        crossing_handled = False
        for i, crossing_times in enumerate(crossing_times_all):
            if len(crossing_times) == 0:
                continue
            _, block = simstate.crossing_detectors[i]
            source_name = getattr(block, "name", str(block))
            state_list = crossing_states[i] if i < len(crossing_states) else []
            for j, t_crossing in enumerate(crossing_times):
                crossing_handled = True
                y_crossing = state_list[j] if j < len(state_list) else None
                crossing_state_map = bd.state_map(y_crossing, simstate)
                bd.evaluate(crossing_state_map, float(t_crossing), sinks=False)
                simstate.stats.events_detected_total += 1
                simstate.stats.events_detected_by_source[source_name] += 1
                self._dispatch_crossing_event(
                    block,
                    float(t_crossing),
                    y_crossing,
                    simstate,
                    crossing_state_map,
                )

        # return final continuous state and actual end time reached
        t_final = float(result.t[-1]) if len(result.t) > 0 else float(t0)
        if len(result.t) > 0:
            if crossing_handled:
                x_final = bd.continuous_state_vector(crossing_state_map)

                # Ensure logged trajectory reflects any state mutation performed by
                # crossing handlers (for example STOP handlers that rewrite state).
                if len(simstate.xlist) > 0:
                    simstate.xlist[-1] = np.array(x_final, copy=True)

                # Move just beyond the crossing so restart does not re-trigger the same event.
                _kick_dt = 1e-9
                try:
                    kick_state_map = bd.state_map(x_final, simstate)
                    bd.evaluate(kick_state_map, t_final, sinks=False)
                    _kick_ydot = bd.deriv(t_final)
                    _kick_arr = np.asarray(_kick_ydot)
                    if _kick_arr.size == x_final.size:
                        x_final = x_final + _kick_dt * _kick_arr
                except Exception:
                    pass

                return x_final, t_final + _kick_dt
            return result.y[:, -1], t_final

        # if integration produced no points, return initial state
        return np.array(x0), t_final

    def _interval_discrete(
        self, bd: Any, t0: float, t1: float, x0: np.ndarray, simstate: BDSimState
    ) -> tuple[np.ndarray, float]:
        """
        Evaluate one discrete interval boundary at the scheduled tick time.

        :param bd: system block diagram
        :type bd: BlockDiagram
        :param t0: interval start time (previous clock boundary)
        :type t0: float
        :param t1: interval end time / scheduled clock tick time for this sample
        :type t1: float
        :param x0: unchanged continuous state placeholder
        :type x0: ndarray(n)
        :param simstate: per-run simulation state
        :type simstate: BDSimState
        :return: unchanged state placeholder and reached boundary time
        :rtype: tuple(ndarray(n), float)

        For diagrams without continuous states, evaluate at the scheduled clock
        tick time t1. Between ticks [t0, t1), the zero-order hold output remains
        constant from the previous sample.
        """
        # block diagram has no continuous states
        # Evaluate at the SCHEDULED TICK TIME (t1), not the start of interval (t0)
        t = t1
        simstate.t = t

        simstate.count += 1
        eval_start = time.time()
        bd.evaluate(bd.state_map(np.array([]), simstate), t)
        eval_end = time.time()
        simstate.bdtime += eval_end - eval_start

        self._record_sample_and_service_hooks(
            bd, simstate, t, None, stop_short_circuit=False
        )

        # Report reaching the scheduled boundary at t1
        t_final = float(t1)
        return np.array(x0), t_final

    def blockdiagram(self, name: str = "main") -> BlockDiagram:
        """
        Instantiate a new block diagram object.

        :param name: diagram name, defaults to 'main'
        :type name: str, optional
        :return: parent object for blockdiagram
        :rtype: BlockDiagram

        This object describes the connectivity of a set of blocks and wires.

        It is an instantiation of the ``BlockDiagram`` class with a factory
        method for every dynamically loaded block which returns
        an instance of the block.  These factory methods have names
        which are all upper case, for example, the method ``.GAIN`` invokes
        the constructor for the ``Gain`` class.

        :seealso: :func:`BlockDiagram`
        """

        # instantiate a new blockdiagram
        #  it includes stubs for factory methods defined in the BlockDiagramMixin class
        bd = BlockDiagram(name=name)

        def new_method(block_name: str, bd: Any) -> Any:
            # return a wrapper for the block constructor that automatically
            # adds the block to the diagram's blocklist
            def block_init_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
                # we catch errors in the block constructor and print them in red to make
                # it clear that the error is in the block definition, not in the user
                # code that creates the block diagram
                cls = self._resolve_block_class(block_name)
                try:
                    block = cls(*args, bd=bd, **kwargs)  # call __init__ on the block
                    return block
                except Exception as err:
                    callsite = self._format_external_callsite()
                    self._print_exception_red(
                        f"runtime error while creating block {cls.__name__}",
                        err,
                        callsite=callsite,
                    )
                    message = f"failed to create block {cls.__name__}"
                    if callsite is not None:
                        message += f"\nTriggered by:\n{callsite}"
                    raise BlockCreationError(message) from None

            # return a function that invokes the class constructor
            f = block_init_wrapper

            return f

        # bind the block constructors as new methods on this instance
        assert self._blocklibrary is not None
        for blockname, info in self._blocklibrary.items():
            # create a function to invoke the block's constructor
            f = new_method(blockname, bd)

            # Use metadata docstring to avoid forcing class resolution at bind time.
            f.__doc__ = info.get("doc")

            # get a bound version of this function
            bound_method: types.MethodType = f.__get__(self)
            # and set it as an attribute of the instance
            setattr(bd, blockname, bound_method)

        # finally we need to check that all the upper-case methods of the block diagram
        # have been defined via load_blocks. If they are just a stub we replace that
        # with a function that raises an exception at runtime.
        for blockname in dir(bd):
            if blockname.isupper() and blockname not in self._blocklibrary.keys():
                # this is a method we haven't already defined, so add it as a
                # factory method that raises an error if called
                # print(f"block {blockname} is not defined in the block library")

                def undefined_block_factory(
                    *args: Any, blockname: str = blockname, **kwargs: Any
                ) -> NoReturn:
                    raise NotImplementedError(
                        f"block {blockname} is not defined in the block library: missing block definition, block path error, or syntax error in the body of the block's code."
                    )

                setattr(bd, blockname, undefined_block_factory)

        # add a clone of the options
        # bd.options = copy.copy(self.options)
        bd.runtime = self

        return bd

    def DEBUG(self, debug: str, fmt: str, *args: Any) -> None:
        context: SimulationContext | None = self._get_context()
        assert self.options is not None
        options: OptionsBase = context.options if context is not None else self.options
        if debug[0] in options.debug:
            print(f"DEBUG.{debug:s}: " + fmt.format(*args))

    def done(self, bd: Any, block: bool = False) -> None:
        context: SimulationContext = self._require_context()
        if context.options.hold:
            block = context.options.hold

        try:
            plt.show(block=block)
        except KeyboardInterrupt:
            print("bdsim: closing all windows")
            plt.close("all")
            # sys.exit(1)  # not sure why we have this
            return
        bd.done()
        plt.close("all")
        plt.pause(0.5)  # let the event handler do its work

    def closefigs(self) -> None:
        context: SimulationContext = self._require_context()
        for i in range(context.simstate.fignum):
            print("close", i + 1)
            plt.close(i + 1)
            plt.pause(0.1)
        context.simstate.fignum = 0  # reset figure counter

    def savefig(
        self,
        block: Any,
        filename: str | None = None,
        format: str = "pdf",
        **kwargs: Any,
    ) -> None:
        block.savefig(filename=filename, format=format, **kwargs)

    def savefigs(self, bd: Any, format: str = "pdf", **kwargs: Any) -> None:
        from bdsim.block_types import GraphicsBlock

        for b in bd.blocklist:
            if isinstance(b, GraphicsBlock):
                b.savefig(filename=b.name, format=format, **kwargs)

    def showgraph(self, bd: Any, **kwargs: Any) -> None:
        # create the temporary dotfile
        dotfile: io.TextIOWrapper = tempfile.TemporaryFile(mode="w")
        bd.dotfile(dotfile, **kwargs)

        # rewind the dot file, create PDF file in the filesystem, run dot
        dotfile.seek(0)
        pdffile: tempfile._TemporaryFileWrapper[bytes] = tempfile.NamedTemporaryFile(
            suffix=".pdf", delete=False
        )
        subprocess.run("dot -Tpdf", shell=True, stdin=dotfile, stdout=pdffile)

        # open the PDF file in browser (hopefully portable), then cleanup
        webbrowser.open(f"file://{pdffile.name}")
        os.remove(pdffile.name)

    def fatal(self, message: str, retval: int = 1) -> NoReturn:
        """
        Fatal simulation error

        :param message: Error message
        :type message: str
        :param retval: system return value (``*nix`` only) defaults to 1
        :type retval: int, optional

        Display the error message then terminate the process.  For operating
        systems that support it, return an integer code.
        """
        # TODO print text in some color
        print(message)
        sys.exit(retval)

    def load_blocks(
        self, verbose: bool = True, toolboxes: bool = True
    ) -> dict[str, dict[str, Any]]:
        """
        Dynamically load all block definitions.

        :raises ImportError: module could not be imported
        :return: dictionary of block metadata
        :rtype: dict of dict

        Reads blocks from .py files found in bdsim/bdsim/blocks, folders
        given by colon separated list in envariable BDSIMPATH, and the
        command line option ``packages``.

        The result is a dict indexed by the upper-case block name with elements:
        - ``path`` to the folder holding the Python file defining the block
        - ``classname``
        - ``blockname``, upper case version of ``classname``
        - ``url`` of online documentation for the block
        - ``package`` containing the block
        - `doc` is the docstring from the class constructor
        """

        def parse_docstring(ds: str) -> dict[str, Any]:
            import re
            from collections import OrderedDict

            re_isfield: re.Pattern[str] = re.compile(r"\s*:[a-zA-Zα-ωΑ-Ω0-9_ ]+:")
            re_field: re.Pattern[str] = re.compile(
                r"^\s*:(?P<field>[a-zA-Z]+)(?:"
                r" +(?P<var>[a-zA-Zα-ωΑ-Ω0-9_]+))?:(?P<body>.+)$"
            )

            # a-zA-Zα-ωΑ-Ω0-9_
            def indent(s: str) -> int:
                return len(s) - len(s.lstrip())

            fieldnames = ("param", "type", "input", "output")
            excludevars = ("kwargs", "inputs")

            # parse out all lines of the form:
            #
            #  :field var: body
            # or
            #  :field var: body with a very long description that
            #       carries over to another line or two
            fieldlines = []
            for para in ds.split("\n\n"):
                # print(para)
                # print('--')

                indent_prev = None
                infield = False

                for line in para.split("\n"):
                    if len(line) == 0:
                        continue
                    if indent_prev is None:
                        indent_prev = indent(line)
                    if re_isfield.match(line) is not None:
                        fieldlines.append(line.lstrip())
                        infield = True
                    if indent(line) > indent_prev and infield:
                        fieldlines[-1] += " " + line.lstrip()
                    if indent(line) == indent_prev:
                        infield = False

            # fieldlines is a list of lines of the form
            #
            #   :field var: body
            #
            # where extension lines have been concatenated

            # create a dict of dicts
            #
            #   dict[field][var] -> body
            dict = OrderedDict()

            for line in fieldlines:
                m: re.Match[str] | None = re_field.match(line)
                if m is not None:
                    field, var, body = m.groups()
                    if var in excludevars or field not in fieldnames:
                        continue
                    if field not in dict:
                        dict[field] = {var: body}
                    else:
                        dict[field][var] = body
                    dict[m.group("field")]

            # now connect pairs of lines of the form
            #
            # :param X: param description
            # :type X: type description
            #
            # params[X] = (type description, param description)
            params = {}
            if "param" in dict:
                for var, descrip in dict["param"].items():
                    typ = dict["type"].get(var, None)
                    params[var] = (typ, descrip)

            return params

        def get_package_url(blocks_path: str) -> str | None:
            init_file = Path(blocks_path) / "__init__.py"
            if not init_file.exists():
                return None

            try:
                mod = ast.parse(init_file.read_text(), filename=str(init_file))
            except OSError:
                return None

            for stmt in mod.body:
                if not isinstance(stmt, ast.Assign):
                    continue
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == "url":
                        if isinstance(stmt.value, ast.Constant) and isinstance(
                            stmt.value.value, str
                        ):
                            return stmt.value.value
            return None

        def ast_to_literal(node: ast.AST) -> Any:
            try:
                return ast.literal_eval(node)
            except Exception:
                return None

        def parse_module(
            module_file: Path,
            module_name: str,
            package: str,
            package_url: str | None,
            blocks_path: str,
            blocks: dict[str, dict[str, Any]],
            moduledict: dict[str, list[str]],
        ) -> None:
            try:
                source = module_file.read_text()
                tree = ast.parse(source, filename=str(module_file))
            except OSError:
                return
            except SyntaxError as err:
                self._print_exception_red(
                    f"load_blocks:: package {package} contains a compile error",
                    err,
                )
                return

            class_defs = [node for node in tree.body if isinstance(node, ast.ClassDef)]
            class_meta: dict[str, dict[str, Any]] = {}
            for class_def in class_defs:
                name = class_def.name

                base_names: list[str] = []
                for base in class_def.bases:
                    if isinstance(base, ast.Name):
                        base_names.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        base_names.append(base.attr)

                class_values: dict[str, Any] = {
                    "nin": None,
                    "nout": None,
                    "inlabels": None,
                    "outlabels": None,
                    "_blockclass": None,
                }
                is_deprecated = any(
                    (isinstance(d, ast.Name) and d.id == "deprecated_block")
                    or (
                        isinstance(d, ast.Call)
                        and isinstance(d.func, ast.Name)
                        and d.func.id == "deprecated_block"
                    )
                    for d in class_def.decorator_list
                )
                init_doc = ""

                for stmt in class_def.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if (
                                isinstance(target, ast.Name)
                                and target.id in class_values
                            ):
                                class_values[target.id] = ast_to_literal(stmt.value)
                    elif isinstance(stmt, ast.AnnAssign):
                        if (
                            isinstance(stmt.target, ast.Name)
                            and stmt.target.id in class_values
                        ):
                            if stmt.value is not None:
                                class_values[stmt.target.id] = ast_to_literal(
                                    stmt.value
                                )
                    elif isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__":
                        init_doc = ast.get_docstring(stmt) or ""

                class_meta[name] = {
                    "name": name,
                    "base_names": base_names,
                    "class_values": class_values,
                    "is_deprecated": is_deprecated,
                    "class_doc": ast.get_docstring(class_def) or "",
                    "init_doc": init_doc,
                }

            resolved_blockclass: dict[str, str | None] = {}

            def resolve_blockclass(class_name: str, stack: set[str]) -> str | None:
                cached = resolved_blockclass.get(class_name)
                if class_name in resolved_blockclass:
                    return cached
                if class_name in stack:
                    return None
                meta = class_meta.get(class_name)
                if meta is None:
                    return None

                stack.add(class_name)

                explicit = meta["class_values"].get("_blockclass")
                if isinstance(explicit, str):
                    result: str | None = explicit
                else:
                    result = None
                    for base_name in meta["base_names"]:
                        if base_name.endswith("Block"):
                            result = base_name.lower().replace("block", "")
                            break
                        inherited = resolve_blockclass(base_name, stack)
                        if inherited is not None:
                            result = inherited
                            break

                stack.remove(class_name)
                resolved_blockclass[class_name] = result
                return result

            def resolve_port_count(class_name: str, key: str, stack: set[str]) -> int:
                meta = class_meta.get(class_name)
                if meta is None or class_name in stack:
                    return 0
                own = meta["class_values"].get(key)
                if isinstance(own, int):
                    return own
                stack.add(class_name)
                for base_name in meta["base_names"]:
                    if base_name in class_meta:
                        value = resolve_port_count(base_name, key, stack)
                        if value != 0:
                            stack.remove(class_name)
                            return value
                stack.remove(class_name)
                return 0

            for name, meta in class_meta.items():
                if name.endswith("Block"):
                    continue

                block_class = resolve_blockclass(name, set())
                if block_class is None:
                    continue

                ds = meta["class_doc"] + meta["init_doc"]
                param_dict = parse_docstring(ds)

                info: dict[str, Any] = {}
                info["path"] = [blocks_path]
                info["classname"] = name
                info["blockname"] = blockname(name)
                info["url"] = (
                    None
                    if package_url is None
                    else f"{package_url}#{module_name}.{name}"
                )
                info["class"] = _LazyBlockClass(module_name, name)
                info["module"] = module_name
                info["package"] = package
                info["doc"] = ds
                info["params"] = param_dict
                info["inputs"] = param_dict.get("input")
                info["outputs"] = param_dict.get("output")
                info["nin"] = resolve_port_count(name, "nin", set())
                info["nout"] = resolve_port_count(name, "nout", set())
                info["blockclass"] = block_class
                info["deprecated"] = meta["is_deprecated"]

                key = blockname(name)
                blocks[key] = info
                moduledict.setdefault(module_name, []).append(name)

        if toolboxes:
            packages: list[str] = [
                "bdsim",
                "roboticstoolbox",
                "machinevisiontoolbox",
            ]
        else:
            packages = ["bdsim"]  # type: ignore[no-redef]
        env: str | None = os.getenv("BDSIMPATH")
        if env is not None:
            packages += env.split(":")
        if self.packages is not None:
            packages += self.packages.split(":")

        def find_blocks_dirs(
            package_name: str,
        ) -> tuple[str, list[str]]:
            """Locate a package's blocks directory without importing the package.

            Walks ``sys.path`` looking for ``<entry>/<package_name>/blocks/``
            with an ``__init__.py``.  Returns the dotted module name for the
            blocks sub-package and a list of matching filesystem paths.

            If *package_name* looks like an absolute or relative filesystem
            path (contains a separator or starts with ``/``), it is treated
            as a direct path to a blocks directory rather than a package name.
            """
            if os.sep in package_name or package_name.startswith("/"):
                # Bare directory path, not a package name
                d = Path(package_name)
                if d.is_dir():
                    return package_name, [str(d)]
                return package_name, []

            blocks_module = f"{package_name}.blocks"
            found: list[str] = []
            for entry in sys.path:
                if not entry:
                    continue
                d = Path(entry) / package_name / "blocks"
                if d.is_dir() and (d / "__init__.py").exists():
                    found.append(str(d))
            return blocks_module, found

        blocks: dict[str, dict[str, Any]] = {}
        moduledicts: dict[str, dict[str, list[str]]] = {}
        for package in packages:
            if os.getenv("BDSIM_DEBUG_DISCOVERY"):
                print(f"[bdsim] discover package {package}", flush=True)

            blocks_module_name, module_paths = find_blocks_dirs(package)

            if len(module_paths) == 0:
                print(
                    f"package {package} not loaded: not found, not a proper package, no blocks module"
                )
                continue

            moduledict: dict[str, list[str]] = {}
            for blocks_path in module_paths:
                package_url = get_package_url(blocks_path)
                for module_file in sorted(Path(blocks_path).glob("*.py")):
                    stem = module_file.stem
                    if stem.startswith("_"):
                        continue
                    module_name = f"{blocks_module_name}.{stem}"
                    parse_module(
                        module_file,
                        module_name,
                        package,
                        package_url,
                        blocks_path,
                        blocks,
                        moduledict,
                    )

            moduledicts[package] = moduledict

        self.moduledicts = moduledicts
        return blocks

    def blocks(self) -> None:
        """
        List all loaded blocks.

        Example::

            73  blocks loaded
            bdsim.blocks.functions..................: SUM PROD GAIN CLIP FUNCTION INTERPOLATE
            bdsim.blocks.sources....................: CONSTANT TIME WAVEFORM PIECEWISE STEP RAMP
            bdsim.blocks.sinks......................: PRINT STOP NULL WATCH
            bdsim.blocks.continuous.................: INTEGRATOR POSEINTEGRATOR LTI_SS LTI_SISO
            bdsim.blocks.sampled....................: ZOH INTEGRATOR_S POSEINTEGRATOR_S
            bdsim.blocks.linalg.....................: INVERSE TRANSPOSE NORM FLATTEN SLICE2 SLICE1 DET COND
            bdsim.blocks.displays...................: SCOPE SCOPEXY SCOPEXY1
            bdsim.blocks.connections................: ITEM DICT MUX DEMUX INDEX SUBSYSTEM INPORT OUTPORT
            roboticstoolbox.blocks.arm..............: FKine IKine Jacobian Tr2Delta Delta2Tr Point2Tr TR2T FDyn IDyn Gravload
            ........................................: Inertia Inertia_X FDyn_X ArmPlot Traj JTraj LSPB CTraj CirclePath
            roboticstoolbox.blocks.mobile...........: Bicycle Unicycle DiffSteer VehiclePlot
            roboticstoolbox.blocks.uav..............: MultiRotor MultiRotorMixer MultiRotorPlot
            machinevisiontoolbox.blocks.camera......: Camera Visjac_p EstPose_p ImagePlane
        """

        def dots(s: str, n: int = 40) -> str:
            return s + "." * (n - len(s))

        assert self._blocklibrary is not None
        assert self.moduledicts is not None
        print(len(self._blocklibrary), " blocks loaded")
        for pkg, module_dict in self.moduledicts.items():
            for k, v in module_dict.items():
                line: str = ""
                once = False
                while len(v) > 0:
                    n: str = v.pop(0).upper() + " "
                    if len(line + n) < 80:
                        line += n
                        continue
                    else:
                        # line will be too long
                        if not once:
                            print(f"{dots(k)}: {line}")
                            once = True
                        else:
                            print(f"{dots('')}: {line}")
                        line = ""
                if len(line) > 0:
                    if once:
                        print(f"{dots('')}: {line}")
                    else:
                        print(f"{dots(k)}: {line}")

    def set_options(self, **options: Any) -> None:
        assert self.options is not None
        self.options.set(**options)
        warnings.warn("use sim.options.OPT=VALUE instead", DeprecationWarning)

    def set_globals(self, globs: dict[str, Any]) -> None:
        """
        Set globals as specified by command line

        :param globs: global variables
        :type globs: dict

        The command line option ``--global var=value`` can be used to request the change
        of global variables.  However, actually changing them requires explicit code
        support in the user's program after the ``BDSim`` constructor.

        Example::

            sim.set_globals(globals())

        Messages are displayed by defaulting, indicating which variables are changed,
        and their old and new values.
        """
        # handle the globals
        assert self.options is not None
        for s in self.options.setglob:
            var, value = s.split("=")

            new_value = eval(value)
            print(f"changed value of global {var} from {globs[var]} -> {new_value}")
            globs[var] = new_value

    def report(self, bd: Any, type: str = "summary", **kwargs: Any) -> None:
        """Print block diagram report

        :param bd: the block diagram to be reported
        :type bd: :class:`BlockDiagram`
        :param type: report type, one of: "summary" (default), "lists", "schedule"
        :type type: str, optional
        :param style: table style, one of: ansi (default), markdown, latex
        :type style: str

        Single method wrapper for various block diagram reports.  Obeys the ``-q``
        option to suppress all reports at runtime.

        :seealso: :meth:`BlockDiagram.report_summary` :meth:`BlockDiagram.report_lists` :meth:`BlockDiagram.report_schedule`
        """
        context: SimulationContext | None = self._get_context()
        assert self.options is not None
        options: OptionsBase = context.options if context is not None else self.options
        if options.quiet:
            return

        if type == "lists":
            bd.report_lists(**kwargs)
        elif type == "summary":
            bd.report_summary(**kwargs)
        elif type == "schedule":
            bd.report_schedule(**kwargs)


class Options(OptionsBase):
    def __init__(self, sysargs: bool = True, **options: Any) -> None:
        if "interactive_rate" in options and "animation_rate" not in options:
            options["animation_rate"] = options.pop("interactive_rate")

        def available_matplotlib_backends() -> list[str]:
            try:
                from matplotlib.backends import backend_registry

                backends = list(backend_registry.list_builtin())
            except Exception:
                backends = list(getattr(matplotlib.rcsetup, "all_backends", []))

            # Preserve order while removing duplicates case-insensitively.
            unique: list[str] = []
            seen: set[str] = set()
            for backend in backends:
                key = backend.lower()
                if key not in seen:
                    seen.add(key)
                    unique.append(backend)
            return unique

        default_options: dict[str, Any] = {
            "backend": None,
            "tiles": None,
            "graphics": True,
            "animation": False,
            "animation_rate": 20.0,
            "dt": None,
            "atol": None,
            "rtol": None,
            "max_step": None,
            "method": None,
            "hold": True,
            "shape": None,
            "altscreen": True,
            "progress": True,
            "verbose": False,
            "debug": "",
            "simtime": None,
            "blocks": False,
            "outfile": None,
            "jsonfile": None,
            "quiet": False,
            "setparam": [],
            "setglob": [],
        }

        # modify defaults according to envariable BDSIM which is comma/semicolon
        # separated list of key=value pairs
        # eg. setenv BDSIM graphics=True,hold=True
        env: str | None = os.getenv("BDSIM")
        if env is not None:
            for key_value in env.split(",;"):
                # for each key=value pair
                key, value = [s.strip() for s in key_value.split("=")]
                # attempt an eval, resolves True, False
                try:
                    value = eval(value)
                except SyntaxError:
                    pass
                try:
                    default_options[key] = value
                except KeyError:
                    print("envariable BDSIM, unknown option", key)

        # Constructor-provided options should influence displayed CLI defaults
        # (eg. `BDSim(animation=True)` then `-h` should show animation=True).
        effective_defaults = dict(default_options)
        for key, value in options.items():
            if key in effective_defaults:
                effective_defaults[key] = value

        unknownargs: list[str] = []
        if sysargs:
            raw_argv = list(sys.argv[1:])

            def _option_explicitly_set(option_strings: Sequence[str]) -> bool:
                for token in raw_argv:
                    for opt in option_strings:
                        if token == opt or token.startswith(opt + "="):
                            return True
                        if (
                            len(opt) == 2
                            and opt.startswith("-")
                            and not opt.startswith("--")
                            and token.startswith(opt)
                            and token != opt
                        ):
                            # short-option attached form, eg. -bTkAgg
                            return True
                return False

            # command line arguments and graphics
            class _Fmt(
                argparse.ArgumentDefaultsHelpFormatter,
                argparse.RawDescriptionHelpFormatter,
            ):
                pass

            parser = argparse.ArgumentParser(
                prefix_chars="-+",
                formatter_class=_Fmt,
                description="Block diagram simulation framework",
                epilog=(
                    "Environment variables:\n"
                    "  BDSIM              comma-separated key=value pairs that set option defaults,\n"
                    "                     e.g. BDSIM=graphics=True,hold=True\n"
                    "  BDSIMPATH          colon-separated list of extra paths/packages to search for blocks\n"
                    "  BDSIM_NO_TOOLBOXES set to 1/true/yes/on to skip loading external toolboxes\n"
                    "  BDSIM_DEBUG_LAZY_LOAD  set to any value to trace lazy block-class resolution\n"
                    "  BDSIM_DEBUG_DISCOVERY  set to any value to trace block-package discovery\n"
                ),
            )
            parser.add_argument(
                "--backend",
                "-b",
                type=str,
                nargs="?",
                const="list",
                default=effective_defaults["backend"],
                metavar="BACKEND",
                help=(
                    "matplotlib backend to choose; use with no argument or with "
                    "'list'/'help' to print available backends"
                ),
            )
            parser.add_argument(
                "--tiles",
                "-t",
                type=str,
                default=effective_defaults["tiles"],
                metavar="SPEC",
                help="window tiling as RxC or one of: square, wide, tall",
            )
            parser.add_argument(
                "--shape",
                type=str,
                default=effective_defaults["shape"],
                metavar="WIDTHxHEIGHT",
                help="window size as WxH, defaults to matplotlib default",
            )
            parser.add_argument(
                "--blocks",
                action="store_const",
                const=True,
                default=effective_defaults["blocks"],
                dest="blocks",
                help="Display blocks at startup",
            )

            g_group = parser.add_mutually_exclusive_group()
            g_group.add_argument(
                "-g",
                "--no-graphics",
                action="store_const",
                const=False,
                dest="graphics",
                help="disable graphic display",
            )
            g_group.add_argument(
                "+g",
                "--graphics",
                action="store_const",
                const=True,
                dest="graphics",
                help="enable graphic display",
            )

            a_group = parser.add_mutually_exclusive_group()
            a_group.add_argument(
                "-a",
                "--no-animation",
                action="store_const",
                const=False,
                dest="animation",
                help="do not animate graphics",
            )
            a_group.add_argument(
                "+a",
                "--animation",
                action="store_const",
                const=True,
                dest="animation",
                help="animate graphics (implies --graphics)",
            )

            h_group = parser.add_mutually_exclusive_group()
            h_group.add_argument(
                "-H",
                "--no-hold",
                action="store_const",
                const=False,
                dest="hold",
                help="do not hold graphics in done()",
            )
            h_group.add_argument(
                "+H",
                "--hold",
                action="store_const",
                const=True,
                dest="hold",
                help="hold graphics in done()",
            )

            alt_group = parser.add_mutually_exclusive_group()
            alt_group.add_argument(
                "+A",
                "--altscreen",
                action="store_const",
                const=True,
                dest="altscreen",
                help="display plots on second monitor",
            )
            alt_group.add_argument(
                "-A",
                "--no-altscreen",
                action="store_const",
                const=False,
                dest="altscreen",
                help="do not display plots on second monitor",
            )

            parser.add_argument(
                "--no-progress",
                action="store_const",
                const=False,
                default=effective_defaults["progress"],
                dest="progress",
                help="do not display simulation progress bar",
            )
            parser.add_argument(
                "--verbose",
                "-v",
                action="store_const",
                const=True,
                default=effective_defaults["verbose"],
                help="debug flags",
            )
            parser.add_argument(
                "--debug",
                "-d",
                type=str,
                default=effective_defaults["debug"],
                metavar="[psd]",
                help="debug flags: p/ropagate, s/tate, d/eriv, i/nteractive",
            )
            parser.add_argument(
                "--simtime",
                "-S",
                type=str,
                default=effective_defaults["simtime"],
                help="simulation time: T or T,dt",
            )
            parser.add_argument(
                "--animation-rate",
                type=float,
                default=effective_defaults["animation_rate"],
                metavar="HZ",
                help="target interactive update cadence for animation/debugger",
            )
            parser.add_argument(
                "--dt",
                type=float,
                default=effective_defaults["dt"],
                metavar="DT",
                help="output sample interval used to build solve_ivp t_eval",
            )
            parser.add_argument(
                "--atol",
                type=float,
                default=effective_defaults["atol"],
                metavar="ATOL",
                help="absolute tolerance for solve_ivp",
            )
            parser.add_argument(
                "--rtol",
                type=float,
                default=effective_defaults["rtol"],
                metavar="RTOL",
                help="relative tolerance for solve_ivp",
            )
            parser.add_argument(
                "--max-step",
                type=float,
                default=effective_defaults["max_step"],
                metavar="DT",
                dest="max_step",
                help="maximum solve_ivp integration step",
            )
            parser.add_argument(
                "--method",
                type=str,
                default=(
                    effective_defaults["method"]
                    if effective_defaults["method"] is not None
                    else argparse.SUPPRESS
                ),
                metavar="NAME",
                help=(
                    "solve_ivp method (eg. RK45, DOP853, Radau, BDF, LSODA)"
                    + (
                        " (default: RK45)"
                        if effective_defaults["method"] is None
                        else ""
                    )
                ),
            )
            parser.add_argument(
                "--quiet",
                "-q",
                action="store_const",
                const=True,
                default=effective_defaults["quiet"],
                help="suppress reports and progress bar",
            )
            parser.add_argument(
                "-p",
                "--pickle",
                nargs="?",
                const="bd.out",
                default=effective_defaults["outfile"],
                metavar="FILE",
                dest="outfile",
                help="output pickled simulation results (default filename: bd.out)",
            )
            parser.add_argument(
                "-o",
                "--out",
                nargs="?",
                const="bd.out",
                default=effective_defaults["outfile"],
                metavar="FILE",
                dest="outfile",
                help="[deprecated, use -p/--pickle] output pickled simulation results",
            )
            parser.add_argument(
                "-j",
                "--json",
                nargs="?",
                const="bd.json",
                default=effective_defaults["jsonfile"],
                metavar="FILE",
                dest="jsonfile",
                help="output simulation results as JSON (default filename: bd.json)",
            )
            parser.add_argument(
                "--set",
                "-s",  # NOTE: clashes with `unittest discover -s <startdir>`; use pytest or --start-directory instead
                dest="setparam",
                action="append",
                default=list(effective_defaults["setparam"]),
                type=str,
                help="override block parameter using block:param=value",
            )
            parser.add_argument(
                "--global",
                dest="setglob",
                action="append",
                default=list(effective_defaults["setglob"]),
                type=str,
                help="override global parameter using var=value",
            )

            parser.set_defaults(
                graphics=effective_defaults["graphics"],
                animation=effective_defaults["animation"],
                hold=effective_defaults["hold"],
                altscreen=effective_defaults["altscreen"],
            )

            self._parser = parser
            argv0 = sys.argv[0] if len(sys.argv) > 0 else ""
            args, unknownargs = parser.parse_known_args()
            # Consume bdsim options from sys.argv so user code sees only its own args.
            sys.argv = [argv0, *unknownargs]
            parsed_options: dict[str, Any] = vars(args)
            cmdline_options: dict[str, Any] = {}
            for action in parser._actions:
                if not action.option_strings:
                    continue
                dest = action.dest
                if dest in ("help", argparse.SUPPRESS):
                    continue
                if _option_explicitly_set(action.option_strings):
                    cmdline_options[dest] = parsed_options[dest]

            if _option_explicitly_set(["-o", "--out"]):
                import warnings as _warnings
                _warnings.warn(
                    "-o/--out is deprecated; use -p/--pickle instead",
                    DeprecationWarning,
                    stacklevel=2,
                )

            backend_option = parsed_options.get("backend")
            if isinstance(backend_option, str) and backend_option.lower() in {
                "list",
                "help",
            }:
                backends = sorted(available_matplotlib_backends(), key=str.lower)
                print("available matplotlib backends: " + ", ".join(backends))
                raise SystemExit(0)
        else:
            cmdline_options = dict()  # empty dictionary
            self._parser = None

        # If CLI explicitly disables graphics, also force animation=False so
        # that code-level animation=True (e.g. BDSim(animation=True)) doesn't
        # conflict.  Put it in cmdline_options (readonly) so it wins over kwargs.
        if not cmdline_options.get("graphics", True):
            cmdline_options["animation"] = False

        # --quiet implies --no-progress
        if cmdline_options.get("quiet", False):
            cmdline_options.setdefault("progress", False)

        super().__init__(readonly=cmdline_options, args=effective_defaults)

        # Validate and normalize the initialized option set, including
        # command-line readonly values and environment-derived defaults.
        self.data = self.sanity(dict(self.data))

        # Re-apply only options that were NOT already baked into effective_defaults
        # (i.e. non-standard kwargs not in the registered option set).  Registered
        # options are already present via effective_defaults and should not be
        # re-applied here, as doing so would undo CLI-driven normalization.
        extra_options = {k: v for k, v in options.items() if k not in default_options}
        self.set(**extra_options)

        if self.verbose:
            print(self)

        self._argv: list[str] = unknownargs  # save non-bdsim arguments

    def help(self) -> str:
        """Return the CLI help text as a string (empty string if not in CLI mode)."""
        if self._parser is None:
            return ""
        return self._parser.format_help()

    def print_help(self) -> None:
        """Print the CLI help text to stdout."""
        print(self.help())

    def sanity(self, options: dict[str, Any]) -> dict[str, Any]:
        # ensure animation is disabled if graphics is disabled
        if "graphics" in options and "animation" in options:
            if options["animation"] and not options["graphics"]:
                raise ValueError("cannot enable animation but disable graphics")
        elif "graphics" in options and not options["graphics"]:
            options["animation"] = False
        elif "animation" in options and options["animation"]:
            options["graphics"] = True

        if "animation_rate" in options and float(options["animation_rate"]) <= 0:
            raise ValueError("animation_rate must be > 0")

        if options.get("dt") is not None and float(options["dt"]) <= 0:
            raise ValueError("dt must be > 0")

        if options.get("atol") is not None and float(options["atol"]) <= 0:
            raise ValueError("atol must be > 0")

        if options.get("rtol") is not None and float(options["rtol"]) <= 0:
            raise ValueError("rtol must be > 0")

        if options.get("max_step") is not None and float(options["max_step"]) <= 0:
            raise ValueError("max_step must be > 0")

        return options


if __name__ == "__main__":
    try:
        from ._selftest import run_module_test
    except ImportError:
        from bdsim._selftest import run_module_test

    raise SystemExit(run_module_test(__file__))
