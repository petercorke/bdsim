#!/usr/bin/env python3

# Library imports
import os
import sys
import ctypes
import argparse
from pathlib import Path

from sys import platform
from pathlib import Path

from colored import fg, attr

# PyQt5 imports
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon

# BdEdit imports
from bdsim.bdedit.interface_manager import InterfaceWindow

# Executable code to launch the BdEdit application window
def main():

    print(fg("red"))
    print("bdedit is beta code and prone to random crashing, save your work often")
    print(attr(0))

    # handle command line options, bdedit -h for details
    parser = argparse.ArgumentParser(description="Interactive edit for bdsim models")
    parser.add_argument(
        "file", type=str, nargs="?", help="Load this model into interactive session"
    )
    parser.add_argument(
        "--print",
        "-p",
        nargs="?",
        action="store",
        const="",
        default=None,
        help="Save model to screenshot and exit, can optionally specify a filename, PDF extension is default",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_const",
        const=True,
        default=False,
        help="Enable debugging",
    )
    parser.add_argument(
        "--pdb",
        action="store_const",
        const=True,
        default=False,
        help="Enable pdb for spawned python subprocess",
    )
    parser.add_argument(
        "--background",
        "-b",
        type=str,
        default="grey",
        choices=["white", "grey"],
        help="Set background color",
    )
    parser.add_argument(
        "--fontsize", "-s", type=int, default="12", help="Set font size of block names"
    )
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        nargs="?",
        help="Specify screenshot extension type; PDF (default) or PNG",
    )
    args, unparsed_args = parser.parse_known_args()

    # args holds all the command line info:
    #  args.file file name if given, else None
    #  args.debug True if -d option given
    #  args.print True if -p option given, load the file, save screenshot, then exit
    #  args.fontsize integer fontsize if given, sets default size of block names
    #  args.format PDF if unspecified, PDF or PNG if specified

    # insert argv[0] into head of list of remaining args, and hand that to Qt
    unparsed_args.insert(0, sys.argv[0])

    # A QApplication instance is made, which is the window that holds everything
    app = QApplication(unparsed_args)

    # The resolution of the user's screen is extracted (used for determining
    # the size of the application window)
    screen_resolution = app.desktop().screenGeometry()

    # Set the desktop toolbar icon for this application
    icon = Path(__file__).parent.parent / "bdedit" / "Icons" / "bdsim_logo.png"
    app.setWindowIcon(QIcon(str(icon)))

    myappid = "bdsim.bdsim.bin.bdedit.application"  # arbitrary string for application
    try:
        if platform == "win32":
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        elif platform == "darwin":
            ctypes.cdll.kernel32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        # Toolbar icon for application could not be set.
        pass

    # Finally the window is displayed by creating an instance of Interface,
    # which holds all the logic for how the application should appear and which
    # connects all the other Classes through the Interface.
    # window = Interface(screen_resolution, args.debug)
    window = InterfaceWindow(screen_resolution, args.debug)
    window.args = args

    # Check what command line arguments have been passed, if any
    if args.file or args.print or args.debug or args.fontsize or args.format:

        # Call bdedit functionality based on passed args

        window.centralWidget().scene.block_name_fontsize = args.fontsize

        if args.file is not None:

            # Attempt to load the .bd file
            if os.path.isfile(args.file):
                window.loadFromFilePath(args.file)
            else:
                raise ValueError(f"bdfile {args.file} not found")

        # fire up the GUI
        window.centralWidget().scene.grScene.updateBackgroundMode(args.background, True)

        if args.print is not None:
            # render a screenshot to file
            def screenshot(model_path, screenshot_name):
                # Set the background mode to white, no grid lines
                window.centralWidget().scene.grScene.updateBackgroundMode(
                    "white", False
                )
                window.centralWidget().scene.grScene.checkMode()

                # Hide and then unselect all connector blocks present in the model
                window.centralWidget().scene.hide_connector_blocks = True

                for block in window.centralWidget().scene.blocks:
                    if block.block_type in ["Connector", "CONNECTOR"]:
                        block.grBlock.setSelected(False)

                # Update the points where wires overlap within the scene to draw the wire separations
                if window.centralWidget().scene.wires:
                    window.centralWidget().scene.wires[0].checkIntersections()

                window.centralWidget().save_image(
                    model_path, screenshot_name
                )  # in interface.py
                sys.exit(0)

            # figure out the filename to save it as
            file = Path(args.print)

            if args.print == "":
                # no filename given on command line
                # use the model file name, drop the path, and set extension pdf if none given

                # wait till python 3.9 for the next line to work
                # path = Path(args.file).with_stem(filename.stem + "-screenshot").with_suffix('.pdf').name

                if args.format == "png":
                    path = Path(args.file).with_suffix(".png")
                else:
                    path = Path(args.file).with_suffix(".pdf")

                path = path.stem + path.suffix

            else:
                # filename was given on command line
                path = Path(args.print)
                if path.suffix == "":
                    if args.format == "png":
                        path = path.with_suffix(".png")
                    else:
                        path = path.with_suffix(".pdf")

            # After 100ms non-blocking delay, screenshot the model
            QTimer.singleShot(100, lambda: screenshot(args.file, str(path)))

    # run the GUI until it exits
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
