# PyQt5 imports
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class GraphicsLabel(QGraphicsItem):
    def __init__(self, label, parent=None):
        super().__init__(parent)
        self.floating_label = label
        # self.content = self.floating_label.content

        self._update_text = True

        self.edge_size = 5.0
        self.width = self.floating_label.width
        self.height = self.floating_label.height

        # Text related default settings
        self._default_text_color = Qt.black
        self._default_text_font = "Arial"
        self._default_text_size = 10
        self._text_font = QFont(self._default_text_font, self._default_text_size)

        # Label related outline settings
        self._line_thickness = 3.0              # Thickness of the label outline by default
        self._selected_line_thickness = 5.0     # Thickness of the label outline on selection
        self._pen_default = QPen(QColor("#7F000000"), self._line_thickness)
        self._pen_selected = QPen(QColor("#FFFFA637"), self._selected_line_thickness)
        self._brush_background = QBrush(QColor("#E3212121"))

        self.initLabel()

        self.initUI()

    def initUI(self):
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIsMovable)

        # self.grText = QGraphicsProxyWidget(self)
        # self.content.setGeometry(0, 0, self.width, self.height)
        # self.grText.setWidget(self.content)
        # self.grText.resize(self.width, self.height)

    def initLabel(self):
        self.label_item = QGraphicsTextItem(self)
        self.label_item.setDefaultTextColor(self._default_text_color)
        self.label_item.setFont(self._text_font)
        self.label_item.setTextInteractionFlags(Qt.TextEditorInteraction | Qt.TextEditable)

    def updateLabelText(self):
        # Update the text to whatever the user has written in the label
        self.label_item.setPlainText(self.floating_label.label_text)

        # Update the dimensions of the border around the text label
        self.width = self.textLength() + self.edge_size * 2

        self.label_item.setPos((self.width - self.textLength()) / 2, self.edge_size)

    def textLength(self):
        # Using the known text (and its font and size), determine the length of the
        # text in terms of pixels
        text_pixel_len = QFontMetrics(self._text_font).width(self.floating_label.label_text)
        return text_pixel_len

    def boundingRect(self):
        return QRectF(
            0,
            0,
            2 * self.edge_size + self.width,
            2 * self.edge_size + self.height
        ).normalized()

    def paint(self, painter, style, widget=None):
        # Label text will be redrawn, if needed
        if self._update_text:
            self.updateLabelText()

        # Draw the outline of the box
        path_outline = QPainterPath()
        path_outline.addRoundedRect(self.boundingRect(), self.edge_size, self.edge_size)
        painter.setPen(Qt.NoPen if not self.isSelected() else self._pen_selected)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path_outline.simplified())

    def focusOutEvent(self, event):
        self.label_item.setTextInteractionFlags(Qt.NoTextInteraction)

        super().focusOutEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.label_item.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.label_item.setFocus()

        super().mouseDoubleClickEvent(event)


