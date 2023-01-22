# Library imports
import json
import copy
from collections import OrderedDict

# PyQt5 imports
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

# BdEdit imports
from bdsim.bdedit.interface_serialize import Serializable
from bdsim.bdedit.floating_label_graphics import GraphicsLabel


DEBUG = False


class Floating_Label(Serializable):
    def __init__(self, scene, window, mainwindow, label_text="text", pos=(0, 0)):
        super().__init__()
        self.scene = scene
        self.window = window
        self.interfaceManager = mainwindow
        self.label_text = label_text
        self.position = pos

        self.width = 0
        self.height = 0

        self.content = ContentWidget(self)
        self.grContent = GraphicsLabel(self)

        self.scene.addLabel(self)
        self.scene.grScene.addItem(self.grContent)

        self.scene.has_been_modified = True

    def setPos(self, x, y):
        self.grContent.setPos(x, y)

    def setFocusOfFloatingText(self):
        """
        This method sends all ``FloatingLabel`` instances within the ``Scene`` to back
        and then sends the currently selected ``FloatingLabel`` instance to front.
        """

        # Iterates through each floating label within the relevant list stored in
        # the Scene Class and sets the graphical component of each label to a zValue of -4.
        for floatinglabel in self.scene.floating_labels:
            floatinglabel.grContent.setZValue(-4)

        # Then sets the graphical component of the currently selected label to a
        # zValue of -3, which makes it display above all other labels on screen.
        self.grContent.setZValue(-3)

    # Todo - update comments to match floating label, not block
    def remove(self):

        # For each socket associated with this block, remove the connected wires
        if DEBUG:
            print("> Removing Floating Label", self)

        # Remove the graphical representation of this block from the scene
        # This will also remove the associated graphical representation of the
        # blocks' sockets.
        if DEBUG:
            print(" - removing grContent")
        self.scene.grScene.removeItem(self.grContent)
        self.grContent = None

        # Finally, call the removeBlock method from within the Scene, which
        # removes this block from the list of blocks stored in the Scene.
        if DEBUG:
            print(" - removing Floating Label from the scene")
        self.scene.removeLabel(self)
        if DEBUG:
            print(" - everything was done.")

    # -----------------------------------------------------------------------------
    def serialize(self):
        font_info = self.content.text_edit.toHtml()
        fill_color = self.content.backgroundColor.getRgb()

        return OrderedDict(
            [
                ("id", self.id),
                ("text", self.label_text),
                ("pos_x", self.grContent.scenePos().x()),
                ("pos_y", self.grContent.scenePos().y()),
                ("width", self.width),
                ("height", self.height),
                ("fill_color", fill_color),
                ("styling", font_info),
            ]
        )

    # -----------------------------------------------------------------------------
    def deserialize(self, data, hashmap={}):
        # The id of this floating label is set to whatever was stored as its id in the JSON file.
        self.id = data["id"]
        self.label_text = data["text"]
        self.width = data["width"]
        self.height = data["height"]

        # The position of the Floating Labels within the Scene, are set accordingly.
        self.setPos(data["pos_x"], data["pos_y"])

        self.content.text_edit.document().setHtml(data["styling"])

        try:
            if data["fill_color"]:
                # If fill color exists in json, convert rgba to QColor
                color = QColor(
                    data["fill_color"][0],
                    data["fill_color"][1],
                    data["fill_color"][2],
                    data["fill_color"][3],
                )

                # Grab copy of text edit's color palette, to change its background
                palette = self.content.text_edit.viewport().palette()

                # Update the copy of background color
                self.content.backgroundColor = color
                palette.setColor(
                    self.content.text_edit.viewport().backgroundRole(), color
                )
                self.content.text_edit.viewport().setPalette(palette)

                # Update the text highlighting color
                color_for_highlighting = copy.copy(self.content.backgroundColor)
                color_for_highlighting.setAlpha(0)
                self.content.setTextHighlighting(color_for_highlighting)

                # Update color of rounded border drawn around text edit
                self.grContent.outline_brush = QBrush(self.content.backgroundColor)
        except KeyError:
            # Fill color is a new feature, so some models might not have fill color saved in the json
            # if this is the case, draw the labels with the default white color
            pass

        self.content.updateShape()

        return True


class ContentWidget(QWidget):
    def __init__(self, label):
        super().__init__()

        self.floating_label = label
        self.text_edit = QTextEdit(self)

        self.defaultFont = "Arial"
        self.defaultFontSize = 14
        self.defaultWeight = QFont.Normal
        self.defaultItalics = False
        self.defaultUnderline = False
        # self.defaultColor = QColor("#000000")
        self.defaultColor = QColor("#0000ff")
        self.defaultAlignment = Qt.AlignLeft
        self.defaultBackgroundColor = QColor(255, 255, 255)

        self.currentFontSize = copy.copy(self.defaultFontSize)
        self.backgroundColor = copy.copy(self.defaultBackgroundColor)

        self.padding = 8

        self.setup()
        self.updateShape()

        self.wasEdited = False

        self.initUI()

    def setup(self):
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_edit.setFrameStyle(QFrame.NoFrame)
        self.text_edit.setTextInteractionFlags(Qt.NoTextInteraction)
        self.text_edit.setAutoFillBackground(True)

        self.setDefaultFormatting()

        self.text_edit.setPlainText(self.floating_label.label_text)
        self.text_edit.textChanged.connect(self.updateText)

    def initUI(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(self.layout)
        self.layout.addWidget(self.text_edit)

    def setTextHighlighting(self, highlight):
        p = self.text_edit.palette()
        p.setColor(QPalette.Highlight, highlight)
        self.text_edit.setPalette(p)

    def updateText(self):
        if self.text_edit.document().isModified():
            current_text = self.text_edit.toPlainText()
            # If changes have been made to the labels current text, update it internally
            if current_text != self.floating_label.label_text:
                self.floating_label.label_text = current_text
                self.updateShape()
                self.wasEdited = True

    def updateShape(self):
        # Find the space occupied by text within the floating label
        font = self.text_edit.currentFont()
        fontmetrics = QFontMetrics(font)
        textSize = fontmetrics.size(0, self.text_edit.toPlainText())

        w = textSize.width() + self.padding
        h = textSize.height() + self.padding

        # Resize the interactable area where the text is displayed
        self.text_edit.setMinimumSize(w, h)
        self.text_edit.setMaximumSize(w, h)
        self.text_edit.resize(w, h)

        # Resize max width of widget container for the text area
        self.setMaximumSize(w, h)

        # Update the dimensions of the floating label widget, so that the outline around it could be properly drawn
        self.floating_label.width = w
        self.floating_label.height = h

    def setDefaultFormatting(self):
        self.text_edit.setFont(QFont(self.defaultFont, self.defaultFontSize))
        self.text_edit.setFontPointSize(self.defaultFontSize)
        self.text_edit.setFontWeight(self.defaultWeight)
        self.text_edit.setFontItalic(self.defaultItalics)
        self.text_edit.setFontUnderline(self.defaultUnderline)
        self.text_edit.setAlignment(self.defaultAlignment)
        self.text_edit.setTextColor(self.defaultColor)
