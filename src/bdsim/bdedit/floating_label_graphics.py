import copy

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
        self._selected_line_thickness = (
            5.0  # Thickness of the label outline on selection
        )
        self._pen_selected = QPen(
            QColorConstants.Svg.orange, self._selected_line_thickness
        )
        self.outline_brush = QBrush(QColorConstants.Svg.white)

        self.initUI()
        self.wasMoved = False
        self.lastPos = self.pos()

    def initUI(self):
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setAcceptHoverEvents(True)

        self.grText = QGraphicsProxyWidget(self)
        self.content.setGeometry(
            0, 0, self.floating_label.width, self.floating_label.height
        )
        self.grText.setWidget(self.content)
        self.setZValue(-3)

    def boundingRect(self):
        return QRectF(
            -self.edge_size,
            -self.edge_size,
            2 * self.edge_size + self.floating_label.width,
            2 * self.edge_size + self.floating_label.height,
        ).normalized()

    def paint(self, painter, style, widget=None):
        # Draw the outline of the box and fill in the background whitespace
        path = QPainterPath()
        path.addRoundedRect(self.boundingRect(), self.edge_size, self.edge_size)
        painter.setPen(Qt.NoPen if not self.isSelected() else self._pen_selected)
        painter.setBrush(QColor("#F0F0F0"))
        painter.drawPath(path.simplified())
        painter.setBrush(self.outline_brush)
        painter.drawPath(path.simplified())

    def setLabelUnfocus(self):
        self.floating_label.setFocusOfFloatingText()
        color_for_highlighting = copy.copy(self.floating_label.content.backgroundColor)
        color_for_highlighting.setAlpha(0)
        self.floating_label.content.setTextHighlighting(color_for_highlighting)
        self.floating_label.content.text_edit.setTextInteractionFlags(
            Qt.NoTextInteraction
        )

        # If floating label has been edited, update the variable within the model, to then update the
        # title of the model, to indicate that there is unsaved progress
        if self.content.wasEdited:
            self.content.wasEdited = False
            self.floating_label.scene.has_been_modified = True
            self.floating_label.scene.history.storeHistory("Floating label edited")

    def setLabelFocus(self):
        self.floating_label.content.setTextHighlighting(QColor(225, 225, 225, 127))
        self.floating_label.content.text_edit.setTextInteractionFlags(
            Qt.TextEditorInteraction
        )

    def setLabelSizeBox(self):
        self.floating_label.interfaceManager.updateToolbarValues()

    def hoverEnterEvent(self, event):
        """
        When a ``FloatingLabel`` is hovered over with the cursor, this method will display
        a tooltip with a description of how to change its color.
        :param event: mouse hover detected over floating label
        :type event: QGraphicsSceneHoverEvent
        """

        self.setToolTip("Right click to change background color.")

    def mousePressEvent(self, event):
        def updateColor(chosen_color):
            if chosen_color.isValid():
                # Grab copy of text edit's color palette, to change its background
                palette = self.floating_label.content.text_edit.viewport().palette()

                # Update the copy of background color
                self.floating_label.content.backgroundColor = chosen_color
                palette.setColor(
                    self.floating_label.content.text_edit.viewport().backgroundRole(),
                    chosen_color,
                )
                self.floating_label.content.text_edit.viewport().setPalette(palette)

                # Update the text highlighting color
                color_for_highlighting = copy.copy(
                    self.floating_label.content.backgroundColor
                )
                color_for_highlighting.setAlpha(0)
                self.floating_label.content.setTextHighlighting(color_for_highlighting)

                # Update color of rounded border drawn around text edit
                self.outline_brush = QBrush(self.floating_label.content.backgroundColor)

                self.floating_label.scene.has_been_modified = True
                self.floating_label.scene.history.storeHistory(
                    "Grouping box color changed"
                )

        super().mousePressEvent(event)
        self.setLabelUnfocus()
        self.setLabelSizeBox()

        # If the right mouse button is pressed, bring up a QColorDialog
        if event.button() == Qt.RightButton:
            # Make a backup of the original background color in case user cancels color selection
            # current_palette = self.floating_label.content.text_edit.viewport().palette()
            current_color = copy.copy(self.floating_label.content.backgroundColor)

            # Open a color dialog window, and when the chosen color changes, call func updateColor
            # to update the background color of the floating label
            colorDialog = QColorDialog()
            colorDialog.setOption(QColorDialog.ShowAlphaChannel, on=True)
            colorDialog.currentColorChanged.connect(
                lambda checked: updateColor(colorDialog.currentColor())
            )

            # If user selects okay, this finalizes the color selection
            if colorDialog.exec_() == QDialog.Accepted:
                updateColor(colorDialog.selectedColor())
            # Otherwise, if they exit out of the color picker, the original color will be reverted to.
            else:
                updateColor(current_color)

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
            self.floating_label.scene.history.storeHistory("Floating label moved")
