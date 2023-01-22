import os
from pathlib import Path
import sys
import importlib
import inspect
from collections import Counter, namedtuple
import argparse
import types
import warnings

from bdsim.blockdiagram import BlockDiagram
from bdsim.components import OptionsBase, Block, Clock, BDStruct, Plug, clocklist
import tempfile
import subprocess
import webbrowser

import numpy as np
import scipy.integrate as integrate
import matplotlib.pyplot as plt
import re
from colored import fg, attr

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
    ):

        percent = ("{0:." + str(decimals) + "f}").format(fraction * 100)
        filledLength = int(length * fraction)
        bar = fill * filledLength + "-" * (length - filledLength)
        print(f"\r{prefix} |{bar}| {percent}% {suffix}", end=printEnd)

    def __init__(self, enable=True):
        self.enable = enable
        self.length = 60
        if not enable:
            return

    def start(self, T):

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

    def end(self):
        """
        Clean up progress bar
        """
        if not self.enable:
            return

        if _FillingCirclesBar:
            self.bar.finish()
        else:
            print("\r" + " " * (self.length + 20) + "\r")

    def update(self, t):
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


class TimeQ:
    """
    Time-ordered queue for events

    The list comprises tuples of (time, block) to reflect an event associated
    with the specified block at the specified time.

    The list is not ordered, and is sorted on a pop event.
    """

    def __init__(self):
        self.q = []
        self.dirty = False

    def __len__(self):
        """
        Length of time-ordered queue

        :return: number of items in the queue
        :rtype: int
        """
        return len(self.q)

    def __str__(self):
        """
        String representation of time-ordered queue

        :return: show length and first item
        :rtype: str
        """
        if len(self) == 0:
            return f"TimeQ: len={len(self)}"
        else:
            return f"TimeQ: len={len(self)}, first out {self.q[0]}"

    def __repr__(self):
        return str(self)

    def push(self, value):
        """
        Push value onto time-ordered queue

        :param value: tuple (time, block)
        :type value: tuple

        Push a block and a time onto the queue.
        """
        self.q.append(value)
        self.dirty = True

    def pop(self, dt=0):
        """
        Pop nearest items from the time-ordered queue

        :param dt: time window, defaults to 0
        :type dt: float, optional
        :return: time of first block in queue and a list of blocks within the time window
        :rtype: float, list

        The next block is popped from the queue and all blocks in the time
        window, that occur no more than ``dt`` later, are also popped.
        """
        if len(self) == 0:
            return None, []

        if self.dirty:
            self.q.sort(key=lambda x: x[0])
            self.dirty = False

        qfirst = self.q.pop(0)
        t = qfirst[0]
        blocks = [qfirst[1]]
        while len(self.q) > 0 and self.q[0][0] < (t + dt):
            blocks.append(self.q.pop(0)[1])
        return t, blocks

    def pop_until(self, t):
        """
        Pop nearest items from time-ordered queue

        :param t: time
        :type t: float
        :return: list of blocks remaining sorted by receding time
        :rtype: list

        Pops all items with time less than or equal to ``t``.
        """
        if len(self) == 0:
            return []

        if self.dirty:
            self.q.sort(key=lambda x: x[0])
            self.dirty = False

        i = 0
        while True:
            if self.q[i][0] > t:
                out = self.q[:i]
                self.q = self.q[i:]
                return out
            i += 1


# convert class name to BLOCK name
# strip underscores and capitalize
def blockname(name):
    return name.upper()


class BDSimState:

    """
    :ivar x: state vector
    :vartype x: np.ndarray
    :ivar T: maximum simulation time (seconds)
    :vartype T: float
    :ivar t: current simulation time (seconds)
    :vartype t: float
    :ivar fignum: number of next matplotlib figure to create
    :vartype fignum: int
    :ivar stop: reference to block wanting to stop simulation, else None
    :vartype stop: Block subclass
    :ivar checkfinite: halt simulation if any wire has inf or nan
    :vartype checkfinite: bool
    :ivar graphics: enable graphics
    :vartype graphics: bool
    """

    def __init__(self):

        self.x = None  # continuous state vector numpy.ndarray
        self.T = None  # maximum.BlockDiagram time
        self.t = None  # current time
        self.fignum = 0
        self.stop = None
        self.checkfinite = True

        self.debugger = True
        self.t_stop = None  # time-based breakpoint
        self.eventq = TimeQ()

    def declare_event(self, block, t):
        self.eventq.push((t, block))


class BDSim:

    _blocklibrary = None

    def __init__(self, packages=None, load=True, **kwargs):
        """
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
        --no-hold, -h        hold       True      do not hold graphics in done()
        --no-progress, -p    progress   True      do not display simulation progress bar
        --backend BE         backend    'Qt5Agg'  matplotlib backend
        --tiles RxC, -t RxC  tiles      '3x4'     arrangement of figure tiles on the display
        --shape WxH          shape      None      window size, default matplotlib size
        --altscreen          altscreen  True      use secondary monitor if it exists
        --verbose, -v        verbose    False     be verbose
        --debug F, -d F      debug      ''        debug flag string
        --simtime T[,dt]     simtime    (10,)     simulation time
        ===================  =========  ========  ===========================================

        .. note:: ``animation`` and ``graphics`` options are coupled.  If
            ``graphics=False``, all graphics is suppressed.  If
            ``graphics=True`` then graphics are shown and the behaviour depends
            on ``animation``.  ``animation=False`` shows graphs at the end of
            the simulation, while ``animation=True` will animate the graphs
            during simulation.

        :seealso: :meth:`set_options`
        """

        self.packages = packages

        # process command line and overall options
        self.options = Options(**kwargs)
        # load modules from the blocks folder
        if BDSim._blocklibrary is None and load:
            BDSim._blocklibrary = self.load_blocks(self.options.verbose)
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
            return self._blocklibrary[block]

    def __str__(self):
        """
        String representation of simulation

        :return: single line summary of simulation environment
        :rtype: str
        """
        s = f"BDSim: {len(self._blocklibrary)} blocks in library\n"
        return s

    def __repr__(self):
        s = f"Block diagram simulation runtime, {len(self._blocklibrary)} blocks imported to library.\n"
        s += "simulation options:\n"
        for k, v in self.state.options.items():
            s += "  {:s}: {}\n".format(k, v)
        return s

    def run(
        self,
        bd,
        T=5,
        dt=None,
        solver="RK45",
        solver_args={},
        debug="",
        block=None,
        checkfinite=True,
        minstepsize=1e-12,
        watch=[],
    ):
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

        # get simulation time
        #  --simtime=T  or --simtime=T,dt
        try:
            default_times = eval(self.option("simtime"))
            if isinstance(default_times, (int, float)):
                T = default_times
            else:
                T, dt = default_times
        except:
            pass

        # final default values
        # T = T or 5
        # dt = dt or 0.01

        state = BDSimState()
        self.state = state
        state.T = T

        if dt is None and not "max_step" in solver_args:
            dt = T / 100
        state.dt = dt
        state.count = 0
        state.solver = solver
        state.solver_args = solver_args
        state.minstepsize = minstepsize
        state.stop = None  # allow any block to stop.BlockDiagram by setting this to the block's name
        state.checkfinite = checkfinite
        # state.options = copy.copy(self.options)
        state.options = self.options
        self.bd = bd
        state.t_stop = None
        if debug:
            # append debug flags
            if debug not in state.options.debug:
                state.options.debug += debug

        # turn off progress bar if any debug options are given
        if len(state.options.debug) > 0:
            self.options.progress = False
        if block is not None:
            self.options.hold = block

        # process the watchlist
        #  elements can be:
        #   - block or Plug reference
        #   - str in the form BLOCKNAME[PORT]
        watchlist = []
        watchnamelist = []
        re_block = re.compile(r"(?P<name>[^[]+)(\[(?P<port>[0-9]+)\])")
        for w in watch:
            if isinstance(w, str):
                # a name was given, with optional port number
                m = re_block.match(w)
                if m is None:
                    raise ValueError("watch block[port] not found: " + w)
                name = m.group("name")
                port = int(m.group("port"))
                b = bd.blocknames[name]
                plug = b[port]
            elif isinstance(w, Block):
                # a block was given, defaults to port 0
                plug = w[0]
            elif isinstance(w, Plug):
                # a plug was given
                plug = w
            watchlist.append(plug)
            watchnamelist.append(str(plug))
        state.watchlist = watchlist
        state.watchnamelist = watchnamelist

        x0 = bd.getstate0()
        print("initial state  x0 = ", x0)

        # get the number of discrete states from all clocks
        ndstates = 0
        for clock in bd.clocklist:
            nds = 0
            for b in clock.blocklist:
                nds += b.ndstates
            ndstates += nds
            print(clock.name, "initial dstate x0 = ", clock.getstate())

        # tell all blocks we're starting a BlockDiagram
        self.bd.start(state=state, graphics=self.state.options.graphics)

        # initialize list of time and states
        state.tlist = []
        state.xlist = []
        state.plist = [[] for p in state.watchlist]

        self.progress = Progress(enable=self.options.progress)
        self.progress.start(T)

        if len(self.state.eventq) == 0:
            # no simulation events, solve it in one go
            self.run_interval(bd, 0, T, x0, state=state)
            nintervals = 1
        else:
            # we have simulation events, solve it in chunks
            self.state.declare_event(None, T)  # add an event at end of simulation

            # ignore all the events at zero
            tprev = 0
            self.state.eventq.pop_until(tprev)

            # get the state vector
            x = x0

            nintervals = 0
            while True:
                # get next event from the queue and the list of blocks or
                # clocks at that time
                tnext, sources = self.state.eventq.pop(dt=1e-6)
                if tnext is None:
                    break
                # run system until next event time
                x = self.run_interval(bd, tprev, tnext, x, state=state)
                nintervals += 1

                # visit all the blocks and clocks that have an event now
                for source in sources:
                    if isinstance(source, Clock):
                        # clock ticked, save its state
                        clock.savestate(tnext)
                        clock.next_event(self.state)

                        # get the new state
                        clock._x = clock.getstate()
                tprev = tnext

                # are we done?
                if state.t is not None and state.t >= T:
                    break

        # finished integration

        self.progress.end()  # cleanup the progress bar

        # print some info about the integration
        print(fg("yellow"))
        print(f"integrator steps:      {state.count}")
        print(f"time steps:            {len(state.tlist)}")
        print(f"integration intervals: {nintervals}")
        print(attr(0))

        # save buffered data in a Struct
        out = BDStruct(name="results")
        out.t = np.array(state.tlist)
        out.x = np.array(state.xlist)
        out.xnames = bd.statenames

        # save clocked states
        for c in bd.clocklist:
            name = c.name.replace(".", "")
            clockdata = BDStruct(name)
            clockdata.t = np.array(c.t)
            clockdata.x = np.array(c.x)
            out.add(name, clockdata)

        # save the watchlist into variables named y0, y1 etc.
        for i, p in enumerate(watchlist):
            out["y" + str(i)] = np.array(state.plist[i])
        out.ynames = watchnamelist

        # pause until all graphics blocks close
        if self.options.graphics:
            self.done(self.bd, block=self.options.hold)

        return out

    def run_interval(self, bd, t0, T, x0, state):
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
        try:
            if bd.nstates > 0:
                # system has continuous states, solve it using numerical integration
                # print('initial state x0 = ', x0)

                # block diagram contains states, solve it using numerical integration

                scipy_integrator = integrate.__dict__[
                    state.solver
                ]  # get user specified integrator

                def ydot(t, y):
                    state.t = t
                    state.count += 1
                    return bd.evaluate_plan(y, t)

                if state.dt is not None:
                    state.solver_args["max_step"] = state.dt

                # print(f"run interval: from {t0} to {t0+T}, args={state.solver_args}, x0={x0}")
                integrator = scipy_integrator(
                    ydot, t0=t0, y0=x0, t_bound=T, **state.solver_args
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
                    state.tlist.append(integrator.t)
                    state.xlist.append(integrator.y)

                    # record the ports on the watchlist
                    for i, p in enumerate(state.watchlist):
                        state.plist[i].append(p.block.output(integrator.t)[p.port])

                    # # update all blocks that need to know
                    bd.step(state=self.state)

                    self.progress.update(self.state.t)  # update the progress bar

                    if integrator.status == "finished":
                        break

                    # has any block called a stop?
                    if state.stop is not None:
                        print(
                            fg("red")
                            + f"\n--- stop requested at t={state.t:.4f} by {state.stop}"
                            + attr(0)
                        )
                        break

                    if (
                        state.minstepsize is not None
                        and integrator.step_size < state.minstepsize
                    ):
                        print(
                            fg("red")
                            + f"\n--- stopping on minimum step size at t={state.t:.4f} with last stepsize {integrator.step_size:g}"
                            + attr(0)
                        )
                        break

                    if "i" in state.options.debug:
                        bd._debugger(integrator)

                return integrator.y  # return final state vector

            elif len(clocklist) == 0:
                # block diagram has no continuous or discrete states

                assert dt is not None, "if no states must specify dt"

                for t in np.arange(t0, T, state.dt):  # step through the time range
                    # evaluate the block diagram
                    state.t = t
                    bd.evaluate_plan([], t)

                    # stash the results
                    state.tlist.append(t)

                    # record the ports on the watchlist
                    for i, p in enumerate(state.watchlist):
                        state.plist[i].append(p.block.output(t)[p.port])

                    # update all blocks that need to know
                    bd.step(state=state)

                    self.progress.update(self.state.t)  # update the progress bar

                    # has any block called a stop?
                    if state.stop is not None:
                        print(
                            fg("red")
                            + f"\n--- stop requested at t={state.t:.4f} by {state.stop}"
                            + attr(0)
                        )
                        break

                    if "i" in state.options.debug:
                        bd._debugger(integrator)

            else:
                # block diagram has no continuous states
                t = t0
                state.t = t
                # evaluate the block diagram
                bd.evaluate_plan([], t)

                # stash the results
                state.tlist.append(t)

                # record the ports on the watchlist
                for i, p in enumerate(state.watchlist):
                    state.plist[i].append(p.block.output(t)[p.port])

                # update all blocks that need to know
                bd.step(state=state)

                self.progress.update(self.state.t)  # update the progress bar

                # has any block called a stop?
                if state.stop is not None:
                    print(
                        fg("red")
                        + f"\n--- stop requested at t={bd.simstate.t:.4f} by {bd.simstate.stop}"
                        + attr(0)
                    )

                if "i" in state.options.debug:
                    bd._debugger(state=state)

        except RuntimeError as err:
            # bad things happens, print a message and return no result
            print("unrecoverable error in evaluation: ", err)
            raise

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
        bd = BlockDiagram(name=name)

        def new_method(cls, bd):

            # return a wrapper for the block constructor that automatically
            # adds the block to the diagram's blocklist
            def block_init_wrapper(self, *args, **kwargs):

                block = cls(*args, bd=bd, **kwargs)  # call __init__ on the block
                return block

            # return a function that invokes the class constructor
            f = block_init_wrapper

            # move the __init__ docstring to the class to allow BLOCK.__doc__
            f.__doc__ = cls.__init__.__doc__

            return f

        # bind the block constructors as new methods on this instance
        self.blockdict = {}
        for blockname, info in self._blocklibrary.items():
            # create a function to invoke the block's constructor
            f = new_method(info["class"], bd)

            # set a bound version of this function as an attribute of the instance
            # method = types.MethodType(new_method, bd)
            # setattr(bd, block.name, method)
            setattr(bd, blockname, f.__get__(self))

        # add a clone of the options
        # bd.options = copy.copy(self.options)
        bd.runtime = self

        return bd

    def DEBUG(self, debug, fmt, *args):
        if debug[0] in self.options.debug:
            print(f"DEBUG.{debug:s}: " + fmt.format(*args))

    def done(self, bd, block=False):

        if self.options.hold:
            block = self.options.hold

        try:
            plt.show(block=block)
        except KeyboardInterrupt:
            print("bdsim: closing all windows")
            sys.exit(1)
        bd.done(graphics=self.options.graphics)

    def closefigs(self):
        for i in range(self.simstate.fignum):
            print("close", i + 1)
            plt.close(i + 1)
            plt.pause(0.1)
        self.simstate.fignum = 0  # reset figure counter

    def savefig(self, block, filename=None, format="pdf", **kwargs):
        block.savefig(filename=filename, format=format, **kwargs)

    def savefigs(self, bd, format="pdf", **kwargs):
        from bdsim.graphics import GraphicsBlock

        for b in bd.blocklist:
            if isinstance(b, GraphicsBlock):
                b.savefig(filename=b.name, format=format, **kwargs)

    def showgraph(self, bd, **kwargs):
        # create the temporary dotfile
        dotfile = tempfile.TemporaryFile(mode="w")
        bd.dotfile(dotfile, **kwargs)

        # rewind the dot file, create PDF file in the filesystem, run dot
        dotfile.seek(0)
        pdffile = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        subprocess.run("dot -Tpdf", shell=True, stdin=dotfile, stdout=pdffile)

        # open the PDF file in browser (hopefully portable), then cleanup
        webbrowser.open(f"file://{pdffile.name}")
        os.remove(pdffile.name)

    def fatal(self, message, retval=1):
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

    def load_blocks(self, verbose=True):
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

            re_isfield = re.compile(r"\s*:[a-zA-Zα-ωΑ-Ω0-9_ ]+:")
            re_field = re.compile(
                "^\s*:(?P<field>[a-zA-Z]+)(?: +(?P<var>[a-zA-Zα-ωΑ-Ω0-9_]+))?:(?P<body>.+)$"
            )

            # a-zA-Zα-ωΑ-Ω0-9_
            def indent(s):
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
                m = re_field.match(line)
                if m is not None:
                    if name == "Bicycle":
                        z = 3
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

        block = namedtuple("block", "name, cls, path")

        packages = ["bdsim", "roboticstoolbox", "machinevisiontoolbox"]
        env = os.getenv("BDSIMPATH")
        if env is not None:
            packages.append(env.split)
        if self.packages is not None:
            packages.append(self.packages.split(":"))

        blocks = {}
        moduledicts = {}
        for package in packages:
            try:
                spec = importlib.util.find_spec(".blocks", package=package)
                if spec is None:
                    print(f"package {package} has no blocks module")
                    continue
                pkg = spec.loader.load_module()
            except ModuleNotFoundError:
                print(f"package {package} not found")
                continue

            moduledict = {}

            for name, value in pkg.__dict__.items():
                # check if it's a valid block class
                if not inspect.isclass(value):
                    continue
                if Block not in inspect.getmro(value):
                    continue
                if name.endswith("Block"):
                    continue

                if value.blockclass in ("source", "transfer", "function"):
                    # must have an output function
                    valid = (
                        hasattr(value, "output")
                        and callable(value.output)
                        and len(inspect.signature(value.output).parameters) == 2
                    )
                    if not valid:
                        raise ImportError(
                            "class {:s} has missing/improper output method".format(
                                str(value)
                            )
                        )

                if value.blockclass == "sink":
                    # must have a step function with at least one
                    # parameter: step(self [,state])
                    valid = (
                        hasattr(value, "step")
                        and callable(value.step)
                        and len(inspect.signature(value.step).parameters) >= 1
                    )
                    if not valid:
                        raise ImportError(
                            "class {:s} has missing/improper step method".format(
                                str(value)
                            )
                        )

                # add it to the dict of blocks indexed by module
                if value.__module__ in moduledict:
                    moduledict[value.__module__].append(name)
                else:
                    moduledict[value.__module__] = [name]

                # create a dict for the block with metadata
                block_info = {}
                block_info[
                    "path"
                ] = pkg.__path__  # path to folder holding block definition
                block_info["classname"] = name
                block_info["blockname"] = blockname(name)

                try:
                    block_info["url"] = (
                        pkg.__dict__["url"] + "#" + block.__module__ + "." + name
                    )
                except KeyError:
                    block_info["url"] = None

                block_info["class"] = value
                block_info["module"] = value.__module__
                block_info["package"] = package

                # get the docstring from the class and the constructor
                ds = ""
                if value.__doc__ is not None:
                    ds += value.__doc__
                if value.__init__.__doc__ is not None:
                    ds += value.__init__.__doc__
                if ds is None:
                    raise ValueError("block has no docstring")
                block_info["doc"] = ds
                param_dict = parse_docstring(ds)
                block_info["params"] = param_dict

                # now add all the other stuff we know about the block
                block_info["inputs"] = param_dict.get("input")
                block_info["outputs"] = param_dict.get("output")

                block_info["nin"] = value.nin
                block_info["nout"] = value.nout
                block_info["blockclass"] = value.__base__.__name__.lower().replace(
                    "block", ""
                )

                blocks[blockname(name)] = block_info

            moduledicts[package] = moduledict

        self.moduledicts = moduledicts
        return blocks

    def blocks(self):
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

        print(len(self._blocklibrary), " blocks loaded")
        for pkg, dict in self.moduledicts.items():
            for k, v in dict.items():
                s = ""
                once = False
                while len(v) > 0:
                    n = v.pop(0) + " "
                    if len(s + n) < 80:
                        s += n
                        continue
                    else:
                        # line will be too long
                        if not once:
                            print(f"{dots(k)}: {s}")
                            once = True
                        else:
                            print(f"{dots('')}: {s}")
                        s = ""
                if len(s) > 0:
                    if once:
                        print(f"{dots('')}: {s}")
                    else:
                        print(f"{dots(k)}: {s}")

    def set_options(self, **options):
        self.options.set(**options)
        warnings.warn("use sim.options.OPT=VALUE instead", DeprecationWarning)


class Options(OptionsBase):
    def __init__(self, sysargs=True, **options):

        default_options = {
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
        }

        # modify defaults according to envariable BDSIM which is comma/semicolon
        # separated list of key=value pairs
        # eg. setenv BDSIM graphics=True,hold=True
        env = os.getenv("BDSIM")
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

        if sysargs:
            # command line arguments and graphics
            parser = argparse.ArgumentParser(
                prefix_chars="-+",
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                description="Block diagram simulation framework",
                epilog="set defaults using environment variable BDSIM as a single string containing command line options",
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

            args, unknownargs = parser.parse_known_args()
            cmdline_options = vars(args)  # get args as a dictionary
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

        self._argv = unknownargs  # save non-bdsim arguments

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
