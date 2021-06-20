import matplotlib
import matplotlib.pyplot as plt
from matplotlib import animation
from bdsim import SinkBlock

class GraphicsBlock(SinkBlock):
    """
    A GraphicsBlock is a subclass of SinkBlock that represents a block that has inputs
    but no outputs and creates/updates a graphical display.

    :param movie: Save animation in this file, defaults to None
    :type movie: str, optional
    :param ``**kwargs``: common Block options
    :return: A PRINT block
    :rtype: Print instance

    The animation is saved as an MP4 video in the specified file.
    """

    def __init__(self, movie=None, **kwargs):

        super().__init__(**kwargs)

        self.movie = movie

    def start(self):
        if self.movie is not None and not self.bd.options.animation:
            print('enabling global animation option to allow movie option on block', self)
            self.bd.options.animation = True
        if self.movie is not None:
            self.writer = animation.FFMpegWriter(fps=10, extra_args=['-vcodec', 'libx264'])
            self.writer.setup(fig=self.fig, outfile=self.movie)
            print('movie block', self, ' --> ', self.movie)

    def step(self):
        super().step()
        if self.movie is not None:
            self.writer.grab_frame()

    def done(self):
        if self.bd.options.graphics:
            self.fig.canvas.start_event_loop(0.001)
        if self.movie is not None:
            self.writer.finish()
            # self.cleanup()

    def savefig(self, filename=None, format='pdf', **kwargs):
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
            print('saving {} -> {}'.format(str(self), filename))
            plt.savefig(filename, **kwargs)  # save the current figure

        except:
            pass


    def create_figure(self):

        def move_figure(f, x, y):
            """Move figure's upper left corner to pixel (x, y)"""
            backend = matplotlib.get_backend()
            if backend == 'TkAgg':
                f.canvas.manager.window.wm_geometry("+%d+%d" % (x, y))
            elif backend == 'WXAgg':
                f.canvas.manager.window.SetPosition((x, y))
            else:
                # This works for QT and GTK
                # You can also use window.setGeometry
                f.canvas.manager.window.move(x, y)
        
        gstate = self.bd.state
        options = self.bd.options

        if gstate.fignum == 0:
            # no figures yet created, lazy initialization
            
            matplotlib.use(options.backend)            
            mpl_backend = matplotlib.get_backend()

            # split the string            
            ntiles = [int(x) for x in options.tiles.split('x')]
            
            dpiscale = 1
            print("Graphics:")
            print('  backend:', mpl_backend)

            if mpl_backend == 'Qt5Agg':
                from PyQt5 import QtWidgets
                app = QtWidgets.QApplication([])
                screen = app.primaryScreen()
                if screen.name is not None:
                    print('  Screen: %s' % screen.name())
                size = screen.size()
                print('  Size: %d x %d' % (size.width(), size.height()))
                rect = screen.availableGeometry()
                print('  Available: %d x %d' % (rect.width(), rect.height()))
                sw = rect.width()
                sh = rect.height()
                #dpi = screen.physicalDotsPerInch()
                dpiscale = screen.devicePixelRatio() # is 2.0 for Mac laptop screen
            elif mpl_backend == 'TkAgg':
                window = plt.get_current_fig_manager().window
                sw =  window.winfo_screenwidth()
                sh =  window.winfo_screenheight()
                print('  Size: %d x %d' % (sw, sh))

            # create a figure at default size to get dpi (TODO better way?)
            f = plt.figure(figsize=(1,1))
            dpi = f.dpi / dpiscale
            print('  dpi', dpi)
            
            # compute fig size in inches (width, height)
            figsize = [ sw / ntiles[1] / dpi , sh / ntiles[0] / dpi ]

            # save graphics info away in state
            gstate.figsize = figsize
            gstate.dpi = dpi
            gstate.screensize_pix = (sw, sh)
            gstate.ntiles = ntiles

            # resize the figure
            #plt.figure(num=f.number, figsize=self.figsize)
            f.set_size_inches(figsize, forward=True)
            plt.ion()
        else:
            f = plt.figure(figsize=gstate.figsize)
            
        # move the figure to right place on screen
        row = gstate.fignum // gstate.ntiles[0]
        col = gstate.fignum % gstate.ntiles[0]
        move_figure(f, col * gstate.figsize[0] * gstate.dpi, row * gstate.figsize[1] * gstate.dpi)
        
        gstate.fignum += 1
        #print('create figure', self.fignum, row, col)
        return f

            