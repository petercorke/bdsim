import json
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QMessageBox, QWidget, QVBoxLayout
from collections import OrderedDict

from bdedit.Icons import *
from bdedit.block_wire import Wire
from bdedit.block import *
from bdedit.block_socket_block import Connector
from bdedit.interface_graphics_scene import GraphicsScene
from bdedit.interface_serialize import Serializable


class Scene(Serializable):
    def __init__(self, resolution, window):
        super().__init__()
        self.window = window

        self.blocks = []
        self.wires = []
        self.intersection_list = []

        self.scene_width = resolution.width()
        self.scene_height = resolution.height()

        self.initUI()

    def initUI(self):
        self.grScene = GraphicsScene(self)
        self.updateSceneDimensions()

    def addBlock(self, block):
        self.blocks.append(block)

    def addWire(self, wire):
        self.wires.append(wire)

    def removeBlock(self, block):
        self.blocks.remove(block)

    def removeWire(self, wire):
        self.wires.remove(wire)

    def getSceneWidth(self):
        return self.scene_width

    def getSceneHeight(self):
        return self.scene_height

    def setSceneWidth(self, width):
        self.scene_width = width

    def setSceneHeight(self, height):
        self.scene_height = height

    def updateSceneDimensions(self):
        self.grScene.setGrScene(self.scene_width, self.scene_height)

    # Removes the first block from the self.blocks array, until the array is empty
    def clear(self):
        while len(self.blocks) > 0:
            self.blocks[0].remove()


    def checkForDuplicates(self, name):
        duplicate = False
        for block in self.blocks:
            if name == block.title:
                duplicate = True
                break

        return duplicate

    def displayMessage(self, title, text):
        def closeMessage():
            timer.stop()
            message.close()

        # Create a widget to wrap the QMessageBox into, that it may be displayed in the ParamWindow
        message = QMessageBox()
        message.setIconPixmap(QPixmap(":/Icons_Reference/Icons/Success_Icon.png"))
        # Set the title and text for the message
        message.setText("<font><b> File saved successfully! </font>")
        # Set message modality to be non-blocking (by default, QMessageBox blocks other actions until closed)
        message.setWindowModality(Qt.NonModal)
        self.window.addWidget(message, 2, 5, 1, 1)

        # Create timer to keep success message opened for 1.5 seconds
        timer = QtCore.QTimer()
        timer.setInterval(1000)
        timer.timeout.connect(closeMessage)
        timer.start()

    def saveToFile(self, filename):
        with open(filename, "w") as file:
            file.write(json.dumps(self.serialize(), indent=4))
        self.displayMessage("Success!", "Canvas items successfully saved to " + filename)
        # print("Saving to", filename, "was successful!")

    def loadFromFile(self, filename):
        with open(filename, "r") as file:
            raw_data = file.read()
            data = json.loads(raw_data)
            self.deserialize(data, self.window)

    def serialize(self):
        blocks, wires = [], []
        for block in self.blocks: blocks.append(block.serialize())
        for wire in self.wires: wires.append(wire.serialize())
        return OrderedDict([
            ('id', self.id),
            ('scene_width', self.scene_width),
            ('scene_height', self.scene_height),
            ('blocks', blocks),
            ('wires', wires),
        ])

    def deserialize(self, data, hashmap={}):
        self.clear()
        hashmap = {}

        # create blocks
        for block_data in data["blocks"]:
            block_type = block_data["block_type"]
            if block_type == "Connector":
                Connector(self, self.window, name=block_data['title']).deserialize(block_data, hashmap)
            else:
                for block_class in blocklist:
                    if block_type == block_class.__name__:
                        block_class(self, self.window, name=block_data['title']).deserialize(block_data, hashmap)
                        break

        # create wires
        for wire_data in data["wires"]:
            Wire(self).deserialize(wire_data, hashmap)

        return True

