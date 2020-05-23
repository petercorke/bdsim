#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 21 08:48:47 2020

@author: corkep
"""

import numpy as np

class Block:
    
    def __init__(self, type=None, name=None, pos=None, **kwargs):
        #print('Block constructor'
        self.type = type
        self.name = name
        self.pos = pos
        self.id = None
        self.out = []
        self.inputs = None
        self.updated = False
        
        # self.passthru
        

    @property
    def about(self):
        print("block: " + type(self).__name__)
        for k,v in self.__dict__.items():
            print("  {:8s}{:s}".format(k+":", str(v)))

        
    def __getitem__(self, i):
        return (self, i)
        
    def __repr__(self):
        if self.id is None:
            sid = ""
        else:
            sid = "-{:d}".format(self.id)

        s = "block{:s}: {:8s} {:10s}".format(sid, self.type, type(self).__name__)
        return s
    
    def reset(self):
        if self.nin > 0:
            self.inputs = [None] * self.nin
        self.updated = False
        
    def add_out(self, w):
        self.out.append(w)
    
    def input(self, wire, val):
        """
        Receive input from a wire
        
        :param wire: Incoming wire
        :type wire: Wire
        :param val: Incoming value
        :type val: any
        :return: If all inputs have been received
        :rtype: bool

        """

        # stash it away
        self.inputs[wire.end.port] = val

        # check if all inputs have been assigned
        if all([x is not None for x in self.inputs]):
            self.updated = True
            self.update()
        return self.updated
    
    def start(self):  # begin of a simulation
        pass
    
    def deriv(self):  # return derivative during integration
        pass
    
    def output(self):  # return block output
        pass

    def check(self):  # check validity of block parameters at start
        pass
    
    def update(self):  # inputs are valid
        pass
    
    def done(self):  # end of simulation
        pass
    
    def step(self):  # valid
        pass
        
class Sink(Block):
    
    def __init__(self, **kwargs):
        #print('Sink constructor')
        super().__init__(type='sink', **kwargs)
        self.nin = 1
        self.nout = 0
        self.nstates = 0

class Source(Block):
    
    def __init__(self, **kwargs):
        #print('Source constructor')
        super().__init__(type='source', **kwargs)
        self.nin = 0
        self.nout = 1
        self.nstates = 0
        
class Transfer(Block):
    
    def __init__(self, **kwargs):
        #print('Transfer constructor')
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