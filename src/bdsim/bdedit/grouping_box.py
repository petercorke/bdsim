# Library imports
import json
import copy
from collections import OrderedDict

# PyQt5 imports
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

# BdEdit imports
from bdsim.bdedit.interface_serialize import Serializable
from bdsim.bdedit.grouping_box_graphics import GraphicsGBox


DEBUG = False


class Grouping_Box(Serializable):
    def __init__(
        self,
        scene,
        window,
        width=500,
        height=300,
        bg_color=(146, 187, 255),
        pos=(-200, -100),
    ):
        super().__init__()
        self.scene = scene
        self.window = window
        self.position = pos

        self.width = width
        self.height = height
        self.background_color = QColor(bg_color[0], bg_color[1], bg_color[2], 127)
        self.border_color = QColor(0, 0, 0, 255)

        self.grGBox = GraphicsGBox(self, 0, 0, self.width, self.height)
        self.grGBox.setPos(self.position[0], self.position[1])

        self.scene.addGBox(self)
        self.scene.grScene.addItem(self.grGBox)

        self.scene.has_been_modified = True

    def setPos(self, x, y):
        self.grGBox.setPos(x, y)

    def setFocusOfGroupingBox(self):
        """
        This method sends all ``Grouping Box`` instances within the ``Scene`` to back
        and then sends the currently selected ``Grouping Box`` instance to front.
        """

        # Iterates through each Grouping Box within grouping_boxes list stored in \
        # the Scene Class and sets the graphical component of each gbox to a zValue of -11.
        for groupBox in self.scene.grouping_boxes:
            groupBox.grGBox.setZValue(-11)

        # Then sets the graphical component of the currently selected gbox to a
        # zValue of -10, which makes it display above all other gboxes on screen, but behind
        # all other items drawn in the canvas.
        self.grGBox.setZValue(-10)

    # Todo - update comments to match floating label, not block
    def remove(self):

        if DEBUG:
            print("> Removing Grouping Box", self)

        # Remove the graphical representation of this grouping box from the scene.
        if DEBUG:
            print(" - removing grGBox")
        self.scene.grScene.removeItem(self.grGBox)
        self.grGBox = None

        # Finally, call the removeGBox method from within the Scene, which
        # removes this GBox from the list of grouping boxes stored in the Scene.
        if DEBUG:
            print(" - removing Grouping Box from the scene")
        self.scene.removeGBox(self)
        if DEBUG:
            print(" - everything was done.")

    # -----------------------------------------------------------------------------
    def serialize(self):
        actual_pos = self.grGBox.mapToScene(self.grGBox.rect())
        return OrderedDict(
            [
                ("id", self.id),
                ("pos_x", actual_pos.boundingRect().x()),
                ("pos_y", actual_pos.boundingRect().y()),
                ("width", self.grGBox.rect().width()),
                ("height", self.grGBox.rect().height()),
                ("color", self.grGBox.bg_color.getRgb()[0:3]),
            ]
        )

    # -----------------------------------------------------------------------------
    def deserialize(self, data, hashmap={}):
        # The id of this Grouping Box is set to whatever was stored as its id in the JSON file.
        self.id = data["id"]

        return True
        pass
