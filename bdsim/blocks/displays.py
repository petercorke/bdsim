"""
Sink blocks:

- have inputs but no outputs
- have no state variables
- are a subclass of ``SinkBlock`` |rarr| ``Block``
- that perform graphics are a subclass of  ``GraphicsBlock`` |rarr| ``SinkBlock`` |rarr| ``Block``

"""

import numpy as np
from math import pi, sqrt, sin, cos, atan2

import matplotlib.pyplot as plt
from matplotlib.pyplot import Polygon
from numpy.lib.shape_base import expand_dims


import spatialmath.base as sm

from bdsim.components import SinkBlock
from bdsim.graphics import GraphicsBlock


# ------------------------------------------------------------------------ #


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

    nin = -1
    nout = 0

    def __init__(
        self,
        nin=None,
        vector=None,
        styles=None,
        stairs=False,
        scale="auto",
        labels=None,
        grid=True,
        watch=False,
        **blockargs,
    ):
        """
        Plots input signals against time.

        :param nin: number of inputs, defaults to 1 or if given, the length of
                    style vector
        :type nin: int, optional
        :param vector: vector signal on single input port, defaults to None
        :type vector: int or list, optional
        :param styles: styles for each line to be plotted
        :type styles: str or dict, list of strings or dicts; one per line, optional
        :param stairs: force staircase style plot, defaults to False
        :type stairs: bool, optional
        :param scale: fixed y-axis scale or defaults to 'auto'
        :type scale: str or array_like(2)
        :param labels: vertical axis labels
        :type labels: sequence of strings
        :param grid: draw a grid, defaults to True. Can be boolean or a tuple of
                     options for grid()
        :type grid: bool or sequence
        :param watch: add these signals to the watchlist, defaults to False
        :type watch: bool, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A SCOPE block
        :rtype: Scope instance

        Create a block that plots:

        * scalar input ports against time, ``vector=None``
        * selected elements of a NumPy array on a single input port. If ``vector`` is an
          int this is the expected width of the array. If ``vector`` is a list of ints these
          are the indices of the array to display.

        Each line can have its own color or style which is specified by:

            - a dict of options for `Line2D <https://matplotlib.org/3.2.2/api/_as_gen/matplotlib.lines.Line2D.html#matplotlib.lines.Line2D>`_ or
            - a  MATLAB-style linestyle like 'k--'

        The number of lines to plot will be inferred from:
        * the length of the ``labels`` list if specified
        * the length of the ``styles`` list if specified
        * ``nin`` if specified
        * ``vector`` if specified

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
            SCOPE(vector=[0,1,2]) # display elements 0, 1, 2 of array on port 0


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
                raise ValueError("unknown argument to listify")

        # number of lines plotted (nplots) is inferred from the number of labels
        # or linestyles
        nplots = None

        if nin is not None:
            nplots = nin

        if styles is not None:
            self.styles = listify(styles)
            if nplots is not None:
                assert nplots == len(styles), "need one style per input"
            else:
                nplots = len(styles)

        if labels is not None:
            self.labels = listify(labels)
            if nplots is not None:
                assert nplots == len(labels), "need one label per input"
            else:
                nplots = len(labels)
        else:
            self.labels = None

        if vector is not None:
            # vector argument is given
            #  block has single input which is an array
            #  vector is int, width of vector
            #  vector is a list of ints, select those inputs from the input vector

            if nin is not None and nin != 1:
                raise ValueError("if vector is given, nin must be 1")

            if isinstance(vector, int):
                nvec = vector
            elif isinstance(vector, list):
                nvec = len(vector)
            else:
                raise ValueError("vector must be an int or list of indices")

            if nplots is None:
                nplots = nvec
            else:
                if nvec != nplots:
                    raise ValueError("vector argument doesnt match nplots")

        if nplots is None:
            # still indeterminate, set default
            nin = 1
            nplots = 1

        if vector is not None:
            nin = 1
            nplots = nvec
        else:
            nin = nplots

        self.nplots = nplots
        self.vector = vector

        super().__init__(nin=nin, **blockargs)

        if styles is None:
            self.styles = [None] * nplots

        self.xlabel = "Time (s)"

        self.grid = grid
        self.stairs = stairs

        self.line = [None] * nplots
        self.scale = scale

        self.watch = watch

        # TODO, wire width
        # inherit names from wires, block needs to be able to introspect

    def start(self, state=None):
        # init the arrays that hold the data
        self.tdata = np.array([])
        self.ydata = [
            np.array([]),
        ] * self.nplots

        # create the figures
        self.fig = self.create_figure(state)
        self.ax = self.fig.add_subplot(111)

        if self.stairs:
            kwargs = {**dict(drawstyle="steps"), **kwargs}

        # create empty lines with defined styles
        for i in range(0, self.nplots):
            args = []
            kwargs = {}
            style = self.styles[i]
            if isinstance(style, dict):
                kwargs = style
            elif isinstance(style, str):
                args = [style]
            (self.line[i],) = self.ax.plot(
                self.tdata, self.ydata[i], *args, label=self.styles[i], linewidth=2
            )

        # label the axes
        if self.labels is not None:
            self.ax.set_ylabel(",".join(self.labels))
        self.ax.set_xlabel(self.xlabel)
        self.ax.set_title(self.name_tex)

        # grid control
        if self.grid is True:
            self.ax.grid(self.grid)
        elif isinstance(self.grid, (list, tuple)):
            self.ax.grid(True, *self.grid)

        # set limits
        self.ax.set_xlim(0, state.T)

        if self.scale != "auto":
            self.ax.set_ylim(*self.scale)
        if self.labels is not None:
            self.ax.legend(self.labels)

        if self.watch:
            for wire in self.input_wires:
                plug = wire.start  # start plug for input wire

                # append to the watchlist, bdsim.run() will do the rest
                state.watchlist.append(plug)
                state.watchnamelist.append(str(plug))

        super().start()

    def step(self, state=None):
        # inputs are set
        self.tdata = np.append(self.tdata, state.t)

        if self.vector is None:
            # take data from multiple inputs as a list
            data = self.inputs
            if len(data) != self.nplots:
                raise RuntimeError(
                    "number of signals to plot doesnt match init parameters"
                )

        else:
            # single input with vector data
            data = self.inputs[0]
            if isinstance(self.vector, list):
                data = data[self.vector]

        # append new data to the set
        for i, y in enumerate(data):
            self.ydata[i] = np.append(self.ydata[i], y)

        # plot the data
        for i in range(0, self.nplots):
            self.line[i].set_data(self.tdata, self.ydata[i])

        if self.scale == "auto":
            self.ax.relim()
            self.ax.autoscale_view(scalex=False, scaley=True)
        super().step(state=state)


# ------------------------------------------------------------------------ #


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

    nin = 2
    nout = 0

    def __init__(
        self,
        style=None,
        scale="auto",
        aspect="equal",
        labels=["X", "Y"],
        init=None,
        nin=2,
        **blockargs,
    ):
        """
        :param style: line style, defaults to None
        :type style: optional str or dict
        :param scale: fixed y-axis scale or defaults to 'auto'
        :type scale: str or array_like(2) or array_like(4)
        :param labels: axis labels (xlabel, ylabel), defaults to ["X","Y"]
        :type labels: 2-element tuple or list
        :param init: function to initialize the graphics, defaults to None
        :type init: callable
        :param blockargs: |BlockOptions|
        :type blockargs: dict
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

        :input x: signal plotted on horizontal axis
        :input y: signal plotted on vertical axis
        """
        super().__init__(**blockargs)
        self.xdata = []
        self.ydata = []
        if init is not None:
            assert callable(init), "graphics init function must be callable"
        self.init = init

        self.styles = style
        if scale != "auto":
            scale = sm.expand_dims(scale, 2)
        self.scale = scale
        self.aspect = aspect
        self.labels = labels
        self.inport_names(("x", "y"))

    def start(self, state, **kwargs):
        # create the plot
        super().reset()

        self.fig = self.create_figure(state)
        self.ax = self.fig.gca()

        args = []
        blockargs = {}
        style = self.styles
        if isinstance(style, dict):
            blockargs = style
        elif isinstance(style, str):
            args = [style]
        (self.line,) = self.ax.plot(self.xdata, self.ydata, *args, **kwargs)

        self.ax.grid(True)
        self.ax.set_xlabel(self.labels[0])
        self.ax.set_ylabel(self.labels[1])
        self.ax.set_title(self.name)
        if not (isinstance(self.scale, str) and self.scale == "auto"):
            self.ax.set_xlim(*self.scale[0:2])
            self.ax.set_ylim(*self.scale[2:4])
        self.ax.set_aspect(self.aspect)
        if self.init is not None:
            self.init(self.ax)

        plt.draw()
        plt.show(block=False)

        super().start()

    def step(self, state=None):
        self._step(self.inputs[0], self.inputs[1], state)

    def _step(self, x, y, state):
        self.xdata.append(x)
        self.ydata.append(y)

        # if self.bd.runtime.options.graphics:
        plt.figure(self.fig.number)
        self.line.set_data(self.xdata, self.ydata)

        if self.bd.runtime.options.animation:
            self.fig.canvas.flush_events()

        if isinstance(self.scale, str) and self.scale == "auto":
            self.ax.relim()
            self.ax.autoscale_view()
        super().step(state=state)

    # def done(self, block=False, **blockargs):
    #     if self.bd.runtime.options.graphics:
    #         plt.show(block=block)
    #         super().done()


class ScopeXY1(ScopeXY):
    """
    :blockname:`SCOPEXY1`

    .. table::
       :align: left

    +-------------+---------+---------+
    | inputs      | outputs |  states |
    +-------------+---------+---------+
    | 1           | 0       | 0       |
    +-------------+---------+---------+
    | ndarray(2)  |         |         |
    +-------------+---------+---------+
    """

    nin = 1
    nout = 0

    def __init__(self, indices=[0, 1], **blockargs):
        """
        :param indices: indices of elements to select from block input vector, defaults to [0,1]
        :type indices: array_like(2)
        :param style: line style
        :type style: optional str or dict
        :param scale: fixed y-axis scale or defaults to 'auto'
        :type scale: str or array_like(2) or array_like(4)
        :param labels: axis labels (xlabel, ylabel)
        :type labels: 2-element tuple or list
        :param init: function to initialize the graphics, defaults to None
        :type init: callable
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A SCOPEXY block
        :rtype: ScopeXY instance

        Create an XY scope with vector input

        This block has one vector input and two elemetns are plotted against each other. The first
        selected element is the horizontal axis, and second is the vertical axis.

        The line style is given by either:

            - a dict of options for ``plot``, or
            - as a simple MATLAB-style linestyle like ``'k--'``.

        The scale factor defaults to auto-scaling but can be fixed by
        providing either:

            - a 2-tuple [min, max] which is used for the x- and y-axes
            - a 4-tuple [xmin, xmax, ymin, ymax]
        """
        super().__init__(**blockargs)
        self.inport_names(("xy",))
        if len(indices) != 2:
            raise ValueError("indices must have 2 elements")
        self.indices = [int(x) for x in indices]

    def step(self, state=None):
        # inputs are set
        x = self.inputs[0][self.indices[0]]
        y = self.inputs[0][self.indices[1]]

        super()._step(x, y, state)


# ------------------------------------------------------------------------ #


if __name__ == "__main__":  # pragma: no cover

    from pathlib import Path

    exec(
        open(Path(__file__).parent.parent.parent / "tests" / "test_displays.py").read()
    )
