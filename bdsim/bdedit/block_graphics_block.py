from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from bdedit.Icons import *


class GraphicsBlock(QGraphicsItem):
    def __init__(self, block, parent=None):
        super().__init__(parent)
        self.block = block
        self.icon = self.block.icon

        self.mode = self.block.scene.grScene.mode

        self.counter = 0
        self._draw_title = True

        self.width = self.block.width
        self.height = self.block.height

        # These dimensions are not updated
        self._default_width = self.block.width
        self._default_height = self.block.height

        self.edge_size = 10.0
        self.title_height = 25.0
        self._padding = 5.0
        self._line_thickness = 3.0
        self._selected_line_thickness = 5.0

        self._pen_selected = QPen(QColor("#FFFFA637"), self._selected_line_thickness)

        # Default title colour (Light mode)
        self._default_title_color = Qt.black

        self._title_font = QFont("Ubuntu", 10)

        self.initTitle()
        self.initSockets()

        self.checkMode()

        self.initUI()

    def boundingRect(self):
        return QRectF(
            0,
            0,
            self.width,
            self.height
        ).normalized()

    def initUI(self):
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIsMovable)

    def initSockets(self):
        pass

    # Returns the length of the block's title in pixels
    def titleLength(self):
        # Using the font of the text and the block's title, determine the length of the title in terms of pixels
        title_pixel_len = QFontMetrics(self._title_font).width(self.block.title)
        # As the block width is an even number (100 pixels), to center properly, the width of the title must also be even
        # If title width is odd, add 1 pixel to it to make it even
        if title_pixel_len % 2 != 0:
            title_pixel_len += 1
        return title_pixel_len

    def initTitle(self):
        self.title_item = QGraphicsTextItem(self)
        self.title_item.setDefaultTextColor(self._default_title_color)
        self.title_item.setFont(self._title_font)

    def getTitle(self):
        return self.block.title

    def setTitle(self):
        self._draw_title = False
        self.title_item.setPlainText(self.block.title)
        self.title_item.setPos((self.width - self._padding - self.titleLength()) / 2, self.height + self._padding)
        self.update()

    def updateMode(self, value):
        if value in ["Light", "Dark", "Off"]:
            self.mode = value
            self.checkMode()
            self.update()
        else:
            print("Block mode not supported.")

    def checkMode(self):
        # If dark mode is selected, draw blocks tailored to dark mode
        if self.mode == "Dark":
            self._title_color = Qt.white
            self._pen_default = QPen(Qt.white, self._line_thickness)
            self._brush_background = QBrush(Qt.white)
        # Else light or off mode is selected (No off mode for blocks), draw blocks tailored to light mode
        else:
            self._title_color = Qt.black
            self._pen_default = QPen(QColor("#7F000000"), self._line_thickness)
            self._brush_background = QBrush(QColor("#FFE1E0E8"))

        self.title_item.setDefaultTextColor(self._title_color)

    # Checks if the current height of the block is high enough to space out all the sockets
    def checkBlockHeight(self):
        # The space from edge of the block and the first/last socket
        socket_spacer = self._padding + self.edge_size + self.title_height

        # Last input/output socket ([x,y])
        if self.block.inputs:
            last_input = self.block.inputs[-1].getSocketPosition()
        else:
            last_input = [0, 0]
        if self.block.outputs:
            last_output = self.block.outputs[-1].getSocketPosition()
        else:
            last_output = [0, 0]

        # Max height of input/output sockets - adds socket_spacer height to height of last input/output socket
        max_input_socket_height = last_input[1] + socket_spacer
        max_output_socket_height = last_output[1] + socket_spacer

        # Max block height (determined by which ever has more sockets - inputs or outputs)
        max_block_height = max(max_input_socket_height, max_output_socket_height)

        # If max_block_height is greater than the default block height, set current_block_height to max_block_height
        # Otherwise keep it at the default block height
        if max_block_height > self._default_height:
            self.block.height = max_block_height
        else:
            self.block.height = self._default_height

        self.height = self.block.height
        self.update()

    def paint(self, painter, QtStyleOptionGraphicsItem, widget=None):

        self.checkBlockHeight()

        if self._draw_title:
            self.setTitle()

        # content
        path_content = QPainterPath()
        path_content.setFillRule(Qt.WindingFill)
        path_content.addRoundedRect(0, 0, self.width, self.height, self.edge_size,
                                    self.edge_size)
        path_content.addRect(0, self.title_height, self.edge_size, self.edge_size)
        path_content.addRect(self.width - self.edge_size, self.title_height, self.edge_size, self.edge_size)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._brush_background)
        painter.drawPath(path_content.simplified())

        # outline
        path_outline = QPainterPath()
        path_outline.addRoundedRect(0, 0, self.width, self.height, self.edge_size, self.edge_size)
        painter.setPen(self._pen_default if not self.isSelected() else self._pen_selected)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path_outline.simplified())

        # icon
        icon_item = QPixmap(self.icon).scaledToWidth(50) if self.icon else QPixmap(self.icon)
        target = QRect((self.width-icon_item.width())/2, (self.height-icon_item.height())/2, self.width, self.height)
        source = QRect(0, 0, self.width, self.height)
        painter.drawPixmap(target, icon_item, source)

    def mousePressEvent(self, event):
        self.block.setFocusOfBlocks()
      
        if event.button() == Qt.RightButton:
            if self.isSelected():
                self.block.toggleParamWindow()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

        x = round(self.pos().x() / 20) * 20
        y = round(self.pos().y() / 20) * 20
        pos = QPointF(x, y)
        self.setPos(pos)

        # 20 is the width of the smaller grid squares
        padding = 20
        if self.pos().x() < self.scene().sceneRect().x() + padding:
            # left
            self.setPos(self.scene().sceneRect().x() + padding, self.pos().y())

        if self.pos().y() < self.scene().sceneRect().y() + padding:
            # top
            self.setPos(self.pos().x(), self.scene().sceneRect().y() + padding)

        if self.pos().x() > (self.scene().sceneRect().x() + self.scene().sceneRect().width() - self.width - padding):
            # right
            self.setPos(self.scene().sceneRect().x() + self.scene().sceneRect().width() - self.width - padding, self.pos().y())

        if self.pos().y() > (self.scene().sceneRect().y() + self.scene().sceneRect().height() - self.height - self.title_height - padding):
            # bottom
            self.setPos(self.pos().x(), self.scene().sceneRect().y() + self.scene().sceneRect().height() - self.height - self.title_height - padding)

        for block in self.block.scene.blocks:
            if block.grBlock.isSelected():
                block.updateConnectedEdges()


class GraphicsSocketBlock(QGraphicsItem):
    def __init__(self, block, parent=None):
        super().__init__(parent)
        self.block = block
        self.icon = self.block.icon
        
        self.counter = 0
        self._draw_title = True

        self.width = self.block.width
        self.height = self.block.height

        self.edge_size = 0
        self.title_height = 0
        self._padding = 0
        self._line_thickness = 3.0
        self._selected_line_thickness = 5.0
        self._corner_rounding = 10
        self._pen_selected = QPen(QColor("#FFFFA637"), self._selected_line_thickness)
        self.initSockets()

        self.initUI()

    def boundingRect(self):
        W = self.width
        L = self._line_thickness
        return QRectF(
            1 - W - L,
            1 - W - L,
            3 * W + L,
            2 * W + L
        ).normalized()
        # return QRectF(
        #     1 - 1.5 * W - L,
        #     1 - 1.5 * W - L,
        #     4 * W + L,
        #     3 * W + L
        # ).normalized()

    def mousePressEvent(self, event):
        self.block.setFocusOfBlocks()
        # if self.isSelected():
        #     if event.button() == Qt.LeftButton:
        #         self.setSelected(True)
        #     elif event.button() == Qt.RightButton:
        #         self.block.toggleParamWindow()
       
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

        x = round(self.pos().x() / 20) * 20
        y = round(self.pos().y() / 20) * 20
        pos = QPointF(x, y)
        self.setPos(pos)

        # 20 is the width of the smaller grid squares
        padding = 20
        if self.pos().x() < self.scene().sceneRect().x() + padding:
            # left
            self.setPos(self.scene().sceneRect().x() + padding, self.pos().y())

        if self.pos().y() < self.scene().sceneRect().y() + padding:
            # top
            self.setPos(self.pos().x(), self.scene().sceneRect().y() + padding)

        if self.pos().x() > (self.scene().sceneRect().x() + self.scene().sceneRect().width() - self.width - padding):
            # right
            self.setPos(self.scene().sceneRect().x() + self.scene().sceneRect().width() - self.width - padding, self.pos().y())

        if self.pos().y() > (self.scene().sceneRect().y() + self.scene().sceneRect().height() - self.height - self.title_height - padding):
            # bottom
            self.setPos(self.pos().x(), self.scene().sceneRect().y() + self.scene().sceneRect().height() - self.height - self.title_height - padding)

        for block in self.block.scene.blocks:
            if block.grBlock.isSelected():
                block.updateConnectedEdges()

    def initUI(self):
        # print("initUI")
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setSelected(True)

    def initSockets(self):
        pass

    def updateMode(self, value):
        pass

    def paint(self, painter, QtStyleOptionGraphicsItem, widget=None):
        if self.isSelected():
            # outline
            path_outline = QPainterPath()
            path_outline.addRoundedRect(self.boundingRect(), self._corner_rounding, self._corner_rounding)
            painter.setPen(self._pen_selected)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path_outline.simplified())
