#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Define fundamental blocks available for use in block diagrams.

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
from matplotlib.pyplot import Polygon

import spatialmath.base as sm

from bdsim.components import *



# TODO stop sim, pass in a lambda



# ------------------------------------------------------------------------ #

@block
class _ScopeXY(Sink):
    """
    Plot one input against the other.
    """
    
    def __init__(self, style=None, scale='auto', labels=['X', 'Y'], init=None, **kwargs):
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
        if init is not None:
            assert callable(init), 'graphics init function must be callable'
        self.init = init

        self.styles = style
        if scale != 'auto':
            if len(scale) == 2:
                scale = scale * 2
        self.scale = scale
        self.labels = labels
        
    def start(self, **kwargs):
        # create the plot
        if self.sim.graphics:
            super().reset()

            self.fig = self.sim.create_figure()
            self.ax = self.fig.gca()
            
            args = []
            kwargs = {}
            style = self.styles
            if isinstance(style, dict):
                kwargs = style
            elif isinstance(style, str):
                args = [style]
            self.line, = self.ax.plot(self.xdata, self.ydata, *args, **kwargs)
                
            self.ax.grid(True)
            self.ax.set_xlabel(self.labels[0])
            self.ax.set_ylabel(self.labels[1])
            self.ax.set_title(self.name)
            if self.scale != 'auto':
                self.ax.set_xlim(*self.scale[0:2])
                self.ax.set_ylim(*self.scale[2:4])
            if self.init is not None:
                self.init(self.ax)

        
    def step(self):
        # inputs are set
        self.xdata.append(self.inputs[0])
        self.ydata.append(self.inputs[1])
        if self.sim.graphics:
            plt.figure(self.fig.number)
            self.line.set_data(self.xdata, self.ydata)
        
            plt.draw()
            plt.show(block=False)
            if self.sim.animation:
                self.fig.canvas.start_event_loop(0.001)
        
            if self.scale == 'auto':
                self.ax.relim()
                self.ax.autoscale_view()
        
    def done(self, block=False, **kwargs):
        if self.sim.graphics:
            plt.show(block=block)
            
# ------------------------------------------------------------------------ #

@block
class _Vehicle(Sink):
    """
    Animate a vehicle
    """
    
    def __init__(self, path=True, pathstyle=None, shape='triangle', color="blue", fill="white", size=1, scale='auto', labels=['X', 'Y'], square=True, init=None, **kwargs):
        """
        Create a vehile animation.
        
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
        self.nin = 3
        self.xdata = []
        self.ydata = []
        self.type = 'vehicle'
        if init is not None:
            assert callable(init), 'graphics init function must be callable'
        self.init = init
        self.square = square

        self.path = path
        if path:
            self.pathstyle = pathstyle
        self.color = color
        self.fill = fill
        
        if scale != 'auto':
            if len(scale) == 2:
                scale = scale * 2
        self.scale = scale
        self.labels = labels
        
        d = size
        if shape == 'triangle':
            L = d
            W = 0.6*d
            vertices = [(L, 0), (-L, -W), (-L, W)]
        elif shape == 'box':
            L1 = d
            L2 = d
            W = 0.6*d
            vertices = [(-L1, W), (0.6*L2, W), (L2, 0.5*W), (L2, -0.5*W), (0.6*L2, -W), (-L1, -W)]
        else:
            raise ValueError('bad vehicle shape specified')
        self.vertices_hom = sm.e2h(np.array(vertices).T)
        self.vertices = np.array(vertices)

        
    def start(self, **kwargs):
        # create the plot
        super().reset()
        if self.sim.graphics:
            self.fig = self.sim.create_figure()
            self.ax = self.fig.gca()
            if self.square:
                self.ax.set_aspect('equal')
            
            args = []
            kwargs = {}
            if self.path:
                style = self.pathstyle
                if isinstance(style, dict):
                    kwargs = style
                elif isinstance(style, str):
                    args = [style]
                self.line, = self.ax.plot(self.xdata, self.ydata, *args, **kwargs)
            poly = Polygon(self.vertices, closed=True, edgecolor=self.color, facecolor=self.fill)
            self.vehicle = self.ax.add_patch(poly)

            self.ax.grid(True)
            self.ax.set_xlabel(self.labels[0])
            self.ax.set_ylabel(self.labels[1])
            self.ax.set_title(self.name)
            if self.scale != 'auto':
                self.ax.set_xlim(*self.scale[0:2])
                self.ax.set_ylim(*self.scale[2:4])
            if self.init is not None:
                self.init(self.ax)

        
    def step(self):
        # inputs are set
        if self.sim.graphics:
            self.xdata.append(self.inputs[0])
            self.ydata.append(self.inputs[1])
            plt.figure(self.fig.number)
            if self.path:
                self.line.set_data(self.xdata, self.ydata)
            T = sm.transl2(self.inputs[0], self.inputs[1]) @ sm.trot2(self.inputs[2])
            new = sm.h2e(T @ self.vertices_hom)
            self.vehicle.set_xy(new.T)
        
            plt.draw()
            plt.show(block=False)
            if self.sim.animation:
                self.fig.canvas.start_event_loop(0.001)
        
            if self.scale == 'auto':
                self.ax.relim()
                self.ax.autoscale_view()
        
    def done(self, block=False, **kwargs):
        if self.sim.graphics:
            plt.show(block=block)

# ------------------------------------------------------------------------ #

@block
class _Scope(Sink):
    """
    Plot input ports against time.  Each line can have its own color or style.
    """
    
    def __init__(self, nin=1, styles=None, scale='auto', labels=None, grid=True, **kwargs):
        """
        Create a block that plots input ports against time.
        
        :param nin: number of inputs, defaults to length of style vector if given,
                    otherwise 1
        :type nin: int, optional
        :param styles: styles for each line to be plotted
        :type styles: optional str or dict, list of strings or dicts; one per line
        :param scale: y-axis scale, defaults to 'auto'
        :type scale: 2-element sequence
        :param labels: vertical axis labels
        :type labels: sequence of strings
        :param grid: draw a grid, default is on. Can be boolean or a tuple of 
        options for grid()
        :type grid: bool or sequence
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
        if styles is not None:
            self.styles = list(styles)
            if nin is not None:
                assert nin == len(styles), 'need one style per input'
            nin = len(styles)
        else:
            self.styles = [None,] * nin
            
        if labels is not None:
            self.labels = list(labels)
            if nin is not None:
                assert nin == len(labels), 'need one label per input'
            nin = len(labels)
        else:
            self.labels = ['input%d'%(i,) for i in range(0, nin)]
            
        self.nin = nin
        
        self.grid = grid
                 
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
        
    def start(self, **kwargs):
        # create the plot
        if self.sim.graphics:
            super().reset()   # TODO should this be here?
            if self.sim.graphics:
                self.fig = self.sim.create_figure()
                self.ax = self.fig.gca()
                for i in range(0, self.nin):
                    args = []
                    kwargs = {}
                    style = self.styles[i]
                    if isinstance(style, dict):
                        kwargs = style
                    elif isinstance(style, str):
                        args = [style]
                    self.line[i], = self.ax.plot(self.tdata, self.ydata[i], *args, label=self.styles[i], **kwargs)
                    self.ax.set_ylabel(self.labels[i+1])
                    
                if self.grid is True:
                    self.ax.grid(self.grid)
                elif isinstance(self.grid, (list, tuple)):
                    self.ax.grid(True, *self.grid)
                    
                self.ax.set_xlim(0, self.sim.T)
                # self.ax.set_ylim(-2, 2)
                self.ax.set_xlabel(self.labels[0])
    
                self.ax.set_title(self.name)
                if self.scale != 'auto':
                    self.ax.set_ylim(*self.scale)
        
    def step(self):
        # inputs are set
        if self.sim.graphics:
            self.tdata = np.append(self.tdata, self.sim.t)
            for i,input in enumerate(self.inputs):
                self.ydata[i] = np.append(self.ydata[i], input)
            if self.sim.graphics:
                plt.figure(self.fig.number)
                for i in range(0, self.nin):
                    self.line[i].set_data(self.tdata, self.ydata[i])
            
                plt.draw()
                plt.show(block=False)
                if self.sim.animation:
                    self.fig.canvas.start_event_loop(0.001)
            
                if self.scale == 'auto':
                    self.ax.relim()
                    self.ax.autoscale_view(scalex=False, scaley=True)
        
    def done(self, block=False, **kwargs):
        if self.sim.graphics:
            plt.show(block=block)



if __name__ == "__main__":


    import unittest

    class BlockTest(unittest.TestCase):

        def test_scope(self):
            pass
        
        def test_scopexy(self):
            pass
