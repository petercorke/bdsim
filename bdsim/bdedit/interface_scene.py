# Library imports
import json
import time
import getpass
from collections import OrderedDict

# PyQt5 imports
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QMessageBox, QWidget, QVBoxLayout

# BdEdit imports
from bdsim.bdedit.block import *
from bdsim.bdedit.Icons import *
from bdsim.bdedit.block_wire import Wire
from bdsim.bdedit.block_connector_block import Connector
from bdsim.bdedit.interface_serialize import Serializable
from bdsim.bdedit.interface_graphics_scene import GraphicsScene


# =============================================================================
#
#   Defining the Scene Class, which holds information of all the Blocks and
#   Wires that exist within it.
#
# =============================================================================
class Scene(Serializable):
    """
    The ``Scene`` Class extends the ``Serializable`` Class from BdEdit, and holds
    the information of all the ``Block`` and ``Wire`` instances that are within it.
    It also handles the storage of intersection points of the wires.

    This class includes information about the:

    - blocks, a list containing all ``Block`` instances
    - wires, a list containing all ``Wire`` instances
    - intersection points, a list containing all intersection points between Wires
    """

    # -----------------------------------------------------------------------------
    def __init__(self, resolution, window):
        """
        This method initializes an instance of the ``Scene`` Class.

        :param resolution: the desktop screen resolution of the user
        :type resolution: PyQt5.QtCore.QRect(0, 0, screen_width, screen_height), required
        :param window: the application's layer manager
        :type window: QGridLayout, required
        """
        super().__init__()
        # The application's layer manager is assigned to an internal variable
        self.window = window

        # Empty lists for the blocks, wires and intersection points are initialized
        self.blocks = []
        self.wires = []
        self.intersection_list = []

        # Variables to listen for modifications with in the scene
        self._has_been_modified = False
        self._has_been_modified_listeners = []

        # Variable for toggling between connector blocks being visible or not
        # False by default
        self.hide_connector_blocks = False

        # The scened dimensions are initially set to the width/height of the desktop
        # screen, but later adjusted with self.updateSceneDimensions()
        self.scene_width = resolution.width()
        self.scene_height = resolution.height()

        self.initUI()

    # Todo - add doc for this method
    # -----------------------------------------------------------------------------
    @property
    def has_been_modified(self):
        return self._has_been_modified


    # Todo - add doc for this method
    # -----------------------------------------------------------------------------
    @has_been_modified.setter
    def has_been_modified(self, value):
        if not self._has_been_modified and value:
            self._has_been_modified = value

            # call all registered listeners
            for callback in self._has_been_modified_listeners:
                callback()

        self._has_been_modified = value


    # Todo - add doc for this method
    # -----------------------------------------------------------------------------
    def addHasBeenModifiedListener(self, callback):
        self._has_been_modified_listeners.append(callback)


    # -----------------------------------------------------------------------------
    def initUI(self):
        """
        This method creates an ``GraphicsScene`` instance and associates it to this
        ``Scene`` instance. The GraphicsScene dictates how all items within the Scene
        are visually represented.
        """

        # A GraphicsScene is created and mapped to this Scene,
        # and the scene dimensions are updated
        self.grScene = GraphicsScene(self)
        self.updateSceneDimensions()

        # Create variables to record when and by who this diagram was created
        self.creation_time = int(time.time())
        self.created_by = getpass.getuser()

    # -----------------------------------------------------------------------------
    def addBlock(self, block):
        """
        This method adds a ``Block`` to the ``Scene's`` list of blocks.
        """
        self.blocks.append(block)

    # -----------------------------------------------------------------------------
    def addWire(self, wire):
        """
        This method adds a ``Wire`` to the ``Scene's`` list of wires.
        """
        self.wires.append(wire)

    # -----------------------------------------------------------------------------
    def removeBlock(self, block):
        """
        This method removes a ``Block`` to the ``Scene's`` list of blocks.
        """
        self.blocks.remove(block)

    # -----------------------------------------------------------------------------
    def removeWire(self, wire):
        """
        This method removes a ``Wire`` to the ``Scene's`` list of wires.
        """
        self.wires.remove(wire)

    # -----------------------------------------------------------------------------
    def getSceneWidth(self):
        """
        This method returns the current width of the ``Scene``.
        """
        return self.scene_width

    # -----------------------------------------------------------------------------
    def getSceneHeight(self):
        """
        This method returns the current height of the ``Scene``.
        """
        return self.scene_height

    # -----------------------------------------------------------------------------
    def setSceneWidth(self, width):
        """
        This method sets the current width of the ``Scene``, to the given width.
        """
        self.scene_width = width

    # -----------------------------------------------------------------------------
    def setSceneHeight(self, height):
        """
        This method sets the current height of the ``Scene``, to the given height.
        """
        self.scene_height = height

    # -----------------------------------------------------------------------------
    def updateSceneDimensions(self):
        """
        This method sets the dimensions of the ``Scene`` to the currently set
        scene_width and scene_height.
        """
        self.grScene.setGrScene(self.scene_width, self.scene_height)

    # -----------------------------------------------------------------------------
    def clear(self):
        """
        This method removes all blocks from the list of blocks within the ``Scene``.
        This will subsequently remove any and all wires between these blocks.
        """

        # Removes the first block from the self.blocks array, until the array is empty
        while len(self.blocks) > 0:
            self.blocks[0].remove()

        self.has_been_modified = False

    # -----------------------------------------------------------------------------
    def checkForDuplicates(self, name):
        """
        This method checks if the given name would be a duplicate of an existing
        block name.

        :param name: the desired name for a ``Block``
        :type name: str, required
        :return: - False (if given name is not a duplicate)
                 - True (if given name is a duplicate)
        :rtype: bool
        """

        # Duplicate found is initialized to False
        duplicate = False

        # For each block within the list of blocks
        for block in self.blocks:
            # If the given name matches the title of a block
            if name == block.title:
                # Change the duplicate found variable to True, and end the search
                duplicate = True
                break

        # Return the duplicate variable
        return duplicate

    # -----------------------------------------------------------------------------
    def displayMessage(self):
        """
        This method displays a 'File saved successfully!' pop-up message, providing
        the user with feedback that their was saved. This pop-up message will
        disappear on its own after 1 second.
        """

        # Method for closing the pop-up message
        def closeMessage():
            timer.stop()
            message.close()

        # Create a QMessageBox, in which the pop-up message is displayed
        message = QMessageBox()
        # Set the icon of the message to be a green tick
        message.setIconPixmap(QPixmap(":/Icons_Reference/Icons/Success_Icon.png"))
        # Set the title and text for the message
        message.setText("<font><b> File saved successfully! </font>")
        # Set message modality to be non-blocking (by default, QMessageBox blocks other actions until closed)
        message.setWindowModality(Qt.NonModal)
        # Add the pop-up message into the Scene
        self.window.addWidget(message, 2, 5, 1, 1)

        # Create timer to keep success message opened for 1 second
        timer = QtCore.QTimer()
        timer.setInterval(1000)
        timer.timeout.connect(closeMessage)
        timer.start()

    # -----------------------------------------------------------------------------
    def saveToFile(self, filename):
        """
        This method saves the contents of the ``Scene`` instance into a JSON file
        under the given filename.
        This method will call upon the self.serialize() method which will
        subsequently call the self.serialize() method within each item displayed
        in the ``Scene`` (these being the ``Block``, ``Wire`` and ``Socket``).

        :param filename: name of the file to save into
        :type filename: str, required
        """

        with open(filename, "w") as file:
            file.write(json.dumps(self.serialize(), indent=4))

            self.has_been_modified = False

        # Displays the successfully saved message once finished
        self.displayMessage()

    # -----------------------------------------------------------------------------
    def loadFromFile(self, filename):
        """
        This method loads the contents of a saved JSON file with the given filename
        into an instance of the ``Scene``.

        This method will call upon the self.deserialize() method which will
        subsequently call the self.deserialize() method within each item that should
        be reconstructed for the ``Scene`` (these being the ``Block``, ``Wire``
        and ``Socket``).

        :param filename:  name of the file to load from
        :type filename: str
        """

        with open(filename, "r") as file:
            raw_data = file.read()
            data = json.loads(raw_data)
            self.deserialize(data, self.window)

            self.has_been_modified = False

    # -----------------------------------------------------------------------------
    def serialize(self):
        """
        This method is called to create an ordered dictionary of all of this Scenes'
        parameters - necessary for the reconstruction of this Scene - as key-value
        pairs. This dictionary is later used for writing into a JSON file.

        :return: an ``OrderedDict`` of [keys, values] pairs of all essential ``Scene``
                 parameters.
        :rtype: ``OrderedDict`` ([keys, values]*)
        """

        # The blocks and wires associated with this scene, have their own parameters
        # that are required for their reconstruction, so the serialize method within the
        # Block and Wire classes are called to package this information respectively,
        # also into an OrderedDict. These ordered dictionaries are then stored in a temporary
        # blocks/wires variable and are returned as part of the OrderedDict of this Scene.
        blocks, wires = [], []
        for block in self.blocks: blocks.append(block.serialize())
        for wire in self.wires: wires.append(wire.serialize())
        return OrderedDict([
            ('id', self.id),
            ('created_by', self.created_by),
            ('creation_time', self.creation_time),
            ('scene_width', self.scene_width),
            ('scene_height', self.scene_height),
            ('blocks', blocks),
            ('wires', wires),
        ])

    # -----------------------------------------------------------------------------
    def deserialize(self, data, hashmap={}):
        """
        This method is called to reconstruct a ``Scene`` and all its items when
        loading a saved JSON.

        :param data: a Dictionary of essential information for reconstructing a ``Scene``
        :type data: OrderedDict, required
        :param hashmap: a Dictionary for directly mapping the essential scene variables
                        to this instance of ``Scene``, without having to individually map each variable
        :type hashmap: Dict, required
        :return: True when completed successfully
        :rtype: bool
        """

        # The current scene is cleared if anything inside it exists
        self.clear()

        # Extract data of who created this diagram and when
        try:
            self.creation_time = data["creation_time"]
            self.created_by = data["created_by"]
        # If that information isn't stored in the json file, set it to current user and time
        except:
            self.creation_time = int(time.time())
            self.created_by = getpass.getuser()

        hashmap = {}

        # All the blocks which were saved, are re-created from the JSON file
        # For each block from the saved blocks
        for block_data in data["blocks"]:
            block_type = block_data["block_type"]
            # If it is a Connector Block, then manually re-create this block (since the
            # Connector block is always available with this application, it was manually
            # imported in the Interface Class, hence must be manually re-created)
            if block_type == "CONNECTOR" or block_type == "Connector":
                Connector(self, self.window).deserialize(block_data, hashmap)
            # Otherwise if it is any other block (will be an auto-imported block)
            else:
                # For each block class within the blocklist
                for block_class in blocklist:
                    # Re-create an instance of a block class that matches a name of one of the blocks
                    # from the blocklist. There will always be a match, as the block_type is determined
                    # by the blockname(block_class) in the first place, and this will never change.
                    # The block_class.__name__ supports older files which would of used self.__class__.__name__
                    # to define the block type
                    if block_type == blockname(block_class) or block_type == block_class.__name__:
                        block_class().deserialize(block_data, hashmap)

                        break

        # Finally recreate all the wires that were saved
        for wire_data in data["wires"]:
            Wire(self).deserialize(wire_data, hashmap)

        return True
