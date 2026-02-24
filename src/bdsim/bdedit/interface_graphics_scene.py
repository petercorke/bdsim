# Library imports
import math

# PyQt5 imports
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtSvg import *

# BdEdit imports
from bdsim.bdedit.Icons import *


# =============================================================================
#
#   Defining the GraphicsScene Class, which mainly controls the background and
#   foreground of the canvas within the Scene.
#
# =============================================================================
class GraphicsScene(QGraphicsScene):
    """
    The ``GraphicsScene`` Class extends the ``QGraphicsScene`` Class from PyQt5,
    and controls the basic appearance of the ``Scene`` it belongs to. The things
    it controls include its background, and foreground.
    """

    # -----------------------------------------------------------------------------
    def __init__(self, scene, parent=None):
        """
        This method creates an ``QGraphicsScene`` instance and associates it to this
        ``GraphicsScene`` instance. The GraphicsScene dictates how all items
        within the Scene are visually represented.

        :param scene: the ``Scene`` to which this ``GraphicsScene`` belongs to
        :type scene: Scene, required
        :param parent: the parent widget this GraphicsScene belongs to (should be None)
        :type parent: None, optional
        """
        super().__init__(parent)

        # The Scene this GraphicsScene belongs to, is assigned to an internal variable
        self.scene = scene

        # Grid settings are defined for the spacing of the smaller grid squares (20 px)
        # and how many smaller grid squares fit into a larger grid square (5)
        self.gridSize = 20
        self.gridSquares = 5

        # Set the default background mode of the Scene
        self.mode = False
        # Set the wire overlaps to not being detected by default
        self.enable_intersections = True
        self.mousePressed = False

        # Set the default background color for when no grid lines are drawn
        # Currently set to same color as the background for Light mode
        # self._default_background_color = QColor("#E0E0E0")
        # Alternatively could be set to a plain white background
        self._default_background_color = QColor("#FFFFFF")

        # Set the image used for separating wires at points of overlap
        self.overlap_image_renderer = QSvgRenderer(
            ":/Icons_Reference/Icons/overlap.svg"
        )

    # -----------------------------------------------------------------------------
    def setGrScene(self, width, height):
        """
        This method sets the dimensions of the ``GraphicsScene``.

        :param width: width of the GraphicsScene
        :type width: int, required
        :param height: height of the GraphicsScene
        :type height: int, required
        """

        # Set this way so that the (0,0) coordinate would be in the center
        # of the scene.
        self.setSceneRect(-width // 2, -height // 2, width, height)

    # -----------------------------------------------------------------------------
    def updateBackgroundMode(self, bgcolor, grid):
        """Set the background color and grid status for the GraphicsScene.

        :param bgcolor: the background color
        :type bgcolor: str, required
        :param grid: grid drawn
        :type grid: bool, required
        """

        # Set the mode of the background and update the GraphicsScene
        self.bgcolor = bgcolor
        self.grid = grid
        self.update()

    # -----------------------------------------------------------------------------
    def checkMode(self):
        """
        This method updates the colors used for painting the background of the ``GraphicsScene``.
        """
        if self.bgcolor == "white":
            self._color_background = QColorConstants.Svg.white
        elif self.bgcolor == "grey":
            self._color_background = QColor("#E0E0E0")  # Light gray
        else:
            raise ValueError(f"bad color {self.bgcolor}")

        if self.grid is True:
            # set color of major and minor grid lines
            self._color_light = QColorConstants.Svg.lightgray
            self._color_dark = QColorConstants.Svg.silver
        elif self.grid is False:
            # no grid, major and minor grid lines are background color
            self._color_light = self._color_background
            self._color_dark = self._color_background

        # if self.mode == False:
        #     self._color_background = QColor("#E0E0E0")          # Light gray
        #     self._color_light = QColorConstants.Svg.lightgray
        #     self._color_dark = QColorConstants.Svg.silver
        # elif self.mode == True:
        #     self._color_background = self._default_background_color     # Light gray

        # Set the line thickness of the smaller, then larger grid squares
        self._pen_light = QPen(self._color_light)
        self._pen_light.setWidth(1)
        self._pen_dark = QPen(self._color_dark)
        self._pen_dark.setWidth(2)
        # Set the background fill color
        self.setBackgroundBrush(self._color_background)

    def mousePressEvent(self, event):
        # If the mouse is pressed, an internal variable is set to True
        super().mousePressEvent(event)
        self.mousePressed = True

    def mouseReleaseEvent(self, event):
        # If mouse is released, the internal variable is set to False
        super().mouseReleaseEvent(event)
        self.mousePressed = False

    # -----------------------------------------------------------------------------
    def mouseMoveEvent(self, event):
        """
        This is an inbuilt method of QGraphicsScene, that is overwritten by ``GraphicsScene``.
        It handles the movement related logic for items selected within the ``GraphicsScene``.

        Currently, generic movement logic is applied to instances of the following classes:
        blocks, floating labels, and grouping boxes

        This genermic movement logic consists of the following being applied on mouse movement:

        - a detected mouse move event on selected item will enforce grid-snapping (making it
          move only in increments matching the size of the smaller grid squares in the background).

        - the selected item will be prevented from moving outside the maximum zoomed out border
          of the work area (the GraphicsScene).

        - additioanlly only applies if the selected item is a block:
          * the locations of its sockets, and that of other connected blocks,
            are updated as the block moves around.
          * Additionally, block movements can be relevant to wire routing when they are
            in custom routing mode, so this logic is checked as blocks are moved.
          * Finally, moving a block will affect where wires may overlap,
            so this logic is updated as the blocks are moved.

        - additionally only applies if the selected item is a floating text label:
          * floating labels have the ability of being moved closer to wires and blocks,
            so their grid-snapping is enforced to 5 pixels instead of the typical 20 pixels
            like for all other items.

        - finally, if an item's position within the ``GraphicsScene`` has visually been updated,
          an internal will reflect that the item has moved, to then indicate unsaved changes and
          record a new snapshop of the scene's history.

        :param event: a mouse movement event that has occurred with this GraphicsScene
        :type event: QMouseEvent, automatically recognized by the inbuilt function
        """

        def borderRestriction(item, padding):
            if hasattr(item, "block"):
                item_width = item.width
                item_height = item.height
                item_title = item.title_height
            elif hasattr(item, "floating_label"):
                item_width = item.floating_label.width
                item_height = item.floating_label.height
                item_title = 0
            elif hasattr(item, "grouping_box"):
                item_width = item.grouping_box.width
                item_height = item.grouping_box.height
                item_title = 0

            # left
            if item.pos().x() < item.scene().sceneRect().x() + padding:
                item.setPos(item.scene().sceneRect().x() + padding, item.pos().y())

            # top
            if item.pos().y() < item.scene().sceneRect().y() + padding:
                item.setPos(item.pos().x(), item.scene().sceneRect().y() + padding)

            # right
            if item.pos().x() > (
                item.scene().sceneRect().x()
                + item.scene().sceneRect().width()
                - item_width
                - padding
            ):
                item.setPos(
                    item.scene().sceneRect().x()
                    + item.scene().sceneRect().width()
                    - item_width
                    - padding,
                    item.pos().y(),
                )

            # bottom
            if item.pos().y() > (
                item.scene().sceneRect().y()
                + item.scene().sceneRect().height()
                - item_height
                - item_title
                - padding
            ):
                item.setPos(
                    item.pos().x(),
                    item.scene().sceneRect().y()
                    + item.scene().sceneRect().height()
                    - item_height
                    - item_title
                    - padding,
                )

        super().mouseMoveEvent(event)

        if self.mousePressed:

            # For all moveable items which are selected, update their mouseMove related methods
            for item in self.selectedItems():

                # Padding of 20 pixelsis used for how close the item can come up to the border of the scene
                padding = 20

                # The x,y position of the mouse cursor is grabbed, and is restricted to update
                # every 20 pixels (the size of the smaller grid squares, as defined in GraphicsScene)
                x = round(item.pos().x() / padding) * padding
                y = round(item.pos().y() / padding) * padding
                pos = QPointF(x, y)

                # For blocks:
                if hasattr(item, "block"):
                    # The position of this GraphicsBlock is set to the restricted position of the mouse cursor
                    item.setPos(pos)

                    borderRestriction(item, padding)

                    # Update the connected wires of all Blocks that are affected by this Block being moved
                    item.block.updateConnectedEdges()

                    # Since block was moved, update the wires connected to its input & output
                    # sockets to route the wires using the inbuilt hardcoded logic
                    item.block.updateWireRoutingLogic()

                    # If there are wires within the Scene
                    if self.scene.wires:
                        # Call the first wire in the Scene to check the intersections
                        # Calling the first wire will still check intersection points
                        # of all wires, however since that code is located within the
                        # Wire class, this is how it's accessed.
                        self.scene.wires[0].checkIntersections()

                # For floating text labels:
                elif hasattr(item, "floating_label"):
                    padding = 5
                    x = round(item.pos().x() / padding) * padding
                    y = round(item.pos().y() / padding) * padding
                    pos = QPointF(x, y)

                    # The position of this GraphicsFloatingLabel is set to the restricted position of the mouse cursor
                    item.setPos(pos)
                    borderRestriction(item, padding)

                # For grouping boxes:
                elif hasattr(item, "grouping_box"):
                    # The position of this GraphicsGroupingBox is set to the restricted position of the mouse cursor
                    item.setPos(pos)
                    borderRestriction(item, padding)

                # If selected item is of any block type, floating text label or grouping box, and
                if (
                    hasattr(item, "block")
                    or hasattr(item, "floating_label")
                    or hasattr(item, "grouping_box")
                ):
                    # If the above rounding has rounded to a new value, and the block has actually "moved" in the scene, updated variable to reflect that
                    if pos != item.lastPos:
                        item.lastPos = item.pos()
                        item.wasMoved = True

    # -----------------------------------------------------------------------------
    def drawForeground(self, painter, rect):
        """
        This is an inbuilt method of QGraphicsScene, that is overwritten by ``GraphicsScene``
        to draw additional logic for intersection points between wires. This logic is drawn
        overtop of all other items within the GraphicsScene apart from Blocks. Intersection
        points are drawn as a circle (same fill color as the background) to create a
        separation between the wires, then redraws a vertical section of the wire overtop.

        :param painter: a painter (paint brush) that paints the foreground of this GraphicsScene
        :type painter: QPainter, automatically recognized and overwritten from this method
        :param rect: a rectangle that defines the dimensions of this GraphicsScene
        :type rect: QRect, automatically recognized by the inbuilt function
        """
        # Passes on the drawForeground so that this method wouldn't block any
        # foreground drawing logic in other classes
        super().drawForeground(painter, rect)

        # If user has enabled intersections detection
        if self.enable_intersections:

            # Check first if any wires are present in the scene
            if self.scene.wires:

                # If there are intersection points to draw
                if self.scene.intersection_list:

                    # Check the current colour mode of the scene and set the pen to that colour
                    self.checkMode()
                    painter.setPen(Qt.NoPen)
                    # painter.setBrush(QBrush(self._color_background))

                    # Paint each intersection point
                    for intersection_point in self.scene.intersection_list:
                        painter.setBrush(QBrush(self._color_background))
                        x = intersection_point[0]
                        y = intersection_point[1]

                        # Prepare an overlap rectangle to "white-out" the wires underneath
                        rect = QRectF(x - 7, y - 7.6, 21, 15.2)
                        painter.drawRect(rect)
                        # painter.drawRect(x-7, y-6, 21, 12)

                        # If there are grouping boxes present in the scene
                        if self.scene.grouping_boxes:

                            # Find which grouping boxes, if any, this rectangle overlaps
                            for box in self.scene.grouping_boxes:
                                # Grab QPath of the current location of this grouping box within the scene
                                gbox_location = box.grGBox.mapToScene(box.grGBox.rect())

                                # Find the intersecting area between the overlapping rect and this grouping box, if there is one
                                intersecting = self.findIntersectingAreaPoints(
                                    gbox_location.boundingRect(), rect
                                )

                                # If an overlap was found, an intersecting rect will be provided, else False
                                if intersecting:
                                    painter.setBrush(QBrush(box.grGBox.bg_color))
                                    painter.drawRect(intersecting)

                        # Paint an image over the intersection point
                        self.overlap_image_renderer.render(
                            painter, QRectF(x - 7.2, y - 8, 17, 16)
                        )

            # Else, if no wires in scene, clear intersection_list
            else:
                self.scene.intersection_list.clear()

    # -----------------------------------------------------------------------------
    def drawBackground(self, painter, rect):
        """
        This is an inbuilt method of QGraphicsScene, that is overwritten by
        ``GraphicsScene`` to draw a grid background, or a plain background,
        depending on what grid mode is chosen. This background is drawn behind
        all other items within the GraphicsScene.

        :param painter: a painter (paint brush) that paints the background of this GraphicsScene
        :type painter: QPainter, automatically recognized and overwritten from this method
        :param rect: a rectangle that defines the dimensions of this GraphicsScene
        :type rect: QRect, automatically recognized by the inbuilt function
        """
        # Passes on the drawBackground so that this method wouldn't block any
        # background drawing logic in other classes
        super().drawBackground(painter, rect)

        # Check the grid_mode the user has chosen (Light by default)
        self.checkMode()

        # If the grid_mode is not "Off", we want to draw grid lines,
        # so continue with the following logic
        if self.mode == False:
            # Here we create our grid
            left = int(math.floor(rect.left()))
            right = int(math.ceil(rect.right()))
            top = int(math.floor(rect.top()))
            bottom = int(math.ceil(rect.bottom()))

            first_left = left - (left % self.gridSize)
            first_top = top - (top % self.gridSize)

            # Compute all lines to be drawn
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

            # Draw lines for the smaller grid squares
            painter.setPen(self._pen_light)
            try:
                painter.drawLines(*lines_light)
            except TypeError:
                painter.drawLines(lines_light)

            # Draw lines for the larger grid squares
            painter.setPen(self._pen_dark)
            try:
                painter.drawLines(*lines_dark)
            except TypeError:
                painter.drawLines(lines_dark)

    # -----------------------------------------------------------------------------
    def findIntersectingAreaPoints(self, rectA, rectB):
        """
        This method takes in two QRectF's and finds the union area of overlap between
        these two rects, as well as the points which make up the overlapping rectangle.
        :param rectA: rectangle one (representing the grouping box)
        :type rectA: QRectF
        :param rectB: rectangle two (representing the wire overlap box)
        :type rectB: QRectF
        :return: a rectangle representing the intersection between the two given rectangles
        :rtype: QRectF
        """
        x1 = max(rectA.left(), rectB.left())
        y1 = max(rectA.top(), rectB.top())
        x2 = min(rectA.right(), rectB.right())
        y2 = min(rectA.bottom(), rectB.bottom())

        # If the area of the intersecting rectangle is greater than 0
        if (max(0, x2 - x1) * max(0, y2 - y1)) > 0:
            # Make a new QRectF representing the intersection
            return QRectF(x1, y1, (max(0, x2 - x1)), (max(0, y2 - y1)))
        else:
            # Otherwise return False
            return False
