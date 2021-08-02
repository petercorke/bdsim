#!/usr/bin/env python3

# Library imports
import os
import sys
import argparse

# PyQt5 imports
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QTimer

# BdEdit imports
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

    # The resolution of the user's screen is extracted (used for determining
    # the size of the application window)
    screen_resolution = app.desktop().screenGeometry()

    # Finally the window is displayed by creating an instance of Interface,
    # which holds all the logic for how the application should appear and which
    # connects all the other Classes through the Interface.
    window = Interface(screen_resolution, args.debug)

    # Check what command line arguments have been passed, if any
    if args.file or args.print or args.debug:
        # Call bdedit functionality based on passed args
        if args.file:

            # Check if file at given file path exists
            if os.path.isfile(args.file):
                window.loadFromFilePath(args.file)

            # If file not found at path, return error msg
            else:
                print("File at given path not found")
                sys.exit(0)

        if args.print:
            # Check if a model has been given to load (should always be the case if trying to screenshot)
            # If it has, the logic for validating that path will always be checked before trying to screenshot in the above code
            if args.file:
                def screenshot(filename):
                    window.save_image(filename)
                    sys.exit(0)

                # Extract the name of given model
                file_basename = os.path.basename(args.file)
                filename = os.path.splitext(file_basename)[0]

                # After 100ms non-blocking delay, screenshot the model
                QTimer.singleShot(100, lambda: screenshot(filename + "-screenshot"))

            # No file found, return error and exit
            else:
                print("No file given to load model")
                sys.exit(0)

    # Finally when the application is closed, the application is exited out of
    sys.exit(app.exec_())
