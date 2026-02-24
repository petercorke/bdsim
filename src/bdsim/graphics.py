from __future__ import annotations
import sys
import matplotlib
import matplotlib.figure
import matplotlib.pyplot as plt
from matplotlib import animation
from bdsim.components import SinkBlock


class GraphicsBlock(SinkBlock):
    """
    A GraphicsBlock is a subclass of SinkBlock that represents a block that has inputs
    but no outputs and creates/updates a graphical display.
    """

    blockclass = "graphics"

    def __init__(self, movie=None, **blockargs) -> None:
        """
        Create a graphical display block.

        :param movie: Save animation in this file in MP4 format, defaults to None
        :type movie: str, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: transfer function block base class
        :rtype: TransferBlock

        This is the parent class of all graphic display blocks.
        """

        super().__init__(**blockargs)
        self._graphics = True
        self.fig: matplotlib.figure.Figure | None = None
        self.movie = movie

    def start(self, simstate) -> None:

        # plt.draw()
        # plt.show(block=False)
        self._simstate = simstate
        self._enabled = simstate.options.graphics

        if self.movie is not None and not simstate.options.animation:
            print(
                "enabling global animation option to allow movie option on block", self
            )
            if not simstate.options.animation:
                print("must enable animation to render a movie")
        if self.movie is not None:
            try:
                self.writer = animation.FFMpegWriter(
                    fps=10, extra_args=["-vcodec", "libx264"]
                )
                self.writer.setup(fig=self.fig, outfile=self.movie)  # type: ignore[union-attr]
                print("movie block", self, " --> ", self.movie)
            except FileNotFoundError:
                self.fatal("cannot save movie, please install ffmpeg")  # type: ignore[union-attr]

    def step(self, t, inports) -> None:
        super().step(t, inports)

        # bring the figure up to date in a backend-specific way
        if self._simstate.options.animation:
            if self._simstate.backend == "TkAgg":
                self.fig.canvas.flush_events()  # type: ignore[union-attr]
                plt.show(block=False)
                plt.show(block=False)
            elif self._simstate.backend == "Qt5Agg":
                self.fig.canvas.flush_events()  # type: ignore[union-attr]
                self.fig.canvas.draw()  # type: ignore[union-attr]
            else:
                self.fig.canvas.draw()  # type: ignore[union-attr]

        if self.movie is not None:
            try:
                self.writer.grab_frame()  # type: ignore[union-attr]
            except AttributeError:
                self.fatal("cannot save movie, please install ffmpeg")  # type: ignore[union-attr]

    def done(self, block=False) -> None:
        if self.fig is not None:
            self.fig.canvas.start_event_loop(0.001)  # type: ignore[union-attr]
            if self.movie is not None:
                self.writer.finish()  # type: ignore[union-attr]
                # self.cleanup()
            plt.show(block=block)

    def savefig(self, filename=None, format="pdf", **kwargs) -> None:
        """
        Save the figure as an image file

        :param fname: Name of file to save graphics to
        :type fname: str
        :param ``**kwargs``: Options passed to `savefig <https://matplotlib.org/3.2.2/api/_as_gen/matplotlib.pyplot.savefig.html>`_

        The file format is taken from the file extension and can be
        jpeg, png or pdf.
        """
        try:
            assert self.fig is not None, "no figure to save"
            plt.figure(self.fig.number)  # make block's figure the current one
            if filename is None:
                filename = self.name or ""
            filename += "." + format
            print("saved {} -> {}".format(str(self), filename))
            plt.savefig(filename, **kwargs)  # save the current figure

        except:
            pass

    def create_figure(self, state) -> matplotlib.figure.Figure:
        def move_figure(f, x, y) -> None:
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
                    pass  # can't do this for MacOSX

        gstate = state
        options = state.options

        self.bd.runtime.DEBUG(  # type: ignore[union-attr]
            "graphics", "{} matplotlib figures exist", len(plt.get_fignums())
        )

        if gstate.fignum == 0:
            # no figures yet created, lazy initialization
            self.bd.runtime.DEBUG("graphics", "lazy initialization")  # type: ignore[union-attr]

            if options.backend is None:
                if sys.platform == "darwin":
                    # for MacOS, use Qt5Agg if its installed
                    # otherwise use default (MacOSX)
                    if "Qt5Agg" in matplotlib.rcsetup.all_backends:  # type: ignore[union-attr]
                        try:
                            import PyQt5  # type: ignore[import-untyped]

                            matplotlib.use("Qt5Agg")
                            print(
                                "no graphics backend specified: Qt5Agg found, using"
                                " instead of MacOSX"
                            )
                        except:
                            pass
            else:
                try:
                    matplotlib.use(options.backend)
                except ImportError:
                    self.fatal(f"can't select backend: {options.backend}")  # type: ignore[union-attr]

            mpl_backend: str = matplotlib.get_backend()
            gstate.backend = mpl_backend

            self.bd.runtime.DEBUG("graphics", "  backend={:s}", mpl_backend)  # type: ignore[union-attr]

            # split the string
            ntiles: list[int] = [int(x) for x in options.tiles.split("x")]

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
                    self.bd.runtime.DEBUG(  # type: ignore[union-attr]
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
                        self.bd.runtime.DEBUG(  # type: ignore[union-attr]
                            "graphics", "  altscreen offset {}", xoffset
                        )

                    screen_width, screen_height = sz.width(), sz.height()
                    dpi = QScreen.physicalDotsPerInch()
                    f: matplotlib.figure.Figure = plt.gcf()

                elif mpl_backend == "TkAgg":
                    window = plt.get_current_fig_manager().window  # type: ignore[union-attr]
                    screen_width, screen_height = (
                        window.winfo_screenwidth(),
                        window.winfo_screenheight(),
                    )
                    dpiscale = 1
                    self.bd.runtime.DEBUG(  # type: ignore[union-attr]
                        "graphics",
                        "  screensize: {:d} x {:d}",
                        screen_width,
                        screen_height,
                    )
                    f: matplotlib.figure.Figure = plt.gcf()
                    dpi: float = f.dpi

                else:
                    # all other backends
                    f: matplotlib.figure.Figure = plt.figure()
                    dpi: float = f.dpi
                    dpiscale = 2
                    screen_width, screen_height = f.get_size_inches() * f.dpi

                # compute fig size in inches (width, height)
                figsize = [
                    screen_width / ntiles[1] / dpi,
                    screen_height / ntiles[0] / dpi,
                ]

            else:
                # shape is given explictly
                screen_width, screen_height = [int(x) for x in options.shape.split("x")]

                f: matplotlib.figure.Figure = plt.gcf()

            f.canvas.manager.set_window_title(f"bdsim: Figure {f.number:d}")  # type: ignore[union-attr]

            # save graphics info away in state
            gstate.figsize = figsize
            gstate.dpi = dpi
            gstate.screensize_pix = (screen_width, screen_height)
            gstate.ntiles = ntiles
            gstate.xoffset = xoffset

            # resize the figure
            f.set_dpi(gstate.dpi * dpiscale)
            f.set_size_inches(figsize, forward=True)  # type: ignore[union-attr]
            plt.ion()

        else:
            # subsequent figures
            f: matplotlib.figure.Figure = plt.figure(
                figsize=gstate.figsize, dpi=gstate.dpi
            )

        # move the figure to right place on screen
        row = gstate.fignum // gstate.ntiles[0]
        col = gstate.fignum % gstate.ntiles[0]
        scale = 1.02
        move_figure(
            f,
            col * gstate.figsize[0] * gstate.dpi * scale,
            row * gstate.figsize[1] * gstate.dpi * scale,
        )
        gstate.fignum += 1

        def onkeypress(event) -> None:

            if event.key == "x":
                print("\nclosing all windows")
                plt.close("all")
            elif event.key == "ctrl+c":
                print("\nterminating bdsim")
                sys.exit(1)
            else:
                print("key pressed", event.key)

        f.canvas.mpl_connect("key_press_event", onkeypress)

        self.bd.runtime.DEBUG(  # type: ignore[union-attr]
            "graphics", "create figure {:d} at ({:d}, {:d})", gstate.fignum, row, col
        )
        return f
