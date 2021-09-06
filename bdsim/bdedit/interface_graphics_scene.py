# Library imports
import math

# PyQt5 imports
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *


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

        # Set the default background color for when no grid lines are drawn
        # Currently set to same color as the background for Light mode
        # self._default_background_color = QColor("#E0E0E0")
        # Alternatively could be set to a plain white background
        self._default_background_color = QColor("#FFFFFF")

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
        self.setSceneRect(-width//2, -height//2, width, height)

    # -----------------------------------------------------------------------------
    def updateMode(self, value):
        """
        This method toggles the background mode for the GraphicsScene.
        When background is True [default] background is grey with grid lines.
        When background is False, background is white without grid lines.

        :param value: the boolean value to keep or disable background (True/False)
        :type value: bool, required
        """

        # Set the mode of the background and update the GraphicsScene
        self.mode = value
        self.update()

    # -----------------------------------------------------------------------------
    def checkMode(self):
        """
        This method updates the colors used for painting the background of the ``GraphicsScene``.
        """

        if self.mode == False:
            self._color_background = QColor("#E0E0E0")      # Light gray
            self._color_light = QColor("#D1D1D1")           # Darker gray
            self._color_dark = QColor("#C0C0C0")            # Dark gray
        # elif self.mode == 'Dark':
        #     self._color_background = QColor("#999999")      # Darker gray
        #     self._color_light = QColor("#808080")           # Dark gray
        #     self._color_dark = QColor("#606060")            # Very dark gray
        elif self.mode == True:
            self._color_background = self._default_background_color     # Light gray

        # Set the line thickness of the smaller, then larger grid squares
        self._pen_light = QPen(self._color_light)
        self._pen_light.setWidth(1)
        self._pen_dark = QPen(self._color_dark)
        self._pen_dark.setWidth(2)
        # Set the background fill color
        self.setBackgroundBrush(self._color_background)

    # -----------------------------------------------------------------------------
    def mouseMoveEvent(self, event):
        """
        This is an inbuilt method of QGraphicsScene, that is overwritten by ``GraphicsScene``
        to update the start-end points of where the wires are drawn to, as items
        are moved around within the GraphicsScene.

        :param event: a mouse movement event that has occurred with this GraphicsScene
        :type event: QMouseEvent, automatically recognized by the inbuilt function
        """
        # Passes on the mouseMoveEvent so that this method wouldn't block any
        # mouse movement logic in other classes
        super().mouseMoveEvent(event)

        # Updates the start-end points of each Wire that is connected to any Block
        for block in self.scene.blocks:
            if block.grBlock.isSelected():
                block.updateConnectedEdges()

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
                    painter.setPen(QPen(self._color_background))
                    painter.setBrush(QBrush(self._color_background))
                    # painter.setRenderHint(QPainter.Antialiasing, False)
                    # painter.setRenderHint(QPainter.Antialiasing, True)

                    # Paint each intersection point
                    for intersection_point in self.scene.intersection_list:
                        x = intersection_point[0]
                        y = intersection_point[1]
                        # Paint a 16x16 rectangle
                        painter.drawRect(x-8, y-8, 16, 16)

                    # Set the paintbrush color and width for redrawing a portion of the wire
                    pen = QPen(QColor("#000000"))
                    pen.setWidth(5)
                    painter.setPen(pen)

                    # Go through each intersection point and paint back the horizontal lines
                    for intersection_point in self.scene.intersection_list:
                        x = intersection_point[0]
                        y = intersection_point[1]

                        # line_segement_path = QPainterPath(QPointF(x + 6.5, y))
                        # line_segement_path.lineTo(x - 6.5, y)

                        line_segement_path = QPainterPath(QPointF(x + 6.5, y))
                        line_segement_path.lineTo(x - 6.5, y)

                        painter.drawPath(line_segement_path)

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
            try: painter.drawLines(*lines_light)
            except TypeError: painter.drawLines(lines_light)

            # Draw lines for the larger grid squares
            painter.setPen(self._pen_dark)
            try: painter.drawLines(*lines_dark)
            except TypeError: painter.drawLines(lines_dark)
