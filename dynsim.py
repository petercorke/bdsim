#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May 18 21:43:18 2020

@author: corkep
"""

import numpy as np
from scipy import integrate
import sys

class Block:
    
    def __init__(self, type=None, name=None, pos=None, **kwargs):
    
        self.type = type
        self.name = name
        self.pos = pos
        self.id = None
        
        # self.passthru
        
    def __getitem__(self, i):
        return (self, i)
        
    def __repr__(self):
        if self.id is not None:
            sid = "-{:d}".format(self.id) 
        s = "block{:s}: {:8s} {:10s}".format(sid, self.type, type(self).__name__)
        s += str(self.__dict__)
        return s
    
    def init(self):
        pass

    def setstate(self, x):
        pass
    
    def deriv(self):
        pass
    
    def output(self):
        pass
    
class Sink(Block):
    
    def __init__(self, **kwargs):
        super().__init__(type='sink', **kwargs)
        self.nin = 1
        self.nout = 0
        self.nstates = 0

class Source(Block):
    
    def __init__(self, **kwargs):
        super().__init__(type='source', **kwargs)
        self.nin = 0
        self.nout = 1
        self.nstates = 0
        
class Transfer(Block):
    
    def __init__(self, **kwargs):
        super().__init__(type='transfer', **kwargs)
    

class Function(Block):
    
    def __init__(self, **kwargs):
        super().__init__(type='function', **kwargs)
        self.nstates = 0

# ------------------------------------------------------------------------- # 
                
class Wire:
    
    def __init__(self, start=None, end=None, name=None):
        self.name = name
        self.id = None
        self.start = start
        self.end = end
        self.value = None
        self.type = None
        
    def __repr__(self):
        
        def range(x):
            if isinstance(x,slice):
                return "{:d}:{:d}".format(x.start, x.stop)
            else:
                return "{:d}".format(x)
        if self.id is not None:
            sid = "-{:d}".format(self.id)            
        s = "wire{:s}: {:s}[{:s}] --> {:s}[{:s}]".format(sid, type(self.start[0]).__name__, range(self.start[1]), type(self.end[0]).__name__, range(self.end[1]))

        return s
# ------------------------------------------------------------------------- #    
    
class Simulation:
    
    def __init__(self):
        
        self.wirelist = []
        self.blocklist = []
        self.srcwirelist = []
        self.x = None
    
    def add_block(self, cls, **kwargs):
        block = cls(**kwargs)
        self.blocklist.append(block)
        return block
        
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
    
    def connect(self, start=None, end=None, name=None):
        slices = False
        
        if isinstance(start, Block):
            start = (start, 0)
        elif isinstance(start, tuple):
            if isinstance(start[1], slice):
                slices = True

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
            if w.start[0].type == 'source':
                w.type = 'source'
                
        nstates = 0
        for b in self.blocklist:
            nstates += b.nstates
        print('{:d} states'.format(nstates))
        self.nstates = nstates
         
        # build an adjacency matrix to represent the graph
        A = np.zeros((self.nblocks, self.nblocks))
        for w in self.wirelist:
            start = w.start[0].id
            end = w.end[0].id
            A[end,start] = 1
            
        self.Abb = A
        
        # check for cycles
        cycles = []
        An = A
        for n in range(0, self.nwires-1):
            An *= A   # n=0...nwires-2, A^2...A^nwires
            if np.trace(An) > 0:
                for i in np.find(An.diagonal()):
                    cycles.append((i, n+2))
                    
        if len(cycles) > 0:
            print('{:d} cycles found'.format(len(cycles)))
        
 
        # check for sources and sinks
        dependson = {}   
        for (i,a) in enumerate(A):  # check the rows
            if np.sum(a) == 0:
                print('block {:d} is a source'.format(i))
                assert self.blocklist[i].type == 'source'
            else:
                dependson[i] = tuple(np.where(a > 0))
        for (i,a) in enumerate(A.T): # check the columns
            if np.sum(a) == 0:
                print('block {:d} is a sink'.format(i))
                assert self.blocklist[i].type == 'sink'

        # build an adjacency matrix to represent the graph
        A = np.zeros((self.nblocks, self.nwires))
        for w in self.wirelist:
            b = w.end[0]
            if b.type != 'source':
                A[b.id,w.id] = 1.0 / b.nin
            
        self.Abw = A
        print(A)
        
                
    def run(self, T=10.0, dt=0.1):
        
        # reset all the integrators
        self.init()
        
        x0 = self.x
        integrator = integrate.RK45(lambda t, y: Simulation._deriv(self, t, y), t0=0.0, y0=x0, t_bound=T, max_step=dt)
        
        # we keep results from each step in a list
        #  apparantly fastest https://stackoverflow.com/questions/7133885/fastest-way-to-grow-a-numpy-numeric-array
        t = []
        x = []
        while integrator.status == 'running':
            # step the integrator, calls _deriv multiple times
            integrator.step()
            
            # stash the results
            t.append(integrator.t)
            x.append(integrator.y)

        return np.c_[t,x]
            
    @staticmethod
    def _deriv(s, t, y):
        
        setwires = set()
        
        # initialize wires connected to sources
        for w in s.wirelist:
            if w.type == 'source':
                w.value = w.start[0].output(t)
                setwires |= {w.id}  # add to the set of wires with values
            else:
                w.value = None
                
        # now iterate, running blocks, until we have values for all
        #while True:
            
            
        
        return np.r_[0,0,0]
    
    
    def init(self):
        X0 = np.array([])
        for b in self.blocklist:
            x0 = b.init()
            if x0 is not None:
                X0 = np.r_[X0, x0]
    
        print(X0)
        self.x = X0
    

    def dotfile(self, file):
        with open(file, 'w') as f:
            
            f.write(r"""digraph G {

    graph [splines=ortho, rankdir=LR]
    node [shape=box, style=filled, color=gray90]
    """)

            # add the blocks
            for b in self.blocklist:
                f.write('\t"{:s}"\n'.format(b.name))
            
            # add the wires
            for w in self.wirelist:
                f.write('\t"{:s}" -> "{:s}" [label="{:s}"]\n'.format(w.start[0].name, w.end[0].name, w.name))

            f.write('}\n')

    
    # ---------------------------------- simulation elements ---------------- #
    def constant(self, **kwargs):
        
        # TODO: subclass Block -> Sink, Source, Transfer, Function
        
        class _Constant(Source):
            
            def __init__(self, value=None, **kwargs):
                super().__init__(**kwargs)
                self.value = value


            def output(self, t):
                return self.value                


        return self.add_block(_Constant, **kwargs)
    
    def waveform(self, **kwargs):
        
        class _WaveForm(Source):
            def __init__(self, freq=1, min=0, max=1, duty=0.5, **kwargs):
                super().__init__(**kwargs)
                self.freq = freq
                self.min = min
                self.max = max
                self.duty = duty
                
                assert 0<duty<1, 'duty must be in range [0,1]'

            def output(self, t):
                T = 1.0 / self.freq
                phase = (t % T) * self.freq
                
                if phase < self.duty:
                    out = self.min
                else:
                    out = self.max
                print(out)
                return out

        return self.add_block(_WaveForm, **kwargs)
    
    def scope(self, **kwargs):
        
        class _Scope(Sink):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.nin = 2
        
        return self.add_block(_Scope, **kwargs)

    def bicycle(self, **kwargs):
        
        class _Bicycle(Transfer):
            def __init__(self, x0=None, **kwargs):
                super().__init__(**kwargs)
                self.nin = 2
                self.nout = 3
                self.nstates = 3
                if x0 is None:
                    self.x0 = np.zeros((slef.nstates,))
                else:
                    assert len(x0) == self.nstates, "x0 is {:d} long, should be {:d}".format(len(x0), self.nstates)
                    self.x0 = x0
                
            def init(self):
                self.x = self.x0
                return self.x
                

            def output(self, t):
                return self.value
        
        return self.add_block(_Bicycle, **kwargs)



s = Simulation()

steer = s.waveform(name='siggen', min=-1)
speed = s.constant(value=2)
bike = s.bicycle(x0=[1,2,0])
scope = s.scope()

s.connect(steer, bike[0])
s.connect(speed, bike[1])
s.connect(bike[0:2], scope[0:2])

s.compile()

print(s)

out = s.run()