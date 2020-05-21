#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blocks available for use in block diagrams.

Each class _MyClass in this module becomes a method MYCLASS() of the Simulation object.
This is done in Simulation.__init__()

All arguments to MYCLASS() must be named arguments and passed through to the constructor
_MyClass.__init__().

These classses must subclass one of

- Source, output is a constant or function of time
- Sink, input only
- Transfer, output is a function of state self.x (no pass through)
- Function, output is a direct function of input

These classes all subclass Block.

Every class defined here provides several methods:
    
- __init__, mandatory to handle block specific parameter arguments
- reset, 
- output, to compute the output value as a function of self.inputs which is 
  a dict indexed by input number
- deriv, for Transfer subclass only, return the state derivative vector
- check, to validate parameter settings

Created on Thu May 21 06:39:29 2020

@author: Peter Corke
"""
import numpy as np
import math
from Block import *
    


# ---------------------------------- simulation elements ---------------- #

# could create a decorator for each of these
"""
maybe ??

@block
class _Constant(Source):
    
def block(cls):
    
    def new_method(cls):
        def wrapper_method(self, **kwargs):
            return self.add_block(cls, **kwargs)
        
        return wrapper_method
    
                
    f = new_method(cls)
    bindname = cls.__name__.upper()
    print(cls, bindname, f)
    setattr(Simulation, bindname, f)
    
    return cls
            
"""

class _Constant(Source):
    
    def __init__(self, value=None, **kwargs):
        super().__init__(**kwargs)
        self.value = value

    def output(self, t):
        return self.value                


class _WaveForm(Source):
    def __init__(self, freq=1, phase0=0, signal='square',
                 min=0, max=1, duty=0.5, # for square
                 amplitude=1, offset=0,  # for sine, triangle
                 **kwargs):
        super().__init__(**kwargs)

        assert 0<duty<1, 'duty must be in range [0,1]'
        assert max > min, 'maximum value must be greater than minimum'
        
        self.freq = freq
        self.signal = signal
        self.phase0 = phase0
        self.min = min
        self.max = max
        self.duty = duty
        self.amplitude = amplitude
        self.offset = offset

    def output(self, t):
        T = 1.0 / self.freq
        phase = ((t % T) * self.freq - self.phase0 ) % 1.0
        
        amplitude = self.max - self.min
        
        # define all signals in the range -1 to 1
        if self.signal == 'square':
            if phase < self.duty:
                out = -1
            else:
                out = 1
        elif self.signal == 'triangle':
            if phase < 0.25:
                out = phase * 4
            elif phase < 0.75:
                out = 1 - 4 * (phase - 0.25)
            else:
                out = -1 + 4 * (phase - 0.75)
        elif self.signal == 'sine':
            out = math.sin(phase*2*math.pi)
        else:
            raise ValueError('bad option for signal')

        out = out * amplitude + self.min
        #print(out)
        return out


class _Pulse(Source):
    def __init__(self, time=1, width=1,
                 off=0, on=1,
                 **kwargs):
        super().__init__(**kwargs)
        
        self.t_on = time
        self.t_off =time + width
        self.off = off
        self.on = on

    def output(self, t):
        if self.t_on <= t <= self.t_off:
            out = self.on
        else:
            out = self.off

        #print(out)
        return out

    
class _ScopeXY(Sink):
    def __init__(self, dims=[-1,1], **kwargs):
        super().__init__(**kwargs)
        self.nin = 2
        self.data = []
        
    def update(self):
        # inputs are set
        self.data.append(self.inputs)

class _Scope(Sink):
    def __init__(self, dims=[-1,1], **kwargs):
        super().__init__(**kwargs)
        self.nin = 2
        self.data = []
        
    def update(self):
        # inputs are set
        self.data.append(self.inputs)


class _Bicycle(Transfer):
    def __init__(self, x0=None, L=1, **kwargs):
        super().__init__(**kwargs)
        self.nin = 2
        self.nout = 3
        self.nstates = 3
        self.L = L
        if x0 is None:
            self.x0 = np.zeros((slef.nstates,))
        else:
            assert len(x0) == self.nstates, "x0 is {:d} long, should be {:d}".format(len(x0), self.nstates)
            self.x0 = x0
        
    def output(self, t):
        return self.x
    
    def deriv(self):
        theta = self.x[2]
        v = self.inputs[0]; gamma = self.inputs[1
                                                ]
        return np.r_[v*math.cos(theta), v*math.sin(theta), v*math.tan(gamma)/self.L ]
