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

import matplotlib.pyplot as plt
import time

from bdsim.Block import *



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

# ------------------------------------------------------------------------ #
class _Constant(Source):
    
    def __init__(self, value=None, **kwargs):
        super().__init__(**kwargs)
        self.value = [value]
        self.type = 'constant'

    def output(self, t):
        return self.value               

# ------------------------------------------------------------------------ #

class _WaveForm(Source):
    def __init__(self, freq=1, unit='Hz', phase0=0, wave='square',
                 min=0, max=1, duty=0.5, # for square
                 amplitude=1, offset=0,  # for sine, triangle
                 **kwargs):
        super().__init__(**kwargs)

        assert 0<duty<1, 'duty must be in range [0,1]'
        assert max > min, 'maximum value must be greater than minimum'
        
        self.wave = wave
        if unit == 'Hz':
            self.freq = freq
        elif unit == 'rad/s':
            self.freq = freq / (2 * math.pi)
        self.phase0 = phase0
        self.min = min
        self.max = max
        self.duty = duty
        self.amplitude = amplitude
        self.offset = offset
        self.type = 'waveform'

    def output(self, t):
        T = 1.0 / self.freq
        phase = (t * self.freq - self.phase0 ) % 1.0
        
        amplitude = self.max - self.min
        
        # define all signals in the range -1 to 1
        if self.wave == 'square':
            if phase < self.duty:
                out = self.min
            else:
                out = self.max
        elif self.wave == 'triangle':
            if phase < 0.25:
                out = phase * 4
            elif phase < 0.75:
                out = 1 - 4 * (phase - 0.25)
            else:
                out = -1 + 4 * (phase - 0.75)
        elif self.wave == 'sine':
            out = math.sin(phase*2*math.pi)
        else:
            raise ValueError('bad option for signal')

        #print(out)
        return [out]

# ------------------------------------------------------------------------ #

class _Pulse(Source):
    def __init__(self, T=1, width=1,
                 off=0, on=1,
                 **kwargs):
        super().__init__(**kwargs)
        
        self.t_on = T
        self.t_off =T + width
        self.off = off
        self.on = on
        self.type = "pulsegen"

    def output(self, t):
        if self.t_on <= t <= self.t_off:
            out = self.on
        else:
            out = self.off

        #print(out)
        return [out]
    
# ------------------------------------------------------------------------ #

class _Step(Source):
    def __init__(self, T=1,
                 off=0, on=1,
                 **kwargs):
        super().__init__(**kwargs)
        
        self.T = T
        self.off = off
        self.on = on
        self.type = "step"
        self.nout = 1

    def output(self, t):
        if t >= self.T:
            out = self.on
        else:
            out = self.off

        #print(out)
        return [out]

# ------------------------------------------------------------------------ #

class _ScopeXY(Sink):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.nin = 2
        self.xdata = []
        self.ydata = []
        self.type = 'scopexy'
        
        #TODO, fixed vs autoscale, color
        
    def start(self):
        # create the plot
        super().reset()
        if self.sim.graphics:
            self.fig = plt.figure()
            self.ax = self.fig.gca()
            self.line, = self.ax.plot(self.xdata, self.ydata)
            # self.ax.set_xlim(-2, 2)
            # self.ax.set_ylim(-2, 2)
            self.ax.grid(True)
            self.ax.set_xlabel('X')
            self.ax.set_ylabel('Y')
            self.ax.set_title(self.name)
        
    def step(self):
        # inputs are set
        self.xdata.append(self.inputs[0])
        self.ydata.append(self.inputs[1])
        if self.sim.graphics:
            self.line.set_data(self.xdata, self.ydata)
        
            plt.draw()
            plt.show(block=False)
            self.fig.canvas.start_event_loop(0.001)
        
            self.ax.relim()
            self.ax.autoscale_view()
        
    def done(self):
        print('ScopeXY done')
        if self.sim.graphics:
            plt.show(block=True)

# ------------------------------------------------------------------------ #

class _Scope(Sink):
    def __init__(self, nin=1, **kwargs):
        super().__init__(**kwargs)
        self.nin = 1
        self.tdata = []
        self.ydata = [[]]*nin
        self.line = [None]*nin
        self.type = 'scope'
        
        # TODO, fixed vs autoscale, color, wire width
        
    def start(self):
        # create the plot
        super().reset()   # TODO should this be here?
        if self.sim.graphics:
            self.fig = plt.figure()
            self.ax = self.fig.gca()
            for i in range(0, self.nin):
                self.line[i], = self.ax.plot(self.tdata, self.ydata[i])
            self.ax.set_xlim(0, self.sim.T)
            # self.ax.set_ylim(-2, 2)
            self.ax.grid(True)
            self.ax.set_xlabel('X')
            self.ax.set_ylabel('Y')
            self.ax.set_title(self.name)
        
    #TODO need t
    def step(self):
        # inputs are set
        self.tdata.append(self.sim.t)
        for i in range(0, self.nin):
            self.ydata[i].append(self.inputs[i])
        if self.sim.graphics:
            for i in range(0, self.nin):
                self.line[i].set_data(self.tdata, self.ydata[i])
        
            plt.draw()
            plt.show(block=False)
            self.fig.canvas.start_event_loop(0.001)
        
            self.ax.relim()
            self.ax.autoscale_view(scalex=False, scaley=True)
        
    def done(self):
        print('Scope done')
        if self.sim.graphics:
            plt.show(block=True)

# ------------------------------------------------------------------------ #

class _Integrator(Transfer):
    def __init__(self, N=1, order=1, limit=None, **kwargs):
        super().__init__(**kwargs)
        self.N = N
        self.order = order
        self.limit = limit
        
        self.nin = N
        self.nout = N
        self.nstates = N*order

# ------------------------------------------------------------------------ #

class _LTI_SISO(Transfer):
    def __init__(self, N=1, D=[1, 1], order=1, x0=None, limit=None, **kwargs):
        super().__init__(**kwargs)
        if not isinstance(N, list):
            N = [N]
        if not isinstance(D, list):
            D = [D]
        self.N = N
        self.D = N
        n = len(D) - 1
        nn = len(N)
        if x0 is None:
            self.x0 = np.zeros((n,))
        else:
            self.x0 = x0
        assert nn <= n, 'direct pass through is not supported'
        self.type = 'LTI'
        
        self.nin = 1
        self.nout = 1
        self.nstates = n
        
        self.A = np.eye(len(D)-1, k=1)
        D = [-d/D[0] for d in D]
        self.B = np.zeros((n,))
        if n == 1:
            self.A[0,0] = D[-1]
            self.B[0] = 1
        else:
            self.A[-1,:] = D[::-1]
            self.B[-1] = 1
        nn = len(N)
        self.B = np.array([[0.5]])
        self.C = np.array([[1]])
        #self.C = np.r_[N[::-1], np.zeros((n-nn,))]
        print('A=', self.A)
        print('B=', self.B)
        print('C=', self.C)
        
    def output(self, t):
        return list(self.C*self.x)
    
    def deriv(self):
        return self.A@self.x + self.B@np.array(self.inputs)

# ------------------------------------------------------------------------ #

class _Sum(Function):
    def __init__(self, signs, **kwargs):
        super().__init__(**kwargs)
        assert isinstance(signs, str), 'first argument must be signs string'
        self.nin = len(signs)
        self.nout = 1
        self.type = 'sum'
        self.signs = signs
        
        signdict = {'+': 1, '-': -1, '~': -1}
        self.gain = [signdict[s] for s in signs]
        
    def output(self, t):
        sum = 0
        for i,input in enumerate(self.inputs):
            sum += self.gain[i] * input
        return [sum]

# ------------------------------------------------------------------------ #

class _Gain(Function):
    def __init__(self, gain, **kwargs):
        super().__init__(**kwargs)
        self.nin = 1
        self.nout = 1
        self.gain  = gain
        self.type = 'gain'
        
    def output(self, t):
        return [self.inputs[0] * self.gain]
        
# pulse + pulse train (on, len, ampl) list, min=0
# interpolate
# gain
# code, function or lambda, len(inspect.signature(f).parameters
# sum
# PID
# product
# matrix inv
# saturation

# subsystem

# transform 3D points