# Library imports
import json
import time
import getpass
from PIL import ImageFont
from collections import OrderedDict

# PyQt5 imports
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QMessageBox, QWidget, QVBoxLayout

# BdEdit imports
from bdsim.bdedit.block import *
from bdsim.bdedit.Icons import *
from bdsim.bdedit.block_wire import Wire
from bdsim.bdedit.block_main_block import Main
from bdsim.bdedit.grouping_box import Grouping_Box
from bdsim.bdedit.floating_label import Floating_Label
from bdsim.bdedit.block_connector_block import Connector
from bdsim.bdedit.interface_serialize import Serializable
from bdsim.bdedit.interface_scene_history import SceneHistory
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
    - floating labels, a list containing all the ``Floating Label`` instances
    - grouping boxes, a list containing all the ``Grouping Box`` instances
    - intersection points, a list containing all intersection points between Wires
    """

    # -----------------------------------------------------------------------------
    def __init__(self, resolution, window, main_window):
        """
        This method initializes an instance of the ``Scene`` Class.

        :param resolution: the desktop screen resolution of the user
        :type resolution: PyQt5.QtCore.QRect(0, 0, screen_width, screen_height), required
        :param window: the application's layer manager
        :type window: QGridLayout, required
        """
        super().__init__()
        # The application's layer manager and interface manager are assigned to internal variables
        self.window = window
        self.main_window = main_window

        # Empty lists for the blocks, wires and intersection points are initialized
        self.blocks = []
        self.wires = []
        self.floating_labels = []
        self.grouping_boxes = []
        self.intersection_list = []

        # Set default font size of block names, to be used when they are spawned
        self.block_name_fontsize = 12

        # Variables to listen for modifications with in the scene
        self._has_been_modified = False

        # Initialize listener
        self._has_been_modified_listeners = []

        # Variable for toggling between connector blocks being visible or not
        # False by default
        self.hide_connector_blocks = False

        # The scened dimensions are initially set to the width/height of the desktop
        # screen, but later adjusted with self.updateSceneDimensions()
        self.scene_width = resolution.width()
        self.scene_height = resolution.height()

        self.initUI()
        self.determineFont()
        self.history = SceneHistory(self)
        self.history.storeHistory("Blank canvas loaded")

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

        # Create variables to record when and by whom this diagram was created
        self.creation_time = int(time.time())
        self.created_by = getpass.getuser()

        # Copy variable of simulation time from interface manager for saving
        # Initialized to 10.0, overwritten when changed in GUI or if loaded from model
        self.sim_time = 10.0

    # -----------------------------------------------------------------------------
    def determineFont(self):
        """
        This method sets the truetype font with which socket labels should be drawn.
        Originally, this property was set within the sockets themselves, but when
        they are constantly drawn/redrawn (i.e. when undo/redo is spammed) and as a
        result, multiple attemps are made to access the truetype font, Windows issues
        an OSError crashing the program... So since this font only needs to be defined
        on startup, the font is accessed whenever the scene is created.
        """
        try:
            self._system_font = ImageFont.truetype("arial.ttf", 14)
        except OSError:
            self._system_font = ImageFont.load_default()

    # -----------------------------------------------------------------------------
    def addHasBeenModifiedListener(self, callback: "function"):
        self._has_been_modified_listeners.append(callback)

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
    def addLabel(self, label):
        """
        This method adds a ``Floating Label`` to the ``Scene's`` list of labels.
        """
        self.floating_labels.append(label)

    # -----------------------------------------------------------------------------
    def addGBox(self, GBox):
        """
        This method adds a ``Grouping Box`` to the ``Scene's`` list of grouping boxes.
        """
        self.grouping_boxes.append(GBox)

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
    def removeLabel(self, label):
        """
        This method removes a ``Floating Label`` to the ``Scene's`` list of labels.
        """
        self.floating_labels.remove(label)

    # -----------------------------------------------------------------------------
    def removeGBox(self, GBox):
        """
        This method removes a ``Grouping Box`` to the ``Scene's`` list of grouping boxes.
        """
        self.grouping_boxes.remove(GBox)

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
    def getView(self):
        """
        This method returns the associated ``GraphicsView`` for this ``Scene``.
        :return: ``GraphicsView`` associated to this ``Scene``
        :rtype: ``QGraphicsView``
        """
        self.grScene.views()[0]

    # -----------------------------------------------------------------------------
    def clear(self):
        """
        This method removes all blocks and floating text labels from the list of
        blocks and list of floating labels respectively, within the ``Scene``.
        This will subsequently remove any and all wires between these blocks.
        """

        # Removes the first block from the self.blocks array, until the array is empty
        while len(self.blocks) > 0:
            self.blocks[0].parameterWindow.setVisible(False)
            self.blocks[0].remove()

        # Removes the first label from self.floating_labels array, until it is empty
        while len(self.floating_labels) > 0:
            self.floating_labels[0].remove()

        # Removes the first GBox from self.grouping_boxes array, until it is empty
        while len(self.grouping_boxes) > 0:
            self.grouping_boxes[0].remove()

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
        blocks, wires, labels, gboxes = [], [], [], []
        for block in self.blocks:
            blocks.append(block.serialize())
            # # If parameter window still opened for any block, close it
            # if block.parameterWindow:
            #     if block.parameterWindow.isVisible():
            #         block.closeParamWindow()

        for wire in self.wires:
            wires.append(wire.serialize())
        for label in self.floating_labels:
            labels.append(label.serialize())
        for gbox in self.grouping_boxes:
            gboxes.append(gbox.serialize())
        return OrderedDict(
            [
                ("id", self.id),
                ("created_by", self.created_by),
                ("creation_time", self.creation_time),
                ("simulation_time", self.sim_time),
                ("scene_width", self.scene_width),
                ("scene_height", self.scene_height),
                ("blocks", blocks),
                ("wires", wires),
                ("labels", labels),
                ("grouping_boxes", gboxes),
            ]
        )

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

        # If sim_time parameter exists in model, load it
        try:
            self.sim_time = data["simulation_time"]
        # Otherwise, ignore as model will be updated on save
        except:
            pass

        hashmap = {}

        # All the blocks which were saved, are re-created from the JSON file
        # For each block from the saved blocks
        for block_data in data["blocks"]:
            block_type = block_data["block_type"]
            # If a block is one that is manually defined by bdedit (such as the connector
            # or main blocks, or the text item), they must manaully be re-created.
            if block_type == "CONNECTOR" or block_type == "Connector":
                Connector(self, self.window).deserialize(block_data, hashmap)

            elif block_type == "MAIN" or block_type == "Main":
                Main(self, self.window).deserialize(block_data, hashmap)

            # Otherwise if it is any other block (will be an auto-imported block)
            else:
                # For each block class within the blocklist
                for block_class in blocklist:
                    # Re-create an instance of a block class that matches a name of one of the blocks
                    # from the blocklist. There will always be a match, as the block_type is determined
                    # by the blockname(block_class) in the first place, and this will never change.
                    # The block_class.__name__ supports older files which would of used self.__class__.__name__
                    # to define the block type
                    if (
                        block_type == blockname(block_class)
                        or block_type == block_class.__name__
                    ):
                        block_class().deserialize(block_data, hashmap)
                        break

        # Next recreate all the wires that were saved
        for wire_data in data["wires"]:
            Wire(self).deserialize(wire_data, hashmap)

        # Lastly, if it exists, add the floating text labels that were saved
        try:
            if data["labels"]:
                # If the data for the labels is not null, then create the labels
                for label_data in data["labels"]:
                    if label_data is not None:
                        Floating_Label(self, self.window, self.main_window).deserialize(
                            label_data, hashmap
                        )
        except KeyError:
            # If model data doesn't contain 'labels' then none were saved, so don't create any.
            pass

        # Finally, if it exists, add the grouping boxes that were saved
        try:
            if data["grouping_boxes"]:
                # If the data for the gboxes is not null, then create the grouping boxes
                for gbox_data in data["grouping_boxes"]:
                    if gbox_data is not None:
                        # Ensure essnetial Grouping Box info exists; if it does not, we cannot fully reconstruct Grouping Box, so ignore
                        if (
                            gbox_data["width"]
                            and gbox_data["height"]
                            and gbox_data["color"]
                        ):
                            if (gbox_data["pos_x"] is not None) and (
                                gbox_data["pos_y"] is not None
                            ):
                                pos = (gbox_data["pos_x"], gbox_data["pos_y"])
                                Grouping_Box(
                                    self,
                                    self.window,
                                    gbox_data["width"],
                                    gbox_data["height"],
                                    gbox_data["color"],
                                    pos,
                                ).deserialize(gbox_data, hashmap)
                            else:
                                Grouping_Box(
                                    self,
                                    self.window,
                                    gbox_data["width"],
                                    gbox_data["height"],
                                    gbox_data["color"],
                                ).deserialize(gbox_data, hashmap)
        except KeyError:
            # If model data doesn't contain 'grouping_boxes' then none were saved, so don't create any.
            pass

        return True
