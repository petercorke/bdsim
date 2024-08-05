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

import spatialmath.base as sm

from bdsim.components import SinkBlock
from bdsim.graphics import GraphicsBlock

# ------------------------------------------------------------------------ #


class Scope(GraphicsBlock):
    r"""
    :blockname:`SCOPE`

    Plot input signals against time.

    :inputs: N
    :outputs: 0
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - i
            - float
            - :math:`x_i` is the i'th line

    Create a scope block that plots multiple signals against time.

    For each line plotted we can specify the:

    * line style as a heterogeneous list of:

      * Matplotlib `fmt` string comprising a color and line style, eg. ``"k"`` or ``"r:"``

      * a dict of Matplotlib line style options for `Line2D <https://matplotlib.org/3.2.2/api/_as_gen/matplotlib.lines.Line2D.html#matplotlib.lines.Line2D>`_
        , eg. ``{"color": "k", "linewidth": 3, "alpha": 0.5)``

    * line label, used in the legend and vertical axis. This can include math mode
      notation or unicode characters.

    The vertical scale factor defaults to auto-scaling but can be fixed by
    providing a 2-tuple ``[ymin, ymax]``. All lines are plotted against the
    same vertical scale.

    .. figure:: ../../figs/Figure_1.png
        :width: 500px
        :alt: example of generated graphic

        Example of scope display.

    **Scalar input ports against time**

    The number of lines to plot will be inferred from:

    * the length of the ``labels`` list if specified
    * the length of the ``styles`` list if specified
    * ``nin`` if specified, it defaults to 1

    These numbers must be consistent.

    Examples::

        bd.SCOPE()       # a scope with 1 input port
        bd.SCOPE(nin=3)  # a scope with 3 input ports
        bd.SCOPE(styles=["k", "r--"])        # a scope with 2 input ports
        bd.SCOPE(labels=["x", r"$\gamma$"])  # a scope with 2 input ports
        bd.SCOPE(styles=[{'color': 'blue'}, {'color': 'red', 'linestyle': '--'}])

    **Single input port with NumPy array**

    The port is fed with a 1D-array, and ``vector`` is an:

    * int, this is the expected width of the array, all its elements will be plotted
    * a list of ints, interpretted as indices of the elements to plot.

    Examples::

        bd.SCOPE(vector=[0,1,2]) # display elements 0, 1, 2 of array on port 0
        bd.SCOPE(vector=[0,1], styles=[{'color': 'blue'}, {'color': 'red', 'linestyle': '--'}])

    .. note::
        * If the vector is of width 3, by default the inputs are plotted as red, green
          and blue lines.
        * If the vector is of width 6, by default the first three inputs are plotted as
          solid red, green and blue lines and the last three inputs are plotted as
          dashed red, green and blue lines.
    """

    nin = -1
    nout = 0

    def __init__(
        self,
        nin=1,
        vector=None,
        styles=None,
        stairs=False,
        scale="auto",
        labels=None,
        grid=True,
        watch=False,
        title=None,
        loc="best",
        **blockargs,
    ):
        """
        :param nin: number of inputs, defaults to 1 or if given, the length of
                    style vector
        :type nin: int, optional
        :param vector: vector signal on single input port, defaults to None
        :type vector: int or list, optional
        :param styles: styles for each line to be plotted
        :type styles: str or dict, list of strings or dicts; one per line, optional
        :param stairs: force staircase style plot for all lines, defaults to False
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
        :param title: title of plot
        :type title: str
        :param loc: location of legend, see :meth:`matplotlib.pyplot.legend`, defaults to "best"
        :type loc: str
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """

        def listify(s):
            # guarantee that result is a list
            if isinstance(s, str):
                return [s]
            elif isinstance(s, (list, tuple)):
                return s
            else:
                raise ValueError("unknown argument to listify")

        # number of lines plotted (nplots) is inferred from the number of labels
        # or linestyles

        nplots = None
        if vector is not None:
            # vector argument is given
            #  block has single input which is an array
            #  vector is int, width of vector
            #  vector is a list of ints, select those inputs from the input vector

            if nin != 1:
                raise ValueError("if vector is given, nin must be 1")

            if isinstance(vector, int):
                nplots = vector
            elif isinstance(vector, list):
                nplots = len(vector)
            else:
                raise ValueError("vector must be an int or list of indices")

        if styles is not None:
            self.styles = listify(styles)
            if nplots is None:
                nplots = len(self.styles)
            else:
                assert nplots == len(self.styles), "need one style per plot"
        else:
            self.styles = None

        if labels is not None:
            self.labels = listify(labels)
            if nplots is None:
                nplots = len(self.labels)
            else:
                assert nplots == len(self.labels), "need one label per plot"
        else:
            self.labels = None

        if nplots is None:
            # nplots has not been determined from styles or labels, so use nin
            nplots = nin
        elif nin == 1 and vector is None:
            # nplots is different to the default nin value, override it
            nin = nplots

        self.nplots = nplots
        self.vector = vector

        super().__init__(nin=nin, **blockargs)

        self.xlabel = "Time (s)"

        self.grid = grid
        self.stairs = stairs

        self.line = [None] * nplots
        self.scale = scale

        self.watch = watch
        self.title = title
        self.loc = loc

        # TODO, wire width
        # inherit names from wires, block needs to be able to introspect

    def start(self, simstate):
        super().start(simstate)

        if not self._enabled:
            return

        # init the arrays that hold the data
        self.tdata = np.array([])
        self.ydata = [
            np.array([]),
        ] * self.nplots

        # create the figures
        self.fig = self.create_figure(simstate)
        self.ax = self.fig.add_subplot(111)

        # get labels if not provided
        if self.labels is None:
            if self.vector is None:
                self.labels = [self.sourcename(i) for i in range(self.nin)]
            else:
                self.labels = [str(i) for i in range(self.vector)]
                if self.styles is None:
                    if self.vector == 3:
                        self.styles = ["r", "g", "b"]
                    elif self.vector == 6:
                        self.styles = ["r", "g", "b", "r--", "g--", "b--"]

        if self.styles is None:
            self.styles = [None] * self.nplots

        # create empty lines with defined styles
        for i in range(0, self.nplots):
            args = []
            kwargs = {}
            style = self.styles[i]
            if isinstance(style, dict):
                kwargs = style
            elif isinstance(style, str):
                args = [style]
            if self.stairs:
                kwargs["drawstyle"] = "steps"  # force steppy plot

            (self.line[i],) = self.ax.plot(
                self.tdata,
                self.ydata[i],
                *args,
                label=self.styles[i],
                linewidth=2,
                **kwargs,
            )

        # label the axes
        if self.labels is not None:
            self.ax.set_ylabel(",".join(self.labels))
        self.ax.set_xlabel(self.xlabel)

        if self.title is not None:
            name = self.title
        else:
            name = self.name_tex
        self.ax.set_title(name)

        # grid control
        if self.grid is True:
            self.ax.grid(self.grid)
        elif isinstance(self.grid, (list, tuple)):
            self.ax.grid(True, *self.grid)

        # set limits
        self.ax.set_xlim(0, simstate.T)

        if self.scale != "auto":
            self.ax.set_ylim(*self.scale)
        if self.labels is not None:

            def fix_underscore(s):
                if s[0] == "_":
                    return "-" + s[1:]
                else:
                    return s

            self.ax.legend(
                [fix_underscore(label) for label in self.labels], loc=self.loc
            )

        if self.watch:
            for wire in self.input_wires:
                plug = wire.start  # start plug for input wire

                # append to the watchlist, bdsim.run() will do the rest
                simstate.watchlist.append(plug)
                simstate.watchnamelist.append(str(plug))
        plt.draw()
        plt.show(block=False)

    def step(self, t, inports):
        if not self._enabled:
            return

        # inputs are set
        self.tdata = np.append(self.tdata, t)

        if self.vector is None:
            # take data from multiple inputs as a list
            data = inports
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

        super().step(t, inports)


# ------------------------------------------------------------------------ #


class ScopeXY(GraphicsBlock):
    """
    :blockname:`SCOPEXY`

    Plot X against Y.

    :inputs: 2
    :outputs: 0
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - 0
            - float
            - :math:`x`
        *   - Input
            - 1
            - float
            - :math:`y`

    Create an XY scope where input :math:`y` (vertical axis) is plotted against :math:`x`
    (horizontal axis).

    Line style is one of:

      * Matplotlib `fmt` string comprising a color and line style, eg. ``"k"`` or ``"r:"``

      * a dict of Matplotlib line style options for `Line2D <https://matplotlib.org/3.2.2/api/_as_gen/matplotlib.lines.Line2D.html#matplotlib.lines.Line2D>`_
        , eg. ``dict(color="k", linewidth=3, alpha=0.5)``

    The scale factor defaults to auto-scaling but can be fixed by
    providing either:

        - a 2-tuple ``[min, max]`` which is used for the x- and y-axes
        - a 4-tuple ``[xmin, xmax, ymin, ymax]``
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

    def start(self, simstate):
        super().start(simstate)

        if not self._enabled:
            return

        # create the plot
        super().reset()

        self.fig = self.create_figure(simstate)
        self.ax = self.fig.gca()

        args = []
        blockargs = {}
        style = self.styles
        if isinstance(style, dict):
            blockargs = style
        elif isinstance(style, str):
            args = [style]
        (self.line,) = self.ax.plot(self.xdata, self.ydata, *args)

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

    def step(self, t, inports):
        if not self._enabled:
            return
        self._step(inports[0], inports[1], t)

    def _step(self, x, y, t):
        self.xdata.append(x)
        self.ydata.append(y)

        plt.figure(self.fig.number)
        self.line.set_data(self.xdata, self.ydata)

        if self.bd.runtime.options.animation:
            self.fig.canvas.flush_events()

        if isinstance(self.scale, str) and self.scale == "auto":
            self.ax.relim()
            self.ax.autoscale_view()
        super().step(t, None)

    # def done(self, block=False, **blockargs):
    #     if self.bd.runtime.options.graphics:
    #         plt.show(block=block)
    #         super().done()


class ScopeXY1(ScopeXY):
    """
    :blockname:`SCOPEXY1`

    Plot X[0] against X[1].

    :inputs: 1
    :outputs: 0
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - 0
            - ndarray
            - :math:`x`

    Create an XY scope where input :math:`x_j` (vertical axis) is plotted against
    :math:`x_i` (horizontal axis). This block has one vector input and the elements to
    be plotted are given by a 2-element iterable :math:`(i, j)`.

    Line style is one of:

      * Matplotlib `fmt` string comprising a color and line style, eg. ``"k"`` or ``"r:"``

      * a dict of Matplotlib line style options for `Line2D <https://matplotlib.org/3.2.2/api/_as_gen/matplotlib.lines.Line2D.html#matplotlib.lines.Line2D>`_
        , eg. ``dict(color="k", linewidth=3, alpha=0.5)``

    The scale factor defaults to auto-scaling but can be fixed by
    providing either:

        - a 2-tuple ``[min, max]`` which is used for the x- and y-axes
        - a 4-tuple ``[xmin, xmax, ymin, ymax]``
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
        """
        super().__init__(**blockargs)
        self.inport_names(("xy",))
        if len(indices) != 2:
            raise ValueError("indices must have 2 elements")
        self.indices = [int(x) for x in indices]

    def step(self, t, inports):
        if not self._enabled:
            return

        # inputs are set
        x = inports[0][self.indices[0]]
        y = inports[0][self.indices[1]]

        super()._step(x, y, t)


# ------------------------------------------------------------------------ #


if __name__ == "__main__":  # pragma: no cover

    from pathlib import Path

    exec(
        open(Path(__file__).parent.parent.parent / "tests" / "test_displays.py").read()
    )
