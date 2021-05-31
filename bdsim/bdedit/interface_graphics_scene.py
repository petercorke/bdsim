import math
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class GraphicsScene(QGraphicsScene):
    def __init__(self, scene, parent=None):
        super().__init__(parent)

        self.scene = scene

        # Grid settings
        self.gridSize = 20
        self.gridSquares = 5

        self.mode = "Light"

        self._default_background_color = QColor("#E0E0E0")
        # self._default_background_color = QColor("#FFFFFF")

    def setGrScene(self, width, height):
        self.setSceneRect(-width//2, -height//2, width, height)

    def updateMode(self, value):
        if value in ["Light", "Dark", "Off"]:
            self.mode = value
            self.update()
        else:
            print("Grid mode not supported.")

    def checkMode(self):
        if self.mode == 'Light':
            self._color_background = QColor("#E0E0E0")
            self._color_light = QColor("#D1D1D1")
            self._color_dark = QColor("#C0C0C0")
        elif self.mode == 'Dark':
            self._color_background = QColor("#999999")
            self._color_light = QColor("#808080")
            self._color_dark = QColor("#606060")
        elif self.mode == "Off":
            self._color_background = self._default_background_color

        self._pen_light = QPen(self._color_light)
        self._pen_light.setWidth(1)
        self._pen_dark = QPen(self._color_dark)
        self._pen_dark.setWidth(2)
        self.setBackgroundBrush(self._color_background)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

        for block in self.scene.blocks:
            if block.grBlock.isSelected():
                block.updateConnectedEdges()

        # # Code for collision detection of items in the scene
        # for block in self.scene.blocks:
        #     # For each output socket of a block
        #     for outSocket in block.inputs:
        #         # Grab the wire if the socket has a wire
        #         if outSocket.wire:
        #             print(self.collidingItems(outSocket.wire.grWire, mode=Qt.IntersectsItemShape))

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)

        self.checkMode()

        if self.mode != "Off":
            # here we create our grid
            left = int(math.floor(rect.left()))
            right = int(math.ceil(rect.right()))
            top = int(math.floor(rect.top()))
            bottom = int(math.ceil(rect.bottom()))

            first_left = left - (left % self.gridSize)
            first_top = top - (top % self.gridSize)

            # compute all lines to be drawn
            lines_light, lines_dark = [], []
            for x in range(first_left, right, self.gridSize):
                if x % (self.gridSize * self.gridSquares) != 0:
                    lines_light.append(QLine(x, top, x, bottom))
                else:
                    lines_dark.append(QLine(x, top, x, bottom))

            for y in range(first_top, bottom, self.gridSize):
                if y % (self.gridSize * self.gridSquares) != 0:
                    lines_light.append(QLine(left, y, right, y))
                else:
                    lines_dark.append(QLine(left, y, right, y))

            # draw the lines
            painter.setPen(self._pen_light)
            painter.drawLines(*lines_light)

            painter.setPen(self._pen_dark)
            painter.drawLines(*lines_dark)
