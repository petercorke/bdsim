from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

LEFT = 1
RIGHT = 3

INPUT = 1
OUTPUT = 2
CONNECTOR = 3

PLUS = "+"
MINUS = "-"
MULTIPLY = "*"
DIVIDE = "/"

# =============================================================================
# 
# This class draws the sockets on the blocks that defines the connection of
# the wires between the blocks. It specifies the shape and dimensions of the
# socket as well as the colour of the socket based on the type of the socket
# 
# =============================================================================

class GraphicsSocket(QGraphicsItem):
    def __init__(self, socket):
        self.socket = socket
        super().__init__(socket.node.grBlock)

        self.radius = 6.0
        self.triangle_left = 7
        self.triangle_right = 8
        self.triangle_up = 6
        self.square = 6

        self.outline_width = 1.0
        self.sign_width = 1.5

        self._color_background_input = QColor("#3483eb")
        self._color_background_output = QColor("#f54242")
        self._color_background_connector = QColor("#42f587")
        self._color_outline = QColor("#FF000000")

        self._pen = QPen(self._color_outline)
        self._pen.setWidthF(self.outline_width)
        self._sign_pen = QPen(self._color_outline)
        self._sign_pen.setWidthF(self.sign_width)
        self._char_pen = QPen(QColor('#606060'))
        self._char_pen.setWidthF(self.sign_width)

        if self.socket.socket_type == INPUT:
            self._brush = QBrush(self._color_background_input)
        elif self.socket.socket_type == OUTPUT:
            self._brush = QBrush(self._color_background_output)
        # elif self.socket.socket_type == CONNECTOR:
        #     self._brush = QBrush(self._color_background_connector)
   
    # The Shape of the socket
    
# =============================================================================
#     
# Paint will do the drawing of socket once all the specifications have been
# set, it will get the position on the block that the socket will be drawn
# and then draw the socket based on the socket type. It will then lineTo the
# point to draw the line and then fill the shape to draw the socket.
#     
# =============================================================================
    
    def paint(self, painter, style, widget=None):
        painter.setBrush(self._brush)
        painter.setPen(self._pen)

        multi = 1

        if self.socket.position == RIGHT:
            multi = -1

        # square for input
        if self.socket.socket_type == INPUT:
            painter.drawRect(-self.square, -self.square, 2 * self.square, 2 * self.square)
            if self.socket.socket_sign is not None:
                painter.setPen(self._sign_pen)
                path = self.getSignPath(self.socket.socket_sign, multi)
                painter.drawPath(path)

        if self.socket.socket_type == OUTPUT:
            path = QPainterPath()
            path.moveTo(multi * self.triangle_left, multi * self.triangle_up)
            path.lineTo(-multi * self.triangle_right, 0)
            path.lineTo(multi * self.triangle_left, -multi * self.triangle_up)
            path.lineTo(multi * self.triangle_left, multi * self.triangle_up)
            painter.drawPath(path)

        # if self.socket.socket_type == CONNECTOR:
        #     painter.drawEllipse(-self.radius, -self.radius, 2 * self.radius, 2 * self.radius)

# =============================================================================
# Path for drawing a '+' sign next to given input socket
# =============================================================================
  
    def paintPlus(self, multi):
        path = QPainterPath(QPointF(multi * 2.5 * self.square, 0))
        path.lineTo(multi * 4.5 * self.square - multi * 2, 0)
        path.moveTo(multi * 3.5 * self.square - multi * 1, -self.square + 1)
        path.lineTo(multi * 3.5 * self.square - multi * 1, self.square - 1)
        return path

# =============================================================================
# Path for drawing a '-' sign next to given input socket       
# =============================================================================
    
    def paintMinus(self, multi):
        path = QPainterPath(QPointF(multi * 2.5 * self.square, 0))
        path.lineTo(multi * 4.5 * self.square - multi * 2, 0)
        return path

# =============================================================================
#     Path for drawing a 'x' sign next to given input socket
# =============================================================================
    
    
    def paintMultiply(self, multi):
        path = QPainterPath(QPointF(multi * 2.5 * self.square, -self.square + 1))
        path.lineTo(multi * 4.5 * self.square - multi * 2, self.square - 1)
        path.moveTo(multi * 4.5 * self.square - multi * 2, -self.square + 1)
        path.lineTo(multi * 2.5 * self.square, self.square - 1)
        return path
 
    
# =============================================================================
# Path for drawing a divide sign next to given input socket    
# =============================================================================
    
    def paintDivide(self, multi):
        path = QPainterPath(QPointF(multi * 2.5 * self.square, 0))
        path.lineTo(multi * 4.5 * self.square - 1, 0)
        path.moveTo(multi * 3.5 * self.square - 1, -self.square + 1)
        path.addEllipse(multi * 3.5 * self.square - 1, -self.square + 1, 1, 1)
        path.moveTo(multi * 3.5 * self.square - 1, self.square - 2)
        path.addEllipse(multi * 3.5 * self.square - 1, self.square - 2, 1, 1)
        return path


# =============================================================================
# Depending on the given sign, determines and returns which path to draw
# =============================================================================

    def getSignPath(self, sign, multi):
        if sign == PLUS:
            return self.paintPlus(multi)
        if sign == MINUS:
            return self.paintMinus(multi)
        if sign == MULTIPLY:
            return self.paintMultiply(multi)
        if sign == DIVIDE:
            return self.paintDivide(multi)


# =============================================================================
# Returns a rectangle within which the socket can be interacted with
# =============================================================================
    
    def boundingRect(self):
        return QRectF(
            - self.radius - self.outline_width,
            - self.radius - self.outline_width,
            2 * (self.radius + self.outline_width),
            2 * (self.radius + self.outline_width),
        )
