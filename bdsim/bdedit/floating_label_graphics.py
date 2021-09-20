# PyQt5 imports
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class GraphicsLabel(QGraphicsItem):
    def __init__(self, label, parent=None):
        super().__init__(parent)
        self.floating_label = label
        self.content = self.floating_label.content

        # Label related outline settings
        self.edge_size = 6.0
        self._line_thickness = 3.0              # Thickness of the label outline by default
        self._selected_line_thickness = 5.0     # Thickness of the label outline on selection
        self._pen_default = QPen(QColor("#7F000000"), self._line_thickness)
        self._pen_selected = QPen(QColor("#FFFFA637"), self._selected_line_thickness)

        self.initUI()
        self.wasMoved = False

    def initUI(self):
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIsMovable)

        self.grText = QGraphicsProxyWidget(self)
        self.content.setGeometry(0, 0, self.floating_label.width, self.floating_label.height)
        self.grText.setWidget(self.content)

    def boundingRect(self):
        return QRectF(
            -self.edge_size,
            -self.edge_size,
            2 * self.edge_size + self.floating_label.width,
            2 * self.edge_size + self.floating_label.height
        ).normalized()

    def paint(self, painter, style, widget=None):
        # Draw the outline of the box and fill in the background whitespace
        path = QPainterPath()
        path.addRoundedRect(self.boundingRect(), self.edge_size, self.edge_size)
        # painter.setPen(self._pen_default if not self.isSelected() else self._pen_selected)
        painter.setPen(Qt.NoPen if not self.isSelected() else self._pen_selected)
        painter.setBrush(QBrush(Qt.white))
        # painter.setBrush(Qt.NoBrush)
        painter.drawPath(path.simplified())

    def setLabelUnfocus(self):
        self.floating_label.setFocusOfFloatingText()
        self.floating_label.content.text_edit.setTextInteractionFlags(Qt.NoTextInteraction)

    def setLabelFocus(self):
        self.floating_label.content.text_edit.setTextInteractionFlags(Qt.TextEditorInteraction)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.setLabelUnfocus()

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.setLabelFocus()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

        # If floating label has been moved, update the variable within the model, to then update the
        # title of the model, to indicate that there is unsaved progress
        if self.wasMoved:
            self.wasMoved = False
            self.floating_label.scene.has_been_modified = True

    def mouseMoveEvent(self, event):

        super().mouseMoveEvent(event)

        # For all selected floating labels
        for label in self.floating_label.scene.floating_labels:

            if label.grContent.isSelected():

                spacing = 5

                # The x,y position of the mouse cursor is grabbed, and is restricted to update
                # every 5 pixels (the size of the smaller grid squares, as defined in GraphicsScene)
                x = round(label.grContent.pos().x() / spacing) * spacing
                y = round(label.grContent.pos().y() / spacing) * spacing
                pos = QPointF(x, y)
                # The position of this GraphicsConnectorBlock is set to the restricted position of the mouse cursor
                label.grContent.setPos(pos)

                # 10 is the width of the smaller grid squares
                # This logic prevents the selected QGraphicsConnectorBlock from being dragged outside
                # the border of the work area (GraphicsScene)
                padding = spacing

                # left
                if label.grContent.pos().x() < label.grContent.scene().sceneRect().x() + padding:
                    label.grContent.setPos(label.grContent.scene().sceneRect().x() + padding, label.grContent.pos().y())

                # top
                if label.grContent.pos().y() < label.grContent.scene().sceneRect().y() + padding:
                    label.grContent.setPos(label.grContent.pos().x(), label.grContent.scene().sceneRect().y() + padding)

                # right
                if label.grContent.pos().x() > (label.grContent.scene().sceneRect().x() + label.grContent.scene().sceneRect().width() - label.grContent.floating_label.width - padding):
                    label.grContent.setPos(label.grContent.scene().sceneRect().x() + label.grContent.scene().sceneRect().width() - label.grContent.floating_label.width - padding, label.grContent.pos().y())

                # bottom
                if label.grContent.pos().y() > (label.grContent.scene().sceneRect().y() + label.grContent.scene().sceneRect().height() - label.grContent.floating_label.height - padding):
                    label.grContent.setPos(label.grContent.pos().x(), label.grContent.scene().sceneRect().y() + label.grContent.scene().sceneRect().height() - label.grContent.floating_label.height - padding)

        # If floating labels were moved, change this variable to reflect that.
        self.wasMoved = True