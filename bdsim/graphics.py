import sys
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import animation
from bdsim.components import SinkBlock


class GraphicsBlock(SinkBlock):
    """
    A GraphicsBlock is a subclass of SinkBlock that represents a block that has inputs
    but no outputs and creates/updates a graphical display.
    """

    blockclass = "graphics"

    def __init__(self, movie=None, **blockargs):
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

        self.movie = movie

    def start(self):

        plt.draw()
        plt.show(block=False)

        if self.movie is not None and not self.bd.runtime.options.animation:
            print(
                "enabling global animation option to allow movie option on block", self
            )
            if not self.bd.runtime.options.animation:
                print("must enable animation to render a movie")
        if self.movie is not None:
            try:
                self.writer = animation.FFMpegWriter(
                    fps=10, extra_args=["-vcodec", "libx264"]
                )
                self.writer.setup(fig=self.fig, outfile=self.movie)
                print("movie block", self, " --> ", self.movie)
            except FileNotFoundError:
                self.fatal("cannot save movie, please install ffmpeg")

    def step(self, state=None):
        super().step()

        # bring the figure up to date in a backend-specific way
        if state.options.animation:
            if state.backend == "TkAgg":
                self.fig.canvas.flush_events()
                plt.show(block=False)
                plt.show(block=False)
            elif state.backend == "Qt5Agg":
                self.fig.canvas.flush_events()
                self.fig.canvas.draw()
            else:
                self.fig.canvas.draw()

        if self.movie is not None:
            try:
                self.writer.grab_frame()
            except AttributeError:
                self.fatal("cannot save movie, please install ffmpeg")

    def done(self, state=None, block=False):
        if self.fig is not None:
            self.fig.canvas.start_event_loop(0.001)
            if self.movie is not None:
                self.writer.finish()
                # self.cleanup()
            plt.show(block=block)

    def savefig(self, filename=None, format="pdf", **kwargs):
        """
        Save the figure as an image file

        :param fname: Name of file to save graphics to
        :type fname: str
        :param ``**kwargs``: Options passed to `savefig <https://matplotlib.org/3.2.2/api/_as_gen/matplotlib.pyplot.savefig.html>`_

        The file format is taken from the file extension and can be
        jpeg, png or pdf.
        """
        try:
            plt.figure(self.fig.number)  # make block's figure the current one
            if filename is None:
                filename = self.name
            filename += "." + format
            print("saved {} -> {}".format(str(self), filename))
            plt.savefig(filename, **kwargs)  # save the current figure

        except:
            pass

    def create_figure(self, state):
        def move_figure(f, x, y):
            """Move figure's upper left corner to pixel (x, y)"""
            backend = matplotlib.get_backend()
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

        self.bd.runtime.DEBUG(
            "graphics", "{} matplotlib figures exist", len(plt.get_fignums())
        )

        if gstate.fignum == 0:
            # no figures yet created, lazy initialization
            self.bd.runtime.DEBUG("graphics", "lazy initialization")

            if options.backend is None:
                if sys.platform == "darwin":
                    # for MacOS, use Qt5Agg if its installed
                    # otherwise use default (MacOSX)
                    if "Qt5Agg" in matplotlib.rcsetup.all_backends:
                        try:
                            import PyQt5

                            matplotlib.use("Qt5Agg")
                            print(
                                "no graphics backend specified: Qt5Agg found, using instead of MacOSX"
                            )
                        except:
                            pass
            else:
                try:
                    matplotlib.use(options.backend)
                except ImportError:
                    self.fatal(f"can't select backend: {options.backend}")

            mpl_backend = matplotlib.get_backend()
            gstate.backend = mpl_backend

            self.bd.runtime.DEBUG("graphics", "  backend={:s}", mpl_backend)

            # split the string
            ntiles = [int(x) for x in options.tiles.split("x")]

            xoffset = 0
            if options.shape is None:
                if mpl_backend == "Qt5Agg":
                    # next line actually creates a figure if none already exist
                    QScreen = plt.get_current_fig_manager().canvas.screen()
                    # this is a QScreenClass object, see https://doc.qt.io/qt-5/qscreen.html#availableGeometry-prop
                    # next line creates a figure
                    sz = QScreen.availableSize()
                    dpiscale = (
                        QScreen.devicePixelRatio()
                    )  # is 2.0 for Mac laptop screen
                    self.bd.runtime.DEBUG(
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
                        self.bd.runtime.DEBUG(
                            "graphics", "  altscreen offset {}", xoffset
                        )

                    screen_width, screen_height = sz.width(), sz.height()
                    dpi = QScreen.physicalDotsPerInch()
                    f = plt.gcf()

                elif mpl_backend == "TkAgg":
                    window = plt.get_current_fig_manager().window
                    screen_width, screen_height = (
                        window.winfo_screenwidth(),
                        window.winfo_screenheight(),
                    )
                    dpiscale = 1
                    self.bd.runtime.DEBUG(
                        "graphics",
                        "  screensize: {:d} x {:d}",
                        screen_width,
                        screen_height,
                    )
                    f = plt.gcf()
                    dpi = f.dpi

                else:
                    # all other backends
                    f = plt.figure()
                    dpi = f.dpi
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

                f = plt.gcf()

            f.canvas.manager.set_window_title(f"bdsim: Figure {f.number:d}")

            # save graphics info away in state
            gstate.figsize = figsize
            gstate.dpi = dpi
            gstate.screensize_pix = (screen_width, screen_height)
            gstate.ntiles = ntiles
            gstate.xoffset = xoffset

            # resize the figure
            f.set_dpi(gstate.dpi * dpiscale)
            f.set_size_inches(figsize, forward=True)
            plt.ion()

        else:
            # subsequent figures
            f = plt.figure(figsize=gstate.figsize, dpi=gstate.dpi)

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

        def onkeypress(event):
            print("pressed", event.key)
            plt.close("all")

        f.canvas.mpl_connect("key_press_event", onkeypress)

        self.bd.runtime.DEBUG(
            "graphics", "create figure {:d} at ({:d}, {:d})", gstate.fignum, row, col
        )
        return f
