#!/usr/bin/env python3

# Library imports
import os
import sys
import ctypes
import argparse
import threading
import traceback
from pathlib import Path

from sys import platform
from pathlib import Path

# PySide6 imports
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QEvent, Qt
from PySide6.QtGui import QIcon

# BdEdit imports
from bdedit.interface_manager import InterfaceWindow


class _BdeditApp(QApplication):
    """QApplication subclass that handles QFileOpenEvent (macOS open-with / drag-drop).

    On macOS, files received before the window is created are queued; once the
    window is registered via ``set_window()`` any queued file is loaded
    immediately, and subsequent events are forwarded directly.
    On other platforms ``QEvent.Type.FileOpen`` never fires, so this class is a
    transparent no-op.
    """

    def __init__(self, argv):
        super().__init__(argv)
        self._window = None
        self._pending: list[str] = []

    def set_window(self, window):
        self._window = window
        # Drain any events that arrived before the window was ready
        if self._pending:
            self._open_file(self._pending.pop(0))

    def event(self, e: QEvent) -> bool:
        # QEvent.Type.FileOpen is a macOS-only Apple Event; harmless on other
        # platforms as it simply never fires.
        if e.type() == QEvent.Type.FileOpen:
            if self._window is not None:
                self._open_file(e.file())
            else:
                self._pending.append(e.file())
            return True
        return super().event(e)

    def _open_file(self, path: str):
        if self._window is not None:
            self._window.loadFromFilePath(path)
            self._window.raise_()
            self._window.activateWindow()


# Executable code to launch the BdEdit application window
def main():
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

    # macOS native menu-bar ignores most Qt palette/stylesheet rules, which can
    # make text unreadable when the system auto-switches themes. Force a Qt
    # (in-window) menu-bar so bdedit's adaptive menu styling can be applied.
    if platform == "darwin" and os.getenv("BDEDIT_NATIVE_MENUBAR", "0") != "1":
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar, True)

    # A QApplication instance is made, which is the window that holds everything
    app = _BdeditApp(unparsed_args)
    app.setApplicationName("bdedit")
    app.setApplicationDisplayName("bdedit")
    app.setOrganizationName("bdsim")

    # The resolution of the user's screen is extracted (used for determining
    # the size of the application window)
    screen_resolution = app.primaryScreen().availableGeometry()

    # Set the desktop toolbar icon for this application
    icon = Path(__file__).parent.parent / "bdedit" / "Icons" / "bdsim_logo.png"
    app.setWindowIcon(QIcon(str(icon)))

    myappid = "bdsim.bdsim.bin.bdedit.application"  # arbitrary string for application
    try:
        if platform == "win32":
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        # Toolbar icon for application could not be set.
        pass

    # Finally the window is displayed by creating an instance of Interface,
    # which holds all the logic for how the application should appear and which
    # connects all the other Classes through the Interface.
    # window = Interface(screen_resolution, args.debug)
    window = InterfaceWindow(screen_resolution, args.debug)
    window.args = args

    def _handle_unhandled_exception(exc_type, exc_value, exc_tb):
        traceback.print_exception(exc_type, exc_value, exc_tb)
        saved_path = window.emergencySave("saved.bd")
        if saved_path is not None:
            print("Unhandled exception; attempted emergency save --> saved.bd")
        else:
            print("Unhandled exception; emergency save failed")

    sys.excepthook = _handle_unhandled_exception

    if hasattr(threading, "excepthook"):

        def _threading_excepthook(args):
            _handle_unhandled_exception(
                args.exc_type, args.exc_value, args.exc_traceback
            )

        threading.excepthook = _threading_excepthook

    # Apply non-file args synchronously
    window.centralWidget().scene.block_name_fontsize = args.fontsize
    window.centralWidget().scene.grScene.updateBackgroundMode(args.background, True)

    # Register window with app so QFileOpenEvents load files immediately
    app.set_window(window)

    # Load a CLI-supplied file (handles `bdedit file.bd` and `open -a App --args file.bd`)
    if args.file:
        if not os.path.isfile(args.file):
            raise ValueError(f"bdfile {args.file} not found")
        window.loadFromFilePath(args.file)
        window.raise_()
        window.activateWindow()

        if args.print is not None:

            def screenshot(model_path, screenshot_name):
                window.centralWidget().scene.grScene.updateBackgroundMode(
                    "white", False
                )
                window.centralWidget().scene.grScene.checkMode()
                window.centralWidget().scene.hide_connector_blocks = True
                for block in window.centralWidget().scene.blocks:
                    if block.block_type in ["Connector", "CONNECTOR"]:
                        block.grBlock.setSelected(False)
                if window.centralWidget().scene.wires:
                    window.centralWidget().scene.wires[0].checkIntersections()
                # Resolve to absolute path so save_image doesn't join it
                # against the model's directory
                out_abs = str(Path(screenshot_name).resolve())
                window.centralWidget().save_image(out_abs, picture_name="")
                sys.exit(0)

            if args.print == "":
                out = Path(args.file).with_suffix(
                    ".png" if args.format == "png" else ".pdf"
                )
                out = out.stem + out.suffix
            else:
                out = Path(args.print)
                if out.suffix == "":
                    out = out.with_suffix(".png" if args.format == "png" else ".pdf")

            QTimer.singleShot(100, lambda: screenshot(args.file, str(out)))

    # run the GUI until it exits
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
