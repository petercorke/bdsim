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

class _Constant(Source):
    
    def __init__(self, value=None, **kwargs):
        super().__init__(**kwargs)
        self.value = [value]

    def output(self, t):
        return self.value               


class _WaveForm(Source):
    def __init__(self, freq=1, unit='Hz', phase0=0, signal='square',
                 min=0, max=1, duty=0.5, # for square
                 amplitude=1, offset=0,  # for sine, triangle
                 **kwargs):
        super().__init__(**kwargs)

        assert 0<duty<1, 'duty must be in range [0,1]'
        assert max > min, 'maximum value must be greater than minimum'
        
        self.signal = signal
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

    def output(self, t):
        T = 1.0 / self.freq
        phase = (t * self.freq - self.phase0 ) % 1.0
        
        amplitude = self.max - self.min
        
        # define all signals in the range -1 to 1
        if self.signal == 'square':
            if phase < self.duty:
                out = self.min
            else:
                out = self.max
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

        #print(out)
        return [out]


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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.nin = 2
        self.xdata = []
        self.ydata = []
        
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


class _Scope(Sink):
    def __init__(self, nin=1, **kwargs):
        super().__init__(**kwargs)
        self.nin = 1
        self.tdata = []
        self.ydata = [[]]*nin
        self.line = [None]*nin
        
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
        print('ScopeXY done')
        if self.sim.graphics:
            plt.show(block=True)

class _Integrator(Transfer):
    def __init__(self, N=1, order=1, limit=None, **kwargs):
        self.N = N
        self.order = order
        self.limit = limit
        
        self.nin = N
        self.nout = N
        self.nstates = N*order

class _SISO_LTI(Transfer):
    def __init__(self, N=1, D=[1, 1], order=1, limit=None, **kwargs):
        self.N = N
        self.D = N
        n = len(D) - 1
        nn = len(N)
        assert nn <= n, 'direct pass through is not supported'
        
        self.nin = 1
        self.nout = 1
        self.nstates = n
        
        self.A = sp.eye(len(D)-1, k=1)
        D /= D[0]
        self.A[-1,:] = -D[::-1]
        self.B = np.zeros((n,))
        self.B[-1] = 1
        nn = len(N)
        self.C = np.r_[N[::-1], np.zeros((n-nn,))]
        print('A=', A)
        print('B=', B)
        print('C=', C)


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
        return list(self.x)
    
    def deriv(self):
        theta = self.x[2]
        v = self.inputs[0]; gamma = self.inputs[1]
        xd = np.r_[v*math.cos(theta), v*math.sin(theta), v*math.tan(gamma)/self.L ]
        return xd
