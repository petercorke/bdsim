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
def blockname(cls):
    return cls.__name__.strip('_').upper()


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

    options = None
    blocklibrary = None

    def __init__(self, **kwargs):
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
        
        Graphics display in all blocks can be disabled using the `graphics`
        option to the ``BlockDiagram`` instance.

        ===================  =========  ========  ===========================================
        Command line switch  Argument   Default   Behaviour
        ===================  =========  ========  ===========================================
        --nographics, -g     graphics   True      enable graphical display
        --animation, -a      animation  True      update graphics at each time step
        --noprogress, -p     progress   True      do not display simulation progress bar
        --backend BE         backend    'Qt5Agg'  matplotlib backend
        --tiles RxC, -t RxC  tiles      '3x4'     arrangement of figure tiles on the display
        --verbose, -v        verbose    False     be verbose
        --debug F, -d F      debug      ''        debug flag string
        ===================  =========  ========  ===========================================

        """
        # process command line and overall options
        if BDSim.options is None:
            BDSim.options = self.get_options(**kwargs)

        # load modules from the blocks folder
        if BDSim.blocklibrary is None:
            BDSim.blocklibrary = self.load_blocks(self.options.verbose) #self.verbose)

    def __str__(self):
        s = f"BDSim: {len(self.blocklibrary)} blocks in library\n"
        for k, v in self.options.__dict__.items():
            s += '  {:s}: {}\n'.format(k, v)
        return s
        
    def progress(self, t=None):
        if self.options.progress:
            if t is None:
                t = self.state.t
            printProgressBar(t / self.state.T, prefix='Progress:', suffix='complete', length=60)

    def progress_done(self):
        if self.options.progress:
            print('\r' + ' '* 90 + '\r')

    def run(self, bd, T=10.0, dt=0.1, solver='RK45', debug='',
            block=False, checkfinite=True, minstepsize=1e-12, watch=[],
            intargs={}):
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
        :param intargs: arguments passed to ``scipy.integrate``
        :type intargs: dict
        :return: time history of signals and states
        :rtype: Sim class
        
        Assumes that the network has been compiled.
        
        Results are returned in a class with attributes:
            
        - ``t`` the time vector: ndarray, shape=(M,)
        - ``x`` is the state vector: ndarray, shape=(M,N)
        - ``xnames`` is a list of the names of the states corresponding to columns of `x`, eg. "plant.x0",
            defined for the block using the ``snames`` argument
        - ``uN'` for a watched input where N is the index of the port mentioned in the ``watch`` argument
        - ``unames`` is a list of the names of the input ports being watched, same order as in ``watch`` argument
        
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

        state = BDSimState()
        self.state = state
        state.T = T
        state.dt = dt
        state.count = 0
        state.solver = solver
        state.intargs = intargs
        state.minstepsize = minstepsize
        state.stop = None # allow any block to stop.BlockDiagram by setting this to the block's name
        state.checkfinite = checkfinite
        state.options = copy.copy(self.options)
        self.bd = bd
        if debug:
            # append debug flags
            if debug not in state.options.debug:
                state.options.debug += debug
        
        if len(state.options.debug) > 0:
            state.options.progress = False

        # process the watchlist
        #  elements can be:
        #   - block or Plug reference
        #   - str in the form BLOCKNAME[PORT]
        watchlist = []
        watchnamelist = []
        re_block = re.compile(r'(?P<name>[^[]+)(\[(?P<port>[0-9]+)\])')
        for n in watch:
            if isinstance(n, str):
                # a name was given, with optional port number
                m = re_block.match(n)
                name = m.group('name')
                port = m.group('port')
                b = bd.blocknames[name]
                plug = b[port]
            elif isinstance(n, Block):
                # a block was given, defaults to port 0
                plug = n[0]
            elif isinstance(n, Plug):
                # a plug was given
                plug = n
            watchlist.append(plug)
            watchnamelist.append(str(plug))
        state.watchlist = watchlist

        # initialize list of time and states
        state.tlist = []
        state.xlist = []
        state.plist = [[] for p in state.watchlist]

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
        self.progress(0)

        if len(self.state.eventq) == 0:
            # no simulation events, solve it in one go
            self._run_interval(bd, 0, T, x0, state=state)
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

                # run system until next event time
                x = self._run_interval(bd, tprev, tnext, x, state=state)
                nintervals += 1

                # visit all the blocks and clocks that have an event now
                for source in sources:
                    if isinstance(source, Clock):
                        # clock ticked, save its state
                        clock.savestate(t)
                        clock.next_event()

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
            out['y'+str(i)] = np.array(simstate.plist[i])
        out.ynames = watchnamelist

        # pause until all graphics blocks close
        bd.done(block=block)

        return out

    def done(self, **kwargs):
        self.bd.done(graphics=self.options.graphics, **kwargs)
        
    def _run_interval(self, bd, t0, T, x0, state):
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

                integrator = scipy_integrator(ydot,
                    t0=t0, y0=x0, t_bound=T, max_step=state.dt, **state.intargs)

                # integrate
                while integrator.status == 'running':

                    # step the integrator, calls _deriv multiple times
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
                    
                    # update all blocks that need to know
                    bd.step(state=self.state, graphics=self.state.options.graphics)

                    self.progress()  # update the progress bar

                    if integrator.status == 'finished':
                        break

                    # has any block called a stop?
                    if state.stop is not None:
                        print(fg('red') + f"\n--- stop requested at t={bd.state.t:.4f} by {bd.state.stop}" + attr(0))
                        break

                    if state.minstepsize is not None and integrator.step_size < state.minstepsize:
                        print(fg('red') + f"\n--- stopping on minimum step size at t={bd.simstate.t:.4f} with last stepsize {integrator.step_size:g}" + attr(0))
                        break

                    if 'i' in state.options.debug:
                        bd._debugger(integrator)

                return integrator.y  # return final state vector

            elif len(clocklist) == 0:
                # block diagram has no continuous or discrete states
    
                for t in np.arange(t0, tf, simstate.dt):  # step through the time range
                    # evaluate the block diagram
                    bd.evaluate_plan([], t)

                    # stash the results
                    simstate.tlist.append(t)
                    
                    # record the ports on the watchlist
                    for i, p in enumerate(simstate.watchlist):
                        simstate.plist[i].append(p.block.output(t)[p.port])

                    # update all blocks that need to know
                    bd.step()

                    self.progress()  # update the progress bar

                        
                    # has any block called a stop?
                    if bd.simstate.stop is not None:
                        print(fg('red') + f"\n--- stop requested at t={bd.simstate.t:.4f} by {bd.simstate.stop}" + attr(0))
                        break

                    if 'i' in bd.simstate.options.debug:
                        bd._debugger(integrator)

            else:
                # block diagram has no continuous states
    
                t = t0
                # evaluate the block diagram
                bd.evaluate_plan([], t)

                # stash the results
                simstate.tlist.append(t)
                
                # record the ports on the watchlist
                for i, p in enumerate(simstate.watchlist):
                    simstate.plist[i].append(p.block.output(t)[p.port])

                # update all blocks that need to know
                bd.step()

                self.progress()  # update the progress bar

                    
                # has any block called a stop?
                if bd.simstate.stop is not None:
                    print(fg('red') + f"\n--- stop requested at t={bd.simstate.t:.4f} by {bd.simstate.stop}" + attr(0))

                if 'i' in bd.simstate.options.debug:
                    bd._debugger(integrator)

                
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

        At instantiation it has additional attributes set:

            * a factory method for every block in the block library that returns
              an instance of the block and puts the block into this object's
              ``blocklist``
            * ``options`` a tuple of options

        :seealso: :func:`BlockDiagram`
        """
        
        # instantiate a new blockdiagram
        bd = BlockDiagram(name=name)

        def new_method(cls, bd):

            # return a wrapper for the block constructor that automatically
            # add the block to the diagram's blocklist
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
        for block in self.blocklibrary:
            # create a function to invoke the block's constructor
            f = new_method(block.cls, bd)
            
            # set a bound version of this function as an attribute of the instance
            # method = types.MethodType(new_method, bd)
            # setattr(bd, block.name, method)
            setattr(bd, block.name, f.__get__(self))
            
            # broken, should be by folder
            # blocktype = block.cls.__module__.split('.')[1]
            # if blocktype in self.blockdict:
            #     self.blockdict[blocktype].append(block.name)
            # else:
            #     self.blockdict[blocktype] = [block.name]

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
        Load blocks

        Load all block definitions.

        Reads blocks from .py files found in bdsim/bdsim/blocks and folders
        given by colon separated list in envariable BDSIMPATH.

        The constructors of all classes within the module become a bound method
        of self.

        :raises ImportError: [description]
        :raises ImportError: [description]
        :return: [description]
        :rtype: [type]
        """
        nblocks = len(blocklist)
        # blocks = []
        if nblocks == 0:
            # add bdsim blocks folder
            blockpath = [Path(__file__).parent / 'blocks']

            # add RTB and MVTB if they exist
            try:
                import roboticstoolbox.blocks as pkg
                blockpath.append(Path(pkg.__path__[0]))
            except ImportError:
                pass
            try:
                import machinvevisiontoolbox.blocks as pkg
                blockpath.append(Path(pkg.__path__[0]))
            except ImportError:
                pass
            # blocklist = []

            # path = os.getenv('BDSIMPATH')
            # if path is not None:
            #     for p in path.split(':'):
            #         blockpath.append(Path(p))            
            
            if verbose:
                print('Loading blocks:')

            blocks = []
            for path in blockpath:  # for each folder on the path
                if not path.exists():
                    print(f"WARNING: path does not exist: {path}")
                    continue
                for file in path.iterdir():  # for each file in the folder
                    blocks_this_file = []

                    # scan every file *.py to find block definitions
                    # a block is a class that subclasses Source, Sink, Function, Transfer and
                    # has an @block decorator.
                    #
                    # The decorator adds the classes to a global variable blocklist in the
                    # component module's namespace.
                    if not file.name.startswith('test_') and not file.name.startswith('__') and file.name.endswith('.py'):
                        # valid python module, import it
                        try:
                            # module = importlib.import_module('.' + file.stem, package='bdsim.blocks')
                            spec = importlib.util.spec_from_file_location(file.name, file)
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            # module = importlib.import_module('.' + file.stem, package='bdsim.blocks')
                        except SyntaxError:
                            print(f"-- syntax error in block definition file: {file}")

                        for cls in module.__dict__.values():
                            if not inspect.isclass(cls) or \
                               inspect.getmro(cls)[-2].__name__ != 'Block' or \
                               not cls.__module__.startswith(file.name):
                                    continue

                            # we have a block class candidate
                            if cls.blockclass in ('source', 'transfer', 'function'):
                                # must have an output function
                                valid = hasattr(cls, 'output') and \
                                        callable(cls.output) and \
                                        len(inspect.signature(cls.output).parameters) == 2
                                if not valid:
                                    raise ImportError('class {:s} has missing/improper output method'.format(str(cls)))
                                
                            if cls.blockclass == 'sink':
                                # must have a step function with at least one
                                # parameter: step(self [,state])
                                valid = hasattr(cls, 'step') and \
                                        callable(cls.step) and \
                                        len(inspect.signature(cls.step).parameters) >= 1
                                if not valid:
                                    raise ImportError('class {:s} has missing/improper step method'.format(str(cls)))

                            blocks_this_file.append(blockname(cls))
                            blocks.append(block(blockname(cls), cls, file))

                        if verbose and len(blocks_this_file) > 0:
                                print('  loaded {:d} blocks from {:s}: {:s}'.format(
                                    len(blocks_this_file),
                                    str(file),
                                    ', '.join(b for b in blocks_this_file)))
                

                        # # components.blocklist grows with every block import
                        # if len(blocklist) > nblocks:
                        #     # we just loaded some more blocks
                        #     if verbose:
                        #         print('  loading blocks from {:s}: {:s}'.format(str(file), ', '.join([blockname(cls) for cls in blocklist[nblocks:]])))
                            
                        # # perform basic sanity checks on the blocks just read
                        # for cls in blocklist[nblocks:]:
                        #     print(cls)
                        #     if cls.blockclass in ('source', 'transfer', 'function'):
                        #         # must have an output function
                        #         valid = hasattr(cls, 'output') and \
                        #                 callable(cls.output) and \
                        #                 len(inspect.signature(cls.output).parameters) == 2
                        #         if not valid:
                        #             raise ImportError('class {:s} has missing/improper output method'.format(str(cls)))
                                
                        #     if cls.blockclass == 'sink':
                        #         # must have a step function with at least one
                        #         # parameter: step(self [,state])
                        #         valid = hasattr(cls, 'step') and \
                        #                 callable(cls.step) and \
                        #                 len(inspect.signature(cls.step).parameters) >= 1
                        #         if not valid:
                        #             raise ImportError('class {:s} has missing/improper step method'.format(str(cls)))
                            
                        #     blocks.append(block(blockname(cls), cls, file))

                        # nblocks = len(blocklist)

        return blocks

    def set_options(self, **options):
        """
        Set simulation options at run time

        The option names correspond to command line options

        ===================  =========  ========  ===========================================
        Command line switch  Option     Default   Behaviour
        ===================  =========  ========  ===========================================
        --nographics, -g     graphics   True      enable graphical display
        --animation, -a      animation  True      update graphics at each time step
        --noprogress, -p     progress   True      do not display simulation progress bar
        --backend BE         backend    'Qt5Agg'  matplotlib backend
        --tiles RxC, -t RxC  tiles      '3x4'     arrangement of figure tiles on the display
        --verbose, -v        verbose    False     be verbose
        --debug F, -d F      debug      ''        debug flag string
        ===================  =========  ========  ===========================================

        Example::

                sim = bdsim.BDsim()
                sim.set_options(graphics=False)

        .. note:: ``animation`` and ``graphics`` options are coupled.  If 
            ``graphics=False``, all graphics is suppressed.  If
            ``graphics=True`` then graphics are shown and the behaviour depends
            on ``animation``.  ``animation=False`` shows graphs at the end of
            the simulation, while ``animation=True` will animate the graphs
            during simulation.
        """
        for key, value in options.items():
            self.options[key] = value

        # animation and graphics options are coupled
        #
        #  graphics False, no graphics at all
        #  graphics True, animation False, show graphs at end of run
        #  graphics True, animation True, animate graphs during the run
        if 'animation' in options and options['animation']:
            self.options.graphics = True
        if 'graphics' in options and not options['graphics']:
            self.options.animation = False

    def get_options(sysargs=True, **kwargs):
        # option priority (high to low):
        #  - command line
        #  - argument to BDSim()
        #  - defaults
        # all switches and their default values
        defaults = {
            'backend': 'Qt5Agg',
            'tiles': '3x4',
            'graphics': True,
            'animation': False,
            'progress': True,
            'verbose': False,
            'debug': ''
            }
        
        # any passed kwargs can override the defaults
        options = {**defaults, **kwargs} # second argument has precedence

        if sysargs:
            # command line arguments and graphics
            parser = argparse.ArgumentParser(
                    formatter_class=argparse.ArgumentDefaultsHelpFormatter
                    )
            parser.add_argument('--backend', '-b', type=str, metavar='BACKEND',
                default=options['backend'],
                help='matplotlib backend to choose')
            parser.add_argument('--tiles', '-t', type=str, metavar='ROWSxCOLS',
                default=options['tiles'],
                help='window tiling as NxM')
            parser.add_argument('--nographics', '-g', 
                default=options['graphics'], 
                action='store_const', const=False, dest='graphics',
                help='disable graphic display')
            parser.add_argument('--animation', '-a', 
                default=options['animation'], 
                action='store_const', const=True,
                help='animate graphics')
            parser.add_argument('--noprogress', '-p', 
                default=options['progress'],
                action='store_const', const=False, dest='progress',
                help='animate graphics')
            parser.add_argument('--verbose', '-v', 
                default=options['verbose'],
                action='store_const', const=True,
                help='debug flags')
            parser.add_argument('--debug', '-d', type=str, metavar='[psd]',
                default=options['debug'],
                help='debug flags: p/ropagate, s/tate, d/eriv, i/nteractive')
            options = vars(parser.parse_args())  # get args as a dictionary

        # ensure graphics is enabled if animation is requested
        if options['animation']:
            options['graphics'] = True

        if options['verbose']:
            for k, v in options.items():
                print('{:10s}: {:}'.format(k, v))
        
        # stash these away
        options = Struct(**options, name='Options')

        return options


