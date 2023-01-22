# Library imports
import os
import json
import subprocess
import datetime
from sys import platform
from pathlib import Path

# PyQt5 imports
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

# BdEdit imports
from bdsim.bdedit.Icons import *
from bdsim.bdedit.interface import Interface


# Todo - update documentation for this new class, handles any edits/saves/undo/redo within interface.
#  Also handles the run related functionality now
# =============================================================================
#
#   Defining the Interface Manager Class,
#
# =============================================================================
class InterfaceWindow(QMainWindow):
    def __init__(self, resolution, debug=False):
        super().__init__()

        # The name of the current model is initially set to None, this is then
        # overwritten when the model is saved
        self.filename = None
        self.bgmode = 0  # default background/grid mode

        self.initUI(resolution, debug)

    def initUI(self, resolution, debug):
        # create node editor widget
        self.interface = Interface(resolution, debug, self)
        self.interface.scene.addHasBeenModifiedListener(self.updateApplicationName)
        self.setCentralWidget(self.interface)

        self.runButtonParameters = {
            "SimTime": 10.0,
            "Graphics": True,
            "Animation": True,
            "Verbose": False,
            "Progress": True,
            "Debug": "",
        }

        self.toolbar = QToolBar()
        self.fontSizeBox = QSpinBox()
        self.simTimeBox = QLineEdit()

        self.floatValidator = QDoubleValidator()

        # Create the toolbar action items and the toolbar itself
        self.createActions()
        self.createToolbar()

        # set window properties
        # self.setWindowIcon(QIcon(":/Icons_Reference/Icons/bdsim_icon.png"))
        self.updateApplicationName()
        self.show()

    def createActions(self):
        # Creates basic actions related to saving/loading files
        self.actNew = QAction(
            QIcon(":/Icons_Reference/Icons/new_file.png"),
            "&New",
            self,
            shortcut="Ctrl+N",
            toolTip="Create new model.",
            triggered=self.newFile,
        )
        self.actOpen = QAction(
            QIcon(":/Icons_Reference/Icons/open_folder.png"),
            "&Open",
            self,
            shortcut="Ctrl+O",
            toolTip="Open model.",
            triggered=self.loadFromFile,
        )
        self.actSave = QAction(
            QIcon(":/Icons_Reference/Icons/save.png"),
            "&Save",
            self,
            shortcut="Ctrl+S",
            toolTip="Save model.",
            triggered=self.saveToFile,
        )
        self.actSaveAs = QAction(
            QIcon(":/Icons_Reference/Icons/save_as.png"),
            "&Save As",
            self,
            shortcut="Ctrl+Shift+S",
            toolTip="Save model as.",
            triggered=self.saveAsToFile,
        )
        self.actExit = QAction(
            QIcon(":/Icons_Reference/Icons/quit.png"),
            "&Quit",
            self,
            shortcut="Ctrl+Q",
            toolTip="Quit bdedit.",
            triggered=self.close,
        )

        # Actions related to editing files (undo/redo)
        self.actUndo = QAction(
            QIcon(":/Icons_Reference/Icons/undo.png"),
            "&Undo",
            self,
            shortcut="Ctrl+Z",
            toolTip="Undo last action.",
            triggered=self.editUndo,
        )
        self.actRedo = QAction(
            QIcon(":/Icons_Reference/Icons/redo.png"),
            "&Redo",
            self,
            shortcut="Ctrl+Shift+Z",
            toolTip="Redo last action.",
            triggered=self.editRedo,
        )
        self.actDelete = QAction(
            QIcon(":/Icons_Reference/Icons/remove.png"),
            "&Delete",
            self,
            toolTip="Delete selected items.",
            triggered=self.editDelete,
        )
        self.actDelete.setShortcuts({QKeySequence("Delete"), QKeySequence("Backspace")})

        # Miscellaneous actions
        self.actFlipBlocks = QAction(
            "Flip Blocks",
            self,
            shortcut="F",
            toolTip="Flip selected blocks.",
            triggered=self.miscFlip,
        )
        self.actScreenshot = QAction(
            "Screenshot",
            self,
            shortcut="P",
            toolTip="Take and save a screenshot of your diagram.",
            triggered=lambda checked: self.miscScreenshot(None),
        )
        self.actWireOverlaps = QAction(
            "Toggle Wire Overlaps",
            self,
            shortcut="I",
            toolTip="Toggle markers where wires overlap.",
            triggered=self.miscEnableOverlaps,
            checkable=True,
        )
        self.actHideConnectors = QAction(
            "Toggle Connectors",
            self,
            shortcut="H",
            toolTip="Toggle visibilitiy of connector blocks (hidden/visible).",
            triggered=self.miscHideConnectors,
            checkable=True,
        )
        self.actDisableBackground = QAction(
            "Disable Background",
            self,
            shortcut="T",
            toolTip="Toggle background mode (grey with grid / white without grid).",
            triggered=self.miscToggleBackground,
            checkable=True,
        )

        # Actions related to model simulation
        self.actRunButton = QAction(
            QIcon(":/Icons_Reference/Icons/run.png"),
            "Run",
            self,
            shortcut="R",
            toolTip="<b>Run Button (R)</b><p>Simulate your block diagram model.</p>",
            triggered=self.runButton,
        )
        self.actAbortButton = QAction(
            QIcon(":/Icons_Reference/Icons/abort.png"),
            "Abort",
            self,
            shortcut="Q",
            toolTip="<b>Abort Button (Q)</b><p>Abort simulation of your block diagram model.</p>",
            triggered=self.abortButton,
        )
        self.actSimTime = self.simTimeBox.addAction(
            QIcon(":/Icons_Reference/Icons/simTime.png"),
            self.simTimeBox.LeadingPosition,
        )
        self.actSimTime.setToolTip(
            "<b>Simulation Time</b><p>Description to be added</p>"
        )
        self.simTimeBox.setText(str(self.runButtonParameters["SimTime"]))
        self.simTimeBox.setMinimumWidth(55)
        self.simTimeBox.setMaximumWidth(75)
        self.simTimeBox.setValidator(self.floatValidator)
        self.simTimeBox.editingFinished.connect(self.updateSimTime)

        # Actions related to formatting floating text labels
        self.actAlignLeft = QAction(
            QIcon(":/Icons_Reference/Icons/left_align.png"),
            "Left",
            self,
            shortcut="Ctrl+Shift+L",
            toolTip="<b>Left Align (Ctrl+Shift+L)</b><p>Left align your selected floating text.</p>",
            triggered=lambda: self.textAlignment("AlignLeft"),
            checkable=True,
        )
        self.actAlignCenter = QAction(
            QIcon(":/Icons_Reference/Icons/center_align.png"),
            "Center",
            self,
            shortcut="Ctrl+Shift+C",
            toolTip="<b>Center (Ctrl+Shift+C)</b><p>Center your selected floating text.</p>",
            triggered=lambda: self.textAlignment("AlignCenter"),
            checkable=True,
        )
        self.actAlignRight = QAction(
            QIcon(":/Icons_Reference/Icons/right_align.png"),
            "Right",
            self,
            shortcut="Ctrl+Shift+R",
            toolTip="<b>Right Align (Ctrl+Shift+R)</b><p>Right align your selected floating text.</p>",
            triggered=lambda: self.textAlignment("AlignRight"),
            checkable=True,
        )

        self.actBoldText = QAction(
            QIcon(":/Icons_Reference/Icons/bold.png"),
            "&Bold",
            self,
            shortcut="Ctrl+B",
            toolTip="<b>Bold (Ctrl+B)</b><p>Toggle bold on selected floating text.</p>",
            triggered=self.textBold,
            checkable=True,
        )
        self.actUnderLineText = QAction(
            QIcon(":/Icons_Reference/Icons/underline.png"),
            "&Underline",
            self,
            shortcut="Ctrl+U",
            toolTip="<b>Underline (Ctrl+U)</b><p>Toggle underline on selected floating text.</p>",
            triggered=self.textUnderline,
            checkable=True,
        )
        self.actItalicText = QAction(
            QIcon(":/Icons_Reference/Icons/italic.png"),
            "&Italicize",
            self,
            shortcut="Ctrl+I",
            toolTip="<b>Italic (Ctrl+I)</b><p>Toggle italics on selected floating text.</p>",
            triggered=self.textItalicize,
            checkable=True,
        )

        self.actFontType = QAction(
            "Font",
            self,
            shortcut="Ctrl+Shift+F",
            toolTip="<b>Font (Ctrl+Shift+F)</b><p>Choose a font style for floating text.</p>",
            triggered=self.textFontStyle,
        )
        self.fontSizeBox.setValue(14)
        self.fontSizeBox.valueChanged.connect(self.textFontSize)
        self.actTextColor = QAction(
            QIcon(":/Icons_Reference/Icons/color_picker.png"),
            "Text Color",
            self,
            toolTip="<b>Font Color</b><p>Change the color of your text.</p>",
            triggered=self.textColor,
        )
        self.actRemoveFormat = QAction(
            QIcon(":/Icons_Reference/Icons/clear_format.png"),
            "Clear Format",
            self,
            toolTip="<b>Clear Text Formatting</b><p>Removes all formatting from selected floating text.</p>",
            triggered=self.removeFormat,
        )

        self.actRunBtnOp1 = QAction(
            "Graphics",
            self,
            toolTip="<b>Toggle Graphics</b><p>Description to be added</p>",
            triggered=lambda checked: self.setRunBtnOptions("Graphics"),
            checkable=True,
        )
        self.actRunBtnOp2 = QAction(
            "Animation",
            self,
            toolTip="<b>Toggle Animation</b><p>Description to be added</p>",
            triggered=lambda checked: self.setRunBtnOptions("Animation"),
            checkable=True,
        )
        self.actRunBtnOp3 = QAction(
            "Verbose",
            self,
            toolTip="<b>Toggle Verbose</b><p>Description to be added</p>",
            triggered=lambda checked: self.setRunBtnOptions("Verbose"),
            checkable=True,
        )
        self.actRunBtnOp4 = QAction(
            "Progress",
            self,
            toolTip="<b>Toggle Progress</b><p>Description to be added</p>",
            triggered=lambda checked: self.setRunBtnOptions("Progress"),
            checkable=True,
        )
        self.actRunBtnOp5 = QAction(
            "Debug",
            self,
            toolTip="<b>Debug String</b><p>Description to be added</p>",
            triggered=lambda checked: self.setRunBtnOptions("Debug"),
        )
        self.actRunBtnOp6 = QAction(
            "Simulation Time",
            self,
            toolTip="<b>Simulation Time</b><p>Description to be added</p>",
            triggered=lambda checked: self.setRunBtnOptions("SimTime"),
        )

        self.helpButton = QAction(
            QIcon(":/Icons_Reference/Icons/help.png"),
            "Help",
            self,
            toolTip="<b>Help</b><p>Open BdEdit documentation.</p>",
            triggered=self.displayHelpURL,
        )

    def createToolbar(self):
        self.createFileMenu()
        self.createEditMenu()
        self.createToolsMenu()
        self.createRunButtonParameters()
        self.createToolbarItems()
        self.createHelpItem()

    def createFileMenu(self):
        # self._file_menubar = QMenuBar() if platform == 'darwin' else self.menuBar()
        # self.fileMenu = QMenu('File')
        # self.fileMenu.setToolTipsVisible(True)
        # self.fileMenu.addAction(self.actNew)
        # self.fileMenu.addSeparator()
        # self.fileMenu.addAction(self.actOpen)
        # self.fileMenu.addAction(self.actSave)
        # self.fileMenu.addAction(self.actSaveAs)
        # self.fileMenu.addSeparator()
        # self.fileMenu.addAction(self.actExit)
        # self._file_menubar.addMenu(self.fileMenu)
        # # self._file_menubar.setNativeMenuBar(False)

        menubar = self.menuBar()
        self.fileMenu = menubar.addMenu("File")
        self.fileMenu.setToolTipsVisible(True)
        self.fileMenu.addAction(self.actNew)
        self.fileMenu.addAction(self.actOpen)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.actSave)
        self.fileMenu.addAction(self.actSaveAs)

        exportMenu = QMenu("Export As", self)
        exportMenu.setIcon(QIcon(":/Icons_Reference/Icons/export_as.png"))
        exportPDF = QAction(
            "PDF",
            self,
            toolTip="Export model as a pdf.",
            triggered=lambda checked: self.exportAsToFile("pdf"),
        )
        exportPNG = QAction(
            "PNG",
            self,
            toolTip="Export model as a png.",
            triggered=lambda checked: self.exportAsToFile("png"),
        )
        exportMenu.addAction(exportPDF)
        exportMenu.addAction(exportPNG)
        self.fileMenu.addMenu(exportMenu)

        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.actExit)

    def createEditMenu(self):
        # self._edit_menubar.setNativeMenuBar(False)
        #     self._edit_menubar = QMenuBar() if platform == 'darwin' else self.menuBar()
        #     self.editMenu = QMenu('Edit')
        #     self.editMenu.setToolTipsVisible(True)
        #     self.editMenu.addAction(self.actUndo)
        #     self.editMenu.addAction(self.actRedo)
        #     self.editMenu.addSeparator()
        #     self.editMenu.addAction(self.actDelete)
        #     self._edit_menubar.addMenu(self.editMenu)
        #     # self._edit_menubar.setNativeMenuBar(False)
        menubar = self.menuBar()
        self.editMenu = menubar.addMenu("Edit")
        self.editMenu.setToolTipsVisible(True)
        self.editMenu.addAction(self.actUndo)
        self.editMenu.addAction(self.actRedo)
        self.editMenu.addSeparator()
        self.editMenu.addAction(self.actDelete)

    def createToolsMenu(self):
        # self._tools_menubar = QMenuBar() if platform == 'darwin' else self.menuBar()
        # self.toolsMenu = QMenu('Tools')
        # self.toolsMenu.setToolTipsVisible(True)
        # self.toolsMenu.addAction(self.actFlipBlocks)
        # self.toolsMenu.addAction(self.actScreenshot)
        # self.toolsMenu.addSeparator()
        # self.toolsMenu.addAction(self.actWireOverlaps)
        # self.toolsMenu.addAction(self.actHideConnectors)
        # self.toolsMenu.addAction(self.actDisableBackground)
        # self.toolsMenu.addSeparator()
        # self.toolsMenu.addAction(self.actDelete)
        # self._tools_menubar.addMenu(self.toolsMenu)
        # # self._tools_menubar.setNativeMenuBar(False)
        menubar = self.menuBar()
        self.toolsMenu = menubar.addMenu("Tools")
        self.toolsMenu.setToolTipsVisible(True)
        self.toolsMenu.addAction(self.actFlipBlocks)
        self.toolsMenu.addAction(self.actScreenshot)
        self.toolsMenu.addSeparator()
        self.toolsMenu.addAction(self.actWireOverlaps)
        self.toolsMenu.addAction(self.actHideConnectors)
        self.toolsMenu.addAction(self.actDisableBackground)
        # self.toolsMenu.addSeparator()
        # self.toolsMenu.addAction(self.actDelete)

    def createRunButtonParameters(self):
        # self._params_menubar = QMenuBar() if platform == 'darwin' else self.menuBar()
        # self.runMenu = QMenu('Simulation')
        # self.runMenu.setToolTipsVisible(True)
        # self.runMenu.addAction(self.actRunBtnOp6)
        # self.runMenu.addSeparator()
        # self.runMenu.addAction(self.actRunBtnOp1)
        # self.runMenu.addAction(self.actRunBtnOp2)
        # self.runMenu.addAction(self.actRunBtnOp3)
        # self.runMenu.addAction(self.actRunBtnOp4)
        # self.runMenu.addSeparator()
        # self.runMenu.addAction(self.actRunBtnOp5)
        # self._params_menubar.addMenu(self.runMenu)
        menubar = self.menuBar()
        self.runMenu = menubar.addMenu("Simulation")
        self.runMenu.setToolTipsVisible(True)
        self.runMenu.addAction(self.actRunBtnOp6)
        self.runMenu.addSeparator()
        self.runMenu.addAction(self.actRunBtnOp1)
        self.runMenu.addAction(self.actRunBtnOp2)
        self.runMenu.addAction(self.actRunBtnOp3)
        self.runMenu.addAction(self.actRunBtnOp4)
        self.runMenu.addSeparator()
        self.runMenu.addAction(self.actRunBtnOp5)

    def createHelpItem(self):
        # self._help_menubar = QMenuBar() if platform == 'darwin' else self.menuBar()
        # self.helpBar = QMenu('Help')
        # self.helpBar.setToolTipsVisible(True)
        # self.helpBar.addAction(self.helpButton)
        # self._help_menubar.addMenu(self.helpBar)
        # # self._help_menubar.setNativeMenuBar(False)
        menubar = self.menuBar()
        self.helpBar = menubar.addMenu("Help")
        self.helpBar.setToolTipsVisible(True)
        self.helpBar.addAction(self.helpButton)

    def createToolbarItems(self):
        self.toolbar = self.addToolBar("ToolbarItems")
        self.toolbar.addAction(self.actRunButton)
        self.toolbar.addAction(self.actAbortButton)
        self.toolbar.addWidget(self.simTimeBox)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.actAlignLeft)
        self.toolbar.addAction(self.actAlignCenter)
        self.toolbar.addAction(self.actAlignRight)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.actBoldText)
        self.toolbar.addAction(self.actUnderLineText)
        self.toolbar.addAction(self.actItalicText)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.actFontType)
        self.toolbar.addWidget(self.fontSizeBox)
        self.toolbar.addAction(self.actTextColor)
        self.toolbar.addAction(self.actRemoveFormat)
        self.toolbar.addSeparator()

    # -----------------------------------------------------------------------------

    def updateApplicationName(self):
        name = "bdedit - "
        if self.filename is None:
            name += "untitled.bd"
        else:
            name += os.path.basename(self.filename)

        if self.centralWidget().scene.has_been_modified:
            name += "*"

        self.setWindowTitle(name)

    def closeEvent(self, event):
        if self.exitingWithoutSave():
            event.accept()
        else:
            event.ignore()

    def isModified(self):
        return self.centralWidget().scene.has_been_modified

    def exitingWithoutSave(self):
        if not self.isModified():
            return True

        msg_prompt = QMessageBox.warning(
            self,
            "Exiting without saving work.",
            "The document has been modified.\nDo you want to save your changes?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
        )

        if msg_prompt == QMessageBox.Save:
            return self.saveToFile()
        elif msg_prompt == QMessageBox.Cancel:
            return False

        return True

    # -----------------------------------------------------------------------------
    def setRunBtnOptions(self, value):
        if value not in ["Debug", "SimTime"]:
            self.runButtonParameters[value] = not (self.runButtonParameters[value])

        elif value == "Debug":
            arbitrary_string, done = QInputDialog.getText(
                self, "Input Dialog", "Enter a debug string:"
            )
            if done:
                self.runButtonParameters[value] = arbitrary_string

        elif value == "SimTime":
            sim_time, done = QInputDialog.getText(
                self,
                "Input Dialog",
                "Enter simulation time (sec):",
                QLineEdit.Normal,
                str(self.runButtonParameters[value]),
            )
            if done:
                try:
                    # If simulation time is positive integer, update value
                    if float(sim_time) > 0:
                        self.runButtonParameters[value] = float(sim_time)
                        self.simTimeBox.setText(str(self.runButtonParameters[value]))
                        self.interface.scene.sim_time = float(sim_time)

                    # Else return feedback
                    else:
                        print(
                            "Incompatible simulation time given. Expected a positive non-zero float or integer."
                        )
                        self.setRunBtnOptions(value)

                # If value is not an integer, return feedback
                except ValueError as e:
                    print(
                        "Incompatible simulation time given. Expected a positive non-zero float or integer."
                    )
                    self.setRunBtnOptions(value)

            else:
                # Leave simulation time value unchanged.
                pass

        print(self.runButtonParameters)

    def displayHelpURL(self):
        QDesktopServices.openUrl(
            QtCore.QUrl(
                "https://github.com/petercorke/bdsim/blob/master/bdsim/bdedit/README.md"
            )
        )

    # -----------------------------------------------------------------------------
    def runButton(self):
        self.saveToFile()

        main_block_found = False

        # Go through blocks within scene, if a main block exists, extract the file_name from the main block
        for block in self.centralWidget().scene.blocks:
            if block.block_type in ["Main", "MAIN"]:
                main_block_found = True
                main_file_name = block.parameters[0][2]
                break

        # Convert the GUI simulation options to command line args
        args = []
        for key, value in self.runButtonParameters.items():
            arg = key.lower()
            if isinstance(value, bool):
                if not arg:
                    arg = "no-" + arg
                args.append("--" + arg)
            else:
                if isinstance(value, str):
                    if len(value) > 0:
                        value = '"' + value + '"'
                args.append(f"--{arg}={value}")
        print(args)
        print(self.args)

        if main_block_found:

            # Check if given file_name from the main block, contains a file extension

            bdfile = Path(self.filename)
            mainfile = Path(main_file_name)
            if not mainfile.is_absolute():
                mainfile = bdfile.resolve().with_name(mainfile.name)
            mainfile = mainfile.with_suffix(".py")

            # file_name, extension = os.path.splitext(main_file_name)
            # if not extension:
            #     main_file_name = os.path.join(main_file_name + ".py")
            model_name = os.path.basename(self.filename)
            if not mainfile.is_file():
                print(f"Main block detected: file {main_file_name} could not be opened")
                return

            command = ["python"]
            if self.args.pdb:
                command.extend(["-m", "pdb"])
            command.extend([str(mainfile), str(bdfile)])
            command.extend(args)

        else:
            model_name = os.path.basename(self.filename)

            command = ["bdrun", model_name]
            command.extend(args)

        print("\n" + "#" * 100)
        print(f"{datetime.datetime.now()}:: {' '.join(command)}")

        try:
            subprocess.Popen(command, shell=False)

        except (ValueError, OSError):
            print(f"failed to spawn subprocess")

    # -----------------------------------------------------------------------------
    def abortButton(self):
        # Added function for handling what the abort button does when pressed.
        print(
            "Abort button pressed. Functionality yet to be implemented. Function in 'interface_manager' under 'runButton' function"
        )
        pass

    # -----------------------------------------------------------------------------
    def updateSimTime(self):
        # This function is called when the Simulation Time value has been changed in the toolbar text widget.
        sim_time = self.simTimeBox.text()

        try:
            # If simulation time is positive integer, update value
            if float(sim_time) > 0:
                self.runButtonParameters["SimTime"] = float(sim_time)
                self.simTimeBox.setText(str(self.runButtonParameters["SimTime"]))
                self.interface.scene.sim_time = float(sim_time)

            # Else return feedback
            else:
                print(
                    "Incompatible simulation time given. Expected a positive non-zero float or integer."
                )

        # If value is not an integer, return feedback
        except ValueError as e:
            print(
                "Incompatible simulation time given. Expected a positive non-zero float or integer."
            )

        print(self.runButtonParameters)

    # -----------------------------------------------------------------------------
    def newFile(self):
        if self.exitingWithoutSave():
            # Clear scene and all its elements. Reset simulation time parameters
            self.centralWidget().scene.clear()
            self.runButtonParameters = {
                "SimTime": 10.0,
                "Graphics": True,
                "Animation": True,
                "Verbose": False,
                "Progress": True,
                "Debug": "",
            }
            self.simTimeBox.setText(str(self.runButtonParameters["SimTime"]))
            self.interface.scene.sim_time = self.runButtonParameters["SimTime"]

            # Reset filename and update GUI to display default file name
            self.filename = None
            self.updateApplicationName()

            # Reset history stack
            self.centralWidget().scene.history.clear()
            self.centralWidget().scene.history.storeInitialHistoryStamp()

    # -----------------------------------------------------------------------------
    def loadFromFilePath(self, filepath):
        """
        This method is only used when loading a file from the command line. It will
        check if the file at the given path exists, and if so, will load its contents.
        """

        if self.exitingWithoutSave():
            # Check if file at given path exists, if so, run the deserializing method
            if os.path.isfile(filepath):
                self.centralWidget().scene.loadFromFile(filepath)
                self.filename = filepath
                self.updateApplicationName()
                self.centralWidget().scene.history.clear()
                self.centralWidget().scene.history.storeInitialHistoryStamp()

    # -----------------------------------------------------------------------------
    def loadFromFile(self):
        """
        This method opens a QFileDialog window, prompting the user to select a file
        to load from.
        """

        if self.exitingWithoutSave():
            # The filename of the selected file is grabbed
            fname, filter = QFileDialog.getOpenFileName(self)
            if fname == "":
                return

            # And the method for deserializing from a file is called, feeding in the
            # extracted filename from above
            if os.path.isfile(fname):
                self.centralWidget().scene.loadFromFile(fname)
                self.filename = fname
                self.updateApplicationName()
                # Update SimTime in runButtonParameters in case it was set in model
                self.runButtonParameters["SimTime"] = self.interface.scene.sim_time
                self.simTimeBox.setText(str(self.runButtonParameters["SimTime"]))

    # -----------------------------------------------------------------------------
    def saveToFile(self):
        """
        This method calls the method from within the ``Scene`` to save a copy of the
        current Scene, with all its items under a file with the current filename. If
        this is the first time a user is saving their file, they will be prompted to
        name the file and to choose where it will be saved.
        """

        if self.filename is None:
            return self.saveAsToFile()
        self.centralWidget().scene.saveToFile(self.filename)
        self.updateApplicationName()
        return True

    # -----------------------------------------------------------------------------
    def saveAsToFile(self):
        """
        This method opens a QFileDialog window, prompting the user to enter a name
        under which the current file will be saved. This file will automatically be
        given a .json file type.
        """

        # The allowable file types are defined below
        file_types = "bdedit files(*.bd);;JSON files (*.json)"
        fname, _ = QFileDialog.getSaveFileName(self, "untitled.bd", filter=file_types)

        # The filename is extracted from the QFileDialog
        if fname == "":
            return False

        # The filename of the scene is stored as a variable inside the Interface, and
        # the self.saveToFile method is called (which will call the self.scene.saveToFile
        # method from within the Scene, which will serialize the contents of the Scene
        # into a JSON file with the provided file name).
        self.filename = fname
        self.saveToFile()
        return True

    # -----------------------------------------------------------------------------
    def exportAsToFile(self, fileType):
        self.miscScreenshot(fileType)

    # -----------------------------------------------------------------------------
    def editUndo(self):
        self.interface.scene.history.undo()

    def editRedo(self):
        self.interface.scene.history.redo()

    def editDelete(self):
        if self.interface:
            self.interface.canvasView.deleteSelected()
            self.interface.canvasView.intersectionTest()

    # -----------------------------------------------------------------------------
    def miscFlip(self):
        if self.interface:
            self.interface.canvasView.intersectionTest()
            self.interface.canvasView.flipBlockSockets()

    def miscEnableOverlaps(self):
        if self.interface:
            self.interface.scene.grScene.enable_intersections = (
                not self.interface.scene.grScene.enable_intersections
            )

    def miscScreenshot(self, fileType):
        if self.interface:
            if self.filename is None:
                print(
                    "Please save your model before taking a screenshot, then try again."
                )
                self.saveToFile()
            else:
                self.interface.save_image(
                    self.filename, picture_name=None, picture_format=fileType
                )

    def miscHideConnectors(self):
        if self.interface:
            if self.actHideConnectors.isChecked():
                # Set variable for hiding connector blocks to True
                self.interface.scene.hide_connector_blocks = True
            else:
                # Set variable for hiding connector blocks to False
                self.interface.scene.hide_connector_blocks = False

    def miscToggleBackground(self):
        """
        This method is called to cycle through various background and grid
        options.
        """
        # possible modes
        modes = [("grey", True), ("white", True), ("white", False)]

        self.bgmode = (self.bgmode + 1) % len(modes)  # update current mode
        mode = modes[self.bgmode]
        self.interface.scene.grScene.updateBackgroundMode(*mode)
        # # For each block within the Scene, the mode of their outline is also updated
        # for eachBlock in self.interface.scene.blocks:
        #     # If the block has a mode (Connector Blocks do not)
        #     if not (eachBlock.block_type == "CONNECTOR" or eachBlock.block_type == "Connector"):
        #         # eachBlock.grBlock.updateBackgroundMode(self.actDisableBackground.isChecked())
        #         eachBlock.grBlock.updateBackgroundMode(mode[0], mode[1])

    # -----------------------------------------------------------------------------
    def textAlignment(self, alignment):
        if self.interface.scene.floating_labels:
            # Make a map of alignment text to actual Qt alignments
            map = {
                "AlignLeft": Qt.AlignLeft,
                "AlignCenter": Qt.AlignCenter,
                "AlignRight": Qt.AlignRight,
            }

            # Iterate through each floating label item and if the label is selected,
            # then set the alignment of its contents
            for label in self.interface.scene.floating_labels:
                if self.checkSelection(label):
                    label.content.text_edit.setAlignment(map[alignment])
                    self.interface.scene.has_been_modified = True
                    self.interface.scene.history.storeHistory(
                        "Floating label changed alignment"
                    )

            self.updateToolbarValues()

    def textBold(self):
        if self.interface.scene.floating_labels:
            for label in self.interface.scene.floating_labels:
                if self.checkSelection(label):
                    if self.actBoldText.isChecked():
                        label.content.text_edit.setFontWeight(QFont.Bold)
                    else:
                        label.content.text_edit.setFontWeight(QFont.Normal)

                    label.content.updateShape()

                    self.interface.scene.has_been_modified = True
                    self.interface.scene.history.storeHistory(
                        "Floating label changed boldness"
                    )

    def textUnderline(self):
        if self.interface.scene.floating_labels:
            for label in self.interface.scene.floating_labels:
                if self.checkSelection(label):
                    if self.actUnderLineText.isChecked():
                        label.content.text_edit.setFontUnderline(True)
                    else:
                        label.content.text_edit.setFontUnderline(False)

                    label.content.updateShape()

                    self.interface.scene.has_been_modified = True
                    self.interface.scene.history.storeHistory(
                        "Floating label changed underline"
                    )

    def textItalicize(self):
        if self.interface.scene.floating_labels:
            for label in self.interface.scene.floating_labels:
                if self.checkSelection(label):
                    if self.actItalicText.isChecked():
                        label.content.text_edit.setFontItalic(True)
                    else:
                        label.content.text_edit.setFontItalic(False)

                    label.content.updateShape()

                    self.interface.scene.has_been_modified = True
                    self.interface.scene.history.storeHistory(
                        "Floating label changed italics"
                    )

    def textFontStyle(self):
        (font, ok) = QFontDialog.getFont()
        # print("ok, font name, font size:", [ok, font.family(), font.styleName(), font.pointSize()])
        if ok:
            if self.interface.scene.floating_labels:
                for label in self.interface.scene.floating_labels:
                    if self.checkSelection(label):
                        label.content.text_edit.setFont(font)
                        label.content.text_edit.setFontWeight(font.weight())
                        label.content.currentFontSize = font.pointSize()
                        label.content.updateText()
                        label.grContent.setLabelSizeBox()
                        label.content.updateShape()

                        self.interface.scene.has_been_modified = True
                        self.interface.scene.history.storeHistory(
                            "Floating label changed font style"
                        )

    def textFontSize(self):
        if self.interface.scene.floating_labels:
            for label in self.interface.scene.floating_labels:
                if self.checkSelection(label):
                    value = self.fontSizeBox.value()
                    label.content.text_edit.setFontPointSize(value)
                    label.content.currentFontSize = value
                    label.content.updateShape()

                    self.interface.scene.has_been_modified = True
                    self.interface.scene.history.storeHistory(
                        "Floating label changed font size"
                    )

    def textColor(self):
        color = QColorDialog.getColor(options=QColorDialog.ShowAlphaChannel)

        if color.isValid():
            if self.interface.scene.floating_labels:
                for label in self.interface.scene.floating_labels:
                    if self.checkSelection(label):
                        label.content.text_edit.setTextColor(color)

                        self.interface.scene.has_been_modified = True
                        self.interface.scene.history.storeHistory(
                            "Floating label changed font color"
                        )

        # self.updateToolbarValues()     # Enable this if you ever make the font color icon update

    # Clears all format on selected floating labels, reverting to default format
    def removeFormat(self):
        if self.interface.scene.floating_labels:
            for label in self.interface.scene.floating_labels:
                if self.checkSelection(label):
                    label.content.setDefaultFormatting()
                    label.content.updateText()

                    self.interface.scene.has_been_modified = True
                    self.interface.scene.history.storeHistory(
                        "Floating label cleared formatting"
                    )
        self.updateToolbarValues()

    # This function checks if the current label is selected
    def checkSelection(self, label):
        if label.grContent.isSelected():
            label.content.text_edit.selectAll()
            return True
        return False

    # This function contains the logic for when to select/unselect toolbar items
    def updateToolbarValues(self):
        selected_labels = []
        any_bold = False
        any_italics = False
        any_underlined = False

        if self.interface.scene.floating_labels:
            for label in self.interface.scene.floating_labels:
                if self.checkSelection(label):
                    selected_labels.append(label)
                    # If any label is bold, or italicized, or underlined,
                    # when mutliple labels are selected the respective icon will be selected
                    if label.content.text_edit.fontWeight() > 50:
                        any_bold = True
                    if label.content.text_edit.fontItalic():
                        any_italics = True
                    if label.content.text_edit.fontUnderline():
                        any_underlined = True

        if len(selected_labels) == 0:
            # If no labels are selected, unselects all toolbar items (alignment, bold, italics, underline)
            self.fontSizeBox.setValue(14)
            self.actBoldText.setChecked(False)
            self.actItalicText.setChecked(False)
            self.actUnderLineText.setChecked(False)
            self.unselectAlignmentIcons()

        elif len(selected_labels) == 1:
            # If only one label is selected, sets the correct values of all toolbar items based on the
            # label's value (alignment, bold, italics, underline)
            our_label = selected_labels[0].content
            self.fontSizeBox.setValue(our_label.currentFontSize)
            self.actBoldText.setChecked(our_label.text_edit.fontWeight() > 50)
            self.actItalicText.setChecked(our_label.text_edit.fontItalic())
            self.actUnderLineText.setChecked(our_label.text_edit.fontUnderline())
            self.actAlignLeft.setChecked(
                our_label.text_edit.alignment() == Qt.AlignLeft
            )
            self.actAlignCenter.setChecked(
                our_label.text_edit.alignment() == Qt.AlignCenter
            )
            self.actAlignRight.setChecked(
                our_label.text_edit.alignment() == Qt.AlignRight
            )

        else:
            # If multiple labels are selected, font size box and alignment options are cleared
            # but bold, italics, underline are selected/unselected depending on if any of the selected
            # labels are bold, italicizied or underlined.
            self.fontSizeBox.clear()
            self.actBoldText.setChecked(any_bold)
            self.actItalicText.setChecked(any_italics)
            self.actUnderLineText.setChecked(any_underlined)
            self.unselectAlignmentIcons()

    def unselectAlignmentIcons(self):
        self.actAlignLeft.setChecked(False)
        self.actAlignCenter.setChecked(False)
        self.actAlignRight.setChecked(False)
