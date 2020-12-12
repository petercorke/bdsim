import matplotlib
import matplotlib.pyplot as plt
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
        if not self.bd.options.animation:
            movie = None
        self.movie = movie

    def start(self):
        if self.movie is not None:
            self.writer = animation.FFMpegWriter(fps=10, extra_args=['-vcodec', 'libx264'])
            self.writer.setup(fig=self.fig, outfile=self.movie)

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

    def savefig(self, name=None, format='pdf', **kwargs):
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
            if name is None:
                name = self.name
            name += "." + format
            print('saving {} -> {}'.format(str(self), name))
            plt.savefig(fname, **kwargs)  # save the current figure

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
                
        if self.bd.fignum == 0:
            # no figures yet created, lazy initialization
            
            matplotlib.use(self.bd.options.backend)            
            mpl_backend = matplotlib.get_backend()
            print('matplotlib backend is', mpl_backend)
            
            dpiscale = 1
            if mpl_backend == 'Qt5Agg':
                from PyQt5 import QtWidgets
                app = QtWidgets.QApplication([])
                screen = app.primaryScreen()
                print('Screen: %s' % screen.name())
                size = screen.size()
                print('Size: %d x %d' % (size.width(), size.height()))
                rect = screen.availableGeometry()
                print('Available: %d x %d' % (rect.width(), rect.height()))
                sw = rect.width()
                sh = rect.height()
                #dpi = screen.physicalDotsPerInch()
                dpiscale = screen.devicePixelRatio() # is 2.0 for Mac laptop screen
            elif mpl_backend == 'TkAgg':
                window = plt.get_current_fig_manager().window
                sw =  window.winfo_screenwidth()
                sh =  window.winfo_screenheight()
                print('Size: %d x %d' % (sw, sh))
            self.bd.screensize_pix = (sw, sh)
            self.bd.tiles = [int(x) for x in self.bd.options.tiles.split('x')]
            
            # create a figure at default size to get dpi (TODO better way?)
            f = plt.figure(figsize=(1,1))
            self.bd.dpi = f.dpi / dpiscale
            print('dpi', self.bd.dpi)
            
            # compute fig size in inches (width, height)
            self.bd.figsize = [ self.bd.screensize_pix[0] / self.bd.tiles[1] / self.bd.dpi , self.bd.screensize_pix[1] / self.bd.tiles[0] / self.bd.dpi ]
            
            # resize the figure
            #plt.figure(num=f.number, figsize=self.figsize)
            f.set_size_inches(self.bd.figsize, forward=True)
            plt.ion()
        else:
            f = plt.figure(figsize=self.bd.figsize)
            
        # move the figure to right place on screen
        row = self.bd.fignum // self.bd.tiles[0]
        col = self.bd.fignum % self.bd.tiles[0]
        move_figure(f, col * self.bd.figsize[0] * self.bd.dpi, row * self.bd.figsize[1] * self.bd.dpi)
        
        self.bd.fignum += 1
        #print('create figure', self.fignum, row, col)
        return f
        