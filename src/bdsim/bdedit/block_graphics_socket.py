# Library imports
import sys
import traceback
from PIL import ImageFont

# PyQt5 imports
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *


# =============================================================================
#
#   Defining and setting global variables
#
# =============================================================================
# Socket positioning variables - used for determining what side of the block the
# socket should be drawn
LEFT = 1
RIGHT = 3

# Socket type classification variables
INPUT = 1
OUTPUT = 2

# Input Socket sign classification variables
PLUS = "+"
MINUS = "-"
MULTIPLY = "*"
DIVIDE = "/"


# =============================================================================
#
#   Defining the GraphicsSocket Class, which is inherited by all Sockets, and
#   controls the graphical appearance of each Socket.
#
# =============================================================================
class GraphicsSocket(QGraphicsItem):
    """
    The ``GraphicsSocket`` Class extends the ``QGraphicsItem`` Class from PyQt5.
    This class is responsible for graphically drawing Sockets on Blocks. It
    specifies the shape, colour, style and dimensions of the Socket and also
    implements the logic for drawing signs alongside the input sockets of ``PROD``
    and ``SUM``` Blocks.
    """

    # -----------------------------------------------------------------------------
    def __init__(self, socket):
        """
        This method initializes an instance of the ``GraphicsSocket`` Class. It
        defines the shapes and sizes for a given input or output Socket. Depending
        on the socket_type, stored within the provided Socket, the shape and colour
        of the given Socket is decided.

        :param socket: the Socket this GraphicsSocket instance relates to
        :type socket: Socket
        """

        self.socket = socket
        # The GraphicsBlock class is initialized for the Block Class this Socket relates to
        super().__init__(socket.node.grBlock)

        # Sizes for the various socket shapes are defined
        self.radius = 6.0
        self.triangle_left = 6
        self.triangle_right = 8
        self.triangle_up = 6
        self.square = 6

        # Outlines of the shapes and signs are defined
        self.outline_width = 1.0
        self.sign_width = 1.5

        # Fill colors of the socket shapes are defined
        self._color_background_input = QColor("#3483eb")  # Blue
        self._color_background_output = QColor("#f54242")  # Red
        self._color_background_connector = QColor(
            "#42f587"
        )  # Lime Green (currently not used)
        self._color_outline = QColor("#000000")  # Black

        # Painter pens are assigned a colour and outline thickness
        self._pen = QPen(self._color_outline)
        self._pen.setWidthF(self.outline_width)
        self._sign_pen = QPen(self._color_outline)
        self._sign_pen.setWidthF(self.sign_width)
        self._char_font = QFont("Arial", 14)

        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setBrush()

        # Internal variable for catching fatal errors, and allowing user to save work before crashing
        self.FATAL_ERROR = False

    def setBrush(self):
        # Depending on the socket type, the painter brush is set
        if self.socket.socket_type == INPUT:
            self._brush = QBrush(self._color_background_input)
        elif self.socket.socket_type == OUTPUT:
            self._brush = QBrush(self._color_background_output)

    # Todo - update docs, and inline comments
    # -----------------------------------------------------------------------------
    def paint(self, painter, style, widget=None):
        """
        This is an inbuilt method of QGraphicsItem, that is overwritten by ``GraphicsSocket``.
        This method is automatically called by the GraphicsView Class whenever even
        a slight user-interaction is detected within the Scene.

        It dictates how both input and output Sockets are painted on their relating Block.
        The position at which to draw the Socket is determined internally by the Socket
        class, so when the GraphicsSocket class paints the Socket, it is painted with
        respects to the point where the Socket should be.

        :param painter: a painter (paint brush) that paints and fills the shape of this GraphicsSocket
        :type painter: QPainter, automatically recognized and overwritten from this method
        :param style: style of the painter (isn't used but must be defined)
        :type style: QStyleOptionGraphicsItem, automatically recognized from this method
        :param widget: the widget this class is being painted on (None)
        :type widget: NoneType, optional, Defaults to None
        """

        # Painter pen(outline) and brush(fill) are set
        painter.setPen(self._pen)
        try:
            painter.setBrush(self._brush)
        except AttributeError as e:
            # For some reason, brush was not set, set it again based on socket type
            self.setBrush()

        # If sockets don't need to be hidden, draw them normally, otherwise don't draw them at all
        if not self.shouldSocketsBeHidden():
            # Multi is an internal variable that dictates the direction the socket shapes
            # should point (this comes into affect when the block sockets are flipped, and the
            # output triangle socket shape should point either right (default), or left (flipped))
            multi = 1
            offset = 0

            # If the socket has a name (character) to display, find the characters' dimensions
            # Dimensions of the socket sign - contains [width, height] of character
            if self.socket.socket_sign:
                (char_width, char_height) = self.charDimensions()
            else:
                (char_width, char_height) = [0, 0]

            # If the socket is flipped, adjust the internal multi variable
            if self.socket.position == RIGHT:
                multi = -1
                if self.socket.socket_sign:
                    offset = char_width

            # This code paints a square for the input socket
            if self.socket.socket_type == INPUT:
                painter.drawRect(
                    -self.square, -self.square, 2 * self.square, 2 * self.square
                )
                # If the input socket has a sign (will be true for the PROD and SUM Blocks)
                # paint the relevant sign (+,-,*,/) next to the input socket
                try:
                    if self.socket.socket_sign is not None:
                        path = self.getSignPath(self.socket.socket_sign, multi)
                        if path is None:
                            painter.setPen(self._sign_pen)
                            painter.setFont(self._char_font)
                            painter.drawText(
                                (10 + offset) * multi,
                                char_height,
                                self.socket.socket_sign,
                            )
                        else:
                            # The painter path for the respective sign depends on the sign relating to this socket
                            painter.setPen(self._sign_pen)
                            painter.drawPath(path)
                except Exception as e:
                    if self.FATAL_ERROR == False:
                        print(
                            "---------------------------------------------------------------------------------------"
                        )
                        print(
                            "Caught fatal exception while trying to draw input socket labels. Please save your work."
                        )
                        print(
                            "---------------------------------------------------------------------------------------"
                        )
                        traceback.print_exc(file=sys.stderr)
                        self.FATAL_ERROR = True

            # This code paints a triangle for the output socket
            if self.socket.socket_type == OUTPUT:
                path = QPainterPath()
                path.moveTo(multi * self.triangle_left, multi * self.triangle_up)
                path.lineTo(-multi * self.triangle_right, 0)
                path.lineTo(multi * self.triangle_left, -multi * self.triangle_up)
                path.lineTo(multi * self.triangle_left, multi * self.triangle_up)
                painter.drawPath(path)

                try:
                    if self.socket.socket_sign is not None:
                        painter.setPen(self._sign_pen)
                        painter.setFont(self._char_font)
                        painter.drawText(
                            (10 + offset) * multi, char_height, self.socket.socket_sign
                        )
                except Exception as e:
                    if self.FATAL_ERROR == False:
                        print(
                            "----------------------------------------------------------------------------------------"
                        )
                        print(
                            "Caught fatal exception while trying to draw output socket labels. Please save your work."
                        )
                        print(
                            "----------------------------------------------------------------------------------------"
                        )
                        traceback.print_exc(file=sys.stderr)
                        self.FATAL_ERROR = True

    # -----------------------------------------------------------------------------
    def paintPlus(self, multi):
        """
        This method creates a painter path for drawing the '+' character next
        to an input socket.

        :param multi: internal variable (1 when default orientation, -1 when flipped)
        :type multi: int, required, 1 or -1
        :return: the painter path to draw this sign
        :rtype: QPainterPath
        """

        path = QPainterPath(QPointF(multi * 2.5 * self.square, 0))
        path.lineTo(multi * 4.5 * self.square - multi * 2, 0)
        path.moveTo(multi * 3.5 * self.square - multi * 1, -self.square + 1)
        path.lineTo(multi * 3.5 * self.square - multi * 1, self.square - 1)
        return path

    # -----------------------------------------------------------------------------
    def paintMinus(self, multi):
        """
        This method creates a painter path for drawing the '-' character next
        to an input socket.

        :param multi: internal variable (1 when default orientation, -1 when flipped)
        :type multi: int, required, 1 or -1
        :return: the painter path to draw this sign
        :rtype: QPainterPath
        """

        path = QPainterPath(QPointF(multi * 2.5 * self.square, 0))
        path.lineTo(multi * 4.5 * self.square - multi * 2, 0)
        return path

    # -----------------------------------------------------------------------------
    def paintMultiply(self, multi):
        """
        This method creates a painter path for drawing the 'x' character next
        to an input socket.

        :param multi: internal variable (1 when default orientation, -1 when flipped)
        :type multi: int, required, 1 or -1
        :return: the painter path to draw this sign
        :rtype: QPainterPath
        """

        path = QPainterPath(QPointF(multi * 2.5 * self.square, -self.square + 1))
        path.lineTo(multi * 4.5 * self.square - multi * 2, self.square - 1)
        path.moveTo(multi * 4.5 * self.square - multi * 2, -self.square + 1)
        path.lineTo(multi * 2.5 * self.square, self.square - 1)
        return path

    # -----------------------------------------------------------------------------
    def paintDivide(self, multi):
        """
        This method creates a painter path for drawing a divide sign character next
        to an input socket.

        :param multi: internal variable (1 when default orientation, -1 when flipped)
        :type multi: int, required, 1 or -1
        :return: the painter path to draw this sign
        :rtype: QPainterPath
        """

        path = QPainterPath(QPointF(multi * 2.5 * self.square, 0))
        path.lineTo(multi * 4.5 * self.square - 1, 0)
        path.moveTo(multi * 3.5 * self.square - 1, -self.square + 1)
        path.addEllipse(multi * 3.5 * self.square - 1, -self.square + 1, 1, 1)
        path.moveTo(multi * 3.5 * self.square - 1, self.square - 2)
        path.addEllipse(multi * 3.5 * self.square - 1, self.square - 2, 1, 1)
        return path

    # Todo - doc comments
    # -----------------------------------------------------------------------------
    def charDimensions(self):

        # Find how many pixels - height wise - this sockets' character is
        (width, baseline), (
            offset_x,
            offset_y,
        ) = self.socket.node.scene._system_font.font.getsize(self.socket.socket_sign)

        char_width = QFontMetrics(self._char_font).width(self.socket.socket_sign)
        height = 5

        # For letters like: a,c,e,m,n,o,r,s,u,v,w,x,z
        if baseline == 8 and offset_y == 5:
            height = 5
        # For letters like: b,d,f,h,i,k,l
        elif baseline == 10 and offset_y == 3:
            height = 7
        # For letters like: g,p,q,y
        elif baseline == 11 and offset_y == 5:
            height = 4
        # For letter: t
        elif baseline == 11 and offset_y == 2:
            height = 7

        dimension = [char_width, height]

        return dimension

    # -----------------------------------------------------------------------------
    def getSignPath(self, sign, multi):
        """
        This method determines and returns what method should be called to paint
        the sign (+,-,*,/) next to an input socket (for PROD and SUM blocks only).

        :param sign: the sign associated with the current Socket (can be '+','-','*', or '/')
        :type sign: str, required
        :param multi: internal variable (1 when default orientation, -1 when flipped)
        :type multi: int, required, 1 or -1
        :return: the relevant painter path method for drawing the desired sign
        :rtype: QPainterPath
        """

        if sign == PLUS:
            return self.paintPlus(multi)
        if sign == MINUS:
            return self.paintMinus(multi)
        if sign == MULTIPLY:
            return self.paintMultiply(multi)
        if sign == DIVIDE:
            return self.paintDivide(multi)

    # Todo - doc comments
    # -----------------------------------------------------------------------------
    def shouldSocketsBeHidden(self):

        # Check if the sockets belong to a connector type block
        if (
            self.socket.node.block_type == "CONNECTOR"
            or self.socket.node.block_type == "Connector"
        ):
            # Check if the toolbar checkbox for hiding connector blocks has been selected
            if self.socket.node.scene.hide_connector_blocks:
                return True
            else:
                return False
        else:
            return False

    # -----------------------------------------------------------------------------
    def boundingRect(self):
        """
        This is an inbuilt method of QGraphicsItem, that is overwritten by ``GraphicsSocket``
        which returns the area within which the GraphicsSocket can be interacted with.
        When a mouse click event is detected within this area, this will trigger logic
        that relates to a Socket (that being, the generating or completion of a Wire).

        :return: a rectangle within which the Socket can be interacted with
        :rtype: QRectF
        """

        return QRectF(
            -self.radius - self.outline_width,
            -self.radius - self.outline_width,
            2 * (self.radius + self.outline_width),
            2 * (self.radius + self.outline_width),
        )
