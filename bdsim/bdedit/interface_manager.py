# Library imports
import os
import json
import subprocess

# PyQt5 imports
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from bdsim.bdedit.Icons import *

# BdEdit imports
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

        self.initUI(resolution, debug)

    def initUI(self, resolution, debug):
        # create node editor widget
        self.interface = Interface(resolution, debug, self)
        self.interface.scene.addHasBeenModifiedListener(self.updateApplicationName)
        self.setCentralWidget(self.interface)

        # self.interface.canvasView.scenePosChanged.connect(self.onScenePosChanged)

        # set window properties
        self.setWindowIcon(QIcon(":/Icons_Reference/Icons/bdsim_icon.png"))
        self.updateApplicationName()
        self.show()

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

        msg_prompt = QMessageBox.warning(self, "Exiting without saving work.",
                "The document has been modified.\nDo you want to save your changes?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
              )

        if msg_prompt == QMessageBox.Save:
            return self.saveToFile()
        elif msg_prompt == QMessageBox.Cancel:
            return False

        return True

    # -----------------------------------------------------------------------------
    def runButton(self):
        self.saveToFile()

        main_block_found = False

        # Go through blocks within scene, if a main block exists, extract the file_name from the main block
        for block in self.centralWidget().scene.blocks:
            if block.block_type in ["Main", "MAIN"]:
                main_block_found = True
                main_file_name = block.parameters[0][2]

                try:
                    # Check if given file_name from the main block, contains a file extension
                    file_name, extension = os.path.splitext(main_file_name)

                    if not extension:
                        main_file_name = os.path.join(main_file_name + ".py")

                    model_name = os.path.basename(self.filename)
                    print("Invoking subproces with, Python file as:", main_file_name, " | Model name as:", model_name)
                    subprocess.run(['python', main_file_name, model_name], shell=True)

                except Exception:
                    print("Detected Main block in model, but no file name was given. Subprocess cancled.")
                    return

        if not main_block_found:
            print("Model does not contain a main block. Starting bdrun as a subprocess.")
            model_name = os.path.basename(self.filename)
            subprocess.run(['python', 'bdrun.py', model_name], shell=True)

    # -----------------------------------------------------------------------------
    def newFile(self):
        if self.exitingWithoutSave():
            self.centralWidget().scene.clear()
            self.filename = None
            self.updateApplicationName()

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

    # -----------------------------------------------------------------------------
    def loadFromFile(self):
        """
        This method opens a QFileDialog window, prompting the user to select a file
        to load from.
        """

        if self.exitingWithoutSave():
            # The filename of the selected file is grabbed
            fname, filter = QFileDialog.getOpenFileName(self)
            if fname == '':
                return

            # And the method for deserializing from a file is called, feeding in the
            # extracted filename from above
            if os.path.isfile(fname):
                self.centralWidget().scene.loadFromFile(fname)
                self.filename = fname
                self.updateApplicationName()

    # -----------------------------------------------------------------------------
    def saveToFile(self):
        """
        This method calls the method from within the ``Scene`` to save a copy of the
        current Scene, with all its items under a file with the current filename. If
        this is the first time a user is saving their file, they will be prompted to
        name the file and to choose where it will be saved.
        """

        if self.filename is None: return self.saveAsToFile()
        self.centralWidget().scene.saveToFile(self.filename)
        self.updateApplicationName()
        #self.statusBar().showMessage("Successfully saved %s" % self.filename)
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
        fname, _ = QFileDialog.getSaveFileName(self, 'untitled.bd', filter=file_types)

        # The filename is extracted from the QFileDialog
        if fname == '':
            return False

        # The filename of the scene is stored as a variable inside the Interface, and
        # the self.saveToFile method is called (which will call the self.scene.saveToFile
        # method from within the Scene, which will serialize the contents of the Scene
        # into a JSON file with the provided file name).
        self.filename = fname
        self.saveToFile()
        return True
