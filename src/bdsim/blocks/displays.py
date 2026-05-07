"""
Sink blocks:

- have inputs but no outputs
- have no state variables
- are a subclass of ``SinkBlock`` |rarr| ``Block``
- that perform graphics are a subclass of  ``GraphicsBlock`` |rarr| ``SinkBlock`` |rarr| ``Block``

"""

import numpy as np
from math import pi, sqrt, sin, cos, atan2
from pathlib import Path

import matplotlib.pyplot as plt

try:
    from matplotlib.backend_tools import ToolToggleBase
except Exception:  # pragma: no cover
    ToolToggleBase = None  # type: ignore[assignment,misc]

import spatialmath.base as smb  # type: ignore[import-not-found]

from typing import Any, Callable, Literal

from bdsim.block_types import GraphicsBlock
from bdsim.components import SinkBlock

# ------------------------------------------------------------------------ #

# Styling/theme knobs for scope displays. Keep all visual tuning here.
#
# Dark tiled mode: used when multiple scopes share one figure window.
TILE_AXES_FACE_COLOR = "#1e1e1e"
TILE_TEXT_COLOR = "white"
TILE_SPINE_COLOR = "#888888"
TILE_LEGEND_FACE_COLOR = "#3a3a3a"
TILE_LEGEND_EDGE_COLOR = "#888888"

# Cursor visuals.
CURSOR_COLOR_LIGHT = "k"
CURSOR_COLOR_DARK = "white"
CURSOR_LINE_WIDTH = 0.8
CURSOR_LINE_ALPHA = 0.7
CURSOR_MARKER_SIZE = 4
CURSOR_MARKER_ALPHA = 0.7

# Cursor readout textbox visuals.
CURSOR_TEXTBOX_BOXSTYLE = "round"
CURSOR_TEXTBOX_FACE_COLOR = "white"
CURSOR_TEXTBOX_EDGE_COLOR = "0.5"
CURSOR_TEXTBOX_ALPHA = 0.65


_DATA_CURSOR_ICON_PATH = (
    Path(__file__).resolve().parents[3] / "figs" / "data-cursor.png"
)
_DATA_CURSOR_ICON = (
    str(_DATA_CURSOR_ICON_PATH) if _DATA_CURSOR_ICON_PATH.exists() else None
)


def _cursor_controller(fig: Any) -> dict[str, Any]:
    controller = getattr(fig, "_bdsim_cursor_controller", None)
    if controller is None:
        controller = {
            "enabled": True,
            "owners": [],
            "controls_registered": False,
            "tool_id": None,
            "qt_action": None,
        }
        setattr(fig, "_bdsim_cursor_controller", controller)
    return controller


def _cursor_add_owner(owner: Any) -> None:
    if owner.fig is None:
        return
    controller = _cursor_controller(owner.fig)
    if owner not in controller["owners"]:
        controller["owners"].append(owner)


def _cursor_enabled(owner: Any) -> bool:
    if owner.fig is None:
        return True
    return bool(_cursor_controller(owner.fig)["enabled"])


def _cursor_set_enabled_for_figure(fig: Any, enabled: bool) -> None:
    controller = _cursor_controller(fig)
    controller["enabled"] = enabled
    for owner in list(controller["owners"]):
        owner._cursor_apply_enabled(enabled)

    # Keep classic Qt toolbar toggle action state in sync with keyboard toggles.
    qt_action = controller.get("qt_action")
    if qt_action is not None:
        try:
            if bool(qt_action.isChecked()) != bool(enabled):
                qt_action.blockSignals(True)
                qt_action.setChecked(bool(enabled))
                qt_action.blockSignals(False)
        except Exception:
            pass


def _cursor_toggle_for_figure(fig: Any) -> None:
    _cursor_set_enabled_for_figure(fig, not bool(_cursor_controller(fig)["enabled"]))


def _apply_tile_axes_style(ax: Any) -> None:
    """Apply white text/spine colors so plots are readable on the dark tiled background."""
    ax.set_facecolor(TILE_AXES_FACE_COLOR)
    for spine in ax.spines.values():
        spine.set_edgecolor(TILE_SPINE_COLOR)
    ax.tick_params(colors=TILE_TEXT_COLOR)
    ax.xaxis.label.set_color(TILE_TEXT_COLOR)
    ax.yaxis.label.set_color(TILE_TEXT_COLOR)
    ax.title.set_color(TILE_TEXT_COLOR)
    legend = ax.get_legend()
    if legend is not None:
        for text in legend.get_texts():
            text.set_color(TILE_TEXT_COLOR)
        legend.get_frame().set_facecolor(TILE_LEGEND_FACE_COLOR)
        legend.get_frame().set_edgecolor(TILE_LEGEND_EDGE_COLOR)


def _cursor_text_bbox_style() -> dict[str, Any]:
    return dict(
        boxstyle=CURSOR_TEXTBOX_BOXSTYLE,
        facecolor=CURSOR_TEXTBOX_FACE_COLOR,
        edgecolor=CURSOR_TEXTBOX_EDGE_COLOR,
        alpha=CURSOR_TEXTBOX_ALPHA,
    )


def _cursor_register_controls(owner: Any) -> None:
    if owner.fig is None:
        return

    fig = owner.fig
    controller = _cursor_controller(fig)
    if controller["controls_registered"]:
        return
    controller["controls_registered"] = True

    def _on_keypress(event: Any) -> None:
        key = (event.key or "").lower()
        if key == "d":
            _cursor_toggle_for_figure(fig)

    fig.canvas.mpl_connect("key_press_event", _on_keypress)

    manager = getattr(fig.canvas, "manager", None)
    if manager is None:
        return

    toolmanager = getattr(manager, "toolmanager", None)
    toolbar = getattr(manager, "toolbar", None)

    # Preferred path: toolmanager-based toolbar toggle.
    if ToolToggleBase is not None and toolmanager is not None and toolbar is not None:
        tool_id = f"bdsim-datacursor-{fig.number}"
        controller["tool_id"] = tool_id

        class _DataCursorTool(ToolToggleBase):
            default_keymap = ["d"]
            description = "Toggle data cursor"
            image = _DATA_CURSOR_ICON

            def enable(self, *args: Any) -> None:
                _cursor_set_enabled_for_figure(fig, True)

            def disable(self, *args: Any) -> None:
                _cursor_set_enabled_for_figure(fig, False)

        try:
            toolmanager.add_tool(tool_id, _DataCursorTool)
            toolbar.add_tool(tool_id, "navigation")
            if controller["enabled"]:
                toolmanager.trigger_tool(tool_id)
            return
        except Exception:
            pass

    # Fallback for classic Qt toolbar (NavigationToolbar2QT) where toolmanager
    # is not active: add a checkable QAction directly.
    if toolbar is not None and hasattr(toolbar, "addAction"):
        action = None
        try:
            from matplotlib.backends.qt_compat import QtGui  # type: ignore[attr-defined]

            icon = (
                QtGui.QIcon(_DATA_CURSOR_ICON) if _DATA_CURSOR_ICON else QtGui.QIcon()
            )
            action = toolbar.addAction(icon, "Data Cursor")
        except Exception:
            try:
                action = toolbar.addAction("Data Cursor")
            except Exception:
                action = None

        if action is not None:
            try:
                action.setCheckable(True)
                action.setChecked(bool(controller["enabled"]))
                controller["qt_action"] = action

                if hasattr(action, "toggled"):
                    action.toggled.connect(
                        lambda checked: _cursor_set_enabled_for_figure(
                            fig, bool(checked)
                        )
                    )
                elif hasattr(action, "triggered"):
                    action.triggered.connect(lambda *_: _cursor_toggle_for_figure(fig))
            except Exception:
                # Keep keyboard toggle as the final portable fallback.
                pass


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

    .. figure:: ../figs/Figure_1.png
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
        nin: int = 1,
        vector: int | list[int] | None = None,
        styles: str | dict | list[str | dict] | None = None,
        stairs: bool = False,
        scale: Literal["auto"] | float = "auto",
        labels: list[str] | None = None,
        grid: bool | list | tuple = True,
        watch: bool = False,
        title: str | None = None,
        loc: str = "best",
        **blockargs: Any,
    ) -> None:
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
        :param labels: labels for the plotted signals, defaults to block name and port of the source of each signal if not given. Used
            for vertical axis label, legend and cursor readout.
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

        def listify(s: Any) -> list[Any]:
            # guarantee that result is a list
            if isinstance(s, str):
                return [s]
            elif isinstance(s, (list, tuple)):
                return list(s)
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
            self.styles: list[Any] | None = listify(styles)
            if nplots is None:
                nplots = len(self.styles)
            else:
                assert nplots == len(self.styles), "need one style per plot"
        else:
            self.styles = None
        if labels is not None:
            self.labels: list[Any] | None = listify(labels)
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

        self.line: list = [None] * nplots
        self.scale = scale

        self.watch = watch
        self.title = title
        self.loc = loc

        # Interactive cursor state (initialized in start()).
        self._cursor_x: float | None = None
        self._cursor_line: Any = None
        self._cursor_text: Any = None
        self._cursor_labels: list[str] = []
        self._cursor_text_xy: tuple[float, float] = (0.02, 0.98)
        self._cursor_dragging: bool = False
        self._cursor_drag_offset: tuple[float, float] = (0.0, 0.0)

        # TODO, wire width
        # inherit names from wires, block needs to be able to introspect

    def start(self, simstate: Any) -> None:
        super().start(simstate)

        if not self._enabled:
            return

        # init the arrays that hold the data
        self.tdata = np.array([])
        self.ydata = [
            np.array([]),
        ] * self.nplots

        # create the figure/axes (subplot axis is pre-assigned in tiled mode)
        self.fig = self.create_figure(simstate)
        tile_ax = getattr(self, "_tile_axes", None)
        self.ax = tile_ax if tile_ax is not None else self.fig.add_subplot(111)

        # get labels if not provided
        if self.labels is None:
            if self.vector is None:
                self.labels = [self.source_name(i) for i in range(self.nin)]
            elif isinstance(self.vector, int):
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
            self.ax.set_title(self.title)
        else:
            self.ax.set_title(self._name_tex or "")

        # grid control
        if self.grid is True:
            self.ax.grid(self.grid)
        elif isinstance(self.grid, (list, tuple)):
            self.ax.grid(True, *self.grid)  # type: ignore[arg-type]

        # set limits
        self.ax.set_xlim(0, simstate.tf)

        if self.scale != "auto":
            self.ax.set_ylim(*self.scale)  # type: ignore
        if self.labels is not None:

            def fix_underscore(s: str) -> str:
                if s[0] == "_":
                    return "-" + s[1:]
                else:
                    return s

            self._cursor_labels = [fix_underscore(label) for label in self.labels]
            legend = self.ax.legend(self._cursor_labels, loc=self.loc)
            if legend is not None:
                legend.set_draggable(False)
        else:
            self._cursor_labels = [f"y{i}" for i in range(self.nplots)]

        # Apply dark-theme text styling when inside a tiled (shared-figure) layout.
        if getattr(self, "_tile_axes", None) is not None:
            _apply_tile_axes_style(self.ax)
        cursor_color = (
            CURSOR_COLOR_DARK
            if getattr(self, "_tile_axes", None) is not None
            else CURSOR_COLOR_LIGHT
        )

        # Add interactive data cursor: a thin vertical line + translucent value box.
        self._cursor_line = self.ax.axvline(
            0.0,
            color=cursor_color,
            linewidth=CURSOR_LINE_WIDTH,
            alpha=CURSOR_LINE_ALPHA,
            visible=False,
            zorder=3,
        )
        self._cursor_text = self.ax.text(
            self._cursor_text_xy[0],
            self._cursor_text_xy[1],
            "",
            transform=self.ax.transAxes,
            va="top",
            ha="left",
            visible=False,
            bbox=_cursor_text_bbox_style(),
        )
        self.fig.canvas.mpl_connect("motion_notify_event", self._cursor_on_move)
        self.fig.canvas.mpl_connect("axes_leave_event", self._cursor_on_leave)
        self.fig.canvas.mpl_connect("button_press_event", self._cursor_on_press)
        self.fig.canvas.mpl_connect("button_release_event", self._cursor_on_release)
        _cursor_add_owner(self)
        _cursor_register_controls(self)

        if self.watch:
            for wire in self.input_wires:  # type: ignore[attr-defined]
                plug = wire.start  # start plug for input wire

                # append to the watchlist, bdsim.run() will do the rest
                simstate.watchlist.append(plug)
                simstate.watchnamelist.append(str(plug))
        plt.draw()

    def step(self, t: float, inports: list[Any]) -> None:
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
            data = inports[0]
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

        # Keep cursor readout up to date while data evolves.
        if self._cursor_x is not None:
            self._cursor_update(self._cursor_x)

        super().step(t, inports)

    def _cursor_values(self, x: float) -> list[float]:
        if len(self.tdata) == 0:
            return []

        values = []
        for i in range(self.nplots):
            y = self.ydata[i]
            if len(y) == 0:
                values.append(float("nan"))
            else:
                values.append(float(np.interp(x, self.tdata, y)))
        return values

    def _cursor_update(self, x: float) -> None:
        if self._cursor_line is None or self._cursor_text is None:
            return
        if len(self.tdata) == 0:
            return

        self._cursor_x = x
        self._cursor_line.set_xdata([x, x])
        self._cursor_line.set_visible(True)

        values = self._cursor_values(x)
        lines = []
        for label, value in zip(self._cursor_labels, values):
            lines.append(f"{label}: {value:.6g}")
        self._cursor_text.set_text("\n".join(lines))
        self._cursor_text.set_visible(True)
        if self.fig is not None:
            self.fig.canvas.draw_idle()

    def _cursor_on_move(self, event: Any) -> None:
        if not self._enabled:
            return
        if not _cursor_enabled(self):
            return
        if self._cursor_dragging:
            self._cursor_move_textbox(event)
        if event.inaxes is not self.ax or event.xdata is None:
            return
        self._cursor_update(float(event.xdata))

    def _cursor_on_leave(self, event: Any) -> None:
        if not _cursor_enabled(self):
            return
        if self._cursor_dragging:
            return
        if self._cursor_line is not None:
            self._cursor_line.set_visible(False)
        if self._cursor_text is not None:
            self._cursor_text.set_visible(False)
        if self.fig is not None:
            self.fig.canvas.draw_idle()

    def _event_to_axes(self, event: Any) -> tuple[float, float] | np.ndarray | None:
        if self.ax is None or event.x is None or event.y is None:
            return None
        return self.ax.transAxes.inverted().transform((event.x, event.y))

    def _cursor_move_textbox(self, event: Any) -> None:
        if self._cursor_text is None:
            return
        point = self._event_to_axes(event)
        if point is None:
            return
        x = float(np.clip(point[0] - self._cursor_drag_offset[0], 0.01, 0.99))
        y = float(np.clip(point[1] - self._cursor_drag_offset[1], 0.01, 0.99))
        self._cursor_text_xy = (x, y)
        self._cursor_text.set_position(self._cursor_text_xy)
        if self.fig is not None:
            self.fig.canvas.draw_idle()

    def _cursor_on_press(self, event: Any) -> None:
        if not _cursor_enabled(self):
            return
        if self._cursor_text is None or event.button != 1:
            return
        contains, _ = self._cursor_text.contains(event)
        if not contains:
            return
        point = self._event_to_axes(event)
        if point is None:
            return
        self._cursor_dragging = True
        self._cursor_drag_offset = (
            point[0] - self._cursor_text_xy[0],
            point[1] - self._cursor_text_xy[1],
        )

    def _cursor_on_release(self, event: Any) -> None:
        if event.button == 1:
            self._cursor_dragging = False

    def _cursor_apply_enabled(self, enabled: bool) -> None:
        if not enabled:
            self._cursor_dragging = False
            self._cursor_x = None
            if self._cursor_line is not None:
                self._cursor_line.set_visible(False)
            if self._cursor_text is not None:
                self._cursor_text.set_visible(False)
            if self.fig is not None:
                self.fig.canvas.draw_idle()


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
        style: str | dict | None = None,
        scale: Literal["auto"] | list | tuple = "auto",
        aspect: str = "equal",
        labels: list[str] = ["X", "Y"],
        init: Callable | None = None,
        nin: int = 2,
        **blockargs: Any,
    ) -> None:
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
        super().__init__(inames=("x", "y"), **blockargs)

        self.xdata: list[Any] = []
        self.ydata: list[Any] = []
        self.line: Any = None
        if init is not None:
            assert callable(init), "graphics init function must be callable"
        self.init = init

        self.styles = style
        if scale != "auto":
            scale = smb.expand_dims(scale, 2)  # type: ignore[arg-type]
        self.scale = scale
        self.aspect = aspect
        self.labels = labels

        # Interactive cursor state (initialized in start()).
        self._cursor_marker: Any = None
        self._cursor_text: Any = None
        self._cursor_index: int | None = None
        self._cursor_text_xy: tuple[float, float] = (0.02, 0.98)
        self._cursor_dragging: bool = False
        self._cursor_drag_offset: tuple[float, float] = (0.0, 0.0)

    def start(self, simstate: Any) -> None:
        super().start(simstate)

        if not self._enabled:
            return

        # create the plot
        super().reset()

        self.fig = self.create_figure(simstate)
        tile_ax = getattr(self, "_tile_axes", None)
        self.ax = tile_ax if tile_ax is not None else self.fig.gca()

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
        self.ax.set_title(self.name or "")
        if not (isinstance(self.scale, str) and self.scale == "auto"):
            self.ax.set_xlim(*self.scale[0:2])  # type: ignore[arg-type]
            self.ax.set_ylim(*self.scale[2:4])  # type: ignore[arg-type]
        self.ax.set_aspect(self.aspect)  # type: ignore[arg-type]
        if self.init is not None:
            self.init(self.ax)

        # Apply dark-theme text styling when inside a tiled (shared-figure) layout.
        if getattr(self, "_tile_axes", None) is not None:
            _apply_tile_axes_style(self.ax)
        cursor_color = (
            CURSOR_COLOR_DARK
            if getattr(self, "_tile_axes", None) is not None
            else CURSOR_COLOR_LIGHT
        )

        self._cursor_marker = self.ax.plot(
            [],
            [],
            marker="o",
            linestyle="None",
            color=cursor_color,
            markersize=CURSOR_MARKER_SIZE,
            alpha=CURSOR_MARKER_ALPHA,
            visible=False,
            zorder=3,
        )[0]
        self._cursor_text = self.ax.text(
            self._cursor_text_xy[0],
            self._cursor_text_xy[1],
            "",
            transform=self.ax.transAxes,
            va="top",
            ha="left",
            visible=False,
            bbox=_cursor_text_bbox_style(),
        )
        self.fig.canvas.mpl_connect("motion_notify_event", self._cursor_on_move)
        self.fig.canvas.mpl_connect("axes_leave_event", self._cursor_on_leave)
        self.fig.canvas.mpl_connect("button_press_event", self._cursor_on_press)
        self.fig.canvas.mpl_connect("button_release_event", self._cursor_on_release)
        _cursor_add_owner(self)
        _cursor_register_controls(self)

        plt.draw()

    def step(self, t: float, inports: list[Any]) -> None:
        if not self._enabled:
            return
        self._step(inports[0], inports[1], t)

    def _step(self, x: Any, y: Any, t: float) -> None:
        self.xdata.append(x)
        self.ydata.append(y)

        assert self.fig is not None, "figure not created, step called before start?"
        plt.figure(self.fig.number)
        self.line.set_data(self.xdata, self.ydata)

        assert (
            self.bd is not None
        ), f"block {self.name} not connected to a block diagram, step called before start?"
        if self.bd.runtime.options.animation:
            self.fig.canvas.flush_events()

        if isinstance(self.scale, str) and self.scale == "auto":
            self.ax.relim()
            self.ax.autoscale_view()

        if self._cursor_index is not None:
            self._cursor_update_from_index(self._cursor_index)
        super().step(t, [])

    def _xy_nearest_index(self, event: Any) -> int | None:
        if len(self.xdata) == 0 or len(self.ydata) == 0:
            return None
        if event.x is None or event.y is None:
            return None

        points = np.column_stack((self.xdata, self.ydata))
        points_disp = self.ax.transData.transform(points)
        delta = points_disp - np.array([event.x, event.y])
        idx = int(np.argmin(np.sum(delta * delta, axis=1)))
        return idx

    def _cursor_update_from_index(self, index: int) -> None:
        if self._cursor_marker is None or self._cursor_text is None:
            return
        if len(self.xdata) == 0 or len(self.ydata) == 0:
            return

        index = max(0, min(index, len(self.xdata) - 1))
        self._cursor_index = index
        x = float(self.xdata[index])
        y = float(self.ydata[index])
        self._cursor_marker.set_data([x], [y])
        self._cursor_marker.set_visible(True)

        x_label = self.labels[0] if len(self.labels) > 0 else "x"
        y_label = self.labels[1] if len(self.labels) > 1 else "y"
        self._cursor_text.set_text(f"{x_label}: {x:.6g}\\n{y_label}: {y:.6g}")
        self._cursor_text.set_visible(True)
        if self.fig is not None:
            self.fig.canvas.draw_idle()

    def _event_to_axes(self, event: Any) -> tuple[float, float] | np.ndarray | None:
        if self.ax is None or event.x is None or event.y is None:
            return None
        return self.ax.transAxes.inverted().transform((event.x, event.y))

    def _cursor_move_textbox(self, event: Any) -> None:
        if self._cursor_text is None:
            return
        point = self._event_to_axes(event)
        if point is None:
            return
        x = float(np.clip(point[0] - self._cursor_drag_offset[0], 0.01, 0.99))
        y = float(np.clip(point[1] - self._cursor_drag_offset[1], 0.01, 0.99))
        self._cursor_text_xy = (x, y)
        self._cursor_text.set_position(self._cursor_text_xy)
        if self.fig is not None:
            self.fig.canvas.draw_idle()

    def _cursor_on_move(self, event: Any) -> None:
        if not self._enabled:
            return
        if not _cursor_enabled(self):
            return
        if self._cursor_dragging:
            self._cursor_move_textbox(event)
        if event.inaxes is not self.ax:
            return
        idx = self._xy_nearest_index(event)
        if idx is None:
            return
        self._cursor_update_from_index(idx)

    def _cursor_on_leave(self, event: Any) -> None:
        if not _cursor_enabled(self):
            return
        if self._cursor_dragging:
            return
        if self._cursor_marker is not None:
            self._cursor_marker.set_visible(False)
        if self._cursor_text is not None:
            self._cursor_text.set_visible(False)
        if self.fig is not None:
            self.fig.canvas.draw_idle()

    def _cursor_on_press(self, event: Any) -> None:
        if not _cursor_enabled(self):
            return
        if self._cursor_text is None or event.button != 1:
            return
        contains, _ = self._cursor_text.contains(event)
        if not contains:
            return
        point = self._event_to_axes(event)
        if point is None:
            return
        self._cursor_dragging = True
        self._cursor_drag_offset = (
            point[0] - self._cursor_text_xy[0],
            point[1] - self._cursor_text_xy[1],
        )

    def _cursor_on_release(self, event: Any) -> None:
        if event.button == 1:
            self._cursor_dragging = False

    def _cursor_apply_enabled(self, enabled: bool) -> None:
        if not enabled:
            self._cursor_dragging = False
            self._cursor_index = None
            if self._cursor_marker is not None:
                self._cursor_marker.set_visible(False)
            if self._cursor_text is not None:
                self._cursor_text.set_visible(False)
            if self.fig is not None:
                self.fig.canvas.draw_idle()

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

    def __init__(self, indices: list[int] = [0, 1], **blockargs: Any) -> None:
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

    def step(self, t: float, inports: list[Any]) -> None:
        if not self._enabled:
            return

        # inputs are set
        x = inports[0][self.indices[0]]
        y = inports[0][self.indices[1]]

        super()._step(x, y, t)


# ------------------------------------------------------------------------ #


if __name__ == "__main__":  # pragma: no cover
    from pathlib import Path
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[3]
    test_file = (
        root / "tests" / "blocks" / f"test_blocks_{Path(__file__).stem.lower()}.py"
    )

    if not test_file.exists():
        print(f"No module unit tests found for {Path(__file__).name}: {test_file}")
        raise SystemExit(0)

    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", str(test_file)]))
