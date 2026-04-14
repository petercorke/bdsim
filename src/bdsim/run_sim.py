"""Offline simulation runner and dynamic block-loading support."""

from __future__ import annotations

import ast
from concurrent.futures import Future, ThreadPoolExecutor
from collections import Counter, namedtuple
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
from typing import Any, NoReturn

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
    clocklist,
)
from bdsim.block import BlockApiError, BlockRuntimeError
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
        fraction, prefix="", suffix="", decimals=1, length=50, fill="█", printEnd="\r"
    ) -> None:
        percent: str = ("{0:." + str(decimals) + "f}").format(fraction * 100)
        filledLength = int(length * fraction)
        bar: str = fill * filledLength + "-" * (length - filledLength)
        print(f"\r{prefix} |{bar}| {percent}% {suffix}", end=printEnd)

    def __init__(self, enable=True) -> None:
        self.enable: bool = enable
        self.length = 60
        if not enable:
            return

    def start(self, T) -> None:
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

    def update(self, t) -> None:
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
def blockname(name):
    return name.upper()


class _LazyBlockClass:
    """Proxy object that resolves a block class on first use."""

    __slots__ = ("_module_name", "_class_name", "_resolved")

    def __init__(self, module_name: str, class_name: str) -> None:
        self._module_name = module_name
        self._class_name = class_name
        self._resolved: type[Block] | None = None

    @property
    def __name__(self) -> str:
        return self._class_name

    @property
    def __module__(self) -> str:
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

    def __call__(self, *args, **kwargs):
        return self._resolve()(*args, **kwargs)

    def __getattribute__(self, name: str):
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


class BDSimState(SimulationState):
    """
    Offline simulation state: extends SimulationState with offline-specific fields.

    Holds the mutable execution state for a single offline run, created fresh
    each time run() is called. This keeps BDSim.run() reentrant.
    """

    def __init__(self) -> None:
        super().__init__()
        # offline-specific fields
        self.dt: float | None = None
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
        self, banner=True, packages=None, load=True, toolboxes=True, **kwargs
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
        :param backend: matplotlib backend, defaults to 'Qt5Agg''
        :type backend: str, optional
        :param tiles: figure tile layout on monitor, defaults to '3x4'
        :type tiles: str, optional
        :raises ImportError: syntax error in block
        :return: parent object for blockdiagram simulation
        :rtype: BDSim

        If ``sysargs`` is True, process command line arguments and passed
        options.  Command line arguments have precedence.

        ===================  =========  ========  ===========================================
        Command line switch  Argument   Default   Behaviour
        ===================  =========  ========  ===========================================
        --graphics, +g       graphics   True      enable graphical display
        --animation, +a      animation  True      update graphics at each time step
        --hold, +h           hold       True      hold graphics in done()
        --no-graphics, -g    graphics   True      disable graphical display
        --no-animation, -a   animation  True      don't update graphics at each time step
        --no-hold, -H        hold       True      do not hold graphics in done()
        --no-progress, -p    progress   True      do not display simulation progress bar
        --backend BE         backend    'Qt5Agg'  matplotlib backend
        --tiles RxC, -t RxC  tiles      '3x4'     arrangement of figure tiles on the display
        --shape WxH          shape      None      window size, default matplotlib size
        --altscreen, +A,     altscreen  True      display plots on second monitor
        --no-altscreen, -A   altscreen  True      do not display plots on second monitor
        --debug F, -d F      debug      ''        debug flag string
        --simtime T[,dt]     simtime    (10,)     simulation time
        --verbose, -v        verbose    False     be verbose
        --quiet, -q          quiet      False     suppress reports
        -o                   outfile    None      output pickled simulation results to bd.out
        --out OUTFILE        outfile    None      file to save pickled simulation results
        --set P, -s P        setparam   []        override block parameter using ``P=block:param=value``
        --global G           setglob    []        override global parameter using ``G=var=value``
        ===================  =========  ========  ===========================================

        .. note:: ``animation`` and ``graphics`` options are coupled.  If
            ``graphics=False``, all graphics is suppressed.  If
            ``graphics=True`` then graphics are shown and the behaviour depends
            on ``animation``.  ``animation=False`` shows graphs at the end of
            the simulation, while ``animation=True` will animate the graphs
            during simulation.

        :seealso: :meth:`set_globals()`
        """

        super().__init__()
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

    def blockinfo(self, block=None):
        """Return info about all blocks

        :param block: name of block to return info for, otherwise list of info for all
        :type block: str, optional
        :returns: parameters of blocks
        :rtype: dict or list of dicts

        Detailed metadata about a block is obtained by introspection and parsing the block's docstring.

        ==========   =====================================================
        Key          Description
        ==========   =====================================================
        path         Path to the folder containing block definition
        classname    Name of class
        url          URL of online documentation
        class        Reference to the class
        module       Name of the module  package.blocks.module
        package      Name of the package, eg. bdsim, roboticstoolbox
        params       Dict of (type, descrip), indexed by parameter name
        inputs       List of names of block inputs
        outputs      List of names of block outputs
        nin          Number of inputs, -1 if variable
        nout         Number of outputs, -1 if variable
        blockclass   Block class, eg. source, sink etc.
        ==========   =====================================================

        """
        if block is None:
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
            raise RuntimeError("no active simulation context")
        return context

    def _set_context(self, context: SimulationContext | None) -> None:
        self._context_local.current = context

    def _make_run_options(self, *, threaded: bool = False, **overrides) -> OptionsBase:
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
        self, message: str, err: Exception, traceback: bool = True
    ) -> None:
        print(fg("red"))
        print(message)

        if traceback and err.__traceback__ is not None:
            frame: tb.FrameSummary = tb.extract_tb(err.__traceback__)[-1]
            print(f'  File "{frame.filename}", line {frame.lineno}, in {frame.name}')
            if frame.line is not None:
                print(f"    {frame.line.strip()}")
        print("  " + "".join(tb.format_exception_only(type(err), err)).strip())
        print(attr(0))

    def run(
        self,
        bd,
        T=5,
        dt=None,
        solver="RK45",
        solver_args=None,
        debug="",
        block=None,
        checkfinite=True,
        minstepsize=1e-12,
        watch=None,
        threaded: bool = False,
    ) -> BDStruct:
        """
        Run the block diagram

        :param T: maximum integration time, defaults to 10.0
        :type T: float, optional
        :param dt: maximum time step
        :type dt: float, optional
        :param solver: integration method, defaults to ``RK45``
        :type solver: str, optional
        :param block: matplotlib block at end of run, default False
        :type block: bool
        :param checkfinite: error if inf or nan on any wire, default True
        :type checkfinite: bool
        :param minstepsize: minimum step length, default 1e-6
        :type minstepsize: float
        :param watch: list of input ports to log
        :type watch: list
        :param solver_args: arguments passed to ``scipy.integrate``
        :type solver_args: dict
        :return: time history of signals and states
        :rtype: Sim class

        Assumes that the network has been compiled.

        The system is simulated from time 0 to ``T``.

        The integration step time ``dt`` defaults to ``T/100`` but can be
        specified.  Finer control can be achieved using ``max_step`` and
        ``first_step`` parameters to the underlying integrator using the
        ``solver_args`` parameter.

        Results are returned in a class with attributes:

        - ``t`` the time vector: ndarray, shape=(M,)
        - ``x`` is the state vector: ndarray, shape=(M,N)
        - ``xnames`` is a list of the names of the states corresponding to columns of `x`, eg. "plant.x0",
            defined for the block using the ``snames`` argument
        - ``yN`` for a watched input where N is the index of the port mentioned in the ``watch`` argument
        - ``ynames`` is a list of the names of the input ports being watched, same order as in ``watch`` argument

        If there are no dynamic elements in the diagram, ie. no states, then ``x`` and ``xnames`` are not
        present.

        The ``watch`` argument is a list of one or more input ports whose value during simulation
        will be recorded.  The elements of the list can be:
            - a ``Block`` reference, which is interpretted as input port 0
            - a ``Plug`` reference, ie. a block with an index or attribute
            - a string of the form "block[i]" which is port i of the block named block.

        The debug string comprises single letter flags:

                - 'p' debug network value propagation
                - 's' debug state vector
                - 'd' debug state derivative

        .. note:: Simulation stops if the step time falls below ``minsteplength``
            which typically indicates that the solver is struggling with a very
            harsh non-linearity.
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

        # final default values
        # T = T or 5
        # dt = dt or 0.01

        simstate = BDSimState()
        simstate.T = T

        if dt is None and not "max_step" in solver_args:
            dt = T / 100
        simstate.dt = dt
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
            if len(simstate.options.debug) > 0:
                simstate.options.progress = False
            if block is not None:
                simstate.options.hold = block

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
                    plug: Plug = w[0]
                elif isinstance(w, Plug):
                    # a plug was given
                    plug: Plug = w
                watchlist.append(plug)
                watchnamelist.append(str(plug))
            simstate.watchlist = watchlist
            simstate.watchnamelist = watchnamelist

            x0 = bd.getstate0()
            if not simstate.options.quiet:
                print(fg("yellow"))
                print(f">>> Start simulation: T = {T}, dt = {dt}")
                print(f"  Continuous state variables: {bd.nstates}")
                print("     x0 = ", x0)

                print(f"  Discrete state variables:   {bd.ndstates}")

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
            context.progress.start(T)

            if len(simstate.eventq) == 0:
                # no simulation events, solve it in one go
                self.run_interval(bd, 0, T, x0, simstate=simstate)
                nintervals = 1
            else:
                # we have simulation events, solve it in chunks
                simstate.declare_event(None, T)  # add an event at end of simulation

                # ignore all the events at zero
                tprev = 0
                simstate.eventq.pop_until(tprev)

                # get the state vector
                x = x0

                nintervals = 0
                while True:
                    # get next event from the queue and the list of blocks or
                    # clocks at that time
                    tnext, sources = simstate.eventq.pop(dt=1e-6)
                    if tnext is None:
                        break
                    # run system until next event time
                    x = self.run_interval(bd, tprev, tnext, x, simstate=simstate)
                    nintervals += 1

                    # visit all the blocks and clocks that have an event now
                    for source in sources:
                        if isinstance(source, Clock):
                            # clock ticked, save its state
                            source.savestate(tnext)
                            source.next_event(simstate)

                            # get the new state
                            try:
                                source._x = source.getstate(tnext)
                            except BlockRuntimeError as err:
                                bd._handle_block_runtime_error(err)
                    tprev: float = tnext

                    # are we done?
                    if simstate.t is not None and simstate.t >= T:
                        break

            # finished integration

            context.progress.end()  # cleanup the progress bar

            # print some info about the integration
            if not simstate.options.quiet:
                print(fg("yellow"))
                print("<<< Simulation complete")
                print(f"  block diagram evaluations: {simstate.count}")
                print(
                    "  block diagram exec time:  "
                    f" {simstate.bdtime / simstate.count * 1000.0:.3f} ms"
                )
                print(f"  time steps:                {len(simstate.tlist)}")
                print(f"  integration intervals:     {nintervals}")
                print(attr(0))

            # save buffered data in a Struct
            out = BDStruct(name="results")
            out["t"] = np.array(simstate.tlist)
            out["x"] = np.array(simstate.xlist)
            out["xnames"] = bd.statenames

            # save clocked states
            for c in bd.clocklist:
                name = str(c.name).replace(".", "")
                clockdata = BDStruct(name)
                clockdata["t"] = np.array(c.t)
                clockdata["x"] = np.array(c.x)
                out.add(name, clockdata)

            # save the watchlist into variables named y0, y1 etc.
            for i, p in enumerate(watchlist):
                out["y" + str(i)] = np.array(simstate.plist[i])
            out["ynames"] = watchnamelist

            # the command line options -o or --out saves results as a pickle file
            #  -o defaults to bd.out
            #  --out FILE allows the filename to be specified
            #
            # we can visualize the output file by
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

            # pause until all graphics blocks close

            if simstate.options.graphics and simstate.options.hold:
                self.done(bd, block=simstate.options.hold)
            return out
        finally:
            self._set_context(previous_context)

    def submit(self, bd, **kwargs) -> SimulationJob:
        if BDSim._executor is None:
            BDSim._executor = ThreadPoolExecutor()
        kwargs.setdefault("threaded", True)
        future: Future[BDStruct] = BDSim._executor.submit(self.run, bd, **kwargs)
        return SimulationJob(future)

    def update_parameters(self, bd) -> None:
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

    def run_interval(self, bd, t0, T, x0, simstate: BDSimState):
        """
        Integrate system over interval

        :param bd: the system blockdiagram
        :type bd: BlockDiagram
        :param t0: initial time
        :type t0: float
        :param tf: final time
        :type tf: float
        :param x0: initial state vector
        :type x0: ndarray(n)
        :param simstate: simulation state object
        :type simstate: SimState
        :return: final state vector xf
        :rtype: ndarray(n)

        The system is integrated from from ``x0`` to ``xf`` over the interval ``t0`` to ``tf``.

        """
        progress: Progress | None = self._require_context().progress
        assert progress is not None
        try:
            if bd.nstates > 0:
                # system has continuous states, solve it using numerical integration
                # print('initial state x0 = ', x0)

                # block diagram contains states, solve it using numerical integration

                scipy_integrator = integrate.__dict__[
                    simstate.solver
                ]  # get user specified integrator

                def ydot(t, y):
                    simstate.t = t
                    simstate.count += 1
                    eval_start = time.time()
                    yd = bd.schedule_evaluate(y, t, sinks=False, simstate=simstate)
                    eval_end = time.time()
                    simstate.bdtime += eval_end - eval_start
                    return yd

                if simstate.dt is not None:
                    simstate.solver_args["max_step"] = simstate.dt

                # print(f"run interval: from {t0} to {t0+T}, args={state.solver_args}, x0={x0}")
                integrator = scipy_integrator(
                    ydot, t0=t0, y0=x0, t_bound=T, **simstate.solver_args
                )

                # integrate
                while integrator.status == "running":
                    # step the integrator, calls _deriv and evaluate block diagram multiple times
                    message = integrator.step()

                    if integrator.status == "failed":
                        print(
                            fg("red")
                            + f"\nintegration completed with failed status: {message}"
                            + attr(0)
                        )
                        break

                    # stash the results
                    simstate.t = integrator.t
                    simstate.tlist.append(integrator.t)
                    simstate.xlist.append(integrator.y)

                    # record the ports on the watchlist
                    for i, p in enumerate(simstate.watchlist):
                        b = p.block
                        out = b.output_safe(integrator.t, b.inputs, b._x)[p.port]
                        simstate.plist[i].append(out)

                    # update all blocks that need to know
                    if (integrator.t - simstate.gtime) > (simstate.T / 200):
                        bd.step(integrator.t)
                        simstate.gtime = integrator.t
                    # bd.step(integrator.t)

                    progress.update(simstate.t)  # update the progress bar

                    if integrator.status == "finished":
                        break

                    # has any block called a stop?
                    if simstate.stop is not None:
                        print(
                            fg("red") + f"\n--- stop requested at t={simstate.t:.4f} by"
                            f" {simstate.stop}" + attr(0)
                        )
                        break

                    if (
                        simstate.minstepsize is not None
                        and integrator.step_size < simstate.minstepsize
                    ):
                        print(
                            fg("red") + "\n--- stopping on minimum step size at"
                            f" t={simstate.t:.4f} with last stepsize"
                            f" {integrator.step_size:g}" + attr(0)
                        )
                        break

                    if "i" in simstate.options.debug:
                        bd._debugger(simstate, integrator)

                return integrator.y  # return final state vector

            elif len(clocklist) == 0:
                # block diagram has no continuous or discrete states

                assert simstate.dt is not None, "if no states must specify dt"

                for t in np.arange(t0, T, simstate.dt):  # step through the time range
                    # evaluate the block diagram
                    simstate.t = t

                    simstate.count += 1
                    eval_start = time.time()
                    bd.schedule_evaluate([], t)
                    eval_end = time.time()
                    simstate.bdtime += eval_end - eval_start

                    # stash the results
                    simstate.tlist.append(t)

                    # record the ports on the watchlist
                    for i, p in enumerate(simstate.watchlist):
                        b = p.block
                        out = b.output_safe(t, b.inputs, b._x)[p.port]
                        simstate.plist[i].append(out)

                    # update all blocks that need to know
                    bd.step(t)

                    progress.update(t)  # update the progress bar

                    # has any block called a stop?
                    if simstate.stop is not None:
                        print(
                            fg("red") + f"\n--- stop requested at t={simstate.t:.4f} by"
                            f" {simstate.stop}" + attr(0)
                        )
                        break

                    if "i" in simstate.options.debug:
                        bd._debugger(simstate)

            else:
                # block diagram has no continuous states
                t = t0
                simstate.t = t
                # evaluate the block diagram

                simstate.count += 1
                eval_start = time.time()
                bd.schedule_evaluate([], t)
                eval_end = time.time()
                simstate.bdtime += eval_end - eval_start

                # stash the results
                simstate.tlist.append(t)

                # record the ports on the watchlist
                for i, p in enumerate(simstate.watchlist):
                    b = p.block
                    out = b.output_safe(t, b.inputs, b._x)[p.port]
                    simstate.plist[i].append(out)

                # update all blocks that need to know
                if (t - simstate.gtime) > (simstate.T / 200):
                    bd.step(t)
                    simstate.gtime = t
                # bd.step(t)

                progress.update(simstate.t)  # update the progress bar

                # has any block called a stop?
                if simstate.stop is not None:
                    print(
                        fg("red") + f"\n--- stop requested at t={simstate.t:.4f} by"
                        f" {simstate.stop}" + attr(0)
                    )

                if "i" in simstate.options.debug:
                    bd._debugger(simstate)

        except BlockRuntimeError as err:
            bd._handle_block_runtime_error(err)

    def blockdiagram(self, name="main") -> BlockDiagram:
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

        def new_method(block_name: str, bd):
            # return a wrapper for the block constructor that automatically
            # adds the block to the diagram's blocklist
            def block_init_wrapper(self, *args, **kwargs):
                # we catch errors in the block constructor and print them in red to make
                # it clear that the error is in the block definition, not in the user
                # code that creates the block diagram
                cls = self._resolve_block_class(block_name)
                try:
                    block = cls(*args, bd=bd, **kwargs)  # call __init__ on the block
                    return block
                except Exception as err:
                    self._print_exception_red(
                        f"runtime error while creating block {cls.__name__}", err
                    )
                raise RuntimeError(f"failed to create block {cls.__name__}") from None

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
                    *args, blockname=blockname, **kwargs
                ) -> NoReturn:
                    raise NotImplementedError(
                        f"block {blockname} is not defined in the block library: missing block definition, block path error, or syntax error in the body of the block's code."
                    )

                setattr(bd, blockname, undefined_block_factory)

        # add a clone of the options
        # bd.options = copy.copy(self.options)
        bd.runtime = self

        return bd

    def DEBUG(self, debug, fmt, *args) -> None:
        context: SimulationContext | None = self._get_context()
        assert self.options is not None
        options: OptionsBase = context.options if context is not None else self.options
        if debug[0] in options.debug:
            print(f"DEBUG.{debug:s}: " + fmt.format(*args))

    def done(self, bd, block=False) -> None:
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

    def savefig(self, block, filename=None, format="pdf", **kwargs) -> None:
        block.savefig(filename=filename, format=format, **kwargs)

    def savefigs(self, bd, format="pdf", **kwargs) -> None:
        from bdsim.block_types import GraphicsBlock

        for b in bd.blocklist:
            if isinstance(b, GraphicsBlock):
                b.savefig(filename=b.name, format=format, **kwargs)

    def showgraph(self, bd, **kwargs) -> None:
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

    def fatal(self, message, retval=1) -> NoReturn:
        """
        Fatal simulation error

        :param message: Error message
        :type message: str
        :param retval: system return value (*nix only) defaults to 1
        :type retval: int, optional

        Display the error message then terminate the process.  For operating
        systems that support it, return an integer code.
        """
        # TODO print text in some color
        print(message)
        sys.exit(retval)

    def load_blocks(self, verbose=True, toolboxes=True) -> dict[str, dict[str, Any]]:
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

        def parse_docstring(ds):
            # this should have two versions: sphinx, numpy doc styles
            import re
            from collections import OrderedDict

            re_isfield: re.Pattern[str] = re.compile(r"\s*:[a-zA-Zα-ωΑ-Ω0-9_ ]+:")
            re_field: re.Pattern[str] = re.compile(
                r"^\s*:(?P<field>[a-zA-Z]+)(?:"
                r" +(?P<var>[a-zA-Zα-ωΑ-Ω0-9_]+))?:(?P<body>.+)$"
            )

            # a-zA-Zα-ωΑ-Ω0-9_
            def indent(s) -> int:
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
            packages: list[str] = ["bdsim"]
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
            bdsim.blocks.functions..................: Sum Prod Gain Clip Function Interpolate
            bdsim.blocks.sources....................: Constant Time WaveForm Piecewise Step Ramp
            bdsim.blocks.sinks......................: Print Stop Null Watch
            bdsim.blocks.transfers..................: Integrator PoseIntegrator LTI_SS LTI_SISO
            bdsim.blocks.discrete...................: ZOH DIntegrator DPoseIntegrator
            bdsim.blocks.linalg.....................: Inverse Transpose Norm Flatten Slice2 Slice1 Det Cond
            bdsim.blocks.displays...................: Scope ScopeXY ScopeXY1
            bdsim.blocks.connections................: Item Dict Mux DeMux Index SubSystem InPort OutPort
            roboticstoolbox.blocks.arm..............: FKine IKine Jacobian Tr2Delta Delta2Tr Point2Tr TR2T FDyn IDyn Gravload
            ........................................: Inertia Inertia_X FDyn_X ArmPlot Traj JTraj LSPB CTraj CirclePath
            roboticstoolbox.blocks.mobile...........: Bicycle Unicycle DiffSteer VehiclePlot
            roboticstoolbox.blocks.uav..............: MultiRotor MultiRotorMixer MultiRotorPlot
            machinevisiontoolbox.blocks.camera......: Camera Visjac_p EstPose_p ImagePlane
        """

        def dots(s, n=40):
            return s + "." * (n - len(s))

        assert self._blocklibrary is not None
        assert self.moduledicts is not None
        print(len(self._blocklibrary), " blocks loaded")
        for pkg, module_dict in self.moduledicts.items():
            for k, v in module_dict.items():
                line: str = ""
                once = False
                while len(v) > 0:
                    n: str = v.pop(0) + " "
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

    def set_options(self, **options) -> None:
        assert self.options is not None
        self.options.set(**options)
        warnings.warn("use sim.options.OPT=VALUE instead", DeprecationWarning)

    def set_globals(self, globs) -> None:
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

    def report(self, bd, type="summary", **kwargs) -> None:
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
    def __init__(self, sysargs=True, **options) -> None:
        default_options: dict[str, Any] = {
            "backend": None,
            "tiles": "3x4",
            "graphics": True,
            "animation": False,
            "hold": True,
            "shape": None,
            "altscreen": True,
            "progress": True,
            "verbose": False,
            "debug": "",
            "simtime": None,
            "blocks": False,
            "outfile": None,
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

        unknownargs: list[str] = []
        if sysargs:
            # command line arguments and graphics
            parser = argparse.ArgumentParser(
                prefix_chars="-+",
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                description="Block diagram simulation framework",
                epilog=(
                    "set defaults using environment variable BDSIM as a single string"
                    " containing command line options"
                ),
            )
            parser.add_argument(
                "--backend",
                "-b",
                type=str,
                metavar="BACKEND",
                help="matplotlib backend to choose",
            )
            parser.add_argument(
                "--tiles",
                "-t",
                type=str,
                metavar="ROWSxCOLS",
                help="window tiling as NxM",
            )
            parser.add_argument(
                "--shape",
                type=str,
                metavar="WIDTHxHEIGHT",
                help="window size as WxH, defaults to matplotlib default",
            )
            parser.add_argument(
                "--blocks",
                action="store_const",
                const=True,
                default=False,
                dest="blocks",
                help="Display blocks at startup",
            )

            parser.add_argument(
                "-g",
                "--no-graphics",
                action="store_const",
                const=False,
                dest="graphics",
                help="disable graphic display, also does --no-animation",
            )
            parser.add_argument(
                "+g",
                "--graphics",
                action="store_const",
                const=True,
                dest="graphics",
                help="enable graphic display",
            )

            parser.add_argument(
                "-a",
                "--no-animation",
                action="store_const",
                const=False,
                dest="animation",
                help="do not animate graphics",
            )
            parser.add_argument(
                "+a",
                "--animation",
                action="store_const",
                const=True,
                dest="animation",
                help="animate graphics, also does ++graphics",
            )

            parser.add_argument(
                "-H",
                "--no-hold",
                action="store_const",
                const=False,
                dest="hold",
                help="do not hold graphics in done()",
            )
            parser.add_argument(
                "+H",
                "--hold",
                action="store_const",
                const=True,
                dest="hold",
                help="hold graphics in done()",
            )

            parser.add_argument(
                "+A",
                "--altscreen",
                action="store_const",
                const=True,
                dest="altscreen",
                help="display plots on second monitor",
            )
            parser.add_argument(
                "-A",
                "--no-altscreen",
                action="store_const",
                const=False,
                dest="altscreen",
                help="do not display plots on second monitor",
            )

            parser.add_argument(
                "--no-progress",
                "-p",
                action="store_const",
                const=False,
                dest="progress",
                help="animate graphics",
            )
            parser.add_argument(
                "--verbose", "-v", action="store_const", const=True, help="debug flags"
            )
            parser.add_argument(
                "--debug",
                "-d",
                type=str,
                metavar="[psd]",
                help="debug flags: p/ropagate, s/tate, d/eriv, i/nteractive",
            )
            parser.add_argument(
                "--simtime", "-S", type=str, help="simulation time: T or T,dt"
            )
            parser.add_argument(
                "--quiet",
                "-q",
                action="store_const",
                const=True,
                help="suppress reports",
            )
            parser.add_argument(
                "-o",
                action="store_const",
                const="bd.out",
                dest="outfile",
                help="output pickled simulation results to bd.out",
            )
            parser.add_argument(
                "--out",
                type=str,
                dest="outfile",
                help="file to save pickled simulation results",
            )
            parser.add_argument(
                "--set",
                "-s",  # NOTE: clashes with `unittest discover -s <startdir>`; use pytest or --start-directory instead
                dest="setparam",
                action="append",
                type=str,
                help="override block parameter using block:param=value",
            )
            parser.add_argument(
                "--global",
                dest="setglob",
                action="append",
                type=str,
                help="override global parameter using var=value",
            )

            args, unknownargs = parser.parse_known_args()
            cmdline_options: dict[str, Any] = vars(args)  # get args as a dictionary
            # keep only the options that are not None, ie. those that were
            # explicitly set on the command line
            cmdline_options = {
                option: value
                for option, value in cmdline_options.items()
                if value is not None
            }

            if "graphics" in cmdline_options:
                # -g or +g present
                if not cmdline_options["graphics"]:
                    # -g then disable animation
                    cmdline_options["animation"] = False
            elif "animation" in cmdline_options and cmdline_options["animation"]:
                # +a present
                cmdline_options["graphics"] = True
        else:
            cmdline_options = dict()  # empty dictionary

        super().__init__(readonly=cmdline_options, args=default_options)

        # now handle the passed options
        self.set(**options)

        if self.verbose:
            print(self)

        self._argv: list[str] = unknownargs  # save non-bdsim arguments

    def sanity(self, options):
        # ensure graphics is enabled if animation is requested
        # ensure animation is disabled if graphics is disabled
        if "graphics" in options and "animation" in options:
            if options["animation"] and not options["graphics"]:
                raise ValueError("cannot enable animation but disable graphics")
        elif "graphics" in options and not options["graphics"]:
            options["animation"] = False
        elif "animation" in options and options["animation"]:
            options["graphics"] = True

        return options
