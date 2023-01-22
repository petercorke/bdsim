# Library imports
import sys
import traceback

# PyQt5 imports
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

# BdEdit imports
from bdsim.bdedit.Icons import *

# =============================================================================
#
#   Defining and setting global variables
#
# =============================================================================
# Socket positioning variables - used for determining what side of the block the
# socket should be drawn
LEFT = 1
RIGHT = 3


# =============================================================================
#
#   Defining the GraphicsBlock Class, which is inherited by all Blocks and
#   controls the graphical appearance of each Block.
#
# =============================================================================
class GraphicsBlock(QGraphicsItem):
    """
    The ``GraphicsBlock`` Class extends the ``QGraphicsItem`` Class from PyQt5.
    This class is responsible for graphically drawing Blocks within the GraphicsScene.
    Using the provided Block dimensions, it specifies the Blocks' shape and colour.
    """

    # -----------------------------------------------------------------------------
    def __init__(self, block, parent=None):
        """
        This method initializes an instance of the ``GraphicsBlock`` Class.
        It inherits the dimensions of its Block, and defines its shape and colour.

        :param block: the Block this GraphicsBlock instance relates to
        :type block: Block, required
        :param parent: the parent widget this class instance belongs to (None)
        :type parent: NoneType, optional, defaults to None
        """

        super().__init__(parent)
        # The block properties are inherited from the provided block
        self.block = block
        self.icon = self.block.icon
        self.width = self.block.width
        self.height = self.block.height

        # The color mode of the block is also stored (Light or Dark mode)
        self.mode = self.block.scene.grScene.mode

        # Internal variable which dictate whether a title needs to be drawn
        # The first time the Block is drawn, this is True, then it is set to
        # False, and only changed to True when the title is called to update
        self._draw_title = True

        # These dimensions are not updated
        self._default_width = self.block.width
        self._default_height = self.block.height

        # Pen thickness and block-related spacings are defined
        self.edge_size = 10.0  # How rounded the rectangle corners are
        self.title_height = (
            25.0  # How many pixels underneath the block the title is displayed at
        )
        self._padding = (
            5.0  # Minimum distance inside the block that things should be displayed at
        )
        self._line_thickness = 3.0  # Thickness of the block outline by default
        self._selected_line_thickness = (
            5.0  # Thickness of the block outline on selection
        )

        # Colours for pens are defined, and the text font is set
        self._default_title_color = (
            Qt.black
        )  # Title colour (set to Light mode by default)
        # self._pen_selected = QPen(QColor("#FFFFA637"), self._selected_line_thickness)
        self._pen_selected = QPen(
            QColorConstants.Svg.orange, self._selected_line_thickness
        )  # Orange
        self._title_font = QFont("Arial", self.block.scene.block_name_fontsize)

        # Internal variable for catching fatal errors, and allowing user to save work before crashing
        self.FATAL_ERROR = False

        # Methods called to:
        # * draw the title for the block
        # * check current colour mode the block should display in (Light/Dark)
        # * further initialize necessary block settings
        self.initTitle()
        self.checkMode()
        self.initUI()

        # Variable for storing whether block was moved or not
        self.wasMoved = False
        self.lastPos = self.pos()

    # -----------------------------------------------------------------------------
    def initUI(self):
        """
        This method sets flags to allow for this Block to be movable and selectable.
        """
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setAcceptHoverEvents(True)

    # -----------------------------------------------------------------------------
    def initTitle(self):
        """
        This method initializes a QGraphicsTextItem which will graphically represent
        the title (name) of this Block.
        """
        self.title_item = QGraphicsTextItem(self)
        self.title_item.setDefaultTextColor(self._default_title_color)
        self.title_item.setFont(self._title_font)

    # -----------------------------------------------------------------------------
    def titleLength(self):
        """
        This method calculates and returns the length of this Blocks' title in pixels.

        :return: the pixel length of this Blocks' title
        :rtype: int
        """

        # Using the font of the text and the block's title, determine the length of the
        # title in terms of pixels
        title_pixel_len = QFontMetrics(self._title_font).width(self.block.title)

        # As the block width is an even number (100 pixels), to center properly, the
        # width of the title must also be even
        # If title width is odd, add 1 pixel to it to make it even
        if title_pixel_len % 2 != 0:
            title_pixel_len += 1
        return title_pixel_len

    # -----------------------------------------------------------------------------
    def getTitle(self):
        """
        This method returns the current title of this Block.

        :return: Block title
        :rtype: str
        """

        return self.block.title

    # -----------------------------------------------------------------------------
    def setTitle(self):
        """
        This method updates this Blocks' graphical title to the stored title of the Block.
        """

        # Once the title has been set, this method will handle redrawing the title
        # Hence the title doesn't need to be redrawn after
        self._draw_title = False

        # Graphical title is set to the block's title is set
        self.title_item.setPlainText(self.block.title)

        # Title length is found (using self.titleLength()), and centered under the block
        self.title_item.setPos(
            (self.width - self._padding - self.titleLength()) / 2,
            self.height + self._padding,
        )

        # The GraphicsBlock instance is called to be updated
        self.update()

    # -----------------------------------------------------------------------------
    def checkMode(self):
        """
        This method checks the mode of the GraphicsScene's background (Light, Dark)
        and updates the colour mode of the pens and brushes used to paint this Block.
        """

        # If dark mode is selected, draw blocks tailored to dark mode
        # if self.mode == "Dark":
        #     self._title_color = Qt.white
        #     self._pen_default = QPen(Qt.white, self._line_thickness)
        #     self._brush_background = QBrush(Qt.white)
        # # Else light or off mode is selected (No off mode for blocks), draw blocks tailored to light mode
        # else:
        self._title_color = Qt.black
        # self._pen_default = QPen(QColor("#7F000000"), self._line_thickness)
        self._pen_default = QPen(QColorConstants.Svg.dimgrey, self._line_thickness)
        self._brush_background = QBrush(QColor("#FFE1E0E8"))

        self.title_item.setDefaultTextColor(self._title_color)

    # Todo - update code
    # -----------------------------------------------------------------------------
    def updateMode(self, value):
        """
        This method updates the mode of the Block to the provided value (should only
        ever be "Light", "Dark" or "Off").

        :param value: current mode of the GraphicsScene's background ("Light", "Dark", "Off")
        :type value: str, required
        """

        self.mode = value
        self.checkMode()
        self.update()

    # -----------------------------------------------------------------------------
    def checkBlockHeight(self):
        """
        This method checks if the current height of the Block is enough to fit all
        the Sockets that are to be drawn, while following the set socket spacing.
        It also handles the resizing of the Block (if there isn't enough space for
        all the sockets), ensuring the sockets are evenly spaced while following
        the set socket spacing.
        """

        # The offset distance from the top of the Block to the first Socket.
        # The same offset is used for from the bottom of the Block to the last Socket.
        socket_spacer = self._padding + self.edge_size + self.title_height

        # This code grabs the coordinates ([x,y]) of last input and output sockets if any exist
        if self.block.inputs:
            last_input = self.block.inputs[-1].getSocketPosition()
        else:
            last_input = [0, 0]

        if self.block.outputs:
            last_output = self.block.outputs[-1].getSocketPosition()
        else:
            last_output = [0, 0]

        # The max height of the Block could depend on either the input or output sockets
        # Hence the max height of both types are found (max height is the height at which
        # the last socket should be placed, in order for sockets to be evenly spaced)

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

        # Update the internal height of the GraphicsBlock to the updated height of the Block
        self.height = self.block.height
        self.update()

    # -----------------------------------------------------------------------------
    def hoverEnterEvent(self, event):
        """
        When a ``GraphicsBlock`` is hovered over with the cursor, this method will display
        a tooltip with the type of block underneath the mouse.
        :param event: mouse hover detected over block
        :type event: QGraphicsSceneHoverEvent
        """

        # QToolTip.setFont(QFont("Ubuntu", 10))
        self.setToolTip("<b>" + self.block.block_type + "</b> block")
        # self.setToolTip("<b>" + self.block.block_type + "</b>")

    # -----------------------------------------------------------------------------
    def boundingRect(self):
        """
        This is an inbuilt method of QGraphicsItem, that is overwritten by ``GraphicsBlock``
        which returns the area within which the GraphicsBlock can be interacted with.
        When a mouse click event is detected within this area, this will trigger logic
        that relates to a Block (that being, selecting/deselecting, moving, deleting,
        flipping or opening a parameter window).

        :return: a rectangle within which the Block can be interacted with
        :rtype: QRectF
        """

        return QRectF(0, 0, self.width, self.height)

    # -----------------------------------------------------------------------------
    def paint(self, painter, style, widget=None):
        """
        This is an inbuilt method of QGraphicsItem, that is overwritten by ``GraphicsBlock``.
        This method is automatically called by the GraphicsView Class whenever even
        a slight user-interaction is detected within the Scene.

        Before drawing, the dimensions of the Block are checked, to ensure they can
        hold all the necessary Sockets. Then the following are drawn in order:

        - the title of the block
        - the fill of the block (a rounded rectangle)
        - the outline of the block (a rounded rectangle)
        - the icon of the block (if one exists)

        :param painter: a painter (paint brush) that paints and fills the shape of this GraphicsBlock
        :type painter: QPainter, automatically recognized and overwritten from this method
        :param style: style of the painter (isn't used but must be defined)
        :type style: QStyleOptionGraphicsItem, automatically recognized from this method
        :param widget: the widget this class is being painted on (None)
        :type widget: NoneType, optional, defaults to None
        """

        try:

            # Block dimensions are checked for to ensure there's enough space for all sockets
            self.checkBlockHeight()

            # Title will be redrawn, if needed
            if self._draw_title:
                self.setTitle()

            # Background (fill) of the block is drawn
            path_content = QPainterPath()
            path_content.setFillRule(Qt.WindingFill)
            path_content.addRoundedRect(
                0, 0, self.width, self.height, self.edge_size, self.edge_size
            )
            path_content.addRect(0, self.title_height, self.edge_size, self.edge_size)
            path_content.addRect(
                self.width - self.edge_size,
                self.title_height,
                self.edge_size,
                self.edge_size,
            )
            painter.setPen(Qt.NoPen)
            painter.setBrush(self._brush_background)
            painter.drawPath(path_content.simplified())

            # Outline of the block is drawn
            path_outline = QPainterPath()
            path_outline.addRoundedRect(
                0, 0, self.width, self.height, self.edge_size, self.edge_size
            )
            painter.setPen(
                self._pen_default if not self.isSelected() else self._pen_selected
            )
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path_outline.simplified())

            # Icon of the block is drawn overtop the blocks' background
            if QtCore.QFile.exists(self.icon):
                if self.block.flipped and QtCore.QFile.exists(self.block.flipped_icon):
                    icon_image = QImage(self.block.flipped_icon)
                    # icon_item = QPixmap(self.block.flipped_icon).scaledToWidth(50) if self.block.flipped_icon else QPixmap(self.block.flipped_icon)  # Icons are scaled down to 50 pixels
                else:
                    icon_image = QImage(self.icon)
                    # icon_item = QPixmap(self.icon).scaledToWidth(50) if self.icon else QPixmap(self.icon)
                # target = QRect((self.width - icon_item.width()) / 2, (self.height - icon_item.height()) / 2, self.width, self.height)
                # source = QRect(0, 0, self.width, self.height)
                painter.drawImage(
                    QRectF(
                        (self.width - (icon_image.width()) / 5) / 2,
                        (self.height - (icon_image.height()) / 5) / 2,
                        50,
                        50,
                    ),
                    icon_image,
                )
                # painter.drawPixmap(target, icon_item, source)

        except Exception as e:
            if self.FATAL_ERROR == False:
                print(
                    "--------------------------------------------------------------------------"
                )
                print(
                    "Caught fatal exception while trying to draw blocks. Please save your work."
                )
                print(
                    "--------------------------------------------------------------------------"
                )
                traceback.print_exc(file=sys.stderr)
                self.FATAL_ERROR = True

    # -----------------------------------------------------------------------------
    def mousePressEvent(self, event):
        """
        This is an inbuilt method of QGraphicsItem, that is overwritten by
        ``GraphicsBlock`` to detect, and assign logic to a right mouse press event.

        Currently a detected mouse press event on the GraphicsBlock will select
        or deselect it.

        - If selected, the GraphicsBlock will be sent to front and will appear on
          top of other blocks.
        - Additionally, if the right mouse button is pressed and a GraphicsBlock
          is selected, a parameter window will be toggled for this Block.

        :param event: a mouse press event (Left, Middle or Right)
        :type event: QMousePressEvent, automatically recognized by the inbuilt function
        """

        # When the current GraphicsBlock is pressed on, it is sent to the front
        # of the work area (in the GraphicsScene)
        self.block.setFocusOfBlocks()

        # If the GraphicsBlock is currently selected when the right mouse button
        # is pressed, the parameter window will be toggled (On/Off)
        if event.button() == Qt.RightButton:
            self.block.toggleParamWindow()

        super().mousePressEvent(event)

    # Todo - add documentation
    # -----------------------------------------------------------------------------
    def mouseReleaseEvent(self, event):

        super().mouseReleaseEvent(event)

        # If block has been moved, update the variable within the model, to then update the
        # title of the model, to indicate that there is unsaved progress
        if self.wasMoved:
            self.wasMoved = False
            self.block.scene.has_been_modified = True
            self.block.scene.history.storeHistory("Block moved")


class GraphicsConnectorBlock(QGraphicsItem):
    """
    The ``GraphicsConnectorBlock`` Class extends the ``QGraphicsItem`` Class from PyQt5.
    This class is responsible for graphically drawing Connector Blocks within the
    GraphicsScene.
    """

    # -----------------------------------------------------------------------------
    def __init__(self, block, parent=None):
        """
        This method initializes an instance of the ``GraphicsConnectorBlock`` Class
        (otherwise known as the Graphics Class of the Connector Block).

        :param block: the Connector Block this GraphicsConnectorBlock instance relates to
        :type block: Connector Block
        :param parent: the parent widget this class instance belongs to (None)
        :type parent: NoneType, optional, defaults to None
        """

        super().__init__(parent)
        self.block = block
        self.icon = self.block.icon

        self._draw_title = False

        self.width = self.block.width
        self.height = self.block.height

        # As the connector block consists of two sockets (1 input, 1 output) which
        # use the following commands in determining where they need to be placed,
        # these commands must be included, but are set to 0 as no shape is drawn for
        # the connector block, aside from these two sockets.
        self.edge_size = 0
        self.title_height = 0
        self._padding = 0

        # Definition for the line thickness when the Connector block is selected
        # Internal padding is half this value
        # Corner rounding is by how many pixels the corners are rounded of the selected box that is drawn
        self._selected_line_thickness = 5.0
        self._internal_padding = 2.5
        self._corner_rounding = 10

        # Color of the selected line is set
        # self._pen_selected = QPen(QColor("#FFFFA637"), self._selected_line_thickness)   # Orange
        self._pen_selected = QPen(
            QColorConstants.Svg.orange, self._selected_line_thickness
        )  # Orange
        # Color of wire to be drawn between sockets, when connector block is hidden (to make solid line)
        self._color = QColor("#000000")

        # Internal variable for catching fatal errors, and allowing user to save work before crashing
        self.FATAL_ERROR = False

        # Further initialize necessary Connector Block settings
        self.initUI()
        self.wasMoved = False
        self.lastPos = self.pos()

    # -----------------------------------------------------------------------------
    def initUI(self):
        """
        This method sets flags to allow for this Connector Block to be movable and selectable.
        """

        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIsMovable)

        # When first created, the Connector block spawns highlighted
        self.setSelected(True)

    # -----------------------------------------------------------------------------
    def boundingRect(self):
        """
        This is an inbuilt method of QGraphicsItem, that is overwritten by ``GraphicsConnectorBlock``
        which returns the area within which the GraphicsConnectorBlock can be interacted with.
        When a mouse click event is detected within this area, this will trigger logic
        that relates to a Block (that being, selecting/deselecting, moving, deleting,
        flipping or opening a parameter window. Or if its Sockets are clicked on,
        this will trigger a wire to be created or ended).

        :return: a rectangle within which the Block can be interacted with
        :rtype: QRectF
        """

        W = self.width
        P = self._internal_padding
        # return QRectF(
        #     1 - W - P,
        #     1 - W - P,
        #     3 * W + P,
        #     2 * W + P
        # ).normalized()

        # Alternative selection area that is larger, but will overlap wires directly
        # one grid block step above the connector block, when the connector block is
        # selected.
        return QRectF(
            1 - 1.5 * W - P, 1 - 1.5 * W - P, 4 * W + P, 3 * W + P
        ).normalized()

    # -----------------------------------------------------------------------------
    def paint(self, painter, style, widget=None):
        """
        This is an inbuilt method of QGraphicsItem, that is overwritten by
        ``GraphicsConnectorBlock`` (otherwise referred to as the Graphics Class of
        the Connector Block. This method is automatically called by the GraphicsView
        Class whenever even a slight user-interaction is detected within the Scene.

        When the Connector Block is selected, this method will draw an orange
        outline around the Connector Block, within which it can be interacted with.

        :param painter:a painter (paint brush) that paints and fills the shape of this GraphicsConnectorBlock
        :type painter: QPainter, automatically recognized and overwritten from this method
        :param style: style of the painter (isn't used but must be defined)
        :type style: QStyleOptionGraphicsItem, automatically recognized from this method
        :param widget: the widget this class is being painted on (None)
        :type widget: NoneType, optional, defaults to None
        """
        try:
            if self.isSelected():
                # Draws orange outline around the Connector Block when it is selected
                path_outline = QPainterPath()
                # The size of the rectangle drawn, is dictated by the boundingRect (interactive area)
                path_outline.addRoundedRect(
                    self.boundingRect(), self._corner_rounding, self._corner_rounding
                )
                painter.setPen(self._pen_selected)
                painter.setBrush(Qt.NoBrush)
                painter.drawPath(path_outline.simplified())

            # If the user has chosen to hide the connector blocks, redraw the sockets to be hidden
            if self.block.scene.hide_connector_blocks:
                # Grab the [x,y] coordinates of both the input and output sockets of the
                # connector block, and create a wire path to be drawn between them
                input_pos = self.block.inputs[0].getSocketPosition()
                output_pos = self.block.outputs[0].getSocketPosition()

                multi = 1

                # If connector block is flipped, draw the wire path in the opposite direction
                if self.block.inputs[0].position == RIGHT:
                    multi = -1

                wire_path = QPainterPath(
                    QPointF(input_pos[0] + (multi * 4.5), input_pos[1])
                )
                wire_path.lineTo(output_pos[0] - (multi * 4.5), output_pos[1])

                # Set the paint brush width and colour
                wire_pen = QPen(self._color)
                wire_pen.setWidth(5)
                painter.setPen(wire_pen)
                painter.drawPath(wire_path)

        except Exception as e:
            if self.FATAL_ERROR == False:
                print(
                    "------------------------------------------------------------------------------------"
                )
                print(
                    "Caught fatal exception while trying to draw connector blocks. Please save your work."
                )
                print(
                    "------------------------------------------------------------------------------------"
                )
                traceback.print_exc(file=sys.stderr)
                self.FATAL_ERROR = True

    # -----------------------------------------------------------------------------
    def mousePressEvent(self, event):
        """
        This is an inbuilt method of QGraphicsItem, that is overwritten by
        ``GraphicsConnectorBlock`` to detect, and assign logic to a right mouse press event.

        Currently a detected mouse press event on the GraphicsConnectorBlock will
        select or deselect it.

        Additionally if selected, the GraphicsBlock will be sent to front and will
        appear on top of other blocks.

        :param event: a mouse press event (Left, Middle or Right)
        :type event: QMousePressEvent, automatically recognized by the inbuilt function
        """

        # When the current GraphicsSocketBlock is pressed on, it is sent to the front
        # of the work area (in the GraphicsScene)
        self.block.setFocusOfBlocks()

        super().mousePressEvent(event)

    # Todo - add documentation
    # -----------------------------------------------------------------------------
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

        # If block has been moved, update the variable within the model, to then update the
        # title of the model, to indicate that there is unsaved progress
        if self.wasMoved:
            self.wasMoved = False
            self.block.scene.has_been_modified = True
            self.block.scene.history.storeHistory("Connector Block moved")
