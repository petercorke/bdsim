#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May 18 21:43:18 2020

@author: corkep
"""

import numpy as np
from scipy import integrate
import sys
import math

class Block:
    
    def __init__(self, type=None, name=None, pos=None, **kwargs):
    
        self.type = type
        self.name = name
        self.pos = pos
        self.id = None
        self.out = {}
        self.inputs = {}
        
        # self.passthru
        
    def check(self):
        pass
        
    @property
    def about(self):
        print("block:")
        for k,v in self.__dict__.items():
            print("  {:8s}{:s}".format(k+":", str(v)))

        
    def __getitem__(self, i):
        return (self, i)
        
    def __repr__(self):
        if self.id is not None:
            sid = "-{:d}".format(self.id) 
        s = "block{:s}: {:8s} {:10s}".format(sid, self.type, type(self).__name__)
        return s
    
    def reset(self):
        self.nset = 0
        self.done = False
    
    def input(self, port, val, i):
        if isinstance(val, np.ndarray):
            self.inputs[port] = val[i]
        elif i == 0:
            self.inputs[port] = val
        else:
            raise ValueError('bad val to input')
        self.nset += 1
        if self.nset == self.nin:
            self.done = True
        return self.done
    
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
        
    def reset(self):
        super().reset()
        self.x = self.x0
        return self.x
    
    def setstate(self, x):
        self.x = x[:self.nstates] # take as much state vector as we need
        return x[self.nstates:]   # return the rest
    
    def getstate(self):
        return self.x0
    
    def check(self):
        assert len(self.x0) == self.nstates, 'incorrect length for initial state'
                
    

class Function(Block):
    
    def __init__(self, **kwargs):
        super().__init__(type='function', **kwargs)
        self.nstates = 0

# ------------------------------------------------------------------------- # 
                
class Wire:
    
    class Port:
        def __init__(self, bp):
            self.block = bp[0]
            self.port = bp[1]
                
                
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
        if self.id is not None:
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
            if w.start.block.type == 'source':
                w.type = 'source'
        
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
                for i in np.find(An.diagonal()):
                    cycles.append((i, n))
                    
        if len(cycles) > 0:
            print("cycles found")
            for cycle in cycles:
                print(" len=" + cycle[1] + " block " + self.blocklist(cycle[0]))
        
 
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

        # build an adjacency matrix to check for connected outputs
        A = np.zeros((self.nwires, self.nblocks))
        for w in self.wirelist:
            b = w.start.block
            A[w.id,b.id] = 1
        for (i,a) in enumerate(A):  # check the rows
            if np.sum(a) > 1:    
                print("tied outputs: " + ",".join([str(self.blocklist[i]) for i in np.where(a>0)[0]]))
                
        # find the inputs connected to each output
        for w in self.wirelist:
            b = w.start.block
            b.out[w.start.port] = (w.end.block, w.end.port)
        
                
    def run(self, T=10.0, dt=0.1):
        
        # get the state from each stateful block
        x0 = np.array([])
        for b in s.blocklist:
            if b.type == 'transfer':
                x0 = np.r_[x0, b.getstate()]
        print('x0', x0)

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
    
    def _propagate(self, b, t):
        print('propagating:', b)
        out = b.output(t)
        for srcp, dest in b.out.items():
            destb = dest[0]
            destp = dest[1]
            print(' --> ', destb, '[', destp, ']')
            
            if destb.input(destp, out, srcp) and destb.nout > 0:
                self._propagate(destb, t)
            
    @staticmethod
    def _deriv(s, t, y):
        
        # reset all the blocks
        for b in s.blocklist:
            b.reset()
            
        # initialize the state
        for b in s.blocklist:
            if b.type == 'transfer':
                y = b.setstate(y)
        
        # process blocks with initial outputs
        for b in s.blocklist:
            if b.type in ('source', 'transfer'):
                s._propagate(b, t)
                
        # now iterate, running blocks, until we have values for all
        for b in s.blocklist:
            if b.type in ('sink', 'function', 'transfer') and not b.done:
                print('block not set')
            
        # gather the derivative
        YD = np.array([])
        for b in s.blocklist:
            if b.type == 'transfer':
                yd = b.getderiv()
                YD = np.r_[YD, yd]
        return YD
    
    def reset(self):
        X0 = np.array([])
        for b in self.blocklist:
            x0 = b.reset()
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
                f.write('\t"{:s}" -> "{:s}" [label="{:s}"]\n'.format(w.start.block.name, w.end.block.name, w.name))

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
                #print(out)
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
                
            def output(self, t):
                return np.array([1, 1, 0])
            
            def getderiv(self):
                theta = self.x[2]
                v = self.inputs[0]; gamma = self.inputs[1
                                                        ]
                return np.r_[v*math.cos(theta), v*math.sin(theta), v*math.tan(gamma) ]
        
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
