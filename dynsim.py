#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May 18 21:43:18 2020

@author: corkep
"""

import numpy as np
import scipy.integrate as integrate

from Block import Block

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
        import blocks
        
       
        def new_method(cls):
            def wrapper_method(self, **kwargs):
                block = cls(**kwargs)
                self.add_block(block)
                return block
            
            return wrapper_method
    
        for item in dir(blocks):
            if item.startswith('_') and not item.endswith('_'):

                cls = blocks.__dict__[item]
                
                f = new_method(cls)
                
                bindname = item[1:].upper()
                print(item, cls, bindname, f)
                setattr(Simulation, bindname, f)
        
    
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
    
    def connect(self, start=None, end=None, name=None):
        
        """
        TODO:
            s.connect(out[3], in1[2], in2[3])  # one to many
            block[1] = SigGen()  # use setitem
            block[1] = SumJunction(block2[3], block3[4]) * Gain(value=2)
        """
        
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
        
                
    def run(self, T=10.0, dt=0.1, solver='RK45', 
            graphics=True,
            **kwargs):
        for b in s.blocklist:
            b.start()
        
        self.T = T
        # get the state from each stateful block
        x0 = np.array([])
        for b in s.blocklist:
            if b.type == 'transfer':
                x0 = np.r_[x0, b.getstate()]
        print('x0', x0)


        # out = scipy.integrate.solve_ivp(Simulation._deriv, args=(self,), t_span=(0,T), y0=x0, 
        #             method=solver, t_eval=np.linspace(0, T, 100), events=None, **kwargs)
        
        integrator = integrate.__dict__[solver](lambda t, y: Simulation._deriv(t, y, self), t0=0.0, y0=x0, t_bound=T, max_step=dt)
        
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
            
            for b in self.blocklist:
                b.step()
            
        return np.c_[t,x]
    
    def done(self):
        for b in s.blocklist:
            b.done()
            
    def _propagate(self, b, t):
        #print('propagating:', b)
        out = b.output(t)
        for srcp, dest in b.out.items():
            destb = dest[0]
            destp = dest[1]
            #print(' --> ', destb, '[', destp, ']')
            
            if destb.input(destp, out, srcp) and destb.nout > 0:
                self._propagate(destb, t)
            
    @staticmethod
    def _deriv(t, y, s):
        
        # reset all the blocks
        for b in s.blocklist:
            b.reset()
            
        # split the state vector to stateful blocks
        for b in s.blocklist:
            if b.type == 'transfer':
                y = b.setstate(y)
        
        # process blocks with initial outputs
        for b in s.blocklist:
            if b.nout > 0:
                s._propagate(b, t)
                
        # now iterate, running blocks, until we have values for all
        for b in s.blocklist:
            if b.type in ('sink', 'function', 'transfer') and not b.done:
                print('block not set')
            
        # gather the derivative
        YD = np.array([])
        for b in s.blocklist:
            if b.type == 'transfer':
                yd = b.deriv()
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
            
            header = r"""digraph G {

    graph [splines=ortho, rankdir=LR]
    node [shape=box, style=filled, color=gray90]
    
    """
            f.write(header)
            # add the blocks
            for b in self.blocklist:
                f.write('\t"{:s}"\n'.format(b.name))
            
            # add the wires
            for w in self.wirelist:
                f.write('\t"{:s}" -> "{:s}" [label="{:s}"]\n'.format(w.start.block.name, w.end.block.name, w.name))

            f.write('}\n')


if __name__ == "__main__":
    s = Simulation()
    
    steer = s.WAVEFORM(name='siggen', freq=0.5, min=-0.5, max=0.5)
    speed = s.CONSTANT(value=0.5)
    bike = s.BICYCLE(x0=[0, 0, 0])
    scope = s.SCOPEXY()
    
    s.connect(speed, bike[0])
    s.connect(steer, bike[1])

    s.connect(bike[0:2], scope[0:2])
    
    s.compile()
    
    print(s)
    
    out = s.run()
    
    s.done()
