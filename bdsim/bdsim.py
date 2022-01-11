import os
from pathlib import Path
import sys
import importlib
import inspect
from collections import Counter, namedtuple
from typing import NamedTuple
import argparse
import types
from bdsim.components import *
from bdsim.blockdiagram import BlockDiagram
import copy
import tempfile
import subprocess
import webbrowser

import numpy as np
import scipy.integrate as integrate
import re
from colored import fg, attr


block = namedtuple('block', 'name, cls, path')

# convert class name to BLOCK name
# strip underscores and capitalize
def blockname(name):
    return name.upper()


# print a progress bar
# https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
def printProgressBar (fraction, prefix='', suffix='', decimals=1, length=50, fill = '█', printEnd = "\r"):

    percent = ("{0:." + str(decimals) + "f}").format(fraction * 100)
    filledLength = int(length * fraction)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)


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

        self.x = None           # continuous state vector numpy.ndarray
        self.T = None           # maximum.BlockDiagram time
        self.t = None           # current time
        self.fignum = 0
        self.stop = None
        self.checkfinite = True

        self.debugger = True
        self.t_stop = None  # time-based breakpoint
        self.eventq = PriorityQ()

    def declare_event(self, block, t):
        self.eventq.push((t, block))

class BDSim:

    _blocklibrary = None

    def __init__(self, packages=None, **kwargs):
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
        self._init_options(**kwargs)
        # load modules from the blocks folder
        if BDSim._blocklibrary is None:
            BDSim._blocklibrary = self.load_blocks(self.options.verbose)

    def __str__(self):
        """
        String representation of simulation

        :return: single line summary of simulation environment
        :rtype: str
        """
        s = f"BDSim: {len(self._blocklibrary)} blocks in library\n"
        return s
        
    
    def __repr__(self):
        s = str(self)
        for k, v in self.options._asdict().items():
            s += '  {:s}: {}\n'.format(k, v)
        return s

    def progress(self, t=None):
        """
        Update progress bar

        :param t: current simulation time, defaults to None
        :type t: float, optional

        Update progress bar as a percentage of the maximum simulation time,
        given as an argument to ``run``.

        :seealso: :meth:`run` :meth:`progress_done`
        """
        if self.options.progress:
            if t is None:
                t = self.state.t
            printProgressBar(t / self.state.T, prefix='Progress:', suffix='complete', length=60)

    def progress_done(self):
        """
        Clean up progress bar
        """
        if self.options.progress:
            print('\r' + ' '* 90 + '\r')

    def run(self, bd, T=5, dt=0.01, solver='RK45', solver_args={}, debug='',
            block=None, checkfinite=True, minstepsize=1e-12, watch=[],
            ):
        """
        Run the block diagram
        
        :param T: maximum integration time, defaults to 10.0
        :type T: float, optional
        :param dt: maximum time step, defaults to 0.1
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
        
        assert bd.compiled, 'Network has not been compiled'

        # get simulation time
        #  --simtime=T  or --simtime=T,dt
        try:
            default_times = eval(self.option('simtime'))
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
        state.dt = dt
        state.count = 0
        state.solver = solver
        state.solver_args = solver_args
        state.minstepsize = minstepsize
        state.stop = None # allow any block to stop.BlockDiagram by setting this to the block's name
        state.checkfinite = checkfinite
        state.options = copy.copy(self.options)
        self.bd = bd
        state.t_stop = None
        if debug:
            # append debug flags
            if debug not in state.options.debug:
                state.options.debug += debug
        
        # turn off progress bar if any debug options are given
        if len(state.options.debug) > 0:
            self.set_options(progress = False)

        # process the watchlist
        #  elements can be:
        #   - block or Plug reference
        #   - str in the form BLOCKNAME[PORT]
        watchlist = []
        watchnamelist = []
        re_block = re.compile(r'(?P<name>[^[]+)(\[(?P<port>[0-9]+)\])')
        for w in watch:
            if isinstance(w, str):
                # a name was given, with optional port number
                m = re_block.match(w)
                if m is None:
                    raise ValueError('watch block[port] not found: ' + w)
                name = m.group('name')
                port = int(m.group('port'))
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
        print('initial state  x0 = ', x0)

        # get the number of discrete states from all clocks
        ndstates = 0
        for clock in bd.clocklist:
            nds = 0
            for b in clock.blocklist:
                nds += b.ndstates
            ndstates += nds
            print(clock.name, 'initial dstate x0 = ', clock.getstate())

        # tell all blocks we're starting a BlockDiagram
        self.bd.start(state=state, graphics=self.state.options.graphics)

        # initialize list of time and states
        state.tlist = []
        state.xlist = []
        state.plist = [[] for p in state.watchlist]

        self.progress(0)

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

        self.progress_done()  # cleanup the progress bar

        # print some info about the integration
        print(fg('yellow'))
        print(f"integrator steps:      {state.count}")
        print(f"time steps:            {len(state.tlist)}")
        print(f"integration intervals: {nintervals}")
        print(attr(0))

        # save buffered data in a Struct
        out = Struct('results')
        out.t = np.array(state.tlist)
        out.x = np.array(state.xlist)
        out.xnames = bd.statenames

        # save clocked states
        for c in bd.clocklist:
            name = c.name.replace('.', '')
            clockdata = Struct(name)
            clockdata.t = np.array(c.t)
            clockdata.x = np.array(c.x)
            out.add(name, clockdata)

        # save the watchlist into variables named y0, y1 etc.
        for i, p in enumerate(watchlist):
            out['y'+str(i)] = np.array(state.plist[i])
        out.ynames = watchnamelist

        # pause until all graphics blocks close
        self.done(self.bd, block=self.options.hold)

        return out

    def done(self, bd, block=False):

        if 'hold' in self.cmd_options:
            block = self.cmd_options['hold']

        plt.show(block=block)
        bd.done(graphics=self.options.graphics)
        
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

                scipy_integrator = integrate.__dict__[state.solver]  # get user specified integrator

                def ydot(t, y):
                    state.t = t
                    return bd.evaluate_plan(y, t)

                if state.dt is not None:
                    state.solver_args['max_step'] = state.dt

                print(f"run interval: from {t0} to {t0+T}, args={state.solver_args}, {x0=}")
                integrator = scipy_integrator(ydot,
                    t0=t0, y0=x0, t_bound=T, **state.solver_args)

                # integrate
                while integrator.status == 'running':

                    # step the integrator, calls _deriv and evaluate block diagram multiple times
                    message = integrator.step()

                    if integrator.status == 'failed':
                        print(fg('red') + f"\nintegration completed with failed status: {message}" + attr(0))
                        break

                    # stash the results
                    state.tlist.append(integrator.t)
                    state.xlist.append(integrator.y)
                    
                    # record the ports on the watchlist
                    for i, p in enumerate(state.watchlist):
                        state.plist[i].append(p.block.output(integrator.t)[p.port])
                    
                    # # update all blocks that need to know
                    bd.step(state=self.state)

                    self.progress()  # update the progress bar

                    if integrator.status == 'finished':
                        break

                    # has any block called a stop?
                    if state.stop is not None:
                        print(fg('red') + f"\n--- stop requested at t={state.t:.4f} by {state.stop}" + attr(0))
                        break

                    if state.minstepsize is not None and integrator.step_size < state.minstepsize:
                        print(fg('red') + f"\n--- stopping on minimum step size at t={state.t:.4f} with last stepsize {integrator.step_size:g}" + attr(0))
                        break

                    if 'i' in state.options.debug:
                        bd._debugger(integrator)

                return integrator.y  # return final state vector

            elif len(clocklist) == 0:
                # block diagram has no continuous or discrete states
    
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

                    self.progress()  # update the progress bar

                        
                    # has any block called a stop?
                    if state.stop is not None:
                        print(fg('red') + f"\n--- stop requested at t={state.t:.4f} by {state.stop}" + attr(0))
                        break

                    if 'i' in state.options.debug:
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

                self.progress()  # update the progress bar

                # has any block called a stop?
                if state.stop is not None:
                    print(fg('red') + f"\n--- stop requested at t={bd.simstate.t:.4f} by {bd.simstate.stop}" + attr(0))

                if 'i' in state.options.debug:
                    bd._debugger(state=state)

        except RuntimeError as err:
            # bad things happens, print a message and return no result
            print('unrecoverable error in evaluation: ', err)
            raise

    def blockdiagram(self, name='main'):
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
            f = new_method(info['class'], bd)
            
            # set a bound version of this function as an attribute of the instance
            # method = types.MethodType(new_method, bd)
            # setattr(bd, block.name, method)
            setattr(bd, blockname, f.__get__(self))

        # add a clone of the options
        bd.options = copy.copy(self.options)

        return bd

    def closefigs(self):
        for i in range(self.simstate.fignum):
            print('close', i+1)
            plt.close(i+1)
            plt.pause(0.1)
        self.simstate.fignum = 0  # reset figure counter
            
    def savefig(self, block, filename=None, format='pdf', **kwargs):
        block.savefig(filename=filename, format=format, **kwargs)

    def savefigs(self, bd, format='pdf', **kwargs):
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
        
        packages = ['bdsim', 'roboticstoolbox', 'machinevisiontoolbox']
        env = os.getenv('BDSIMPATH')
        if env is not None:
            packages.append(env.split)
        if self.packages is not None:
            packages.append(self.packages.split(':'))

        blocks = {}
        moduledicts = {}
        for package in packages:
            try:
                spec = importlib.util.find_spec('.blocks', package=package)
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
                if name.endswith('Block'):
                    continue

                if value.blockclass in ('source', 'transfer', 'function'):
                    # must have an output function
                    valid = hasattr(value, 'output') and \
                            callable(value.output) and \
                            len(inspect.signature(value.output).parameters) == 2
                    if not valid:
                        raise ImportError('class {:s} has missing/improper output method'.format(str(value)))
                    
                if value.blockclass == 'sink':
                    # must have a step function with at least one
                    # parameter: step(self [,state])
                    valid = hasattr(value, 'step') and \
                            callable(value.step) and \
                            len(inspect.signature(value.step).parameters) >= 1
                    if not valid:
                        raise ImportError('class {:s} has missing/improper step method'.format(str(value)))


                # add it to the dict of blocks indexed by module
                if value.__module__ in moduledict:
                    moduledict[value.__module__].append(name)
                else:
                    moduledict[value.__module__] = [name]

                # create a dict for the block with metadata
                block_info = {}
                block_info['path'] = pkg.__path__  # path to folder holding block definition
                block_info['classname'] = name
                block_info['blockname'] = blockname(name)

                try:
                    block_info['url'] = pkg.__dict__['url'] + "#" \
                            + block.__module__ + "." + name
                except KeyError:
                    block_info['url'] = None
                    
                block_info['class'] = value
                block_info['module'] = value.__module__
                block_info['package'] = package
                block_info['doc'] = block.__init__.__doc__ #inspect.getdoc(block)
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
            return s + '.' * (n - len(s))

        print(len(self._blocklibrary), ' blocks loaded')
        for pkg, dict in self.moduledicts.items():
            for k, v in dict.items():
                s = ''
                once = False
                while len(v) > 0:
                    n = v.pop(0) + ' '
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
                        s = ''
                if len(s) > 0:
                    if once:
                        print(f"{dots('')}: {s}")
                    else:
                        print(f"{dots(k)}: {s}")

    @property
    def options(self):
        """
        Return current options.

        :return: current options
        :rtype: namedtuple

        Return an immutable named tuple containing the current options, 
        for example::

                sim.options.graphics

        The option are determined from a merge of two dictionaries:
        - command line options (higheset precedence)
        - program options from constructor or ``set_options``.

        :seealso: :meth:`set_options` :meth:`__init__`
        """
        return self._options

    def option(self, option, default=None):
        """
        Return value of particular option

        :param option: option name
        :type option: str
        :param default: default value
        :type default: any
        :return: value of option
        :rtype: any

        If the ``option`` has been overridden by command line option, return
        that value, otherwise the ``default`` value.
        """
        if option in self.cmd_options:
            return self.cmd_options[option]
        else:
            return default

    def set_options(self, **options):
        """
        Set simulation options at run time

        The options are the same as those for the constructor, for example:

            sim = bdsim.BDsim()
            sim.set_options(graphics=False)

        or::

            sim = bdsim.BDsim(graphics=False)

        Command line options override program set options.

        :seealso: :meth:`__init__`
        """
        for key, value in options.items():
            self.prog_options[key] = value

        # animation and graphics options are coupled
        #
        #  graphics False, no graphics at all
        #  graphics True, animation False, show graphs at end of run
        #  graphics True, animation True, animate graphs during the run

        optdict = {**self.prog_options, **self.cmd_options}

        if optdict['animation']:
            optdict['graphics'] = True
        if not optdict['graphics']:
            optdict['animation'] = False
        self._options = self.opt_tuple(**optdict)

    def _init_options(self, sysargs=True, **unused):
        self.prog_options = {
            'backend': 'Qt5Agg',  # 'TkAgg',
            'tiles': '3x4',
            'graphics': True,
            'animation': False,
            'hold':  True,
            'shape': None,
            'altscreen': True,
            'progress': True,
            'verbose': False,
            'debug': '',
            'simtime': None,
            }
        self.opt_tuple = namedtuple('bdsim_options', self.prog_options.keys())

        # option priority (high to low):
        #  - command line
        #  - argument to BDSim()
        #  - defaults
        # all switches and their default values
        
        # any passed kwargs can override the defaults

        if sysargs:
            # command line arguments and graphics
            parser = argparse.ArgumentParser(
                prefix_chars='-+',
                    formatter_class=argparse.ArgumentDefaultsHelpFormatter
                    )
            parser.add_argument('--backend', '-b', type=str, metavar='BACKEND',
                help='matplotlib backend to choose')
            parser.add_argument('--tiles', '-t', type=str, metavar='ROWSxCOLS',
                help='window tiling as NxM')
            parser.add_argument('--shape', type=str, metavar='WIDTHxHEIGHT',
                help='window size as WxH, defaults to matplotlib default')

            parser.add_argument('-g', '--no-graphics',
                action='store_const', const=False, dest='graphics',
                help='disable graphic display, also does --no-animation')
            parser.add_argument('+g', '--graphics',
                action='store_const', const=True, dest='graphics',
                help='enable graphic display')

            parser.add_argument('-a', '--no-animation',
                action='store_const', const=False, dest='animation',
                help='do not animate graphics')
            parser.add_argument('+a', '--animation',
                action='store_const', const=True, dest='animation',
                help='animate graphics, also does ++graphics')

            parser.add_argument('-H', '--no-hold',
                action='store_const', const=False, dest='hold',
                help='do not hold graphics in done()')
            parser.add_argument('+H', '--hold',
                action='store_const', const=True, dest='hold',
                help='hold graphics in done()')

            parser.add_argument('+A', '--altscreen',
                action='store_const', const=True, dest='altscreen',
                help='display plots on second monitor')
            parser.add_argument('-A', '--no-altscreen',
                action='store_const', const=False, dest='altscreen',
                help='do not display plots on second monitor')

            parser.add_argument('--no-progress', '-p', 
                action='store_const', const=False, dest='progress',
                help='animate graphics')
            parser.add_argument('--verbose', '-v', 
                action='store_const', const=True,
                help='debug flags')
            parser.add_argument('--debug', '-d', type=str, metavar='[psd]',
                help='debug flags: p/ropagate, s/tate, d/eriv, i/nteractive')
            parser.add_argument('--simtime', '-S', type=str,
                help='simulation time: T or T,dt')

            args, unknownargs = parser.parse_known_args()
            options = vars(args)  # get args as a dictionary
            self.argv = unknownargs

        # print(options)
        # ensure graphics is enabled if animation is requested
        if options['animation']:
            options['graphics'] = True

        if options['verbose']:
            for k, v in options.items():
                print('{:10s}: {:}'.format(k, v))
        
        # stash these away
        optdict = {}
        for k, v in args._get_kwargs():
            if v is not None:
                optdict[k] = v

        self.cmd_options = optdict


        self.set_options(**unused)
