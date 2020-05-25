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

from bdsim.components import Sink, Source, Transfer, Function



# ---------------------------------- simulation elements ---------------- #

# could create a decorator for each of these
"""
maybe ??

perhaps add decorator adds the class to a global list _block_classes

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
        """
        Create a constant block.
        
        :param value: the constant, defaults to None
        :type value: any
        :param **kwargs: common Block options
        :return: a STEP block
        :rtype: _Constant
        
        This block has only one output port, but the value can be any 
        Python type, so long as the connected input port can handle it.
        For example float, list or numpy ndarray.

        """
        super().__init__(**kwargs)
        self.value = [value]
        self.type = 'constant'

    def output(self, t):
        return self.value               

# ------------------------------------------------------------------------ #

class _WaveForm(Source):
    def __init__(self, wave='square',
                 freq=1, unit='Hz', phase0=0, amplitude=1, offset=0,
                 min=None, max=None, duty=0.5,
                 **kwargs):
        """
        Create a waveform generator block.
        
        :param wave: type of waveform to generate: 'sine', 'square' [default], 'triangle'
        :type wave: str, optional
        :param freq: frequency, defaults to 1
        :type freq: float, optional
        :param unit: frequency unit, can be 'rad/s', defaults to 'Hz'
        :type unit: str, optional
        :param amplitude: amplitude, defaults to 1
        :type amplitude: float, optional
        :param offset: signal offset, defaults to 0
        :type offset: float, optional        :param phase0: Initial phase of signal in the range [0,1], defaults to 0
        :type phase0: float, optional
        :param min: minimum value, defaults to 0
        :type min: float, optional
        :param max: maximum value, defaults to 1
        :type max: float, optional
        :param duty: duty cycle for square wave in range [0,1], defaults to 0.5
        :type duty: float, optional
        :param **kwargs: common Block options
        :return: a STEP block
        :rtype: _Step
        
        Examples::
            
            WAVEFORM(wave='sine', freq=2)   # 2Hz sine wave varying from -1 to 1
            WAVEFORM(wave='square', freq=2, unit='rad/s') # 2rad/s square wave varying from -1 to 1
            
        The minimum and maximum values of the waveform are given by default in
        terms of amplitude and offset. The signals are symmetric about the offset 
        value. For example::
            
            WAVEFORM(wave='sine') varies between -1 and +1
            WAVEFORM(wave='sine', amplitude=2) varies between -2 and +2
            WAVEFORM(wave='sine', offset=1) varies between 0 and +2
            WAVEFORM(wave='sine', amplitude=2, offset=1) varies between -1 and +3
            
        Alternatively we can specify the minimum and maximum values which override
        amplitude and offset::
            
            WAVEFORM(wave='triangle', min=0, max=5) varies between 0 and +5
        
        At time 0 the sine and triangle wave are zero and increasing, and the
        square wave has its first rise.  We can specify a phase shift with 
        a number in the range [0,1] where 1 corresponds to one cycle.
        
        """
        super().__init__(**kwargs)

        assert 0<duty<1, 'duty must be in range [0,1]'
        
        self.wave = wave
        if unit == 'Hz':
            self.freq = freq
        elif unit == 'rad/s':
            self.freq = freq / (2 * math.pi)
        self.phase0 = phase0
        if max is not None and min is not None:
            amplitude = (max - min) / 2
            offset = (max + min) / 2 
            self.min = min
            self.max = max
        self.duty = duty
        self.amplitude = amplitude
        self.offset = offset
        self.type = 'waveform'

    def output(self, t):
        T = 1.0 / self.freq
        phase = (t * self.freq - self.phase0 ) % 1.0
        
        # define all signals in the range -1 to 1
        if self.wave == 'square':
            if phase < self.duty:
                out = -1
            else:
                out = 1
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

        out = out * self.amplitude + self.offset

        #print('waveform = ', out)
        return [out]

# ------------------------------------------------------------------------ #

# class _Pulse(Source):
#     def __init__(self, T=1, width=1,
#                  off=0, on=1,
#                  **kwargs):
#         super().__init__(**kwargs)
        
#         self.t_on = T
#         self.t_off =T + width
#         self.off = off
#         self.on = on
#         self.type = "pulsegen"

#     def output(self, t):
#         if self.t_on <= t <= self.t_off:
#             out = self.on
#         else:
#             out = self.off

#         #print(out)
#         return [out]
    
# ------------------------------------------------------------------------ #

class _Step(Source):
    def __init__(self, T=1,
                 off=0, on=1,
                 **kwargs):
        """
        Create a step signal block.
        
        :param T: time of step, defaults to 1
        :type T: float, optional
        :param off: initial value, defaults to 0
        :type off: float, optional
        :param on: final value, defaults to 1
        :type on: float, optional
        :param **kwargs: common Block options
        :return: a STEP block
        :rtype: _Step

        """
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
    """
    Plot one nput against the other.  Each line can have its own color or style.
    """
    
    def __init__(self, style=None, scale='auto', labels=['X', 'Y'], **kwargs):
        """
        Create an XY scope.
        
        :param style: line style
        :type style: optional str or dict
        :param scale: y-axis scale, defaults to 'auto'
        :type scale: 2- or 4-element sequence
        :param labels: axis labels (xlabel, ylabel)
        :type labels: 2-element tuple or list
        :param **kwargs: common Block options
        :return: A SCOPEXY block
        :rtype: _Scope

        This block has two inputs which are plotted against each other. Port 0
        is the horizontal axis, and port 1 is the vertical axis.
        
        The line style is given by either:
            
            - a dict of options for `plot` ,or
            - as a simple MATLAB-style linestyle like 'k--'.
        
        The scale factor defaults to auto-scaling but can be fixed by
        providing either:
            - a 2-tuple [min, max] which is used for the x- and y-axes
            - a 4-tuple [xmin, xmax, ymin, ymax]
            
        """
        super().__init__(**kwargs)
        self.nin = 2
        self.xdata = []
        self.ydata = []
        self.type = 'scopexy'

        self.styles = style
        if scale != 'auto':
            if len(scale) == 2:
                scale = scale * 2
        self.scale = scale
        self.labels = labels
        
    def start(self):
        # create the plot
        super().reset()
        if self.sim.graphics:
            self.fig = plt.figure()
            self.ax = self.fig.gca()
            
            args = []
            kwargs = {}
            style = self.styles
            if isinstance(style, dict):
                kwargs = style
            elif isinstance(style, str):
                args = [style]
            self.line, = self.ax.plot(self.xdata, self.ydata, *args, **kwargs)
                
            # self.ax.set_xlim(-2, 2)
            # self.ax.set_ylim(-2, 2)
            self.ax.grid(True)
            self.ax.set_xlabel(self.labels[0])
            self.ax.set_ylabel(self.labels[1])
            self.ax.set_title(self.name)
            if self.scale != 'auto':
                self.ax.set_xlim(*self.scale[0:2])
                self.ax.set_ylim(*self.scale[2:4])
        
    def step(self):
        # inputs are set
        self.xdata.append(self.inputs[0])
        self.ydata.append(self.inputs[1])
        if self.sim.graphics:
            self.line.set_data(self.xdata, self.ydata)
        
            plt.draw()
            plt.show(block=False)
            self.fig.canvas.start_event_loop(0.001)
        
            if self.scale == 'auto':
                self.ax.relim()
                self.ax.autoscale_view()
        
    def done(self):
        print('ScopeXY done')
        if self.sim.graphics:
            plt.show(block=True)

# ------------------------------------------------------------------------ #

class _Scope(Sink):
    """
    Plot input ports against time.  Each line can have its own color or style.
    """
    
    def __init__(self, nin=None, style=None, scale='auto', labels=None, **kwargs):
        """
        Create a block that plots input ports against time.
        
        :param nin: number of inputs, defaults to length of style vector if given,
                    otherwise 1
        :type nin: int, optional
        :param style: styles for each line to be plotted
        :type style: optional str or dict, list of strings or dicts; one per line
        :param scale: y-axis scale, defaults to 'auto'
        :type scale: 2-element sequence
        :param **kwargs: common Block options
        :return: A SCOPE block
        :rtype: _Scope
        
        Line styles are given by either a dict of options for `plot` or as
        a simple MATLAB-style linestyle like 'k--'.
        
        If multiple lines are plotted then a list of styles, dicts or strings,
        one per line must be given.
        
        The vertical scale factor defaults to auto-scaling but can be fixed by
        providing a 2-tuple [ymin, ymax]. All lines are plotted against the
        same vertical scale.
        
        Examples::
            
            SCOPE()
            SCOPE(nin=2)
            SCOPE(nin=2, scale=[-1,,2])
            SCOPE(style=['k', 'r--'])
            SCOPE(style='k--')
            SCOPE(style={'color:', 'red, 'linestyle': '--''})
        """
        super().__init__(**kwargs)

        self.type = 'scope'
        if style is not None:
            self.styles = list(style)
            nin = len(style)
        else:
            if nin is None:
                nin = 1     # default number of inputs
            self.styles = [None,] * nin
        self.nin = nin
                 
        # init the arrays that hold the data
        self.tdata = np.array([])
        self.ydata = [np.array([]),] * nin
        
        self.line = [None]*nin
        self.scale = scale
        
        if labels is None:
            labels = ['Y'+str(i) for i in range(0, nin)]
            labels.insert(0, 'Time')
        self.labels = labels
        # TODO, wire width
        # inherit names from wires, block needs to be able to introspect
        
    def start(self):
        # create the plot
        super().reset()   # TODO should this be here?
        if self.sim.graphics:
            self.fig = plt.figure()
            self.ax = self.fig.gca()
            for i in range(0, self.nin):
                args = []
                kwargs = {}
                style = self.styles[i]
                if isinstance(style, dict):
                    kwargs = style
                elif isinstance(style, str):
                    args = [style]
                self.line[i], = self.ax.plot(self.tdata, self.ydata[i], *args, **kwargs)
                self.ax.set_ylabel(self.labels[i+1])
            self.ax.set_xlim(0, self.sim.T)
            # self.ax.set_ylim(-2, 2)
            self.ax.grid(True)
            self.ax.set_xlabel(self.labels[0])

            self.ax.set_title(self.name)
            if self.scale != 'auto':
                self.ax.set_ylim(*self.scale)
        
    def step(self):
        # inputs are set
        self.tdata = np.append(self.tdata, self.sim.t)
        for i,input in enumerate(self.inputs):
            self.ydata[i] = np.append(self.ydata[i], input)
        if self.sim.graphics:
            plt.figure(self.fig.number)
            for i in range(0, self.nin):
                self.line[i].set_data(self.tdata, self.ydata[i])
        
            plt.draw()
            plt.show(block=False)
            self.fig.canvas.start_event_loop(0.001)
        
            if self.scale == 'auto':
                self.ax.relim()
                self.ax.autoscale_view(scalex=False, scaley=True)
        
    def done(self):
        print('Scope done')
        if self.sim.graphics:
            plt.show(block=True)

# ------------------------------------------------------------------------ #

# class _Integrator(Transfer):
#     def __init__(self, N=1, order=1, limit=None, **kwargs):
#         super().__init__(**kwargs)
#         self.N = N
#         self.order = order
#         self.limit = limit
        
#         self.nin = N
#         self.nout = N
#         self.nstates = N*order

# ------------------------------------------------------------------------ #

class _LTI_SISO(Transfer):
    def __init__(self, N=1, D=[1, 1], x0=None, **kwargs):
        """
        Create a SISO LTI block.
        
        :param N: numerator coefficients, defaults to 1
        :type N: array_like, optional
        :param D: denominator coefficients, defaults to [1, 1]
        :type D: array_like, optional
        :param x0: initial states, defaults to zero
        :type x0: array_like, optional
        :param **kwargs: common Block options
        :return: A SCOPE block
        :rtype: _LTI_SISO
        
        Describes the dynamics of a single-input single-output (SISO) linear
        time invariant (LTI) system described by numerator and denominator
        polynomial coefficients.

        Coefficients are given in the order from highest order to zeroth 
        order, ie. :math:`2s^2 - 4s +3` is `[2 -4 3].
        
        Only proper transfer functions, where order of numerator is less
        than denominator are allowed.
        
        The order of the states in `x0` is consistent with controller canonical
        form.
        
        Examples::
            
            LTI_SISO(N=[1,2], D=[2, 3, -4])
            
        is the transfer function :math:`\frac{s+2}{2s^2+3s-4}`

        """
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
        
        # convert to numpy arrays
        N = np.r_[np.zeros((len(D)-len(N),)), np.array(N)]
        D = np.array(D)
        
        # normalize the coefficients to obtain
        #
        #   b_0 s^n + b_1 s^(n-1) + ... + b_n
        #   ---------------------------------
        #   a_0 s^n + a_1 s^(n-1) + ....+ a_n
        

        # normalize so leading coefficient of denominator is one
        D0 = D[0]
        D = D / D0
        N = N / D0
        
        self.A = np.eye(len(D)-1, k=1)  # control canonic (companion matrix) form
        self.A[-1,:] = -D[1:]
        
        self.B = np.zeros((n,1))
        self.B[-1] = 1
        
        self.C = (N[1:] - N[0] * D[1:]).reshape((1,n))
        
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
        """
        Create a summing junction.
        
        :param signs: signs associated with input ports
        :type signs: str
        :param **kwargs: common Block options
        :return: A SCOPE block
        :rtype: _Sum
        
        The number of input ports is determined by the length of the `signs`
        string.  For example::
            
            SUM('+-+')
            
        is a 3-input summing junction where ports 0 and 2 are added and
        port 1 is subtracted.

        """
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
    def __init__(self, gain, order='postmul', **kwargs):
        """
        Create a gain block.
        
        :param gain: The gain value
        :type gain: float
        :param order: the order of multiplication: 'postmul' [default], 'premul'
        :type order: str, optional
        :param **kwargs: common Block options
        :return: A SCOPE block
        :rtype: _Gain
        
        This block has only one input and one output port. The output is the
        product of the input by the gain.
        
        Either or both the input and gain can be numpy arrays and numpy will
        compute the appropriate product.  If both are numpy arrays then the
        matmult operator `@` is used and by default the input is postmultiplied
        by the gain, but this can be changed using the `order` option.

        """
        super().__init__(**kwargs)
        self.nin = 1
        self.nout = 1
        self.gain  = gain
        self.type = 'gain'
        self.order = order
        
    def output(self, t):
        input = self.inputs[0]
        
        if isinstance(input, np.ndarray) and isinstance(self.gain, np.ndarray):
            # array x array case
            if self.order == 'postmul':
                return [input @ self.gain]
            elif self.order == 'premul':
                return [self.gain @ input]
            else:
                raise ValueError('bad value of order')
        else:
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

if __name__ == "__main__":
    a = _LTI_SISO(N=1, D=[1,2])
    
    s = _Scope(nin=2)
    s.reset()
    s.inputs[0] = 3
    s.inputs = np.r_[4]
    s.step()