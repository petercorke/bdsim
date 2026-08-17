"""GraphicsBlock base class: Matplotlib and notebook support.

Everything in this module depends on matplotlib.  It is kept separate from
block.py so that the core block hierarchy (Block, SinkBlock, SourceBlock, …)
can be imported without pulling in the full matplotlib stack.

Public names exported here are re-exported via bdsim.block_types for
backward compatibility.
"""

from __future__ import annotations

import sys
import math
import importlib
from typing import TYPE_CHECKING, Any

import matplotlib
import matplotlib.figure
from matplotlib import animation
import matplotlib.pyplot as plt

from bdsim.block import SinkBlock

if TYPE_CHECKING:
    from bdsim.components import SimulationState


def is_notebook_backend(backend: str) -> bool:
    """Return True if *backend* names a Jupyter/inline rendering backend.

    Matplotlib exposes notebook backends under two different name forms:
    - Full module path: ``module://matplotlib_inline.backend_inline``,
      ``module://ipympl.backend_nbagg``, etc.
    - Short alias registered by the magic: ``inline``, ``widget``, ``nbagg``.

    Recognising both forms prevents bdsim from overriding a notebook backend
    with a desktop GUI backend (e.g. QtAgg) when running inside Jupyter.
    """
    if backend.startswith("module://"):
        return True
    return backend.lower() in ("inline", "widget", "nbagg")


class GraphicsBlock(SinkBlock):
    """
    A GraphicsBlock is a subclass of SinkBlock that represents a block that has inputs
    but no outputs and creates/updates a graphical display.
    """

    PLOT3D = False
    TIMESTAMP = False
    TIMESTAMP_FORMAT = "t={t:.3f}"

    def __init__(
        self,
        movie: str | None = None,
        timestamp: bool | None = None,
        timestamp_fmt: str | None = None,
        watch: bool = False,
        **blockargs: Any,
    ) -> None:
        """
        Create a graphical display block.

        :param movie: Save animation in this file in MP4 format, defaults to None
        :type movie: str, optional
        :param timestamp: Overlay simulation time on rendered graphics frames;
            if None, use class variable ``TIMESTAMP``
        :type timestamp: bool, optional
        :param timestamp_fmt: Format string used for timestamp text,
            defaults to ``TIMESTAMP_FORMAT``
        :type timestamp_fmt: str, optional
        :param watch: add this block's input signal(s) to the watchlist,
            defaults to False
        :type watch: bool, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: transfer function block base class
        :rtype: GraphicsBlock

        This is the parent class of all graphic display blocks.
        """
        super().__init__(**blockargs)
        self._graphics = True
        self._fig: matplotlib.figure.Figure | None = None
        self.ax: Any = None
        self.watch = watch
        self._tile_subplotspec: Any = None
        self._movie = movie
        self._movie_started = False
        self._timestamp = self.TIMESTAMP if timestamp is None else bool(timestamp)
        self._timestamp_fmt = (
            self.TIMESTAMP_FORMAT if timestamp_fmt is None else str(timestamp_fmt)
        )
        self._timestamp_artist: Any = None

    @property
    def fig(self) -> matplotlib.figure.Figure | None:
        return self._fig

    @fig.setter
    def fig(self, v: matplotlib.figure.Figure | None) -> None:
        self._fig = v
        if v is not None and self._movie is not None:
            self._start_movie()

    @property
    def movie(self) -> str | None:
        return self._movie

    @movie.setter
    def movie(self, v: str | None) -> None:
        self._movie = v
        self._movie_started = False

    @property
    def writer(self) -> Any:
        return self._writer

    @writer.setter
    def writer(self, v: Any) -> None:
        self._writer = v

    def start(self, simstate: SimulationState) -> None:
        # plt.draw()
        # plt.show(block=False)
        run_id = id(simstate)

        if (
            getattr(self, "_graphics_start_in_progress", False)
            and getattr(self, "_graphics_start_in_progress_run_id", None) == run_id
        ):
            raise RuntimeError("re-entrant graphics start detected for block")

        if getattr(self, "_graphics_start_run_id", None) == run_id:
            raise RuntimeError("duplicate graphics start detected for block")

        self._simstate = simstate
        self._enabled = simstate.options.graphics

        if self.watch:
            # watch-list registration is a data-collection concern, not a
            # graphics one -- must happen even when graphics is disabled
            # (eg. BDSIM_NO_GRAPHICS=1), otherwise out.y silently ends up
            # empty instead of containing the watched signals. Lives here
            # rather than in each subclass's start() so every GraphicsBlock
            # gets it for free.
            for wire in self._input_wires:  # type: ignore[attr-defined]
                plug = wire.start  # start plug for input wire

                # append to the watchlist, bdsim.run() will do the rest
                simstate.watchlist.append(plug)
                simstate.watchnamelist.append(str(plug))

        self._graphics_start_in_progress = True
        self._graphics_start_in_progress_run_id = run_id
        try:
            if self._enabled:
                # Fresh graphics setup once per run.
                self.fig = None
                self.ax = None
                self.fig = self.create_figure(simstate)
                self.ax = self._create_default_axes()
        finally:
            self._graphics_start_in_progress = False
            self._graphics_start_in_progress_run_id = None

        self._graphics_start_run_id = run_id

    def validate_start(self) -> None:
        if not getattr(self, "_enabled", False):
            return

        if self.fig is None:
            raise RuntimeError("graphics start did not create a figure")

        if self.ax is None:
            raise RuntimeError("graphics start did not create axes")

    def _create_default_axes(self) -> Any:
        if self.fig is None:
            return None

        tile_subplotspec = getattr(self, "_tile_subplotspec", None)
        if tile_subplotspec is not None:
            if bool(getattr(self, "PLOT3D", False)):
                return self.fig.add_subplot(tile_subplotspec, projection="3d")
            return self.fig.add_subplot(tile_subplotspec)

        if bool(getattr(self, "PLOT3D", False)):
            return self.fig.add_subplot(111, projection="3d")
        return self.fig.add_subplot(111)

    def _start_movie(self) -> None:
        """Set up the FFMpeg writer once self._fig has been created."""
        if self._movie_started:
            return

        if self._movie is not None:
            try:
                fps = float(getattr(self._simstate.options, "animation_rate", 10.0))
                if fps <= 0:
                    fps = 10.0
                fps_int = max(1, int(round(fps)))
                self._writer = animation.FFMpegWriter(
                    fps=fps_int, extra_args=["-vcodec", "libx264"]
                )
                self._writer.setup(fig=self._fig, outfile=self._movie)  # type: ignore[union-attr]
                self._movie_started = True
                print("movie block", self, " --> ", self._movie)
            except FileNotFoundError:
                self.fatal("cannot save movie, please install ffmpeg")  # type: ignore[union-attr]

    def _update_timestamp(self, t: float) -> None:
        if not self._timestamp or self._fig is None:
            return

        if self._timestamp_artist is None:
            self._timestamp_artist = self._fig.text(
                0.01,
                0.01,
                "",
                ha="left",
                va="bottom",
                fontsize=9,
                color="white",
                bbox={
                    "facecolor": "black",
                    "alpha": 0.55,
                    "pad": 2,
                    "edgecolor": "none",
                },
            )

        try:
            label = self._timestamp_fmt.format(t=float(t))
        except Exception:
            label = f"t={float(t):.3f}"
        self._timestamp_artist.set_text(label)

    def step(self, t: float, inports: list[Any]) -> None:
        # super().step(t, inports)  # type: ignore[safe-super]

        simstate = getattr(self, "_simstate", None)
        if simstate is not None and bool(getattr(simstate, "_stop_requested", False)):
            return

        self._update_timestamp(t)

        # bring the figure up to date in a backend-specific way
        if self._simstate.options.animation:
            notebook_backend = bool(getattr(self._simstate, "notebook_backend", False))
            tiled = getattr(self._simstate, "ntiles", None) not in (None, [], [1, 1])
            draw_key = float(t)
            already_drawn = bool(
                tiled
                and self._fig is not None
                and getattr(self._fig, "_bdsim_last_draw_t", None) == draw_key
            )

            if notebook_backend:
                # Notebook refresh is coordinated centrally by DisplayManager.
                pass
            elif not already_drawn:
                if tiled and self._fig is not None:
                    self._fig._bdsim_last_draw_t = draw_key

                if self._simstate.backend == "TkAgg":
                    self._fig.canvas.flush_events()  # type: ignore[union-attr]
                    plt.show(block=False)
                    plt.show(block=False)
                elif self._simstate.backend == "Qt5Agg":
                    self._fig.canvas.flush_events()  # type: ignore[union-attr]
                    self._fig.canvas.draw()  # type: ignore[union-attr]
                else:
                    self._fig.canvas.draw()  # type: ignore[union-attr]

        if self._movie is not None:
            try:
                self._writer.grab_frame()  # type: ignore[union-attr]
            except AttributeError:
                self.fatal("cannot save movie, please install ffmpeg")  # type: ignore[union-attr]

    def done(self, block=False, **kwargs) -> None:
        if self._fig is not None:
            simstate = getattr(self, "_simstate", None)
            notebook_backend = bool(getattr(simstate, "notebook_backend", False))
            if not notebook_backend:
                self._fig.canvas.start_event_loop(0.001)  # type: ignore[union-attr]
            if self._movie is not None and self._movie_started:
                self._writer.finish()  # type: ignore[union-attr]
                self._movie_started = False
                self._timestamp_artist = None
                # self.cleanup()
            if notebook_backend:
                self._fig.canvas.draw_idle()  # type: ignore[union-attr]
            else:
                plt.show(block=block)

    def savefig(
        self, filename: str | None = None, format: str = "pdf", **kwargs: Any
    ) -> None:
        """
        Save the figure as an image file

        :param fname: Name of file to save graphics to
        :type fname: str
        :param ``**kwargs``: Options passed to `savefig <https://matplotlib.org/3.2.2/api/_as_gen/matplotlib.pyplot.savefig.html>`_

        The file format is taken from the file extension and can be
        jpeg, png or pdf.
        """
        try:
            assert self._fig is not None, "no figure to save"
            plt.figure(self._fig.number)  # make block's figure the current one
            if filename is None:
                filename = self.name or ""
            filename += "." + format
            print("saved {} -> {}".format(str(self), filename))
            plt.savefig(filename, **kwargs)  # save the current figure

        except:
            pass

    def create_figure(self, state: SimulationState) -> matplotlib.figure.Figure:
        def resolve_tiles_spec(spec: str | None) -> list[int] | None:
            if spec is None:
                return None
            spec_l = spec.strip().lower()
            if spec_l == "":
                return None
            if spec_l in {"square", "wide", "tall"}:
                ngraphics = sum(
                    1 for b in self.bd.blocklist if getattr(b, "isgraphics", False)
                )
                ngraphics = max(1, ngraphics)
                if spec_l == "wide":
                    # Arrange windows horizontally.
                    return [1, ngraphics]
                if spec_l == "tall":
                    # Arrange windows vertically.
                    return [ngraphics, 1]
                rows = int(math.ceil(math.sqrt(ngraphics)))
                cols = int(math.ceil(ngraphics / rows))
                return [rows, cols]

            parts = spec_l.split("x")
            if len(parts) != 2:
                raise ValueError(
                    f"bad tiles spec '{spec}', expected RxC or one of square|wide|tall"
                )
            try:
                rows, cols = int(parts[0]), int(parts[1])
            except ValueError as exc:
                raise ValueError(
                    f"bad tiles spec '{spec}', expected integer RxC"
                ) from exc
            if rows <= 0 or cols <= 0:
                raise ValueError(f"bad tiles spec '{spec}', row/col must be > 0")
            return [rows, cols]

        def move_figure(
            f: matplotlib.figure.Figure, x: int | float, y: int | float
        ) -> None:
            """Move figure's upper left corner to pixel (x, y)"""
            backend: str = matplotlib.get_backend()
            x = int(x) + gstate.xoffset
            y = int(y)
            if backend == "TkAgg":
                f.canvas.manager.window.wm_geometry("+%d+%d" % (x, y))
            elif backend == "WXAgg":
                f.canvas.manager.window.SetPosition((x, y))
            else:
                # This works for QT and GTK
                # You can also use window.setGeometry
                try:
                    f.canvas.manager.window.move(x, y)
                except AttributeError:
                    # Native MacOSX backend does not expose a window move API.
                    if (
                        backend.lower() == "macosx"
                        and getattr(gstate, "ntiles", [1, 1]) not in (None, [1, 1])
                        and not getattr(gstate, "_warned_nomove", False)
                    ):
                        print(
                            "bdsim: backend MacOSX cannot position figure windows;"
                            " tiled windows may overlap. Use --backend QtAgg or TkAgg"
                            " (or BDSIM backend=QtAgg/TkAgg)."
                        )
                        gstate._warned_nomove = True
                    pass  # can't do this for MacOSX

        gstate = state
        options = state.options
        f: matplotlib.figure.Figure
        dpi: float
        row = 0
        col = 0

        if not hasattr(gstate, "_graphics_slot_claims"):
            gstate._graphics_slot_claims = []

        # Reset per-block tile assignment each start.
        self._tile_subplotspec = None

        self.bd.runtime.DEBUG(  # type: ignore[attr-defined]
            "graphics", "{} matplotlib figures exist", len(plt.get_fignums())
        )

        if gstate.fignum == 0:
            # no figures yet created, lazy initialization
            self.bd.runtime.DEBUG("graphics", "lazy initialization")  # type: ignore[attr-defined]

            def backend_available(name: str) -> bool:
                try:
                    from matplotlib.backends import backend_registry

                    return name.lower() in {
                        backend.lower() for backend in backend_registry.list_builtin()
                    }
                except Exception:
                    backends = getattr(matplotlib.rcsetup, "all_backends", [])
                    return name.lower() in {backend.lower() for backend in backends}

            # Non-interactive backends (Agg, Svg, Pdf, …) have no display and
            # must never be overridden by a GUI backend, regardless of platform.
            _NON_INTERACTIVE = {"agg", "svg", "pdf", "ps", "cairo", "template"}

            if options.backend is None:
                # If %matplotlib magic (or any other code) already set a notebook
                # or non-interactive backend, honour it and don't override.
                _current_backend = matplotlib.get_backend()
                if is_notebook_backend(_current_backend):
                    pass  # already a notebook backend, leave it alone
                elif _current_backend.lower() in _NON_INTERACTIVE:
                    pass  # headless/non-interactive backend, leave it alone
                elif sys.platform == "darwin":
                    # For macOS, prefer backends that allow window placement.
                    selected = False
                    for backend_name, module_names in (
                        ("QtAgg", ("PyQt6", "PySide6", "PyQt5", "PySide2")),
                        ("Qt5Agg", ("PyQt5", "PySide2")),
                        ("TkAgg", ("tkinter",)),
                    ):
                        if not backend_available(backend_name):
                            continue
                        for module_name in module_names:
                            try:
                                importlib.import_module(module_name)
                                matplotlib.use(backend_name)
                                print(
                                    "no graphics backend specified: "
                                    f"{backend_name} found, using instead of MacOSX"
                                )
                                selected = True
                                break
                            except Exception:
                                continue
                        if selected:
                            break
            else:
                try:
                    matplotlib.use(options.backend)
                except Exception as exc:
                    raise RuntimeError(
                        "can't select matplotlib backend "
                        f"'{options.backend}': {exc}. "
                        "If this is a Qt backend, install one of: PyQt6, PySide6, "
                        "PyQt5, or PySide2. Or use --backend TkAgg (requires tkinter)."
                    ) from exc

            mpl_backend: str = matplotlib.get_backend()
            gstate.backend = mpl_backend

            self.bd.runtime.DEBUG("graphics", "  backend={:s}", mpl_backend)  # type: ignore[attr-defined]

            # Resolve tile specification from explicit grid or shape keyword.
            # If no tiles are specified, graphics blocks each use their own figure.
            ntiles: list[int] | None = resolve_tiles_spec(options.tiles)

            xoffset = 0
            if options.shape is None:
                if mpl_backend == "Qt5Agg":
                    # next line actually creates a figure if none already exist
                    QScreen = plt.get_current_fig_manager().canvas.screen()  # type: ignore[union-attr]
                    # this is a QScreenClass object, see https://doc.qt.io/qt-5/qscreen.html#availableGeometry-prop
                    # next line creates a figure
                    sz = QScreen.availableSize()
                    dpiscale = (
                        QScreen.devicePixelRatio()
                    )  # is 2.0 for Mac laptop screen
                    self.bd.runtime.DEBUG(  # type: ignore[attr-defined]
                        "graphics",
                        "  {} x {} @ {}dpi",
                        sz.width(),
                        sz.height(),
                        dpiscale,
                    )

                    # check for a second screen
                    if options.altscreen:
                        vsize = QScreen.availableVirtualGeometry().getCoords()
                        if vsize[0] < 0:
                            # extra monitor to the left
                            xoffset = vsize[0]
                        elif vsize[0] >= sz.width():
                            # extra monitor to the right
                            xoffset = vsize[0]
                        self.bd.runtime.DEBUG(  # type: ignore[attr-defined]
                            "graphics", "  altscreen offset {}", xoffset
                        )

                    screen_width, screen_height = sz.width(), sz.height()
                    dpi = QScreen.physicalDotsPerInch()
                    f = plt.gcf()

                elif mpl_backend == "TkAgg":
                    window = plt.get_current_fig_manager().window  # type: ignore[union-attr]
                    screen_width, screen_height = (
                        window.winfo_screenwidth(),
                        window.winfo_screenheight(),
                    )
                    dpiscale = 1
                    self.bd.runtime.DEBUG(  # type: ignore[attr-defined]
                        "graphics",
                        "  screensize: {:d} x {:d}",
                        screen_width,
                        screen_height,
                    )
                    f = plt.gcf()
                    dpi = f.dpi

                else:
                    # all other backends (e.g. QtAgg, inline, widget)
                    # Modern backends handle HiDPI/Retina natively so dpiscale=1.
                    # Using dpiscale=2 double-counts the device pixel ratio on
                    # Retina Macs and makes everything visually half-sized.
                    f = plt.figure()
                    dpi = f.dpi
                    dpiscale = 1
                    screen_width, screen_height = f.get_size_inches() * f.dpi

                # Shared tiled mode uses one figure containing multiple subplots,
                # so preserve the normal figure size instead of shrinking the
                # container to a single-tile window.
                default_figsize = list(f.get_size_inches())
                effective_dpi = dpi * dpiscale
                if ntiles is None or ntiles == [1, 1]:
                    figsize = default_figsize
                else:
                    figsize = default_figsize

            else:
                # shape is given explictly
                screen_width, screen_height = [int(x) for x in options.shape.split("x")]

                f = plt.gcf()
                dpi = f.dpi
                dpiscale = 1
                figsize = [
                    screen_width / dpi,
                    screen_height / dpi,
                ]

            # Notebook/inline backends have no window manager; skip desktop GUI ops.
            _is_notebook_backend = is_notebook_backend(mpl_backend)
            if not _is_notebook_backend:
                f.canvas.manager.set_window_title(f"bdsim: Figure {f.number:d}")  # type: ignore[union-attr]

            # save graphics info away in state
            gstate.figsize = figsize
            gstate.dpi = dpi * dpiscale
            gstate.screensize_pix = (screen_width, screen_height)
            gstate.ntiles = ntiles
            gstate.xoffset = xoffset
            gstate.tiled_figure = None
            gstate.notebook_backend = _is_notebook_backend

            # resize the figure (skip in notebook: Jupyter controls figure size)
            if not _is_notebook_backend:
                f.set_dpi(gstate.dpi)
                f.set_size_inches(figsize, forward=True)  # type: ignore[union-attr, arg-type]
                plt.ion()

        else:
            # subsequent graphics blocks
            if gstate.ntiles is None:
                f = plt.figure(figsize=gstate.figsize, dpi=gstate.dpi)
            else:
                tiled_figure = getattr(gstate, "tiled_figure", None)
                assert tiled_figure is not None
                f = tiled_figure

        _notebook = getattr(gstate, "notebook_backend", False)
        if gstate.ntiles is None:
            # Untiled mode: each graphics block gets its own figure.
            if gstate.fignum > 0 and not _notebook:
                f.canvas.manager.set_window_title(f"bdsim: Figure {f.number:d}")  # type: ignore[union-attr]
        else:
            # Tiled mode: one shared figure with subplots; each block gets a tile.
            rows, cols = gstate.ntiles
            max_tiles = rows * cols
            claims_all = list(getattr(gstate, "_graphics_slot_claims", []))
            # Robustly derive occupied tiles from unique non-self claimants.
            # This tolerates stale/duplicate claim entries without overcounting.
            claimed_by_other: list[dict[str, Any]] = []
            seen_block_ids: set[int] = set()
            for claim in claims_all:
                bid = int(claim.get("block_id", -1))
                if bid < 0 or bid == id(self) or bid in seen_block_ids:
                    continue
                seen_block_ids.add(bid)
                claimed_by_other.append(claim)
            # In tiled mode, choose tile index by number of blocks that already
            # claimed a slot in this run, not by the global fignum counter.
            # This avoids false overflow if fignum drifts in notebook backends.
            tile_index = len(claimed_by_other)
            if tile_index >= max_tiles:
                raise ValueError(
                    "tile specification "
                    f"'{options.tiles}' has {max_tiles} tile(s) but "
                    f"requires at least {tile_index + 1}."
                )

            if tile_index == 0:
                gstate.tiled_figure = f
                f.clf()
                base_w = float(gstate.figsize[0])
                base_h = float(gstate.figsize[1])
                fig_w = max(base_w, 4.0 * cols)
                fig_h = max(base_h, 3.0 * rows)
                f.set_size_inches(fig_w, fig_h, forward=True)
                gstate.figsize = [fig_w, fig_h]
                gstate.tile_gridspec = f.add_gridspec(
                    rows, cols, wspace=0.25, hspace=0.30
                )

            row = tile_index // cols
            col = tile_index % cols
            subplotspec = gstate.tile_gridspec[row, col]
            self._tile_subplotspec = subplotspec

        # move figure windows only when not using shared tiled subplots,
        # and only when a real window manager is available (not notebook backends)
        if not _notebook:
            if gstate.ntiles is not None:
                if row == 0 and col == 0:
                    move_figure(f, 0, 0)
            else:
                move_figure(f, 0, 0)

        gstate.fignum += 1
        if gstate.ntiles is None:
            slot = gstate.fignum
        else:
            slot = row * cols + col + 1

        claims = getattr(gstate, "_graphics_slot_claims", [])
        claim_data = {
            "slot": slot,
            "name": str(getattr(self, "name", "") or "<unnamed>"),
            "type": str(getattr(self, "type", type(self).__name__)),
            "class": type(self).__name__,
            "block_id": id(self),
            "simstate_id": id(gstate),
        }
        existing_idx = next(
            (i for i, c in enumerate(claims) if int(c.get("block_id", -1)) == id(self)),
            None,
        )
        if existing_idx is None:
            claims.append(claim_data)
        else:
            claims[existing_idx] = claim_data

        def onkeypress(event: Any) -> None:
            key = str(getattr(event, "key", ""))
            key_l = key.lower()

            if key_l == "q" and key != "Q":
                plt.close(f)
            elif key_l == "q":
                print("\nclosing all windows")
                simstate = getattr(self, "_simstate", None)
                if simstate is not None:
                    simstate.stop = self
                    simstate._stop_requested = True
                    if getattr(simstate, "options", None) is not None:
                        simstate.options.hold = False
                plt.close("all")
            elif key_l == "x":
                print("\nclosing all windows")
                plt.close("all")
            elif key_l == "ctrl+c":
                print("\nterminating bdsim")
                sys.exit(1)
            else:
                print("key pressed", key)

        if not getattr(f, "_bdsim_global_keys", False):
            f.canvas.mpl_connect("key_press_event", onkeypress)
            f._bdsim_global_keys = True

        self.bd.runtime.DEBUG(  # type: ignore[attr-defined]
            "graphics", "create figure {:d} at ({:d}, {:d})", gstate.fignum, row, col
        )
        return f
