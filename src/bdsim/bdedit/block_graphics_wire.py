# Library imports
import sys
import traceback
from math import dist

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
TOP = 2
RIGHT = 3
BOTTOM = 4

# Variable for enabling/disabling debug comments
DEBUG = False
DEBUG_COORDINATES = False


# =============================================================================
#
#   Defining the GraphicsWire Class, which is inherited by all Wires and controls
#   the graphical appearance of each Wire.
#
# =============================================================================
class GraphicsWire(QGraphicsPathItem):

    # Handles for displaying cursors when trying to move wire segments
    handleHSeg1 = 0
    handleVSeg1 = 1
    handleHSeg2 = 2
    handleVSeg2 = 3
    handleHSeg3 = 4

    handleSize = +4.0

    handleCursors = {
        handleHSeg1: Qt.ArrowCursor,
        handleVSeg1: Qt.SizeHorCursor,
        handleHSeg2: Qt.SizeVerCursor,
        handleVSeg2: Qt.SizeHorCursor,
        handleHSeg3: Qt.ArrowCursor,
    }

    handleSegments = 5

    """
    The ``GraphicsWire`` Class extends the ``QGraphicsPathItem`` Class from PyQt5.
    This class is responsible for graphically drawing Wires between Sockets.

    This class takes a Wire as an input and then looks for the coordinates of the
    start and end socket defined within it. Then based on these coordinates,
    connects them with a Wire of the selected type. It is also used to redraw
    the wires when they are moved around, and if a wire is selected it will
    redraw the wire thicker and in a different colour.
    """

    # -----------------------------------------------------------------------------
    def __init__(self, wire):
        """
        This method initializes an instance of the ``GraphicsWire`` Class. It
        initially specifies the starting and ending sockets as being None, sets
        the Wire to always be drawn underneath other items within the GraphicsScene,
        and defines the colors with which the wire can be drawn.

        :param wire: the Wire Class instance this GraphicsWire relates to
        :type wire: Wire
        """

        super().__init__()

        # Dictionary for storing which mouse cursor to display when mouse hovering over
        # vertical or horizontal wire segment
        self.segment_handles = {}
        self.handleSelected = None
        self.mousePressPos = None

        self.wire = wire

        # Setting the colour, pens, and pen thickness
        self._color = QColorConstants.Svg.black
        self._color_selected = QColorConstants.Svg.orange

        # self._pen = QPen(self._color, 5, Qt.SolidLine, Qt.SquareCap, Qt.BevelJoin)
        self._pen = QPen(self._color, 5, Qt.SolidLine, Qt.SquareCap, Qt.RoundJoin)
        self._pen_selected = QPen(
            self._color_selected, 8, Qt.SolidLine, Qt.SquareCap, Qt.BevelJoin
        )

        # Initializing the start and end sockets
        self.posSource = [0, 0]
        self.posDestination = [100, 100]

        self.posSource_Orientation = None
        self.posDestination_Orientation = None

        # Method called to further intialize necessary block settings
        self.initUI()

        # Internal variables for:
        # * knowing if wire segments were moved since diagram was saved
        # * setting which routing logic to display (custom or hard-coded)
        # * catching fatal errors, and allowing user to save work before crashing
        self.wasMoved = False
        self.customlogicOverride = False
        self.FATAL_ERROR = False

    # -----------------------------------------------------------------------------
    def initUI(self):
        """
        This method sets flags to allow for this Wire to be selectable and be
        displayed at the correct z-level.
        """

        # Setting the wire to be selectable and drawn behind all items
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setFlag(QGraphicsItem.ItemIsFocusable)
        self.setAcceptHoverEvents(True)
        self.setZValue(-1)

    # -----------------------------------------------------------------------------
    def setSource(self, x, y):
        """
        This method sets the point from where the Wire will start. This is
        based on the position of the start Socket.

        :param x: x coordinate of the start Socket
        :type x: int, required
        :param y: y coordinate of the start Socket
        :type y: int, required
        """

        self.posSource = [x, y]

    # -----------------------------------------------------------------------------
    def setDestination(self, x, y):
        """
        This method sets the point of where the Wire will end. This is
        based on the position of the end Socket.

        :param x: x coordinate of the end Socket
        :type x: int, required
        :param y: y coordinate of the end Socket
        :type y: int, required
        """

        self.posDestination = [x, y]

    # -----------------------------------------------------------------------------
    def setSourceOrientation(self, orientation):
        """
        This method sets the orientation (position) of the source (start)
        Socket - in terms of where it is drawn on the block (LEFT/RIGHT) - to
        the provided orientation.

        :param orientation: where on the Block the start Socket is drawn (LEFT(1) or RIGHT(2))
        :type orientation: enumerate, required
        """

        self.posSource_Orientation = orientation

    # -----------------------------------------------------------------------------
    def setDestinationOrientation(self, orientation):
        """
        This method sets the orientation (position) of the destination (end)
        Socket - in terms of where it is drawn on the block (LEFT/RIGHT) - to
        the provided orientation.

        :param orientation: where on the Block the end Socket is drawn (LEFT(1) or RIGHT(2))
        :type orientation: enumerate, required
        """

        self.posDestination_Orientation = orientation

    # Todo add doc to describe purpose of this method (overrides the shape this drawn path takes, with custom path)
    # This method is used by PyQt to interpret the bounding box area within which this line can be interacted with
    # -----------------------------------------------------------------------------
    def shape(self):
        return self.polyPath()

    # -----------------------------------------------------------------------------
    def paint(self, painter, style, widget=None):
        """
        This is an inbuilt method of QGraphicsItem, that is overwritten by ``GraphicsWire``.
        This method is automatically called by the GraphicsView Class whenever even
        a slight user-interaction is detected within the Scene.

        It sets up the painter object and draws the line based on the path that
        will be set by the specific implementation of GraphicsWire that is
        calling paint. Then the painter will select the way the wire will be
        drawn depending on whether or not the wire is selected.

        :param painter: a painter that paints the path (line) of this GraphicsWire
        :type painter: QPainter, automatically recognized and overwritten from this method
        :param style: style of the painter (isn't used but must be defined)
        :type style: QStyleOptionGraphicsItem, automatically recognized from this method
        :param widget: the widget this class is being painted on (None)
        :type widget: NoneType, optional, Defaults to None
        """

        # Update the wire with the drawn intersection point(s)
        try:
            self.setPath(self.updatePath())
            painter.setPen(self._pen if not self.isSelected() else self._pen_selected)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(self.path())

            # if self.isSelected():
            #     painter.setRenderHint(QPainter.Antialiasing)
            #     painter.setBrush(QBrush(QColor("#FFFF4538")))
            #     painter.setPen(QPen(QColor(0, 0, 0, 255), 1.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            #     for handle, rect in self.segment_handles.items():
            #         if rect:
            #             painter.drawRect(rect)

        except Exception as e:
            if self.FATAL_ERROR == False:
                print(
                    "-------------------------------------------------------------------------"
                )
                print(
                    "Caught fatal exception while trying to draw wires. Please save your work."
                )
                print(
                    "-------------------------------------------------------------------------"
                )
                traceback.print_exc(file=sys.stderr)
                self.FATAL_ERROR = True

    # Todo - add docstring to this new method, add inline comments (makes custom polygon around drawn line)
    # -----------------------------------------------------------------------------
    def polyPath(self):
        if self.wire.wire_coordinates:
            newpolyPath = QPainterPath()

            width = 8

            self.wire_points = []
            (p1x, p1y) = self.wire.wire_coordinates[0]
            self.wire_points.append(QPointF(p1x, p1y))

            for i, (x, y) in enumerate(self.wire.wire_coordinates):
                if i == 0 or i == len(self.wire.wire_coordinates):
                    self.wire_points.append(QPointF(x, y + width))
                else:
                    self.wire_points.append(QPointF(x + width, y + width))

            for i, (x, y) in enumerate(reversed(self.wire.wire_coordinates)):
                if i == 0 or i == len(self.wire.wire_coordinates):
                    self.wire_points.append(QPointF(x, y - width))
                else:
                    self.wire_points.append(QPointF(x - width, y - width))

            poly = QPolygonF(self.wire_points)
            newpolyPath.addPolygon(poly)

            return newpolyPath
        else:
            return self.updatePath()

    # -----------------------------------------------------------------------------
    def updatePath(self):
        """
        This method is inherited and overwritten (currently) by the GraphicsWireDirect,
        GraphicsWireBezier or GraphicsWireStep classes, which dictate the pathing
        logic of the wire between the start and end socket.
        """

        raise NotImplemented("This method is to be over written by child class")

    # -----------------------------------------------------------------------------
    def updateCursorSegments(self, segments):
        """
        This method updates which mouse cursor should be displayed for each line segment of
        the wire, depending on how many wire segments there are, which is given as an input.
        :param segments: Number of line segments in this wire
        :type segments: int
        """

        # Upate cursor handles
        if segments == 5:
            self.handleCursors[self.handleHSeg1] = Qt.ArrowCursor
            self.handleCursors[self.handleVSeg1] = Qt.SizeHorCursor
            self.handleCursors[self.handleHSeg2] = Qt.SizeVerCursor
            self.handleCursors[self.handleVSeg2] = Qt.SizeHorCursor
            self.handleCursors[self.handleHSeg3] = Qt.ArrowCursor
            self.handleSegments = 5

        elif segments == 3:
            self.handleCursors = self.handleCursors.fromkeys(
                self.handleCursors.keys(), Qt.ArrowCursor
            )
            self.handleCursors[self.handleVSeg1] = Qt.SizeHorCursor
            self.handleSegments = 3

        else:
            self.handleCursors = self.handleCursors.fromkeys(
                self.handleCursors.keys(), Qt.ArrowCursor
            )
            self.handleSegments = segments

    # -----------------------------------------------------------------------------
    def updateLineSegments(self):
        """
        This method uses the coordinates of the points this wire goes through, to
        determine the coordinates that make up the horizontal and vertical line
        segments of this wire (this logic is only applicable to GraphicsWireStep).
        """

        # If the wire coordinates exist
        if self.wire.wire_coordinates:
            # Clear current horizontal and vertical segemnt lists, and clear cursor handles
            self.wire.horizontal_segments.clear()
            self.wire.vertical_segments.clear()
            self.segment_handles = self.segment_handles.fromkeys(
                self.segment_handles.keys(), None
            )

            # Find max number of segments in our line
            max_seg = len(self.wire.wire_coordinates) - 1

            # From first to 2nd last coordinate point of the wire
            for counter in range(0, max_seg):
                # Find top left and btm right points
                top_left = min(
                    (
                        self.wire.wire_coordinates[counter],
                        self.wire.wire_coordinates[counter + 1],
                    )
                )
                btm_right = max(
                    (
                        self.wire.wire_coordinates[counter],
                        self.wire.wire_coordinates[counter + 1],
                    )
                )
                s = self.handleSize

                # Line segments always alternate, from horizontal to vertical to horizontal etc.
                # Even iterations of coordinate points are always the beginning to horizontal segments
                # Append a line represented as ((x1,y2),(x2,y2)) to either horizontal or vertical line segment list
                if counter % 2 == 0:
                    # Current and next coordinates are added into the horizontal line segments list
                    self.wire.horizontal_segments.append(
                        [
                            self.wire.wire_coordinates[counter],
                            self.wire.wire_coordinates[counter + 1],
                        ]
                    )
                    # Update rectangles for horizontal segments
                    self.segment_handles[counter] = QRectF(
                        QPointF(top_left[0] + s, top_left[1] - s),
                        QPointF(btm_right[0] - s, btm_right[1] + s),
                    )

                else:
                    # Current and next coordinates are added into the vertical line segments list
                    self.wire.vertical_segments.append(
                        [
                            self.wire.wire_coordinates[counter],
                            self.wire.wire_coordinates[counter + 1],
                        ]
                    )
                    # Update rectangles for vertical segments
                    self.segment_handles[counter] = QRectF(
                        QPointF(top_left[0] - s, top_left[1] + s),
                        QPointF(btm_right[0] + s, btm_right[1] - s),
                    )

            # Upate cursor handles
            if self.handleSegments != max_seg:
                self.updateCursorSegments(max_seg)

    # -----------------------------------------------------------------------------
    def updateWireCoordinates(self, new_coordinates):
        """
        This method checks if the list of coordinate points this wire passes through,
        has changed and needs to be updated. This method reduces the computational
        resources required to otherwise re-write the list of coordinate points for
        this wire, every time a user-interaction is detected within the GraphicsView.

        :param new_coordinates: proposed coordinate points for this Wire
        :type new_coordinates: list
        """

        # Update current wire coordinates, if the new coordinates are different
        # Also update the horizontal and vertical line segments
        if new_coordinates != self.wire.wire_coordinates:
            self.wire.wire_coordinates.clear()
            self.wire.wire_coordinates = new_coordinates
            self.updateLineSegments()

            # If in DEBUG mode, this code will print the coordinates list and the
            # separated horizontal and vertical line segments of this Wire
            if DEBUG_COORDINATES:
                print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
            if DEBUG_COORDINATES:
                print("coordinates:", [self.wire.wire_coordinates])
            if DEBUG_COORDINATES:
                print("\nhorizontal lines:", [self.wire.horizontal_segments])
            if DEBUG_COORDINATES:
                print("\nvertical lines:", [self.wire.vertical_segments])
            if DEBUG_COORDINATES:
                print("\nline segments:")
            if DEBUG_COORDINATES:
                [
                    print("segment" + str(i) + ":", segment)
                    for i, segment in enumerate(self.segment_handles.items())
                ]
            if DEBUG_COORDINATES:
                print("-------------------------------------------------------")

    # -----------------------------------------------------------------------------
    def handleAt(self, point):
        """
        Returns the resize handle below the given point.
        """
        for (
            k,
            v,
        ) in self.segment_handles.items():
            if v is None:
                return None
            elif v.contains(point):
                return k
        return None

    # -----------------------------------------------------------------------------
    def hoverMoveEvent(self, moveEvent):
        """
        Executed when the mouse moves over the shape (NOT PRESSED).
        """
        if self.isSelected():
            handle = self.handleAt(moveEvent.pos())
            # print("handle:", handle)
            cursor = Qt.ArrowCursor if handle is None else self.handleCursors[handle]
            self.setCursor(cursor)
        super().hoverMoveEvent(moveEvent)

    # -----------------------------------------------------------------------------
    def hoverLeaveEvent(self, moveEvent):
        """
        Executed when the mouse leaves the shape (NOT PRESSED).
        """
        self.setCursor(Qt.ArrowCursor)
        super().hoverLeaveEvent(moveEvent)

    # -----------------------------------------------------------------------------
    def mousePressEvent(self, mouseEvent):
        """
        Executed when the mouse is pressed on the item.
        """
        self.wire.setFocusOfWire()

        self.handleSelected = self.handleAt(mouseEvent.pos())
        if self.handleSelected is not None:
            self.mousePressPos = mouseEvent.pos()
            self.mousePressRect = self.segment_handles[self.handleSelected]

        super().mousePressEvent(mouseEvent)

    # -----------------------------------------------------------------------------
    def mouseMoveEvent(self, mouseEvent):
        """
        Executed when the mouse is being moved over the item while being pressed.
        """

        if self.handleSelected is not None:
            if not self.customlogicOverride:
                self.customlogicOverride = True

            self.interactiveResize(mouseEvent.pos())
            self.wasMoved = True
            self.wire.checkIntersections()
        else:
            super().mouseMoveEvent(mouseEvent)

    # -----------------------------------------------------------------------------
    def mouseReleaseEvent(self, mouseEvent):
        """
        Executed when the mouse is released from the item.
        """
        super().mouseReleaseEvent(mouseEvent)
        self.handleSelected = None
        self.mousePressPos = None
        self.mousePressRect = None
        self.update()

        # If wire segments have been moved, update the variable within the model, to then
        # update the title of the model, to indicate that there is unsaved progress
        if self.wasMoved:
            self.wasMoved = False
            self.wire.scene.has_been_modified = True
            self.wire.scene.history.storeHistory("Wire segment moved")

    # -----------------------------------------------------------------------------
    def interactiveResize(self, mousePos):
        """
        Perform shape interactive resize.
        """
        diff = QPointF(0, 0)

        x_diff = mousePos.x() - self.mousePressPos.x()
        y_diff = mousePos.y() - self.mousePressPos.y()

        # Quantize resizing of grouping box
        spacing = 10
        x = round(x_diff / spacing) * spacing
        y = round(y_diff / spacing) * spacing

        # Calculate how far the mouse has moved from the point it was initially clicked from
        fromCenter = self.mousePressRect.center()
        toX = fromCenter.x() + x
        toY = fromCenter.y() + y

        custom_wire_coordinates = self.wire.wire_coordinates.copy()

        self.prepareGeometryChange()

        # If there are three segments, 1st and last segments cannot be moved (which are horizontally attacked to the sockets)
        # so this leaves only the vertical segment connecting them. If that segment is dragged, adjust the points accordingly.
        # If any other segments are being dragged, don't do anything
        if self.handleSegments == 3:

            if self.handleSelected == self.handleVSeg1:
                # Only 1 vertical segment in this case, so take the first vert segment [0]
                segment = self.wire.vertical_segments[0].copy()
                # Copy that segment, and add the difference the mouse has moved to the x [0] coord of the two points that make up this segment
                for i, point in enumerate(segment.copy()):
                    new_point = list(point)
                    new_point[0] = toX
                    segment[i] = tuple(new_point)
                # Override the points making up this semgent in the temporary wire_coordinates -> 2nd and 3rd points [1:3]
                custom_wire_coordinates[1:3] = segment

        # Otherwise if there are five segments, since first and last segment cannot be moved, this leaves us with 3 segments which can
        # Two vertical segments, and one horizontal segment. If any of those three are selected, adjust the points accordingly.
        elif self.handleSegments == 5:

            if self.handleSelected == self.handleHSeg2:
                # There are three horizontal segments to choose from, 1st and 3rd (last) cannot be moved, this means our segment is #2 [1].
                segment = self.wire.horizontal_segments[1].copy()
                # Copy that segment, and add the difference the mouse has moved to the y [1]) coord of the two points that make up this segment
                for i, point in enumerate(segment.copy()):
                    new_point = list(point)
                    new_point[1] = toY
                    segment[i] = tuple(new_point)
                # Override the points making up this semgent in the temporary wire_coordinates -> 3rd and 4th points [2:4]
                custom_wire_coordinates[2:4] = segment

            elif self.handleSelected in [self.handleVSeg1, self.handleVSeg2]:
                # There are two vertical segments to choose from, either can be moved as they do not attach directly to a socket.
                if self.handleSelected == self.handleVSeg1:
                    segment = self.wire.vertical_segments[0].copy()
                else:
                    segment = self.wire.vertical_segments[1].copy()
                # Copy that segment, and add the difference the mouse has moved to the x [0]) coord of the two points that make up this segment
                for i, point in enumerate(segment.copy()):
                    new_point = list(point)
                    new_point[0] = toX
                    segment[i] = tuple(new_point)
                # Override the points making up this semgent in the temporary wire_coordinates. Since we can either select the 1st or 2nd
                # vertical segment, these points correspond to 2nd and 3rd points [1:3] or the 4th and 5th points [3:5]
                if self.handleSelected == self.handleVSeg1:
                    custom_wire_coordinates[1:3] = segment
                else:
                    custom_wire_coordinates[3:5] = segment

        self.updateWireCoordinates(custom_wire_coordinates)

        self.updatePath()

    # -----------------------------------------------------------------------------
    def adjustCustomRoutingWireCoordinates(self):
        # When both blocks connected to a wire are being moved, both start and end sockets
        # that this wire is connected to will move the same amount. So we will just grab
        # the data from the start_socket.

        # Start sockets could be an input or output socket, so find its true position w.r.t its block
        start_point = (
            self.wire.start_socket.node.grBlock.pos()
            + self.wire.start_socket.grSocket.pos()
        )
        start_coords = (start_point.x(), start_point.y())

        # print("\nsocket coords:", [start_coords])
        # print("wire coords:", self.wire.wire_coordinates)

        # Wire can be drawn from either input to output socket, or output to input socket. This means
        # our start_socket can either be the first or last point in the wire.wire_coordinates list
        # Check which of these are closest to our start_socket_coords, then take the difference between those

        dist1 = dist(start_coords, self.wire.wire_coordinates[0])
        dist2 = dist(start_coords, self.wire.wire_coordinates[-1])

        # Take difference between start_socket_coords and whichever point is closest from wire.wire_coordinates
        if dist1 < dist2:
            diff = [
                start_coords[0] - self.wire.wire_coordinates[0][0],
                start_coords[1] - self.wire.wire_coordinates[0][1],
            ]
        else:
            diff = [
                start_coords[0] - self.wire.wire_coordinates[-1][0],
                start_coords[1] - self.wire.wire_coordinates[-1][1],
            ]

        # print("difference:", diff)

        # If there is a difference, then adjust the wire coordinates
        if diff == [0, 0]:
            return

        # Adjust wire.wire_coordinates by subtracting that diff from each point
        new_wire_coordinates = []
        for point in self.wire.wire_coordinates:
            new_point = (point[0] + diff[0], point[1] + diff[1])
            new_wire_coordinates.append(new_point)

        # print("old wire coords before:", self.wire.wire_coordinates)
        # print("new_wire_coords:       ", new_wire_coordinates)

        # Once points are adjusted, replace the wire.wire_coordinates list with this list
        self.updateWireCoordinates(new_wire_coordinates)
        # print("old wire coords after: ", self.wire.wire_coordinates)


class GraphicsWireDirect(GraphicsWire):
    """
    The ``GraphicsWireDirect`` Class extends the ``GraphicsWire`` Class from BdEdit.
    This class is responsible for providing a straight painter path that the
    GraphicsWire class should follow when drawing the Wire. This wire type will draw
    a straight line between two Sockets. It will take the shortest distance between
    these two points, and will go through other Blocks to do so.
    """

    # -----------------------------------------------------------------------------
    def updatePath(self):
        """
        This method creates a painter path that connects two points (start/end sockets)
        with a straight line.
        """

        # A straight line is drawn between the two provided points
        path = QPainterPath(QPointF(self.posSource[0], self.posSource[1]))
        path.lineTo(self.posDestination[0], self.posDestination[1])
        return path


class GraphicsWireBezier(GraphicsWire):
    """
    The ``GraphicsWireBezier`` Class extends the ``GraphicsWire`` Class from BdEdit.
    This class is responsible for providing a bezier painter path that the
    GraphicsWire class should follow when drawing the Wire. This wire type option
    looks good in the first direction it is drawn (e.g. left-to-right) but will not
    wrap logically when blocks are flipped or moved past each other (e.g. such that
    the wire would now be right-to-left).
    """

    # -----------------------------------------------------------------------------
    def updatePath(self):
        """
        This method creates a painter path that connects two points (start/end sockets)
        with a bezier line. This line is drawn as a cubic (think sine wave).
        """

        # The start and end coordinates are grabbed into variables s and d
        s = self.posSource
        d = self.posDestination

        # This code decides the direction the bezier should point from the start socket
        # either left or right of the start socket.
        dist = (d[0] - s[0]) * 0.5
        if s[0] > d[0]:
            dist *= -1

        # Then a cubic line is drawn between the two provided points
        path = QPainterPath(QPointF(self.posSource[0], self.posSource[1]))
        path.cubicTo(
            s[0] + dist,
            s[1],
            d[0] - dist,
            d[1] - dist,
            self.posDestination[0],
            self.posDestination[1],
        )
        return path


class GraphicsWireStep(GraphicsWire):
    """
    The ``GraphicsWireStep`` Class extends the ``GraphicsWire`` Class from BdEdit.
    This class is responsible for providing a stepped painter path that the
    GraphicsWire class should follow when drawing the Wire. This is the default wire
    style used within BdEdit, and has the most supporting logic built around it.

    This wire option draws a straight line between two sockets when the two blocks
    side by side at equal heights, are connected with a wire in the middle.

    Otherwise if the two blocks are at varying heights, a stepped line will be drawn
    from the starting socket, with 90 degree bends at each point the wire must turn
    to reach the end socket.
    """

    def updatePath(self):
        if self.customlogicOverride:

            self.adjustCustomRoutingWireCoordinates()

            # The path of the wire is set to be drawn with either
            # custom routing logic or with hard-coded routing logic
            for i, (x, y) in enumerate(self.wire.wire_coordinates):
                if i == 0:
                    path = QPainterPath(QPointF(x, y))
                elif i == len(self.wire.wire_coordinates):
                    path.lineTo(x, y)
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            return path
        else:
            return self.wireRoutingLogic()

    # -----------------------------------------------------------------------------
    def wireRoutingLogic(self):
        """
        This method creates a painter path that connects two points (start/end sockets)
        with a stepped line. This path is returned as a straight line if two blocks
        at equal heights, are connected with a wire on the inside of each of the blocks.
        Otherwise the path is returned as a stepped line with 90 degree bends at each
        point the wire must turn.

        The logic for when this wire should turn is calculated internally. Please refer
        to the technical document accompanying the BdEdit code for visual explanations
        for how this logic is determined.
        """

        try:
            # _____________________________________ Preparing Wire related variables ______________________________________

            # List into which the coordinate points of the wire will be appended into when
            # this wire is updated. This will be compared against the current list of this
            # wires' coordinates, to check if it needs to be updated
            temporary_wire_coordinates = []
            # This variable prevents a stepped wire from being drawn until it is connected
            # to the end socket. Until then a straight line will be drawn
            wire_completed = False

            # Block padding is the space at which wires will be wrapped around blocks
            block_padding = 20

            # The title height is extracted from the block this wire starts from
            title_height = self.wire.start_socket.node.grBlock.title_height - 5

            # __________________________________ Extracting Logic of Start/End Sockets ____________________________________

            # The global (scene) x,y coordinates of the source (start) and destination (end) sockets are extracted
            sx = self.posSource[0]
            sy = self.posSource[1]
            dx = self.posDestination[0]
            dy = self.posDestination[1]
            # The horizontal distance between these two sockets is found
            xDist = (dx - sx) / 2

            # The index at which the start socket is drawn on its block is extracted + 1
            # (0th index will be our first index, as this variable is used as a multiplier)
            s_index = self.wire.start_socket.index + 1

            # Dimensions of the start sockets' block are extracted
            source_block_width = self.wire.start_socket.node.width
            source_block_height = self.wire.start_socket.node.height

            # The local (in reference to its block) x-y coordinates of the start socket
            s_Offset = self.wire.start_socket.getSocketPosition()

            # Same logic (as above) is extracted for the destination (end) socket if it has been set
            if self.wire.end_socket is not None:
                d_index = self.wire.end_socket.index + 1
                destination_block_width = self.wire.end_socket.node.width
                destination_block_height = self.wire.end_socket.node.height
                d_Offset = self.wire.end_socket.getSocketPosition()
            else:
                d_index = 0
                destination_block_width = 0
                destination_block_height = 0
                d_Offset = [0, 0]

            # The previous temporary coordinates of this wire are cleared, and the new start point coordinate is added
            temporary_wire_coordinates.clear()
            temporary_wire_coordinates.append((sx, sy))

            # ###########################################  Start of Wire Logic  ##########################################

            # ======================================  If Wire hasn't been completed  =====================================
            if self.wire.end_socket is None:
                # If two sockets haven't been connected yet

                # Don't do anything, start and end points of the path have already been defined, so a straight line will be drawn
                if DEBUG:
                    print("Wire style: O")
                pass

            # =========================  Start & End Sockets are on the same side of two Blocks  =========================
            elif self.posSource_Orientation == self.posDestination_Orientation:
                # If sockets are both on the same side (both coming out of the left or right)

                # -----------------------------------  Start Socket LEFT OF End Socket  ----------------------------------
                if sx < dx:
                    # - - - - - - - - - - - - Continue with Extracted Logic of Start/End Sockets - - - - - - - - - - - - -
                    # Continue path from source
                    # Destination_block & Source_block are kept the same
                    pass

                # ------------------------------  Start Socket EQUAL or RIGHT OF End Socket  -----------------------------
                else:
                    # - - - - - - - - - - - Re-Extract Logic of Start/End Sockets (Switching them) - - - - - - - - - - - -
                    # Use the same logic as for above, but swap positions of start socket with end socket
                    sx, sy = self.posDestination[0], self.posDestination[1]
                    dx, dy = self.posSource[0], self.posSource[1]

                    # Destination_block & Source_block = node of start_socket and end_socket respectively
                    d_index = self.wire.start_socket.index + 1
                    destination_block_width = self.wire.start_socket.node.width
                    destination_block_height = self.wire.start_socket.node.height

                    # Switch the indexes of the sockets
                    if self.wire.end_socket is not None:
                        s_index = self.wire.end_socket.index + 1
                        source_block_width = self.wire.end_socket.node.width
                        source_block_height = self.wire.end_socket.node.height
                    else:
                        s_index = 0
                        source_block_width = 0
                        source_block_height = 0

                    # Restart path from destination
                    temporary_wire_coordinates.clear()
                    temporary_wire_coordinates.append((sx, sy))

                # -------------------------------  End Socket on RHS of Destination Block  -------------------------------
                if self.posDestination_Orientation == RIGHT:
                    # xDist is from RHS of source block, to LHS of destination block
                    xDist = (dx - destination_block_width - sx) / 2

                    # Top of the destination block is above source block
                    # Should be dy > sy, but graphics view draws the y-axis inverted
                    if dy - d_Offset[1] - (d_index * block_padding) < sy:

                        # Bottom of destination block is above top of source block OR
                        # LHS of destination block is further left than RHS of source block

                        # Wire from multiple sockets spaced from bottom of destination block at index (no overlap)
                        if (
                            dy
                            - d_Offset[1]
                            + destination_block_height
                            + title_height
                            + (d_index * block_padding)
                            < sy
                        ) or (sx + xDist <= sx + (block_padding / 2)):
                            if DEBUG:
                                print("Wire style: A")
                            # Draw C (inverted equivalent) line from S up to D, clipped to RHS of destination block
                            # ----------------------
                            #       (d-block)-<-|
                            #                   |
                            #  (s-block)->------|
                            # ----------------------

                            temporary_wire_coordinates.append(
                                (dx + (d_index * block_padding), sy)
                            )
                            temporary_wire_coordinates.append(
                                (dx + (d_index * block_padding), dy)
                            )

                        # Bottom of destination block is equal to or below top of source block
                        else:
                            if DEBUG:
                                print("Wire style: B")
                            # Draw wrapped line between source and destination block, then above and around destination block
                            # --------------------------------
                            #              |---------------|
                            #              |               |
                            #              |   (d-block)-<-|
                            #              |
                            #  (s-block)->-|
                            # --------------------------------

                            temporary_wire_coordinates.append((sx + xDist, sy))
                            temporary_wire_coordinates.append(
                                (
                                    sx + xDist,
                                    dy - d_Offset[1] - (d_index * block_padding),
                                )
                            )
                            temporary_wire_coordinates.append(
                                (
                                    dx + d_index * block_padding,
                                    dy - d_Offset[1] - (d_index * block_padding),
                                )
                            )
                            temporary_wire_coordinates.append(
                                (dx + d_index * block_padding, dy)
                            )

                    # Top of destination block is equal to or below source block socket
                    else:
                        if DEBUG:
                            print("Wire style: C")
                        # Draw C (inverted equivalent) line from S down to D, clipped to RHS of destination block
                        # ------------------------
                        #   (s-block)->---------|
                        #                       |
                        #           (d-block)-<-|
                        # ------------------------

                        temporary_wire_coordinates.append(
                            (dx + d_index * block_padding, sy)
                        )
                        temporary_wire_coordinates.append(
                            (dx + d_index * block_padding, dy)
                        )

                # -------------------------------  End Socket on LHS of Destination Block  -------------------------------
                else:
                    # xDist is from RHS of source block, to LHS of destination block
                    xDist = (dx - (sx + source_block_width)) / 2

                    # Should be sy > dy, but graphics view draws the y-axis inverted
                    # Top of source block is above destination block
                    if sy - s_Offset[1] - (s_index * block_padding) < dy:
                        # Bottom of source block is above top of destination block OR
                        # RHS of source block further left than LHS of destination block

                        # Wire from multiple sockets spaced from bottom of source block at index (no overlap)
                        if (
                            sy
                            - s_Offset[1]
                            + source_block_height
                            + title_height
                            + (s_index * block_padding)
                            < dy
                        ) or (dx + xDist <= dx + (block_padding / 2)):
                            if DEBUG:
                                print("Wire style: D")
                            # Draw C line from S down to D, clipped to LHS of source block
                            # ----------------------
                            #  |--<-(s-block)
                            #  |
                            #  |----->-(d-block)
                            # ----------------------

                            temporary_wire_coordinates.append(
                                (sx - (s_index * block_padding), sy)
                            )
                            temporary_wire_coordinates.append(
                                (sx - (s_index * block_padding), dy)
                            )

                        # Bottom of source block is equal to or below top of destination block
                        else:
                            if DEBUG:
                                print("Wire style: E")
                            # Draw wrapped line above and around the source block, then between the source and destination block
                            # --------------------------------
                            #  |---------------|
                            #  |               |
                            #  |-<-(s-block)   |
                            #                  |
                            #                  |->-(d-block)
                            # --------------------------------

                            temporary_wire_coordinates.append(
                                (sx - s_index * block_padding, sy)
                            )
                            temporary_wire_coordinates.append(
                                (
                                    sx - s_index * block_padding,
                                    sy - s_Offset[1] - (s_index * block_padding),
                                )
                            )
                            temporary_wire_coordinates.append(
                                (
                                    sx + source_block_width + xDist,
                                    sy - s_Offset[1] - (s_index * block_padding),
                                )
                            )
                            temporary_wire_coordinates.append(
                                (sx + source_block_width + xDist, dy)
                            )

                    # Top of source block is equal to or below destination block
                    else:
                        if DEBUG:
                            print("Wire style: F")
                        # Draw C line from S up to D, clipped to LHS of source block
                        # --------------------
                        # |------->-(d-block)
                        # |
                        # |-<-(s-block)
                        # --------------------

                        temporary_wire_coordinates.append(
                            (sx - s_index * block_padding, sy)
                        )
                        temporary_wire_coordinates.append(
                            (sx - s_index * block_padding, dy)
                        )

                # Update boolean that wire is completed, as to get here, the end point of the wire must be dropped
                wire_completed = True

            # ========================  Start & End Sockets are on opposite sides of two blocks  =========================
            elif self.posSource_Orientation != self.posDestination_Orientation:
                # Otherwise sockets are on different sides (out from left into right, or out of right into left)

                # --------------------------------  Start Socket on LHS of Source Block  ---------------------------------
                if self.posSource_Orientation == LEFT:
                    # - - - - - - - - - - - - Continue with Extracted Logic of Start/End Sockets - - - - - - - - - - - - -
                    # Continue path from source
                    # Destination_block & Source_block are kept the same
                    xDist = (sx - dx) / 2

                # --------------------------------  Start Socket on RHS of Source Block  ---------------------------------
                else:
                    # - - - - - - - - - - - Re-Extract Logic of Start/End Sockets (Switching them) - - - - - - - - - - - -
                    # Use the same logic as for above, but swap positions of start socket with end socket
                    sx, sy = self.posDestination[0], self.posDestination[1]
                    dx, dy = self.posSource[0], self.posSource[1]

                    # Destination_block & Source_block = node of start_socket and end_socket respectively
                    d_index = self.wire.start_socket.index + 1
                    destination_block_width = self.wire.start_socket.node.width
                    destination_block_height = self.wire.start_socket.node.height
                    d_Offset = self.wire.start_socket.getSocketPosition()

                    # Switch the indexes of the sockets
                    if self.wire.end_socket is not None:
                        s_index = self.wire.end_socket.index + 1
                        source_block_width = self.wire.end_socket.node.width
                        source_block_height = self.wire.end_socket.node.height
                        s_Offset = self.wire.end_socket.getSocketPosition()
                    else:
                        s_index = 0
                        source_block_width = 0
                        source_block_height = 0
                        s_Offset = [0, 0]

                    # Restart path from destination
                    temporary_wire_coordinates.clear()
                    temporary_wire_coordinates.append((sx, sy))

                # ----------------------------------  Start Socket RIGHT OF End Socket  ----------------------------------
                if sx > dx:
                    # If start socket is not on same height as end socket
                    # Otherwise a straight line will be drawn when this logic is passed through
                    if sy != dy:
                        if DEBUG:
                            print("Wire style: G")
                        # Draw normal step line
                        # ---------------------------
                        #              |-<-(s-block)
                        #              |
                        #  (d-block)-<-|
                        # ---------------------------

                        temporary_wire_coordinates.append((sx - xDist, sy))
                        temporary_wire_coordinates.append((sx - xDist, dy))

                # ------------------------------  Start Socket EQUAL or LEFT OF End Socket  ------------------------------
                else:

                    # Source block is above destination block
                    if sy - s_Offset[1] - (s_index * block_padding) < dy - d_Offset[
                        1
                    ] - (d_index * block_padding):
                        # Distance between bottom of source block and top of destination block
                        yDist = (
                            (dy - d_Offset[1])
                            - (sy - s_Offset[1] + source_block_height + title_height)
                        ) / 2

                        # Bottom of source block is above top of destination block OR
                        # --
                        if (sy - s_Offset[1] + source_block_height + title_height) < (
                            dy - d_Offset[1] - block_padding
                        ):
                            if DEBUG:
                                print("Wire style: H")
                            # Draw S line
                            #  |---<-(s-block)
                            #  |
                            #  |--------------|
                            #                 |
                            #    (d-block)-<--|
                            # ------------------

                            temporary_wire_coordinates.append(
                                (sx - (s_index * block_padding), sy)
                            )
                            temporary_wire_coordinates.append(
                                (
                                    sx - (s_index * block_padding),
                                    dy - d_Offset[1] - yDist,
                                )
                            )
                            temporary_wire_coordinates.append(
                                (
                                    dx + (d_index * block_padding),
                                    dy - d_Offset[1] - yDist,
                                )
                            )
                            temporary_wire_coordinates.append(
                                (dx + (d_index * block_padding), dy)
                            )

                        # Bottom of source block is at level with or below top of destination block
                        else:

                            # RHS of destination block is further left than RHS of source block
                            if (dx + block_padding) < (
                                sx + source_block_width + block_padding
                            ):
                                if DEBUG:
                                    print("Wire style: I")
                                # Draw line going around the top of the source block, clipped to RHS of source block + padding
                                # --------------------------------------------------
                                #     |--------------|            |--------------|
                                #     |              |            |              |
                                #     |-<-(s-block)  |     or     |-<-(s-block)  |
                                #  (d-block)-<-------|               (d-block)-<-|
                                # --------------------------------------------------

                                temporary_wire_coordinates.append(
                                    (sx - (s_index * block_padding), sy)
                                )
                                temporary_wire_coordinates.append(
                                    (
                                        sx - (s_index * block_padding),
                                        sy - s_Offset[1] - (s_index * block_padding),
                                    )
                                )
                                temporary_wire_coordinates.append(
                                    (
                                        sx
                                        + source_block_width
                                        + (s_index * block_padding),
                                        sy - s_Offset[1] - (s_index * block_padding),
                                    )
                                )
                                temporary_wire_coordinates.append(
                                    (
                                        sx
                                        + source_block_width
                                        + (s_index * block_padding),
                                        dy,
                                    )
                                )
                                # path.lineTo(sx + source_block_width + block_padding, sy - s_Offset[1] - (s_index * block_padding))
                                # path.lineTo(sx + source_block_width + block_padding, dy)

                            # RHS of destination block is equal to or right of RHS of source block
                            else:
                                if DEBUG:
                                    print("Wire style: J")
                                # Draw line going around the top of the source block, clipped to RHS of destination block + padding
                                # -------------------------------------------------------------------------
                                #  |-----------------------------|           |---------------------------|
                                #  |                             |           |                           |
                                #  |-<-(s-block)                 |    or     |-<-(s-block)   (d-block)-<-|
                                #                    (d-block)-<-|
                                # -------------------------------------------------------------------------

                                temporary_wire_coordinates.append(
                                    (sx - (s_index * block_padding), sy)
                                )
                                temporary_wire_coordinates.append(
                                    (
                                        sx - (s_index * block_padding),
                                        sy - s_Offset[1] - (s_index * block_padding),
                                    )
                                )
                                temporary_wire_coordinates.append(
                                    (
                                        dx + (d_index * block_padding),
                                        sy - s_Offset[1] - (s_index * block_padding),
                                    )
                                )
                                temporary_wire_coordinates.append(
                                    (dx + (d_index * block_padding), dy)
                                )

                    # Source block is below destination block
                    else:
                        # Distance between top of source block and bottom of destination block
                        yDist = (
                            (sy - s_Offset[1])
                            - (
                                dy
                                - d_Offset[1]
                                + destination_block_height
                                + title_height
                            )
                        ) / 2

                        # Top of source block is below bottom of destination block OR
                        # --
                        if (sy - s_Offset[1] - block_padding) > (
                            dy - d_Offset[1] + destination_block_height + title_height
                        ):
                            if DEBUG:
                                print("Wire style: K")
                            # Draw Z line
                            # -----------------------
                            #        (d-block)-<--|
                            #                     |
                            #  |------------------|
                            #  |
                            #  |-<-(s-block)
                            # -----------------------

                            temporary_wire_coordinates.append(
                                (sx - (s_index * block_padding), sy)
                            )
                            temporary_wire_coordinates.append(
                                (
                                    sx - (s_index * block_padding),
                                    sy - yDist - s_Offset[1],
                                )
                            )
                            temporary_wire_coordinates.append(
                                (
                                    dx + (s_index * block_padding),
                                    sy - yDist - s_Offset[1],
                                )
                            )
                            temporary_wire_coordinates.append(
                                (dx + (s_index * block_padding), dy)
                            )

                        # Top of source block is at level with or above bottom of destination block
                        else:

                            # LHS of destination is further left than LHS of source block
                            if (dx - destination_block_width - block_padding) < (
                                sx - block_padding
                            ):
                                if DEBUG:
                                    print("Wire style: L")
                                # Draw line going around the top of the destination block, clipped to the LHS of destination block minus padding
                                # ------------------------
                                #  |--------------|
                                #  |              |
                                #  |  (d-block)-<-|
                                #  |
                                #  |----------<-(s-block)
                                # ------------------------

                                temporary_wire_coordinates.append(
                                    (
                                        dx
                                        - destination_block_width
                                        - (s_index * block_padding),
                                        sy,
                                    )
                                )
                                temporary_wire_coordinates.append(
                                    (
                                        dx
                                        - destination_block_width
                                        - (s_index * block_padding),
                                        dy - d_Offset[1] - (d_index * block_padding),
                                    )
                                )
                                temporary_wire_coordinates.append(
                                    (
                                        dx + d_index * block_padding,
                                        dy - d_Offset[1] - (d_index * block_padding),
                                    )
                                )
                                temporary_wire_coordinates.append(
                                    (dx + d_index * block_padding, dy)
                                )

                            # LHS of destination is equal to or right of LHS of source block
                            else:
                                if DEBUG:
                                    print("Wire style: M")
                                # Draw line going around the top of the destination block, clipped to the LHS of source block minus padding
                                # ----------------------
                                #  |----------------|
                                #  |                |
                                #  |    (d-block)-<-|
                                #  |
                                #  |-<-(s-block)
                                # ----------------------

                                temporary_wire_coordinates.append(
                                    (sx - s_index * block_padding, sy)
                                )
                                temporary_wire_coordinates.append(
                                    (
                                        sx - s_index * block_padding,
                                        dy - d_Offset[1] - (d_index * block_padding),
                                    )
                                )
                                temporary_wire_coordinates.append(
                                    (
                                        dx + d_index * block_padding,
                                        dy - d_Offset[1] - (d_index * block_padding),
                                    )
                                )
                                temporary_wire_coordinates.append(
                                    (dx + d_index * block_padding, dy)
                                )

                # Update boolean that wire is completed, as to get here, the end point of the wire must be dropped
                wire_completed = True

            # ############################################  End of Wire Logic  ###########################################

            # Finally the Wire is finished, by connecting the path to the destination (end) Socket coordinates
            # that coordinate is also added as the final coordinate point of the wire to the temporary coordinates list
            temporary_wire_coordinates.append((dx, dy))

            # The path of the wire is set to be drawn under the path logic that has just been calculated
            for i, (x, y) in enumerate(temporary_wire_coordinates):
                if i == 0:
                    path = QPainterPath(QPointF(x, y))
                elif i == len(temporary_wire_coordinates):
                    path.lineTo(x, y)
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)

            # If the wire has been dropped on a destination socket (and is not being dragged around), update its coordinates
            if wire_completed:
                self.updateWireCoordinates(temporary_wire_coordinates)
            return path
        except Exception as e:
            if self.FATAL_ERROR == False:
                print(
                    "------------------------------------------------------------------------------------"
                )
                print(
                    "Caught fatal exception while trying to calculate wire bends. Please save your work."
                )
                print(
                    "------------------------------------------------------------------------------------"
                )
                traceback.print_exc(file=sys.stderr)
                self.FATAL_ERROR = True
