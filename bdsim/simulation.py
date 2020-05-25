#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May 18 21:43:18 2020

@author: corkep
"""
import os
import os.path
import importlib
import inspect
import re

import numpy as np
import scipy.integrate as integrate


from bdsim.components import Block, Wire


# ------------------------------------------------------------------------- #    
    
class Simulation:
    
    def __init__(self):
        
        self.wirelist = []      # list of all wires
        self.blocklist = []     # list of all blocks
        self.x = None           # state vector numpy.ndarray
        self.graphics = True    # graphics enabled
        self.compiled = False   # network has been compiled
        self.T = None           # maximum simulation time
        self.t = None           # current time
        
        
        # load modules from the blocks folder
        
        def new_method(cls):
            def block_method_wrapper(self, *args, **kwargs):
                block = cls(*args, **kwargs)
                self.add_block(block)
                return block
            
            # return a function that invokes the class constructor
            f = block_method_wrapper
            # move the __init__ docstring to the class to allow BLOCK.__doc__
            cls.__doc__ = cls.__init__.__doc__  
            return f
    
        # scan every file for classes and make their constructors methods of this class
        for file in os.listdir(os.path.join(os.path.dirname(__file__), 'blocks')):
            if file.endswith('.py'):
                
                # valid python module, import it
                blocks = importlib.import_module('.' + os.path.splitext(file)[0], package='bdsim.blocks')
                
                blocknames = []
                for item in dir(blocks):
                    if item.startswith('_') and not item.endswith('_'):
        
                        # valid class name within module
                        cls = blocks.__dict__[item]
                        
                        # test the class is a valid block
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

                        # create a function to invoke the block's constructor
                        f = new_method(cls)
                        
                        # create the new method name
                        bindname = item[1:].upper()
                        blocknames.append(bindname)
                        
                        # set an attribute of the class
                        #  it becomes a bound method of the instance.
                        setattr(Simulation, bindname, f)

                if len(blocknames) > 0:
                    print('Loading blocks from {:s}: {:s}'.format(file, ', '.join(blocknames)))

    
    def add_block(self, block):
        block.sim = self   # block back pointer to the simulator
        self.blocklist.append(block)  # add to the list of available blocks
        
    def add_wire(self, wire):
        return self.wirelist.append(wire)
    
    def __repr__(self):
        s = ""
        for block in self.blocklist:
            s += str(block) + "\n"
        s += "\n"
        for wire in self.wirelist:
            s += str(wire) + "\n"
        return s.lstrip("\n")
    
    def connect(self, *args, name=None):
        
        """
        TODO:
            s.connect(out[3], in1[2], in2[3])  # one to many
            block[1] = SigGen()  # use setitem
            block[1] = SumJunction(block2[3], block3[4]) * Gain(value=2)
        """
        
        slices = False
        
        start = args[0]
        
        if isinstance(start, Block):
            start = (start, 0)
        elif isinstance(start, tuple):
            if isinstance(start[1], slice):
                slices = True

        for end in args[1:]:
            if isinstance(end, Block):
                end = (end, 0)
            elif isinstance(end, tuple):
                if isinstance(end[1], slice):
                    slices = True
                    
            if slices:
                # we have a bundle of signals
                
                # TODO: allow destination to have no slice
                
                def slice2list(s):
                    if s.step is None:
                        return list(range(s.start, s.stop))
                    else:
                        return list(range(s.start, s.stop, s.step))
                            
                            
                slist = slice2list(start[1])
                elist = slice2list(end[1])
                assert len(slist) == len(elist), 'slice wires must have same width'
                
                for (s,e) in zip(slist, elist):
                    wire = Wire( (start[0], s), (end[0], e), name)
                    self.wirelist.append(wire)
            else:
                wire = Wire(start, end, name)
                self.wirelist.append(wire)
        
    def compile(self):
        
        # enumrate the elements
        self.nblocks = len(self.blocklist)
        for (i,b) in enumerate(self.blocklist):
            b.id = i
            if b.name is None:
                b.name = "block {:d}".format(i)
        self.nwires = len(self.wirelist)
        for (i,w) in enumerate(self.wirelist):
            w.id = i 
            if w.name is None:
                w.name = "wire {:d}".format(i)
            if w.start.block.blockclass == 'source':
                w.blockclass = 'source'
        
        # run block specific checks
        for b in self.blocklist:
            b.check()
            
        nstates = 0
        for b in self.blocklist:
            nstates += b.nstates
        print('{:d} states'.format(nstates))
        self.nstates = nstates
         
        self.check_connectivity()
                
        # for each wire, connect the source block to the wire
        # TODO do this when the wire is created
        for w in self.wirelist:
            b = w.start.block
            b.add_out(w)
            
        self.compiled = True
        
    def report(self):
        
        def format(table, colsep = 2):
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
            re_fmt = re.compile(r"([a-zA-Z]+)\[([0-9]*)([a-z])\]")
            
            hfmt = ""
            cfmt = ""
            sep = ""
            colheads = []
            
            for col in table.split(' '):
                m = re_fmt.search(col)
                colhead = m.group(1)
                colwidth = m.group(2)
                if colwidth == '':
                    colwidth = len(colhead) + colsep
                else:
                    colwidth = max(int(colwidth), len(colhead) + colsep)
                colfmt = m.group(3)
                colheads.append(colhead)
                if colfmt == 'd':
                    hfmt += "{:>%ds}" % (colwidth,)
                else:
                    hfmt += "{:%ds}" % (colwidth,)
                cfmt += "{:%d%s}" % (colwidth, colfmt)
                hfmt += ' ' * colsep
                cfmt += ' ' * colsep
                sep += '-' * colwidth + '  '
            
            print(hfmt.format(*colheads))
            print(sep)
            return cfmt
        
        # print all the blocks
        print('\nBlocks::\n')
        cfmt = format("id[3d] class[10s] type[10s] name[10s] nin[2d] nout[2d] nstate[2d]")
        for b in self.blocklist:
            print( cfmt.format(b.id, b.blockclass, b.type, b.name, b.nin, b.nout, b.nstates))
        
        # print all the wires
        print('\nWires::\n')
        cfmt = format("id[3d] name[10s] from[6s] to[6s]")
        for w in self.wirelist:
            start = "{:d}[{:d}]".format(w.start.block.id, w.start.port)
            end = "{:d}[{:d}]".format(w.end.block.id, w.end.port)
            print( cfmt.format(w.id, w.name, start, end))
            
    def run(self, T=10.0, dt=0.1, solver='RK45', 
            graphics=True,
            **kwargs):
        """
        
        :param T: maximum integration time, defaults to 10.0
        :type T: float, optional
        :param dt: maximum time step, defaults to 0.1
        :type dt: float, optional
        :param solver: integration method, defaults to 'RK45'
        :type solver: str, optional
        :param graphics: enable graphic display by blocks, defaults to True
        :type graphics: bool, optional
        :param **kwargs: passed to `scipy.integrate`
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
        self.graphics = graphics
        self.T = T
        
        # tell all blocks we're doing a simulation
        self.start()

        # get the state from each stateful block
        x0 = np.array([])
        for b in self.blocklist:
            if b.blockclass == 'transfer':
                x0 = np.r_[x0, b.getstate()]
        #print('x0', x0)
        

        # integratnd function, wrapper for network evaluation method
        def _deriv(t, y, s):
            return s.evaluate(y, t)
    
        # out = scipy.integrate.solve_ivp(Simulation._deriv, args=(self,), t_span=(0,T), y0=x0, 
        #             method=solver, t_eval=np.linspace(0, T, 100), events=None, **kwargs)
        
        if len(x0) > 0:
            integrator = integrate.__dict__[solver](lambda t, y: _deriv(t, y, self), t0=0.0, y0=x0, t_bound=T, max_step=dt)
        
            t = []
            x = []
            while integrator.status == 'running':
                # step the integrator, calls _deriv multiple times
                integrator.step()
                
                # stash the results
                t.append(integrator.t)
                x.append(integrator.y)
                
                self.step()
                
                return np.c_[t,x]
        else:
            for t in np.arange(0, T, dt):
                _deriv(t, [], self)
                self.step()
        
        self.done()
        

    
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
        
        # reset all the blocks ready for the evalation
        self.reset()
        
        # split the state vector to stateful blocks
        for b in self.blocklist:
            if b.blockclass == 'transfer':
                x = b.setstate(x)
        
        # process blocks with initial outputs
        for b in self.blocklist:
            if b.blockclass in ('source', 'transfer'):
                self._propagate(b, t)
                
        # now iterate, running blocks, until we have values for all
        for b in self.blocklist:
            if b.blockclass in ('sink', 'function', 'transfer') and not b.done:
                print('block not set')
            
        # gather the derivative
        YD = np.array([])
        for b in self.blocklist:
            if b.blockclass == 'transfer':
                yd = b.deriv().flatten()
                YD = np.r_[YD, yd]
        return YD

    def _propagate(self, b, t):
        """
        Propogate values of a block to all connected inputs.
        
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
        #print('propagating:', b)
        
        # get output of block at time t
        out = b.output(t)
        
        # check for validity
        assert isinstance(out, list) and len(out) == b.nout, 'block output is wrong type/length'
        # TODO check output validity once at the start
        
        # iterate over all outgoing wires
        for w in b.out:
            #print(' --> ', w.end.block.name, '[', w.end.port, ']')
            
            val = out[w.start.port]
            dest = w.end.block
            
            if dest.setinput(w, val) and dest.blockclass == 'function':
                self._propagate(dest, t)
                
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
                    
    def start(self):
        """
        Inform all active blocks that simulation is about to start.  Opem files,
        initialize graphics, etc.
        
        Invokes the `start` method on all blocks.
        
        """            
        for b in self.blocklist:
            b.start()
            
    def done(self):
        """
        Inform all active blocks that simulation is complete.  Close files,
        graphics, etc.
        
        Invokes the `done` method on all blocks.
        
        """
        for b in self.blocklist:
            b.done()
            

    def check_connectivity(self):
        """
        
        Perform a number of connectivity checks on the network:
            
            - cycles
            - multiple outputs driving one input port
    
        """
        # build an adjacency matrix to represent the graph
        A = np.zeros((self.nblocks, self.nblocks))
        for w in self.wirelist:
            start = w.start.block.id
            end = w.end.block.id
            A[end,start] = 1
            
        self.A = A
        print(A)
        
        # check for cycles
        cycles = []
        An = A
        for n in range(2, self.nwires+1):
            An = An @ A   # compute A**n
            if np.trace(An) > 0:
                for i in np.argwhere(An.diagonal()):
                    cycles.append((i, n))
                    
        if len(cycles) > 0:
            print("cycles found")
            for cycle in cycles:
                print(" - length of {:d} involving block id={:d} ({:s})".format(cycle[1], cycle[0][0], self.blocklist[cycle[0][0]].name))
        
 
        # check for sources and sinks
        dependson = {}   
        for (i,a) in enumerate(A):  # check the rows
            if np.sum(a) == 0:
                print('block {:d} is a source'.format(i))
                assert self.blocklist[i].blockclass == 'source'
            else:
                dependson[i] = tuple(np.where(a > 0))
        for (i,a) in enumerate(A.T): # check the columns
            if np.sum(a) == 0:
                print('block {:d} is a sink'.format(i))
                assert self.blocklist[i].blockclass == 'sink'

        # build an adjacency matrix to check for connected outputs
        A = np.zeros((self.nwires, self.nblocks))
        for w in self.wirelist:
            b = w.start.block
            A[w.id,b.id] = 1
        for (i,a) in enumerate(A):  # check the rows
            if np.sum(a) > 1:    
                print("tied outputs: " + ",".join([str(self.blocklist[i]) for i in np.where(a>0)[0]]))
                
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
            


if __name__ == "__main__":
    
    s = Simulation()
    
    
    # demand = s.WAVEFORM(wave='square', freq=2, pos=(0,0))
    # sum = s.SUM('+-', pos=(1,0))
    # gain = s.GAIN(2, pos=(1.5,0))
    # plant = s.LTI_SISO(0.5, [1, 2], name='plant', pos=(3,0))
    # scope = s.SCOPE(pos=(4,0))
    
    # s.connect(demand, sum[0])
    # s.connect(plant, sum[1])
    # s.connect(sum, gain)
    # s.connect(gain, plant)
    # s.connect(plant, scope)
    
    # s.compile()
    
    # #s.dotfile('bd1.dot')
    
    # s.report()
    # #s.run(10)
    
    s = Simulation()

    wave = s.WAVEFORM(freq=2)
    scope = s.SCOPE(nin=1)
    
    s.connect(wave, scope)
    
    s.compile()
    s.run(5)
