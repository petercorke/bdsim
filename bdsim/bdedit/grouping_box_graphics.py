# PyQt5 imports
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *


# Majority of this code has been adapted from: https://stackoverflow.com/a/34442054

class GraphicsGBox(QGraphicsRectItem):

    handleTopLeft = 1
    handleTopMiddle = 2
    handleTopRight = 3
    handleMiddleLeft = 4
    handleMiddleRight = 5
    handleBottomLeft = 6
    handleBottomMiddle = 7
    handleBottomRight = 8

    handleSize = +8.0
    handleSpace = -4.0

    handleCursors = {
        handleTopLeft: Qt.SizeFDiagCursor,
        handleTopMiddle: Qt.SizeVerCursor,
        handleTopRight: Qt.SizeBDiagCursor,
        handleMiddleLeft: Qt.SizeHorCursor,
        handleMiddleRight: Qt.SizeHorCursor,
        handleBottomLeft: Qt.SizeBDiagCursor,
        handleBottomMiddle: Qt.SizeVerCursor,
        handleBottomRight: Qt.SizeFDiagCursor,
    }

    # -----------------------------------------------------------------------------
    def __init__(self, gbox, *args):

        super().__init__(*args)
        # Handles dictionary and variables to manage cursors
        self.handles = {}
        self.handleSelected = None
        self.mousePressPos = None
        self.mousePressRect = None

        # Inherit properties from parent grouping box
        self.grouping_box = gbox
        self.width = self.grouping_box.width
        self.height = self.grouping_box.height

        # Pen thickness and block-related spacings are defined
        self._line_thickness = 3.0  # Thickness of the block outline by default
        self._selected_line_thickness = 5.0  # Thickness of the block outline on selection

        # Colours for pens are defined
        self._pen_selected = QPen(QColor("#FFFFA637"), self._selected_line_thickness, Qt.SolidLine)
        self.bg_color = self.grouping_box.background_color
        self.br_color = self.grouping_box.border_coler

        # Internal variable for catching fatal errors, and allowing user to save work before crashing
        self.FATAL_ERROR = False

        # Method called to further initialize necessary block settings
        self.initUI()
        self.wasMoved = False

    # -----------------------------------------------------------------------------
    def initUI(self):
        """
        This method sets flags to allow for this Block to be movable and selectable.
        """
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setFlag(QGraphicsItem.ItemIsFocusable)
        self.setAcceptHoverEvents(True)
        self.updateHandlesPos()
        self.setZValue(-11)

    def handleAt(self, point):
        """
        Returns the resize handle below the given point.
        """
        for k, v, in self.handles.items():
            if v.contains(point):
                return k
        return None

    def hoverMoveEvent(self, moveEvent):
        """
        Executed when the mouse moves over the shape (NOT PRESSED).
        """
        if self.isSelected():
            handle = self.handleAt(moveEvent.pos())
            cursor = Qt.ArrowCursor if handle is None else self.handleCursors[handle]
            self.setCursor(cursor)
        super().hoverMoveEvent(moveEvent)

    def hoverLeaveEvent(self, moveEvent):
        """
        Executed when the mouse leaves the shape (NOT PRESSED).
        """
        self.setCursor(Qt.ArrowCursor)
        super().hoverLeaveEvent(moveEvent)

    def mousePressEvent(self, mouseEvent):
        """
        Executed when the mouse is pressed on the item.
        """
        self.grouping_box.setFocusOfGroupingBox()

        self.handleSelected = self.handleAt(mouseEvent.pos())
        if self.handleSelected:
            self.mousePressPos = mouseEvent.pos()
            self.mousePressRect = self.boundingRect()

        # If the right mouse button is pressed, bring up a QColorDialog
        if mouseEvent.button() == Qt.RightButton:
            color = QColorDialog.getColor()

            if color.isValid():
                # Set alpha value of chosen color, to half transparency
                color.setAlpha(127)

                self.bg_color = color

        super().mousePressEvent(mouseEvent)

    def mouseMoveEvent(self, mouseEvent):
        """
        Executed when the mouse is being moved over the item while being pressed.
        """

        if self.handleSelected is not None:
            self.interactiveResize(mouseEvent.pos())
        else:
            super().mouseMoveEvent(mouseEvent)

        self.quantizeMovement()

    def mouseReleaseEvent(self, mouseEvent):
        """
        Executed when the mouse is released from the item.
        """
        super().mouseReleaseEvent(mouseEvent)
        self.handleSelected = None
        self.mousePressPos = None
        self.mousePressRect = None
        self.update()

        # If grouping box has been moved, update the variable within the model, to then update the
        # title of the model, to indicate that there is unsaved progress
        if self.wasMoved:
            self.wasMoved = False
            self.grouping_box.scene.has_been_modified = True

    def boundingRect(self):
        """
        Returns the bounding rect of the shape (including the resize handles).
        """
        o = self.handleSize + self.handleSpace
        return self.rect().adjusted(-o, -o, o, o)

    def updateHandlesPos(self):
        """
        Update current resize handles according to the shape size and position.
        """
        s = self.handleSize
        b = self.boundingRect()
        self.handles[self.handleTopLeft] = QRectF(b.left(), b.top(), s, s)
        self.handles[self.handleTopMiddle] = QRectF(b.center().x() - s / 2, b.top(), s, s)
        self.handles[self.handleTopRight] = QRectF(b.right() - s, b.top(), s, s)
        self.handles[self.handleMiddleLeft] = QRectF(b.left(), b.center().y() - s / 2, s, s)
        self.handles[self.handleMiddleRight] = QRectF(b.right() - s, b.center().y() - s / 2, s, s)
        self.handles[self.handleBottomLeft] = QRectF(b.left(), b.bottom() - s, s, s)
        self.handles[self.handleBottomMiddle] = QRectF(b.center().x() - s / 2, b.bottom() - s, s, s)
        self.handles[self.handleBottomRight] = QRectF(b.right() - s, b.bottom() - s, s, s)

    def interactiveResize(self, mousePos):
        """
        Perform shape interactive resize.
        """
        offset = self.handleSize + self.handleSpace
        boundingRect = self.boundingRect()
        rect = self.rect()
        diff = QPointF(0, 0)

        # Quantize resizing of grouping box
        spacing = 20

        x_diff = mousePos.x() - self.mousePressPos.x()
        y_diff = mousePos.y() - self.mousePressPos.y()

        x = round(x_diff / spacing) * spacing
        y = round(y_diff / spacing) * spacing

        self.prepareGeometryChange()

        if self.handleSelected == self.handleTopLeft:

            fromX = self.mousePressRect.left()
            fromY = self.mousePressRect.top()
            toX = fromX + x
            toY = fromY + y
            diff.setX(toX - fromX)
            diff.setY(toY - fromY)
            boundingRect.setLeft(toX)
            boundingRect.setTop(toY)
            rect.setLeft(boundingRect.left() + offset)
            rect.setTop(boundingRect.top() + offset)

        elif self.handleSelected == self.handleTopMiddle:

            fromY = self.mousePressRect.top()
            toY = fromY + y
            diff.setY(toY - fromY)
            boundingRect.setTop(toY)
            rect.setTop(boundingRect.top() + offset)

        elif self.handleSelected == self.handleTopRight:

            fromX = self.mousePressRect.right()
            fromY = self.mousePressRect.top()
            toX = fromX + x
            toY = fromY + y
            diff.setX(toX - fromX)
            diff.setY(toY - fromY)
            boundingRect.setRight(toX)
            boundingRect.setTop(toY)
            rect.setRight(boundingRect.right() - offset)
            rect.setTop(boundingRect.top() + offset)

        elif self.handleSelected == self.handleMiddleLeft:

            fromX = self.mousePressRect.left()
            toX = fromX + x
            diff.setX(toX - fromX)
            boundingRect.setLeft(toX)
            rect.setLeft(boundingRect.left() + offset)

        elif self.handleSelected == self.handleMiddleRight:
            fromX = self.mousePressRect.right()
            toX = fromX + x
            diff.setX(toX - fromX)
            boundingRect.setRight(toX)
            rect.setRight(boundingRect.right() - offset)

        elif self.handleSelected == self.handleBottomLeft:

            fromX = self.mousePressRect.left()
            fromY = self.mousePressRect.bottom()
            toX = fromX + x
            toY = fromY + y
            diff.setX(toX - fromX)
            diff.setY(toY - fromY)
            boundingRect.setLeft(toX)
            boundingRect.setBottom(toY)
            rect.setLeft(boundingRect.left() + offset)
            rect.setBottom(boundingRect.bottom() - offset)

        elif self.handleSelected == self.handleBottomMiddle:

            fromY = self.mousePressRect.bottom()
            toY = fromY + y
            diff.setY(toY - fromY)
            boundingRect.setBottom(toY)
            rect.setBottom(boundingRect.bottom() - offset)

        elif self.handleSelected == self.handleBottomRight:

            fromX = self.mousePressRect.right()
            fromY = self.mousePressRect.bottom()
            toX = fromX + x
            toY = fromY + y
            diff.setX(toX - fromX)
            diff.setY(toY - fromY)
            boundingRect.setRight(toX)
            boundingRect.setBottom(toY)
            rect.setRight(boundingRect.right() - offset)
            rect.setBottom(boundingRect.bottom() - offset)

        # Finally, check if rectangle has been dragged inside out
        if rect.width() < spacing:
            if self.handleSelected in [self.handleTopLeft, self.handleMiddleLeft, self.handleBottomLeft]:
                rect.setLeft(rect.right() - spacing)
            else:
                rect.setRight(rect.left() + spacing)
        if rect.height() < spacing:
            if self.handleSelected in [self.handleTopLeft, self.handleTopMiddle, self.handleTopRight]:
                rect.setTop(rect.bottom() - spacing)
            else:
                rect.setBottom(rect.top() + spacing)

        self.setRect(rect)
        self.updateHandlesPos()

    def quantizeMovement(self):
        # For all selected grouping boxes
        for gbox in self.grouping_box.scene.grouping_boxes:

            if gbox.grGBox.isSelected():

                spacing = 20

                # The x,y position of the mouse cursor is grabbed, and is restricted to update
                # every 20 pixels (the size of the smaller grid squares, as defined in GraphicsScene)
                x = round(gbox.grGBox.pos().x() / spacing) * spacing
                y = round(gbox.grGBox.pos().y() / spacing) * spacing
                pos = QPointF(x, y)
                # The position of this GraphicsGroupingBox is set to the restricted position of the mouse cursor
                gbox.grGBox.setPos(pos)

                # 10 is the width of the smaller grid squares
                # This logic prevents the selected GraphicsGroupingBox from being dragged outside
                # the border of the work area (GraphicsScene)
                padding = spacing

                # left
                if gbox.grGBox.pos().x() < gbox.grGBox.scene().sceneRect().x() + padding:
                    gbox.grGBox.setPos(gbox.grGBox.scene().sceneRect().x() + padding, gbox.grGBox.pos().y())

                # top
                if gbox.grGBox.pos().y() < gbox.grGBox.scene().sceneRect().y() + padding:
                    gbox.grGBox.setPos(gbox.grGBox.pos().x(), gbox.grGBox.scene().sceneRect().y() + padding)

                # right
                if gbox.grGBox.pos().x() > (gbox.grGBox.scene().sceneRect().x() + gbox.grGBox.scene().sceneRect().width() - gbox.grGBox.grouping_box.width - padding):
                    gbox.grGBox.setPos(gbox.grGBox.scene().sceneRect().x() + gbox.grGBox.scene().sceneRect().width() - gbox.grGBox.grouping_box.width - padding, gbox.grGBox.pos().y())

                # bottom
                if gbox.grGBox.pos().y() > (gbox.grGBox.scene().sceneRect().y() + gbox.grGBox.scene().sceneRect().height() - gbox.grGBox.grouping_box.height - padding):
                    gbox.grGBox.setPos(gbox.grGBox.pos().x(), gbox.grGBox.scene().sceneRect().y() + gbox.grGBox.scene().sceneRect().height() - gbox.grGBox.grouping_box.height - padding)

        # If grouping boxes were moved, change this variable to reflect that.
        self.wasMoved = True

    def hoverEnterEvent(self, event):
        """
        When a ``GraphicsGBox`` is hovered over with the cursor, this method will display
        a tooltip with a description of how to change its color.
        :param event: mouse hover detected over grouping box
        :type event: QGraphicsSceneHoverEvent
        """

        self.setToolTip("Right click to change color.")

    def shape(self):
        """
        Returns the shape of this item as a QPainterPath in local coordinates.
        """
        path = QPainterPath()
        path.addRect(self.rect())
        if self.isSelected():
            for shape in self.handles.values():
                path.addEllipse(shape)
        return path

    def paint(self, painter, option, widget=None):
        """
        Paint the node in the graphic view.
        """
        painter.setBrush(QBrush(self.bg_color))
        painter.setPen(QPen(self.br_color, 1.0, Qt.SolidLine) if not self.isSelected() else self._pen_selected)   # black default outline, thicker orange when selected
        painter.drawRect(self.rect())

        if self.isSelected():
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QBrush(QColor("#FFFFA637")))
            painter.setPen(QPen(QColor(0, 0, 0, 255), 1.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            for handle, rect in self.handles.items():
                painter.drawEllipse(rect)
