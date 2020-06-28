"""
Define sink blocks for use in block diagrams.  These are blocks that:

- have inputs but no outputs
- have no state variables
- are a subclass of ``SinkBlock``

Each class MyClass in this module becomes a method MYCLASS() of the Simulation object.
"""

import numpy as np
from math import pi, sqrt, sin, cos, atan2

import matplotlib.pyplot as plt
from matplotlib.pyplot import Polygon


import spatialmath.base as sm

from bdsim.components import SinkBlock, SinkBlockGraphics, block



# ------------------------------------------------------------------------ #

@block
class Print(SinkBlock):
    def __init__(self, fmt=None, *inputs, **kwargs):
        """
        Create a console print block.
        
        :param fmt: Format string, defaults to None
        :type fmt: str, optional
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param ``**kwargs``: common Block options
        :return: A PRINT block
        :rtype: Print instance

        """
        super().__init__(nin=1, inputs=inputs, **kwargs)
        self.format = fmt
        self.type = 'print'
        
        # TODO format can be a string or function

    def step(self):
        print('PRINT {:s} = '.format(self.name), self.inputs)


@block
class ScopeXY(SinkBlockGraphics):
    """
    Plot one input against the other.
    """
    
    def __init__(self, style=None, *inputs, scale='auto', labels=['X', 'Y'], init=None, **kwargs):
        """
        Create an XY scope.
        
        :param style: line style
        :type style: optional str or dict
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param scale: y-axis scale, defaults to 'auto'
        :type scale: 2- or 4-element sequence
        :param labels: axis labels (xlabel, ylabel)
        :type labels: 2-element tuple or list
        :param ``**kwargs``: common Block options
        :return: A SCOPEXY block
        :rtype: ScopeXY instance

        This block has two inputs which are plotted against each other. Port 0
        is the horizontal axis, and port 1 is the vertical axis.
        
        The line style is given by either:
            
            - a dict of options for ``plot``, or
            - as a simple MATLAB-style linestyle like ``'k--'``.
        
        The scale factor defaults to auto-scaling but can be fixed by
        providing either:
            
            - a 2-tuple [min, max] which is used for the x- and y-axes
            - a 4-tuple [xmin, xmax, ymin, ymax]
        """
        super().__init__(nin=2, inputs=inputs, **kwargs)
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
        if self.bd.graphics:
            super().reset()

            self.fig = self.bd.create_figure()
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
            super().start()

        
    def step(self):
        # inputs are set
        self.xdata.append(self.inputs[0])
        self.ydata.append(self.inputs[1])
        if self.bd.graphics:
            plt.figure(self.fig.number)
            self.line.set_data(self.xdata, self.ydata)
        
            plt.draw()
            plt.show(block=False)
            if self.bd.animation:
                self.fig.canvas.start_event_loop(0.001)
        
            if self.scale == 'auto':
                self.ax.relim()
                self.ax.autoscale_view()
            super().step()
        
    def done(self, block=False, **kwargs):
        if self.bd.graphics:
            plt.show(block=block)
            super().done()
            
# ------------------------------------------------------------------------ #

@block
class Vehicle(SinkBlockGraphics):
    """
    Animate a vehicle
    """
    
    def __init__(self, *inputs, path=True, pathstyle=None, shape='triangle', color="blue", fill="white", size=1, scale='auto', labels=['X', 'Y'], square=True, init=None, **kwargs):
        """
        Create a vehile animation.
        
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param style: line style
        :type style: optional str or dict
        :param scale: y-axis scale, defaults to 'auto'
        :type scale: 2- or 4-element sequence
        :param labels: axis labels (xlabel, ylabel)
        :type labels: 2-element tuple or list
        :param ``**kwargs``: common Block options
        :return: A SCOPEXY block
        :rtype: Scope instance

        This block has two inputs which are plotted against each other. Port 0
        is the horizontal axis, and port 1 is the vertical axis.
        
        The line style is given by either:
            
            - a dict of options for ``plot`` ,or
            - as a simple MATLAB-style linestyle like ``'k--'``.
        
        The scale factor defaults to auto-scaling but can be fixed by
        providing either:
            
            - a 2-tuple [min, max] which is used for the x- and y-axes
            - a 4-tuple [xmin, xmax, ymin, ymax]
        """
        super().__init__(nin=3, inputs=inputs, **kwargs)
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
        if self.bd.graphics:
            self.fig = self.bd.create_figure()
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
            super().start()
        
    def step(self):
        # inputs are set
        if self.bd.graphics:
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
            if self.bd.animation:
                self.fig.canvas.start_event_loop(0.001)
        
            if self.scale == 'auto':
                self.ax.relim()
                self.ax.autoscale_view()
            super().step()
        
    def done(self, block=False, **kwargs):
        if self.bd.graphics:
            plt.show(block=block)
            
            super().done()

# ------------------------------------------------------------------------ #

@block
class MultiRotorPlot(SinkBlockGraphics):
    """
    Animate a multi-rotor flyer.
    
    Based on code lovingly coded by Paul Pounds, first coded 17/4/02
    version 2 2004 added scaling and ground display
    version 3 2010 improved rotor rendering and fixed mirroring bug
    
    Displays X-4 flyer position and attitude in a 3D plot.
    GREEN ROTOR POINTS NORTH
    BLUE ROTOR POINTS EAST
    
    PARAMETERS
    s defines the plot size in meters
    swi controls flyer attitude plot; 1 = on, otherwise off.
    
    INPUTS
    1 Center X position
    2 Center Y position
    3 Center Z position
    4 Yaw angle in rad
    5 Pitch angle in rad
    6 Roll angle in rad
    """
     
    def __init__(self, model, *inputs, scale=[-2, 2, -2, 2, 10], flapscale=1, projection='ortho', **kwargs):
        """
        Create a block that displays a multi-rotor flying vehicle.
        
        :param model: A dictionary of vehicle geometric and inertial properties
        :type model: dict
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param scale: dimensions of workspace: xmin, xmax, ymin, ymax, zmin, zmax
        :type scale: array_like
        :param flapscale: exagerate flapping angle by this factor, default is 1
        :type flapscale: float
        :param projection: 3D projection: ortho or perspective, defaults to 'ortho'
        :type projection: str
        :param ``**kwargs``: common Block options
        :return: a MULTIROTOPLOT block
        :rtype: MultiRobotPlot instance

        """
        super().__init__(nin=1, inputs=inputs, **kwargs)
        self.type = 'quadrotorplot'
        self.model = model
        self.scale = scale
        self.nrotors = model['nrotors']
        self.projection = projection
        self.flapscale = flapscale

    def start(self):
        quad = self.model
        
        # vehicle dimensons
        d = quad['d'];  # Hub displacement from COG
        r = quad['r'];  # Rotor radius

        #C = np.zeros((3, self.nrotors))   ## WHERE USED?
        self.D = np.zeros((3,self.nrotors))

        for i in range(0, self.nrotors):
            theta = i / self.nrotors * 2 * pi
            #  Di      Rotor hub displacements (1x3)
            # first rotor is on the x-axis, clockwise order looking down from above
            self.D[:,i] = np.r_[ quad['d'] * cos(theta), quad['d'] * sin(theta), quad['h']]
        
        #draw ground
        self.fig = plt.figure()
        # no axes in the figure, create a 3D axes
        self.ax = self.fig.add_subplot(111, projection='3d', proj_type=self.projection)

        # ax.set_aspect('equal')
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('-Z (height above ground)')
        
        # TODO allow user to set maximum height of plot volume
        self.ax.set_xlim(self.scale[0], self.scale[1])
        self.ax.set_ylim(self.scale[2], self.scale[3])
        self.ax.set_zlim(0, self.scale[4])

        # plot the ground boundaries and the big cross
        self.ax.plot([self.scale[0], self.scale[2]], [self.scale[1], self.scale[3]], [0, 0], 'b-')
        self.ax.plot([self.scale[0], self.scale[3]], [self.scale[1], self.scale[2]], [0, 0], 'b-')
        self.ax.grid(True)
        
        self.shadow, = self.ax.plot([0, 0], [0, 0], 'k--')
        self.groundmark, = self.ax.plot([0], [0], [0], 'kx')
        
        self.arm = []
        self.disk = []
        for i in range(0, self.nrotors):
            h, = self.ax.plot([0], [0], [0])
            self.arm.append(h)
            if i == 0:
                color = 'b-'
            else:
                color = 'g-'
            h, = self.ax.plot([0], [0], [0], color)
            self.disk.append(h)
            
        self.a1s = np.zeros((self.nrotors,))
        self.b1s = np.zeros((self.nrotors,))

    def step(self):

        def plot3(h, x, y, z):
            h.set_data(x, y)
            h.set_3d_properties(z)
            
        # READ STATE
        z = self.inputs[0][0:3]
        n = self.inputs[0][3:6]
        
        # TODO, check input dimensions, 12 or 12+2N, deal with flapping
        
        a1s = self.a1s
        b1s = self.b1s
        
        quad = self.model
        
        # vehicle dimensons
        d = quad['d'];  # Hub displacement from COG
        r = quad['r'];  # Rotor radius
        
        # PREPROCESS ROTATION MATRIX
        phi = n[0];    # Euler angles
        the = n[1];
        psi = n[2];
        
        # BBF > Inertial rotation matrix
        R = np.array([
                [cos(the) * cos(phi), sin(psi) * sin(the) * cos(phi) - cos(psi) * sin(phi), cos(psi) * sin(the) * cos(phi) + sin(psi) * sin(phi)],   
                [cos(the) * sin(phi), sin(psi) * sin(the) * sin(phi) + cos(psi) * cos(phi), cos(psi) * sin(the) * sin(phi) - sin(psi)*  cos(phi)],
                [-sin(the),           sin(psi)*cos(the),                                    cos(psi) * cos(the)]
            ])
        
        # Manual Construction
        #Q3 = [cos(psi) -sin(psi) 0;sin(psi) cos(psi) 0;0 0 1];   %Rotation mappings
        #Q2 = [cos(the) 0 sin(the);0 1 0;-sin(the) 0 cos(the)];
        #Q1 = [1 0 0;0 cos(phi) -sin(phi);0 sin(phi) cos(phi)];
        #R = Q3*Q2*Q1;    %Rotation matrix
        
        # CALCULATE FLYER TIP POSITONS USING COORDINATE FRAME ROTATION
        F = np.array([
                [1,  0,  0],
                [0, -1,  0],
                [0,  0, -1]
            ])
        
        # Draw flyer rotors
        theta = np.linspace(0, 2 * pi, 20)
        circle = np.zeros((3, 20))
        for j, t in enumerate(theta):
            circle[:,j] = np.r_[r * sin(t), r * cos(t), 0]
        
        hub = np.zeros((3, self.nrotors))
        tippath = np.zeros((3, 20, self.nrotors))
        for i in range(0, self.nrotors):
            hub[:,i] = F @ (z + R @ self.D[:,i])  # points in the inertial frame
            
            q = self.flapscale   # Flapping angle scaling for output display - makes it easier to see what flapping is occurring
            # Rotor -> Plot frame
            Rr = np.array([
                    [cos(q * a1s[i]),  sin(q * b1s[i]) * sin(q * a1s[i]),  cos(q * b1s[i]) * sin(q * a1s[i])],
                    [0,                cos(q * b1s[i]),                   -sin(q*b1s[i])],
                    [-sin(q * a1s[i]), sin(q * b1s[i]) * cos(q * a1s[i]),  cos(q * b1s[i]) * cos(q * a1s[i])]
                ])
            
            tippath[:,:,i] = F @ R @ Rr @ circle
            plot3(self.disk[i], hub[0,i] + tippath[0,:,i], hub[1,i] + tippath[1,:,i], hub[2,i] + tippath[2,:,i])

        # Draw flyer
        hub0 = F @ z  # centre of vehicle
        for i in range(0, self.nrotors):
            # line from hub to centre plot3([hub(1,N) hub(1,S)],[hub(2,N) hub(2,S)],[hub(3,N) hub(3,S)],'-b')
            plot3(self.arm[i], [hub[0,i], hub0[0]],[hub[1,i], hub0[1]],[hub[2,i], hub0[2]])
            
            # plot a circle at the hub itself
            #plot3([hub(1,i)],[hub(2,i)],[hub(3,i)],'o')

        # plot the vehicle's centroid on the ground plane
        plot3(self.shadow, [z[0], 0], [-z[1], 0], [0, 0])
        plot3(self.groundmark, z[0], -z[1], 0)


# ------------------------------------------------------------------------ #


@block
class Scope(SinkBlockGraphics):
    """
    Plot input ports against time.  Each line can have its own color or style.
    """
    
    def __init__(self, nin=None, styles=None, scale='auto', labels=None, grid=True, *inputs, **kwargs):
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
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param ``**kwargs``: common Block options
        :return: A SCOPE block
        :rtype: Scope instance
        
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

        self.type = 'scope'
        if styles is not None:
            self.styles = list(styles)
            if nin is not None:
                assert nin == len(styles), 'need one style per input'
            else:
                nin = len(styles)

        if labels is not None:
            self.labels = list(labels)
            if nin is not None:
                assert nin == len(labels), 'need one label per input'
            else:
                nin = len(labels)
        else:
            self.labels = labels

        if nin is None:
            nin = 1
        
        super().__init__(nin=nin, inputs=inputs, **kwargs)

        
        if styles is None:
            self.styles = [ None ] * nin
        
        self.grid = grid
                 
        # init the arrays that hold the data
        self.tdata = np.array([])
        self.ydata = [np.array([]),] * nin
        
        self.line = [None]*nin
        self.scale = scale
        
        self.labels = labels
        # TODO, wire width
        # inherit names from wires, block needs to be able to introspect
        
    def start(self, **kwargs):
        # create the plot
        if self.bd.graphics:
            super().reset()   # TODO should this be here?
            self.fig = self.bd.create_figure()
            self.ax = self.fig.gca()
            # figure out the labels
            if self.labels is None:
                self.labels = [self.sourcename(i) for i in range(0, self.nin)]
                self.labels.insert(0, 'Time')
            elif len(self.labels) == 1:
                self.labels += [self.sourcename(i) for i in range(0, self.nin)]
            else:
                raise ValueError('incorrect number of labels specified for Scope')
            for i in range(0, self.nin):
                args = []
                kwargs = {}
                style = self.styles[i]
                if isinstance(style, dict):
                    kwargs = style
                elif isinstance(style, str):
                    args = [style]
                self.line[i], = self.ax.plot(self.tdata, self.ydata[i], *args, label=self.styles[i], **kwargs)
            self.ax.set_ylabel(','.join(self.labels[1:]))
            if self.grid is True:
                self.ax.grid(self.grid)
            elif isinstance(self.grid, (list, tuple)):
                self.ax.grid(True, *self.grid)
                
            self.ax.set_xlim(0, self.bd.T)
            # self.ax.set_ylim(-2, 2)
            self.ax.set_xlabel(self.labels[0])

            self.ax.set_title(self.name)
            if self.scale != 'auto':
                self.ax.set_ylim(*self.scale)
            if self.labels is not None:
                self.ax.legend(self.labels[1:])
            super().start()
        
    def step(self):
        # inputs are set
        if self.bd.graphics:
            self.tdata = np.append(self.tdata, self.bd.t)
            for i,input in enumerate(self.inputs):
                self.ydata[i] = np.append(self.ydata[i], input)
            if self.bd.graphics:
                plt.figure(self.fig.number)
                for i in range(0, self.nin):
                    self.line[i].set_data(self.tdata, self.ydata[i])
            
                plt.draw()
                plt.show(block=False)
                if self.bd.animation:
                    self.fig.canvas.start_event_loop(0.001)
            
                if self.scale == 'auto':
                    self.ax.relim()
                    self.ax.autoscale_view(scalex=False, scaley=True)
                super().step()
        
    def done(self, block=False, **kwargs):
        if self.bd.graphics:
            plt.show(block=block)
            super().done()

# ------------------------------------------------------------------------ #
            

@block
class Stop(SinkBlock):
    def __init__(self, stop, *inputs, **kwargs):
        """
        Conditionally stop the simulation.
        
        :param stop: Function 
        :type stop: TYPE
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param ``**kwargs``: common Block options
        :return: A STOP block
        :rtype: Stop instance

        """

        super().__init__(nin=1, inputs=inputs, **kwargs)
        self.type = 'stop'
                    
        self.stop  = stop

    def step(self):
        if isinstance(self.stop, bool):
            stop = self.inputs[0]
        elif callable(self.stop):
            stop = self.stop(self.inputs[0])
        else:
            raise RuntimeError('input to stop must be boolean or callable')
        if stop:
            self.bd.stop = self



if __name__ == "__main__":

    import pathlib
    import os.path

    exec(open(os.path.join(pathlib.Path(__file__).parent.absolute(), "test_sinks.py")).read())
