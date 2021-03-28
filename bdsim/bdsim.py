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
import bdsim
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
        self.debug_stop = False
        self.t_stop = None  # time-based breakpoint

class BDSim:

    def __init__(self, verbose=False, **kwargs):
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
        --animation, -a      animation  False     update graphics at each time step
        --noprogress, -p     progress   True      display simulation progress bar
        --backend BE         backend    'Qt5Agg'  matplotlib backend
        --tiles RxC, -t RxC  tiles      '3x4'     arrangement of figure tiles on the display
        --debug F, -d F      debug      ''        debug flag string
        ===================  =========  ========  ===========================================

        """
        # process command line and overall options
        self.options = self.get_options(**kwargs)

        # load modules from the blocks folder
        self.blocklibrary = self.load_blocks(verbose) #self.verbose)

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
            block=False, checkfinite=True, minstepsize=1e-6, watch=[],
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
        if debug:
            state.debug_stop = True
            state.options.progress = False

        # preproces the watchlist
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

        bd.state = state

        x0 = bd.getstate0()
        print('initial state x0 = ', x0)

        # tell all blocks we're starting a BlockDiagram
        bd.start()
        self.progress(0)

        if bd.ndstates == 0:
            # no discrete time states
            self._run_interval(bd, 0, T, state=state)
        else:
            # find the first clock time
            next = []
            tprev = 0
            for clock in bd.clocklist:
                next.append(clock.next(tprev))  # append time of next sample
                clock.x = clock.getstate0()  # get state of all blocks on this clock
            
            # choose the nearest sample time
            tnext = min(next)

            while tnext <= T:
                # print(tnext)

                # run system until next clock time
                self._run_interval(bd, tprev, tnext, state=state)

                tprev = tnext
                for i, t in enumerate(next):
                    if t == tnext:
                        # it was this clock that ticked
                        clock = bd.clocklist[i]

                        # update the next time for this clock
                        next[i] = clock.next(tprev)

                        # get the new state
                        clock._x = clock.getstate()

                    tnext = min(next)

        # self.progress_done()  # cleanup the progress bar
        print()

        # pause until all graphics blocks close
        bd.done(block=block)
        print(bd.state.count,  ' integrator steps')
        print(len(state.tlist), ' time steps')

        # save buffered data in a Struct
        out = Struct('results')
        out.t = np.array(state.tlist)
        out.x = np.array(state.xlist)
        out.xnames = bd.statenames
        for i, p in enumerate(watchlist):
            out['y'+str(i)] = np.array(state.plist[i])
        out.ynames = watchnamelist
        return out
        
    def _run_interval(self, bd, t0, T, state):
        try:
            # get initial state from the stateful blocks



            # out = scipy.integrate.solve_ivp.BlockDiagram._deriv, args=(self,), t_span=(0,T), y0=x0, 
            #             method=solver, t_eval=np.linspace(0, T, 100), events=None, **kwargs)
            if bd.nstates > 0:

                x0 = bd.getstate0()
                # print('initial state x0 = ', x0)

                # block diagram contains states, solve it using numerical integration

                scipy_integrator = integrate.__dict__[state.solver]  # get user specified integrator

                integrator = scipy_integrator(lambda t, y: bd.evaluate(y, t),
                                                t0=t0, y0=x0, t_bound=T, max_step=state.dt, **state.intargs)


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
                    bd.step()
                    
                    self.progress()  # update the progress bar

                    # has any block called a stop?
                    if bd.state.stop is not None:
                        print(fg('red') + f"\n--- stop requested at t={bd.state.t:.4f} by {bd.state.stop}" + attr(0))
                        break

                    if state.minstepsize is not None and integrator.step_size < state.minstepsize:
                        print(fg('red') + f"\n--- stopping on minimum step size at t={bd.t:.4f} with last stepsize {integrator.step_size:g}" + attr(0))
                        break

                    if bd.state.debug_stop:
                        bd._debugger(integrator)

            else:
                # block diagram has no states
    
                for t in np.arange(t0, T, state.dt):  # step through the time range

                    # evaluate the block diagram
                    bd.evaluate([], t)

                    # stash the results
                    state.tlist.append(t)
                    
                    # record the ports on the watchlist
                    for i, p in enumerate(state.watchlist):
                        state.plist[i].append(p.block.output(t)[p.port])

                    # update all blocks that need to know
                    bd.step()

                    self.progress()  # update the progress bar

                        
                    # has any block called a stop?
                    if bd.state.stop is not None:
                        print(fg('red') + f"\n--- stop requested at t={bd.state.t:.4f} by {bd.state.stop}" + attr(0))
                        break

                    if bd.state.debug_stop:
                        bd._debugger(integrator)

                
        except RuntimeError as err:
            # bad things happens, print a message and return no result
            print('unrecoverable error in evaluation: ', err)
            raise

    def done(self, bd, **kwargs):

        bd.done(**kwargs)

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
                bd.add_block(block)
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
        for i in range(self.state.fignum):
            print('close', i+1)
            plt.close(i+1)
            plt.pause(0.1)
        self.state.fignum = 0  # reset figure counter
            
    def savefig(self, block, filename=None, format='pdf', **kwargs):
        block.savefig(filename=filename, format=format, **kwargs)

    def savefigs(self, bd, format='pdf', **kwargs):
        for b in bd.blocklist:
            b.savefig(filename=filename, format=format, **kwargs)

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
        blocks = []
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

            # path = os.getenv('BDSIMPATH')
            # if path is not None:
            #     for p in path.split(':'):
            #         blockpath.append(Path(p))            
            
            if verbose:
                print('Loading blocks:')

            for path in blockpath:  # for each folder on the path
                if not path.exists():
                    print(f"WARNING: path does not exist: {path}")
                    continue
                for file in path.iterdir():  # for each file in the folder
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
                            print(f"-- syntax error in block definiton: {file}")
        
                        # components.blocklist grows with every block import
                        if len(blocklist) > nblocks:
                            # we just loaded some more blocks
                            if verbose:
                                print('  loading blocks from {:s}: {:s}'.format(str(file), ', '.join([blockname(cls) for cls in blocklist[nblocks:]])))
                            
                        # perform basic sanity checks on the blocks just read
                        for cls in blocklist[nblocks:]:
                            
                            if cls.blockclass in ('source', 'transfer', 'function'):
                                # must have an output function
                                valid = hasattr(cls, 'output') and \
                                        callable(cls.output) and \
                                        len(inspect.signature(cls.output).parameters) == 2
                                if not valid:
                                    raise ImportError('class {:s} has missing/improper output method'.format(str(cls)))
                                
                            if cls.blockclass == 'sink':
                                # must have a step function
                                valid = hasattr(cls, 'step') and \
                                        callable(cls.step) and \
                                        len(inspect.signature(cls.step).parameters) == 1
                                if not valid:
                                    raise ImportError('class {:s} has missing/improper step method'.format(str(cls)))
                            
                            blocks.append(block(blockname(cls), cls, file))

                        nblocks = len(blocklist)

        return blocks

    def get_options(sysargs=True, **kwargs):
        
        # all switches and their default values
        defaults = {
            'backend': 'Qt5Agg',
            'tiles': '3x4',
            'graphics': True,
            'animation': False,
            'progress': True,
            'debug': ''
            }
        if sysargs:
            # command line arguments and graphics
            parser = argparse.ArgumentParser()
            parser.add_argument('--backend', '-b', type=str, metavar='BACKEND', default=defaults['backend'],
                                help='matplotlib backend to choose')
            parser.add_argument('--tiles', '-t', type=str, default=defaults['tiles'], metavar='ROWSxCOLS',
                                help='window tiling as NxM')
            parser.add_argument('--nographics', '-g', default=defaults['graphics'], action='store_const', const=False, dest='graphics',
                                help='disable graphic display')
            parser.add_argument('--animation', '-a', default=defaults['animation'], action='store_const', const=True,
                                help='animate graphics')
            parser.add_argument('--noprogress', '-p', default=defaults['progress'], action='store_const', const=False, dest='progress',
                        help='animate graphics')
            parser.add_argument('--debug', '-d', type=str, metavar='[psd]', default=defaults['debug'], 
                                help='debug flags')
            clargs = vars(parser.parse_args())  # get args as a dictionary
            # print(f'clargs {clargs}')

            
        # function arguments override the command line options
        # provide a list of argument names and default values
        options = {}
        for option, default in defaults.items():
            if option in kwargs:
                # first priority is to constructor argument
                assert type(kwargs[option]) is type(default), 'passed argument ' + option + ' has wrong type'
                options[option] = kwargs[option]
            elif sysargs and option in clargs:
                # if not provided, drop through to command line argument
                options[option] = clargs[option]
            else:
                # drop through to the default value
                options[option] = default
            
        # ensure graphics is enabled if animation is requested
        if options['animation']:
            options['graphics'] = True
        
        # stash these away
        options = types.SimpleNamespace(**{**defaults, **options})

        # setup debug parameters from single character codes
        debuglist = []
        if 'p' in options.debug:
            debuglist.append('propagate')
        if 's' in options.debug:
            debuglist.append('state')
        if 'd' in options.debug:
            debuglist.append('deriv')
        if 'i' in options.debug:
            debuglist.append('interactive')

        options.debuglist = debuglist

        return options
        