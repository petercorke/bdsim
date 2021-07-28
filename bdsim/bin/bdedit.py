#!/usr/bin/env python3

# Library imports
import sys
import argparse

# PyQt5 imports
from PyQt5.QtWidgets import *

# BdEdit imports
#from ..bdedit.interface import Interface
from bdsim.bdedit.interface import Interface

# Executable code to launch the BdEdit application window
if __name__ == '__main__':

    # handle command line options, bdedit -h for details
    parser = argparse.ArgumentParser(description='Interactive edit for bdsim models')
    parser.add_argument('file', type=str, nargs='?',
        help='Load this model into interactive session')
    parser.add_argument('--print', '-p', 
        action='store_const', const=True, default=False,
        help='Save model to screenshot and exit')
    parser.add_argument('--debug', '-d', 
        action='store_const', const=True, default=False,
        help='Enable debugging')
    args, unparsed_args = parser.parse_known_args()
    
    # args holds all the command line info:
    #  args.file file name if given, else None
    #  args.debug True if -d option given
    #  args.print True if -p option given, load the file, save screenshot,
    #                then exit

    # insert argv[0] into head of list of remaining args, and hand that to Qt
    unparsed_args.insert(0, sys.argv[0])

    # A QApplication instance is made, which is the window that holds everything
    app = QApplication(unparsed_args)
    # app = QApplication(sys.argv)

    # The resolution of the user's screen is extracted (used for determining
    # the size of the application window)
    screen_resolution = app.desktop().screenGeometry()

    # Finally the window is displayed by creating an instance of Interface,
    # which holds all the logic for how the application should appear and which
    # connects all the other Classes through the Interface.
    window = Interface(screen_resolution)

    # Finally when the application is closed, the application is exited out of
    sys.exit(app.exec_())
