#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May 18 21:43:18 2020

@author: corkep
"""
import os
import os.path
import sys
import importlib
import inspect
import re
import argparse
from collections import Counter
import numpy as np
import scipy.integrate as integrate
import matplotlib
import matplotlib.pyplot as plt

from bdsim.components import *

debuglist = [] # ('propagate', 'state', 'deriv')

def DEBUG(debug, *args):
    if debug in debuglist:
        print('DEBUG.{:s}: '.format(debug), *args)

# ------------------------------------------------------------------------- #    


class BlockDiagram:
    
    def __init__(self, name='main'):
        
        self.wirelist = []      # list of all wires
        self.blocklist = []     # list of all blocks
        self.x = None           # state vector numpy.ndarray
        self.graphics = True    # graphics enabled
        self.compiled = False   # network has been compiled
        self.T = None           # maximum.BlockDiagram time
        self.t = None           # current time
        self.fignum = 0
        self.stop = None
        self.connnecterror = False
        self.checkfinite = True
        self.blockcounter = Counter()
        self.name = name

        # command line arguments and graphics
        parser = argparse.ArgumentParser()
        parser.add_argument('--backend', '-b', type=str, metavar='BACKEND', default='Qt5Agg',
                            help='matplotlib backend to choose')
        parser.add_argument('--tiles', '-t', type=str, default='3x4', metavar='ROWSxCOLS',
                            help='window tiling as NxM')
        parser.add_argument('--nographics', '-g', default=True, action='store_const', const=False, dest='graphics',
                            help='disable graphic display')
        parser.add_argument('--animation', '-a', default=False, action='store_const', const=True,
                            help='animate graphics')
        parser.add_argument('--debug', '-d', type=str, metavar='[psd]', default='', 
                            help='debug flags')
        args = parser.parse_args()      
        
        global debuglist
        if 'p' in args.debug:
            debuglist.append('propagate')
        if 's' in args.debug:
            debuglist.append('state')
        if 'd' in args.debug:
            debuglist.append('deriv')
        
        def blockname(cls):
            return cls.__name__.strip('_').upper()
        
        # load modules from the blocks folder
        
        # scan every file ./blocks/*.py to find block definitions
        # a block is a class that subclasses Source, Sink, Function, Transfer and
        # has an @block decorator.
        #
        # The decorator adds the classes to a global variable module_blocklist in the
        # module's namespace.
        nblocks = len(blocklist)
        if nblocks == 0:
            print('Loading blocks:')
            for file in os.listdir(os.path.join(os.path.dirname(__file__), 'blocks')):
                if not file.startswith('test_') and file.endswith('.py'):
                    # valid python module, import it
                    try:
                        module = importlib.import_module('.' + os.path.splitext(file)[0], package='bdsim.blocks')
                    except SyntaxError:
                        print('-- syntax error in block definiton: ' + file)
    
                    # components.blocklist grows with every block import
                    if len(blocklist) > nblocks:
                        # we just loaded some more blocks
                        print('  loading blocks from {:s}: {:s}'.format(file, ', '.join([blockname(cls) for cls in blocklist[nblocks:]])))

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
                                
                    nblocks = len(blocklist)
        
        def new_method(cls, bd):
            def block_init_wrapper(self, *args, **kwargs):
                block = cls(*args, bd=bd, **kwargs)
                self.add_block(block)
                return block
            
            # return a function that invokes the class constructor
            f = block_init_wrapper
            # move the __init__ docstring to the class to allow BLOCK.__doc__
            cls.__doc__ = cls.__init__.__doc__  
            return f
        
        # bind the block constructors as new methods on this instance
        for cls in blocklist:
            # create a function to invoke the block's constructor
            f = new_method(cls, self)
            
            # create the new method name, strip underscores and capitalize
            bindname = blockname(cls)
            
            # set a bound version of this function as an attribute of the instance
            setattr(self, bindname, f.__get__(self))

        # graphics initialization
        if args.animation:
            args.graphics = True
        self.graphics = args.graphics
        self.animation = args.animation
        self.args = args
            
    def create_figure(self):

        def move_figure(f, x, y):
            """Move figure's upper left corner to pixel (x, y)"""
            backend = matplotlib.get_backend()
            if backend == 'TkAgg':
                f.canvas.manager.window.wm_geometry("+%d+%d" % (x, y))
            elif backend == 'WXAgg':
                f.canvas.manager.window.SetPosition((x, y))
            else:
                # This works for QT and GTK
                # You can also use window.setGeometry
                f.canvas.manager.window.move(x, y)
                
        if self.fignum == 0:
            # no figures yet created, lazy initialization
            
            matplotlib.use(self.args.backend)            
            mpl_backend = matplotlib.get_backend()
            print('matplotlib backend is', mpl_backend)
            
            if mpl_backend == 'Qt5Agg':
                from PyQt5 import QtWidgets
                app = QtWidgets.QApplication([])
                screen = app.primaryScreen()
                print('Screen: %s' % screen.name())
                size = screen.size()
                print('Size: %d x %d' % (size.width(), size.height()))
                rect = screen.availableGeometry()
                print('Available: %d x %d' % (rect.width(), rect.height()))
                sw = rect.width()
                sh = rect.height()
            elif mpl_backend == 'TkAgg':
                window = plt.get_current_fig_manager().window
                sw =  window.winfo_screenwidth()
                sh =  window.winfo_screenheight()
                print('Size: %d x %d' % (sw, sh))
            self.screensize_pix = (sw, sh)
            self.tiles = [int(x) for x in self.args.tiles.split('x')]
            
            # create a figure at default size to get dpi (TODO better way?)
            f = plt.figure(figsize=(1,1))
            self.dpi = f.dpi
            
            # compute fig size in inches (width, height)
            self.figsize = [ self.screensize_pix[0] / self.tiles[1] / self.dpi , self.screensize_pix[1] / self.tiles[0] / self.dpi ]
            
            # resize the figure
            #plt.figure(num=f.number, figsize=self.figsize)
            f.set_size_inches(self.figsize, forward=True)
            plt.ion()
        else:
            f = plt.figure(figsize=self.figsize)
            
        # move the figure to right place on screen
        row = self.fignum // self.tiles[0]
        col = self.fignum % self.tiles[0]
        move_figure(f, col * self.figsize[0] * self.dpi, row * self.figsize[1] * self.dpi)
        
        self.fignum += 1
        #print('create figure', self.fignum, row, col)
        return f
        
    
    def add_block(self, block):
        block.id = len(self.blocklist)
        if block.name is None:
            i = self.blockcounter[block.type]
            self.blockcounter[block.type] += 1
            block.name = "{:s}.{:d}".format(block.type, i)
        block.bd = self
        self.blocklist.append(block)  # add to the list of available blocks
        
    def add_wire(self, wire, name=None):
        wire.id = len(self.wirelist)
        wire.name = name
        return self.wirelist.append(wire)
    
    def __str__(self):
        return 'BlockDiagram: {:s}'.format(self.name)
    
    def __repr__(self):
        return str(self) + " with {:d} blocks and {:d} wires".format(len(self.blocklist), len(self.wirelist))
        # for block in self.blocklist:
        #     s += str(block) + "\n"
        # s += "\n"
        # for wire in self.wirelist:
        #     s += str(wire) + "\n"
        # return s.lstrip("\n")
    
    def connect(self, *args, name=None):
        
        """
        TODO:
            s.connect(out[3], in1[2], in2[3])  # one to many
            block[1] = SigGen()  # use setitem
            block[1] = SumJunction(block2[3], block3[4]) * Gain(value=2)
        """
                
        start = args[0]
        
        # convert to default plug on port 0 if need be
        if isinstance(start, Block):
            start = Plug(start, 0)
        start.type = 'start'

        for end in args[1:]:
            if isinstance(end, Block):
                end = Plug(end, 0)
            end.type = 'end'
                    
            if start.isslice and end.isslice:
                # we have a bundle of signals
                                
                assert start.width == end.width, 'slice wires must have same width'
                
                for (s,e) in zip(start.portlist, end.portlist):
                    wire = Wire( Plug(start.block, s, 'start'), Plug(end.block, e, 'end'), name)
                    self.add_wire(wire)
            elif start.isslice and not end.isslice:
                # bundle goint to a block
                assert start.width == start.block.nin, "bundle width doesn't match number of input ports"
                for inport,outport in enumerate(start.portlist):
                    wire = Wire( Plug(start.block, outport, 'start'), Plug(end.block, inport, 'end'), name)
                    self.add_wire(wire)
            else:
                wire = Wire(start, end, name)
                self.add_wire(wire)
        
    def compile(self, subsystem=False, doimport=True):
        
        # namethe elements
        self.nblocks = len(self.blocklist)
        # for b in self.blocklist:
        #     if b.name is None:
        #         i = self.blockcounter[b.type]
        #         self.blockcounter[b.type] += 1
        #         b.name = "{:s}.{:d}".format(b.type, i)
        self.nwires = len(self.wirelist)
        # for (i,w) in enumerate(self.wirelist):
        #     # w.id = i 
        #     # if w.name is None:
        #     #     w.name = "wire {:d}".format(i)
        #     if w.start.block.blockclass == 'source':
        #         w.blockclass = 'source'
        
        # run block specific checks
        for b in self.blocklist:
            try:
                b.check()
            except:
                raise RuntimeError('block failed check ' + str(b))
            
        nstates = 0
        
        error = False
        
        # TODO blockdiagrams have a name, default is "main"
        if not subsystem:
            print('\nCompiling:')
        
        ssblocks = [b for b in self.blocklist if b.type == 'subsystem']
        for b in ssblocks:
            print('  importing subsystem', b.name)
            if b.ssvar is not None:
                print('-- Wiring in subsystem', b, 'from module local variable ', b.ssvar)
            self.flatten(b, [b.name])
        
        # initialize lists of input and output ports
        for b in self.blocklist:
            nstates += b.nstates
            try:
                b.outports = [[] for i in range(0, b.nout)]
                b.inports = [None for i in range(0, b.nin)]
            except:
                raise RuntimeError('cannot initialize ports for block ' + str(b) + ': ', sys.exc_info()[1])
        
        #print('  {:d} states'.format(nstates))
        self.nstates = nstates
         
        # for each wire, connect the source and destination blocks to the wire
        for w in self.wirelist:
            try:
                w.start.block.add_outport(w)
                w.end.block.add_inport(w)
            except AssertionError as err:
                print('error connecting wire: ', w.fullname, err)
                error = True
            
        # check every block 
        for b in self.blocklist:
            # check all inputs are connected
            for port,connection in enumerate(b.inports):
                if connection is None:
                    print('  ERROR: block {:s} input {:d} is not connected'.format(str(b), port))
                    error = True
                    
            # check all outputs are connected
            for port,connections in enumerate(b.outports):
                if len(connections) == 0:
                    print('  WARNING: block {:s} output {:d} is not connected'.format(str(b), port))
                    
            if b._inport_names is not None:
                assert len(b._inport_names) == b.nin, 'incorrect number of input names given: ' + str(b)
            if b._outport_names is not None:
                assert len(b._outport_names) == b.nout, 'incorrect number of output names given: ' + str(b)
            if b._state_names is not None:
                assert len(b._state_names) == b.nstates, 'incorrect number of state names given: ' + str(b)
                    
        # check for cycles of function blocks
        def _DFS(path):
            start = path[0]
            tail = path[-1]
            for outgoing in tail.outports:
                # for every port on this block
                for w in outgoing:
                    dest = w.end.block
                    if dest == start:
                        print('  ERROR: cycle found: ', ' - '.join([str(x) for x in path + [dest]]))
                        return True
                    if dest.blockclass == 'function':
                        return _DFS(path + [dest]) # recurse
            return False

        for b in self.blocklist:
            if b.blockclass == 'function':
                # do depth first search looking for a cycle
                if _DFS([b]):
                    error = True
        

        # evaluate the network once to check out wire types
        x = self.getstate()
        
        try:
            self.evaluate(x, 0.0)
        except RuntimeError as err:
            print('unrecoverable error in value propagation:', err)
            error = True
            
        if not error:
            self.compiled = True
            
        return self.compiled
    
    #flatten the hierarchy
    
    def flatten(top, subsys, path):
        subsystems = [b for b in subsys.subsystem.blocklist if b.type == 'subsystem']
        # recursively flatten all subsystems
        for ss in subsystems:
            flatten(top, ss, path + [ss.name] )
        
        # compile this subsystem TODO
        if subsys.subsystem.compiled is False:
            ok = subsys.subsystem.compile(subsystem=True)
            if not ok:
                raise ImportError('cant compile subsystem')
        # sort the subsystem blocks into categories
        inports = []
        outports = []
        others = []
        for b in subsys.subsystem.blocklist:
            if b.type == 'inport':
                inports.append(b)
            elif b.type == 'outport':
                outports.append(b)
            else:
                others.append(b)
        if len(inports) >1:
            raise ImportError('subsystem has more than one input port element')
        if len(outports) > 1:
            raise ImportError('subsystem has more than one output port element')
        if len(inports) == 0 and len(outports) == 0:
            raise ImportError('subsystem has no input or output port elements')
            
        # connect the input port
        inport = inports[0]
        for w in top.wirelist:
            if w.end.block == subsys:
                # this top-level wire is input to subsystem
                # reroute it
                port = w.end.port
                for w2 in inport.outports[port]:
                    # w2 is the wire from INPORT to others within subsystem
                    
                    # make w2 start at the source driving INPORT
                    w2.start.block = w.start.block
                    w2.start.port = w.start.port
        # remove all wires connected to the inport
        top.wirelist = [w for w in top.wirelist if w.end.block != subsys]
                
        # connect the output port
        outport = outports[0]
        for w in top.wirelist:
            if w.start.block == subsys:
                # this top-level wire is output from subsystem
                # reroute it
                port = w.start.port
                w2 = outport.inports[port]
                # w2 is the wire to OUTPORT from others within subsystem
                
                # make w2 end at the destination from OUTPORT
                w2.end.block = w.end.block
                w2.end.port = w.end.port
        # remove all wires connected to the outport
        top.wirelist = [w for w in top.wirelist if w.start.block != subsys]
        top.blocklist.remove(subsys)
        for b in others:
            top.add_block(b)   # add remaining blocks from subsystem
            b.name = '/'.join(path + [b.name])
        top.wirelist.extend(subsys.subsystem.wirelist)  # add remaining wires from subsystem
        
    def report(self):
        
        class TableFormat:
            
            def __init__(self, table, colsep = 2):
                """
                Tabular printing
                
                :param table: format string
                :type table: str
                :param extrasep: extra separation between columns, default 2
                :type extrasep: int
                :return: a format string
                :rtype: str
                
                Given an input string like::
                
                    "col1[s] col2[d] col3[10s] col4[3d]"
                    
                where the square brackets denote type  (as per `format`) and the
                number if given is a minumum column width.  The actual column width
                is the maximum of the given value and the width of the heading text
                plus `extrasep`.
                
                Then print the header and a separator line::
                
                col1  col2  col3        col4
                ----  ----  ----------  ----
    
                and return a format string that can be used with `format` to format
                the arguments for subsequent data rows.
                """
                # parse the format line
                re_fmt = re.compile(r"([a-zA-Z]+)\[(\-?[0-9]*|\*)([a-z])\]")
                

                colheads = []
                varwidth = {}
                columns = []
                
                for i, col in enumerate(table.split(' ')):
                    m = re_fmt.search(col)
                    colhead = m.group(1)
                    colwidth = m.group(2)
                    if colwidth == '':
                        colwidth = len(colhead) + colsep
                        coljust = '<'
                    elif colwidth == '*':
                        varwidth[i] = 0
                        colwidth = None
                        coljust = '<'
                    else:
                        w = int(colwidth)
                        if w < 0:
                            coljust = '>'
                            w = -w
                        else:
                            coljust = '<'
                        colwidth = max(w, len(colhead) + colsep)
                    colfmt = m.group(3)
                    columns.append( (colhead, colfmt, coljust, colwidth) )
                else:
                    self.ncols = i + 1
                    
                self.data = []
                self.colsep = colsep
                self.columns = columns
                self.varwidth = varwidth

            
            def add(self, *data):
                assert len(data) == self.ncols, 'wrong number of data items added'
                self.data.append(data)
                for k,v in self.varwidth.items():
                    self.varwidth[k] = max(v, len(data[k]))
            
            def print(self):
                hfmt = ""
                cfmt = ""
                sep = ""
                
                colheads = []
                for i, col in enumerate(self.columns):
                    colhead, colfmt, coljust, colwidth = col
                    
                    colheads.append(colhead)
                    
                    if colwidth is None:
                        colwidth = self.varwidth[i]
                        
                    if colfmt == 'd':
                        hfmt += "{:>%ds}" % (colwidth,)
                    else:
                        hfmt += "{:%ds}" % (colwidth,)
                        
                    cfmt += "{:%s%d%s}" % (coljust, colwidth, colfmt)
                    hfmt += ' ' * self.colsep
                    cfmt += ' ' * self.colsep
                    sep += '-' * colwidth + '  '
                    
                print(hfmt.format(*colheads))
                print(sep)
                
                for d in self.data:
                    print( cfmt.format(*d))
        
        # print all the blocks
        print('\nBlocks::\n')
        cfmt = TableFormat("id[3d] name[*s] nin[2d] nout[2d] nstate[2d]")
        for b in self.blocklist:
            cfmt.add( b.id, str(b), b.nin, b.nout, b.nstates)
        cfmt.print()
        
        # print all the wires
        print('\nWires::\n')
        cfmt = TableFormat("id[3d] from[-6s] to[-6s] description[*s] type[*s]")
        for w in self.wirelist:
            start = "{:d}[{:d}]".format(w.start.block.id, w.start.port)
            end = "{:d}[{:d}]".format(w.end.block.id, w.end.port)
            
            value = w.end.block.inputs[w.end.port]
            typ = type(value).__name__
            if isinstance(value, np.ndarray):
                typ += ' {:s}'.format(str(value.shape))
            cfmt.add( w.id, start, end, w.fullname, typ)
        cfmt.print()
        print('\nState variables: {:d}'.format(self.nstates))
        
        if not self.compiled:
            print('** System has not been compiled, or had a compile time error')
            
    def getstate(self):
        # get the state from each stateful block
        x0 = np.array([])
        for b in self.blocklist:
            if b.blockclass == 'transfer':
                x0 = np.r_[x0, b.getstate()]
        #print('x0', x0)
        return x0
        
    def run(self, T=10.0, dt=0.1, solver='RK45', 
            block=False, checkfinite=True,
            **kwargs):
        """
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
        :param ``**kwargs``: passed to ``scipy.integrate``
        :return: time history of signals and states
        :rtype: Sim class
        
        Assumes tgat the network has been compiled.
        
        Graphics display in all blocks can be disabled using the `graphics`
        option.
        
        Results are returned in a class with attributes:
            
        - `t` the time vector: ndarray, shape=(M,)
        - `x` is the state vector: ndarray, shape=(M,N)
        - `xnames` is a list of the names of the states corresponding to columns of `x`, eg. "plant.x0"

        """
        
        assert self.compiled, 'Network has not been compiled'
        self.T = T
        self.count = 0
        self.stop = None # allow any block to stop.BlockDiagram by setting this to the block's name
        self.checkfinite = checkfinite
        
        # tell all blocks we're doing a.BlockDiagram
        self.start()

        x0 = self.getstate()
        if len(x0) > 0:
            print('initial state x0 = ', x0)
        

        # integratnd function, wrapper for network evaluation method
        def _deriv(t, y, s):
            return s.evaluate(y, t)
    
        try:
            # out = scipy.integrate.solve_ivp.BlockDiagram._deriv, args=(self,), t_span=(0,T), y0=x0, 
            #             method=solver, t_eval=np.linspace(0, T, 100), events=None, **kwargs)
            if len(x0) > 0:
                integrator = integrate.__dict__[solver](lambda t, y: _deriv(t, y, self), t0=0.0, y0=x0, t_bound=T, max_step=dt)
            
                t = []
                x = []
                while integrator.status == 'running':
                    
                    if self.stop is not None:
                         print('--- stop requested at t={:f} by {:s}'.format(self.t, str(self.stop)))
                         break
                    # step the integrator, calls _deriv multiple times
                    integrator.step()
                    
                    # stash the results
                    t.append(integrator.t)
                    x.append(integrator.y)
                    
                    self.step()
                if integrator.status == 'failed':
                    print('integration completed with failed status ')
                out = np.c_[t,x]
            else:
                for t in np.arange(0, T, dt):
                    _deriv(t, [], self)
                    self.step()
                out = None
                
        except RuntimeError as err:
            print('unrecoverable error in value propagation: ', err)
            return None

        self.done(block=block)
        print(self.count, ' integrator steps')
        
        return out
        

    def evaluate(self, x, t):
        """
        Evaluate all blocks in the network
        
        :param x: state
        :type x: numpy.ndarray
        :param t: current time
        :type t: float
        :return: state derivative
        :rtype: numpy.ndarray
        
        Performs the following steps:
            
        1. Partition the state vector to all stateful blocks
        2. Propogate known block output ports to connected input ports


        """
        #print('in evaluate at t=', t)
        self.t = t
        DEBUG('state', '>>>>>>>>> t=', t, ', x=', x, '>>>>>>>>>>>>>>>>')
        
        # reset all the blocks ready for the evalation
        self.reset()
        
        # split the state vector to stateful blocks
        for b in self.blocklist:
            if b.blockclass == 'transfer':
                x = b.setstate(x)
        
        # process blocks with initial outputs and propagate
        for b in self.blocklist:
            if b.blockclass in ('source', 'transfer'):
                self._propagate(b, t)
                
        # check we have values for all
        for b in self.blocklist:
            if b.nin > 0 and not b.done:
                raise RuntimeError(str(b) + ' has incomplete inputs')
            
        # gather the derivative
        YD = np.array([])
        for b in self.blocklist:
            if b.blockclass == 'transfer':
                assert b.updated, str(b) + ' has incomplete inputs'
                yd = b.deriv().flatten()
                YD = np.r_[YD, yd]
        DEBUG('deriv', YD)
        return YD

    def _propagate(self, b, t, depth=0):
        """
        Propagate values of a block to all connected inputs.
        
        :param b: Block with valid output
        :type b: Block
        :param t: current time
        :type t: float

        When all inputs to a block are available, its output can be computed
        using its `output` method (which may also be a function of time).
        
        This value is presented to each connected input port via its
        `setinput` method.  That method returns True if the block now has
        all its inputs defined, in which case we recurse.

        """
        
        # check for a subsystem block here, recurse to evalute it
        # execute the subsystem to obtain its outputs

        # get output of block at time t
        try:
            out = b.output(t)
        except Exception as err:
            print('--Error at t={:f} when computing output of block {:s}'.format(t, str(b)))
            print('  {}'.format(err))
            print('  inputs were: ', b.inputs)
            if b.nstates > 0:
                print('  state was: ', b.x)
            raise RuntimeError from None

            
        DEBUG('propagate', '  '*depth, 'propagating: {:s} @ t={:.3f}: output = '.format(str(b),t) + str(out))

        # check for validity
        assert isinstance(out, list) and len(out) == b.nout, 'block output is wrong type/length'
        # TODO check output validity once at the start
        
        # check it has no nan or inf values
        if self.checkfinite and isinstance(out, (int, float, np.ndarray)) and not np.isfinite(out).any():
            raise RuntimeError('block outputs nan')
        
        # propagate block outputs to all downstream connected blocks
        for (port, outwires) in enumerate(b.outports): # every port
            val = out[port]
            for w in outwires:     # every wire
                
                DEBUG('propagate', '  '*depth, '[', port, '] = ', val, ' --> ', w.end.block.name, '[', w.end.port, ']')
                
                if w.send(val) and w.end.block.blockclass == 'function':
                    self._propagate(w.end.block, t, depth+1)
                
    def reset(self):
        """
        Reset conditions within every active block.  Most importantly, all
        inputs are marked as unknown.
        
        Invokes the `reset` method on all blocks.

        """
        for b in self.blocklist:
            b.reset()     
    
    def step(self):
        """
        Tell all blocks to take action on new inputs.  Relevant to Sink
        blocks only since they have no output function to be called.
        """
        # TODO could be done by output method, even if no outputs
        
        for b in self.blocklist:
            b.step()
            self.count += 1

                    
    def start(self, **kwargs):
        """
        Inform all active blocks that.BlockDiagram is about to start.  Open files,
        initialize graphics, etc.
        
        Invokes the `start` method on all blocks.
        
        """            
        for b in self.blocklist:
            b.start(**kwargs)
            
    def done(self, **kwargs):
        """
        Inform all active blocks that.BlockDiagram is complete.  Close files,
        graphics, etc.
        
        Invokes the `done` method on all blocks.
        
        """
        for b in self.blocklist:
            b.done(**kwargs)
            
    def savefig(self, format='pdf', **kwargs):
        for b in self.blocklist:
            if isinstance(b, SinkBlockGraphics):
                fname = str(b) + '.' + format
                print('saving {} -> {}'.format(str(b), fname))
                b.savefig(fname, **kwargs)
        
    def dotfile(self, file):
        """
        Write a GraphViz dot file representing the network.
        
        :param file: Name of file to write to
        :type file: str

        The file can be processed using neato or dot::
            
            % dot -Tpng -o out.png dotfile.dot

        """
        with open(file, 'w') as file:
            
            header = r"""digraph G {

    graph [splines=ortho, rankdir=LR]
    node [shape=box]
    
    """
            file.write(header)
            # add the blocks
            for b in self.blocklist:
                options = []
                if b.blockclass == "source":
                    options.append("shape=box3d")
                elif b.blockclass == "sink":
                    options.append("shape=folder")
                elif b.blockclass == "function":
                    if b.type == 'gain':
                        options.append("shape=triangle")
                        options.append("orientation=-90")
                        options.append('label="{:g}"'.format(b.gain))
                    elif b.type == 'sum':
                        options.append("shape=point")
                elif b.blockclass == 'transfer':
                    options.append("shape=component")
                if b.pos is not None:
                    options.append('pos="{:g},{:g}!"'.format(b.pos[0], b.pos[1]))
                options.append('xlabel=<<BR/><FONT POINT-SIZE="8" COLOR="blue">{:s}</FONT>>'.format(b.type))
                file.write('\t"{:s}" [{:s}]\n'.format(b.name, ', '.join(options)))
            
            # add the wires
            for w in self.wirelist:
                options = []
                #options.append('xlabel="{:s}"'.format(w.name))
                if w.end.block.type == 'sum':
                    options.append('headlabel="{:s} "'.format(w.end.block.signs[w.end.port]))
                file.write('\t"{:s}" -> "{:s}" [{:s}]\n'.format(w.start.block.name, w.end.block.name, ', '.join(options)))

            file.write('}\n')
            
    def blockvalues(self):
        for b in self.blocklist:
            print('Block {:s}:'.format(b.name))
            print('  inputs:  ', b.inputs)
            print('  outputs: ', b.output(t=0))  
            
if __name__ == "__main__":
    
    import pathlib
    import os.path

    exec(open(os.path.join(pathlib.Path(__file__).parent.absolute(), "test_blockdiagram.py")).read())

