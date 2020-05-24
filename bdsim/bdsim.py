#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May 18 21:43:18 2020

@author: corkep
"""
import os
import os.path
import importlib

import numpy as np
import scipy.integrate as integrate


from bdsim.Block import Block

# ------------------------------------------------------------------------- # 
                
class Wire:
    
    class Port:
        def __init__(self, bp):
            self.block = bp[0]
            self.port = bp[1]
            self.dir = ''
            
        def __repr(self):
            return self.block + "[" + self.port + "]"
                
                
    def __init__(self, start=None, end=None, name=None):
        self.name = name
        self.id = None
        self.start = Wire.Port(start)
        self.end = Wire.Port(end)
        self.value = None
        self.type = None

    @property
    def about(self):
        print("block:")
        for k,v in self.__dict__.items():
            print("  {:8s}{:s}".format(k+":", str(v)))
            
    def __repr__(self):
        
        def range(x):
            if isinstance(x,slice):
                return "{:d}:{:d}".format(x.start, x.stop)
            else:
                return "{:d}".format(x)
        if self.id is None:
            sid = ""
        else:
            sid = "-{:d}".format(self.id)            
        s = "wire{:s}: {:s}[{:s}] --> {:s}[{:s}]".format(sid, type(self.start.block).__name__, range(self.start.port), type(self.end.block).__name__, range(self.end.port))

        return s
# ------------------------------------------------------------------------- #    
    
class Simulation:
    
    def __init__(self):
        
        self.wirelist = []
        self.blocklist = []
        self.srcwirelist = []
        self.x = None
        self.graphics = True
        
        
        # bind blocks to this object
        import bdsim.blocks
        
       
        def new_method(cls):
            def block_method_wrapper(self, *args, **kwargs):
                block = cls(*args, **kwargs)
                self.add_block(block)
                return block
            
            return block_method_wrapper
    
        # load modules from the blocks folder
        for file in os.listdir(os.path.join(os.path.dirname(__file__), 'blocks')):
            if file.endswith('.py'):
                print('Load blocks from', file, ': ', end='')
                blocks = importlib.import_module('.' + os.path.splitext(file)[0], package='bdsim.blocks')
                
                for item in dir(blocks):
                    if item.startswith('_') and not item.endswith('_'):
        
                        cls = blocks.__dict__[item]
                        
                        f = new_method(cls)
                        
                        bindname = item[1:].upper()
                        #print(item, cls, bindname, f)
                        print(bindname, end='')
                        setattr(Simulation, bindname, f)
                print()
        
    
    def add_block(self, block):
        block.sim = self
        self.blocklist.append(block)
        
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
                
        # for each wire, connect the source block to the wire
        # TODO do this when the wire is created
        for w in self.wirelist:
            b = w.start.block
            b.add_out(w)
        
                
    def run(self, T=10.0, dt=0.1, solver='RK45', 
            graphics=True,
            **kwargs):
        
        self.graphics = graphics
        self.T = T
                
        for b in self.blocklist:
            b.start()
        

        # get the state from each stateful block
        x0 = np.array([])
        for b in self.blocklist:
            if b.blockclass == 'transfer':
                x0 = np.r_[x0, b.getstate()]
        print('x0', x0)


        # out = scipy.integrate.solve_ivp(Simulation._deriv, args=(self,), t_span=(0,T), y0=x0, 
        #             method=solver, t_eval=np.linspace(0, T, 100), events=None, **kwargs)
        
        integrator = integrate.__dict__[solver](lambda t, y: Simulation._deriv(t, y, self), t0=0.0, y0=x0, t_bound=T, max_step=dt)
        
        t = []
        x = []
        while integrator.status == 'running':
            # step the integrator, calls _deriv multiple times
            integrator.step()
            
            # stash the results
            t.append(integrator.t)
            x.append(integrator.y)
            
            for b in self.blocklist:
                b.step()
        
        self.done()
        
        return np.c_[t,x]
    
    def done(self):
        for b in self.blocklist:
            b.done()
            
    def _propagate(self, b, t):
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
            
            if dest.input(w, val) and dest.blockclass == 'function':
                self._propagate(dest, t)
    
    def evaluate(self, x, t):
        self.t = t
        
        # reset all the blocks
        for b in self.blocklist:
            b.reset()
            
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
        
    @staticmethod
    def _deriv(t, y, s):
        return s.evaluate(y, t)
    
    def reset(self):
        X0 = np.array([])
        for b in self.blocklist:
            x0 = b.reset()
            if x0 is not None:
                X0 = np.r_[X0, x0]
    
        print(X0)
        self.x = X0
    

    def dotfile(self, file):
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
    
    
    demand = s.WAVEFORM(wave='square', freq=2, pos=(0,0))
    sum = s.SUM('+-', pos=(1,0))
    gain = s.GAIN(2, pos=(1.5,0))
    plant = s.LTI_SISO(0.5, [1, 2], name='plant', pos=(3,0))
    scope = s.SCOPE(pos=(4,0))
    
    s.connect(demand, sum[0])
    s.connect(plant, sum[1])
    s.connect(sum, gain)
    s.connect(gain, plant)
    s.connect(plant, scope)
    
    s.compile()
    
    #s.dotfile('bd1.dot')
    
    s.run(10)