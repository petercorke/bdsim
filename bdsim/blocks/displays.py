"""
Sink blocks:

- have inputs but no outputs
- have no state variables
- are a subclass of ``SinkBlock`` |rarr| ``Block``
- that perform graphics are a subclass of  ``GraphicsBlock`` |rarr| ``SinkBlock`` |rarr| ``Block``

"""

# The constructor of each class ``MyClass`` with a ``@block`` decorator becomes a method ``MYCLASS()`` of the BlockDiagram instance.

import numpy as np
from math import pi, sqrt, sin, cos, atan2

import matplotlib.pyplot as plt
from matplotlib.pyplot import Polygon


import spatialmath.base as sm

from bdsim.components import SinkBlock, block
from bdsim.graphics import GraphicsBlock



# ------------------------------------------------------------------------ #


@block
class Scope(GraphicsBlock):
    """
    :blockname:`SCOPE`
    
    .. table::
       :align: left
    
       +--------+---------+---------+
       | inputs | outputs |  states |
       +--------+---------+---------+
       | 1      | 0       | 0       |
       +--------+---------+---------+
       | float, |         |         | 
       | A(N,)  |         |         | 
       +--------+---------+---------+
    """
    
    def __init__(self, nin=1, vector=0, styles=None, scale='auto', labels=None, grid=True, *inputs, **kwargs):
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

        Create a block that plots input ports against time.  

        Each line can have its own color or style which is specified by:
        
            - a dict of options for `Line2D <https://matplotlib.org/3.2.2/api/_as_gen/matplotlib.lines.Line2D.html#matplotlib.lines.Line2D>`_ or 
            - a  MATLAB-style linestyle like 'k--'
        
        The number of inputs will be inferred from the length of the ``labels``
        list if not specified.

        If multiple lines are plotted then a heterogeneous list of styles, dicts or strings,
        one per line must be given.
        
        The vertical scale factor defaults to auto-scaling but can be fixed by
        providing a 2-tuple [ymin, ymax]. All lines are plotted against the
        same vertical scale.
        
        Examples::
            
            SCOPE()
            SCOPE(nin=2)
            SCOPE(nin=2, scale=[-1,2])
            SCOPE(styles='k--')
            SCOPE(styles=[{'color': 'blue'}, {'color': 'red', 'linestyle': '--'}])
            SCOPE(styles=['k', 'r--'])

            
        .. figure:: ../../figs/Figure_1.png
           :width: 500px
           :alt: example of generated graphic

           Example of scope display.
        """
        def listify(s):
            if isinstance(s, str):
                return [s]
            elif isinstance(s, (list, tuple)):
                return s
            else:
                raise ValueError('unknown argument to listify')

        nplots = None
        self.type = 'scope'

        if styles is not None:
            self.styles = listify(styles)
            if nplots is not None:
                assert nplots == len(styles), 'need one style per input'
            else:
                nplots = len(styles)

        if labels is not None:
            self.labels = listify(labels)
            if nplots is not None:
                assert nplots == len(labels), 'need one label per input'
            else:
                nplots = len(labels)
        else:
            self.labels = None

        if vector > 0 and nin > 1:
            raise ValueError('if vector > 0 nin must be 1')

        if nplots is None:
            if vector > 0:
                nplots = vector
            else:
                nplots = nin
        else:
            nin = nplots

        self.nplots = nplots
        self.vector = vector
        
        super().__init__(nin=nin, inputs=inputs, **kwargs)

        if styles is None:
            self.styles = [ None ] * nplots
      
        self.xlabel = 'Time (s)'
        
        self.grid = grid
        
        self.line = [None] * nplots
        self.scale = scale
        

        # TODO, wire width
        # inherit names from wires, block needs to be able to introspect
        
    def start(self, **kwargs):
        # create the plot
        if self.bd.options.graphics:
            super().reset()   # TODO should this be here?

            # init the arrays that hold the data
            self.tdata = np.array([])
            self.ydata = [np.array([]),] * self.nplots

            # create the figures
            self.fig = self.create_figure()
            self.ax = self.fig.gca()
            
            # create empty lines with defined styles
            for i in range(0, self.nplots):
                args = []
                kwargs = {}
                style = self.styles[i]
                if isinstance(style, dict):
                    kwargs = style
                elif isinstance(style, str):
                    args = [style]
                self.line[i], = self.ax.plot(self.tdata, self.ydata[i], *args, label=self.styles[i], **kwargs)

            # label the axes
            if self.labels is not None:
                self.ax.set_ylabel(','.join(self.labels))
            self.ax.set_xlabel(self.xlabel)
            self.ax.set_title(self.name_tex)

            # grid control
            if self.grid is True:
                self.ax.grid(self.grid)
            elif isinstance(self.grid, (list, tuple)):
                self.ax.grid(True, *self.grid)
            
            # set limits
            self.ax.set_xlim(0, self.bd.state.T)

            if self.scale != 'auto':
                self.ax.set_ylim(*self.scale)
            if self.labels is not None:
                self.ax.legend(self.labels)

            plt.draw()
            plt.show(block=False)

            super().start()
        
    def step(self):
        # inputs are set
        if self.bd.options.graphics:
            self.tdata = np.append(self.tdata, self.bd.state.t)

            if self.vector:
                # vector input on the input
                data = self.inputs[0]
                assert len(data) == self.nplots, 'vector input wrong width'
                for i,input in enumerate(data):
                    self.ydata[i] = np.append(self.ydata[i], input)
            else:
                # stash data from the inputs
                assert len(self.inputs) == self.nplots, 'insufficient inputs'
                for i,input in enumerate(self.inputs):
                    self.ydata[i] = np.append(self.ydata[i], input)

            plt.figure(self.fig.number)  # make current
            for i in range(0, self.nplots):
                self.line[i].set_data(self.tdata, self.ydata[i])
        
            if self.bd.options.animation:
                self.fig.canvas.flush_events()
        
            if self.scale == 'auto':
                self.ax.relim()
                self.ax.autoscale_view(scalex=False, scaley=True)
            super().step()
        
    def done(self, block=False, **kwargs):
        if self.bd.options.graphics:
            plt.show(block=block)
        super().done()

# ------------------------------------------------------------------------ #

@block
class ScopeXY(GraphicsBlock):
    """
    :blockname:`SCOPEXY`
    
    .. table::
       :align: left
    
       +--------+---------+---------+
       | inputs | outputs |  states |
       +--------+---------+---------+
       | 2      | 0       | 0       |
       +--------+---------+---------+
       | float  |         |         | 
       +--------+---------+---------+
    """

    def __init__(self, style=None, *inputs, scale='auto', labels=['X', 'Y'], init=None, **kwargs):
        """
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

        Create an XY scope.

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
        if self.bd.options.graphics:
            super().reset()

            self.fig = self.create_figure()
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

            plt.draw()
            plt.show(block=False)

            super().start()

        
    def step(self):
        # inputs are set
        self.xdata.append(self.inputs[0])
        self.ydata.append(self.inputs[1])
        if self.bd.options.graphics:
            plt.figure(self.fig.number)
            self.line.set_data(self.xdata, self.ydata)
        
            if self.bd.options.animation:
                self.fig.canvas.flush_events()

        
            if self.scale == 'auto':
                self.ax.relim()
                self.ax.autoscale_view()
            super().step()
        
    def done(self, block=False, **kwargs):
        if self.bd.options.graphics:
            plt.show(block=block)
            super().done()
            

# ------------------------------------------------------------------------ #


if __name__ == "__main__":

    import pathlib
    import os.path

    exec(open(os.path.join(pathlib.Path(__file__).parent.absolute(), "test_sinks.py")).read())
