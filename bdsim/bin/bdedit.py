#!/usr/bin/env python3

# Library imports
import sys

# PyQt5 imports
from PyQt5.QtWidgets import *

# BdEdit imports
#from ..bdedit.interface import Interface
from bdsim.bdedit.interface import Interface

# Executable code to launch the BdEdit application window
if __name__ == '__main__':
    # A QApplication instance is made, which is the window that holds everything
    app = QApplication(sys.argv)

    # The resolution of the user's screen is extracted (used for determining
    # the size of the application window)
    screen_resolution = app.desktop().screenGeometry()

    # Finally the window is displayed by creating an instance of Interface,
    # which holds all the logic for how the application should appear and which
    # connects all the other Classes through the Interface.
    window = Interface(screen_resolution)

    # Finally when the application is closed, the application is exited out of
    sys.exit(app.exec_())
