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
    def __init__(self, scene, window, label_text="text", pos=(0,0)):
        super().__init__()
        self.scene = scene
        self.window = window
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

    # Todo - update comments to match floating label, not block
    def remove(self):

        # For each socket associated with this block, remove the connected wires
        if DEBUG: print("> Removing Floating Label", self)

        # Remove the graphical representation of this block from the scene
        # This will also remove the associated graphical representation of the
        # blocks' sockets.
        if DEBUG: print(" - removing grContent")
        self.scene.grScene.removeItem(self.grContent)
        self.grContent = None

        # Finally, call the removeBlock method from within the Scene, which
        # removes this block from the list of blocks stored in the Scene.
        if DEBUG: print(" - removing Floating Label from the scene")
        self.scene.removeLabel(self)
        if DEBUG: print(" - everything was done.")


    # -----------------------------------------------------------------------------
    def serialize(self):
        font_info = self.content.text_edit.toHtml()

        return OrderedDict([
            ('id', self.id),
            ('text', self.label_text),
            ('pos_x', self.grContent.scenePos().x()),
            ('pos_y', self.grContent.scenePos().y()),
            ('width', self.width),
            ('height', self.height),
            ("styling", font_info),
        ])

    # -----------------------------------------------------------------------------
    def deserialize(self, data, hashmap={}):
        # The id of this floating label is set to whatever was stored as its id in the JSON file.
        self.id = data['id']
        self.label_text = data['text']
        self.width = data['width']
        self.height = data['height']

        # The position of the Floating Labels within the Scene, are set accordingly.
        self.setPos(data['pos_x'], data['pos_y'])

        self.content.text_edit.setHtml(data['styling'])

        self.content.updateShape()

        return True


class ContentWidget(QWidget):
    def __init__(self, label):
        super().__init__()

        self.floating_label = label
        self.text_edit = QTextEdit(self)
        self.first_time = True

        self.defaultFont = 'Arial'
        self.defaultFontSize = 14
        self.defaultWeight = QFont.Normal
        self.defaultItalics = False
        self.defaultUnderline = False
        self.defaultColor = QColor("#000000")
        self.defaultAlignment = Qt.AlignLeft

        self.setup()
        self.updateShape()

        self.initUI()

    def setup(self):
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_edit.setFrameStyle(QFrame.NoFrame)
        self.text_edit.setTextInteractionFlags(Qt.NoTextInteraction)

        self.text_edit.setFont(QFont(self.defaultFont, self.defaultFontSize))
        self.text_edit.setFontPointSize(self.defaultFontSize)
        self.text_edit.setFontWeight(self.defaultWeight)
        self.text_edit.setFontItalic(self.defaultItalics)
        self.text_edit.setFontUnderline(self.defaultUnderline)
        self.text_edit.setTextColor(self.defaultColor)
        self.text_edit.setAlignment(self.defaultAlignment)

        self.text_edit.document().setPlainText(self.floating_label.label_text)
        self.text_edit.textChanged.connect(self.updateText)

        # self.text_edit.setStyleSheet("QTextEdit { background-color: rgb(255, 255, 255); }")
        # self.text_edit.setTextBackgroundColor(QColor("#FFFFFF"))

    def initUI(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.setLayout(self.layout)
        self.layout.addWidget(self.text_edit)

    def updateText(self):
        if self.text_edit.document().isModified():
            current_text = self.text_edit.toPlainText()
            self.floating_label.label_text = current_text
            self.updateShape()

    def updateShape(self):
        # Find the space the text with in the floating label occupies
        if self.text_edit.fontWeight() == QFont.Bold:
            font = self.text_edit.document().defaultFont()
            font.setBold(True)
        else:
            font = self.text_edit.document().defaultFont()
        fontMetrics = QFontMetrics(font)
        textSize = fontMetrics.size(0, self.text_edit.toPlainText())

        # If not initializing the first time, if the dimensions of the QWidget
        # are bigger than the space the text inside it occupies, then set
        # the the dimensions of the interactable area (QTextEdit) to that of the
        # QWidget, as the above code doesn't accurately capture the size the
        # text occupies when there are spaces at start/end of lines, or for newlines.

        # But if the size of the QWidget is smaller than what the text seems to
        # occupy, this means the text has been edited, so allow the interactable
        # area to increase with a padding of 10 pixels.
        if not self.first_time:
            if self.width() > textSize.width()+10:
                w = self.width()
            else:
                w = textSize.width() + 10

            if self.height() > textSize.height()+10:
                h = self.height()
            else:
                h = textSize.height() + 10

        # If initializing the first time, the dimensions of the QWidget
        # are very large for some reason, so reset the dimensions to the
        # size they should be based on the space the text occupies
        else:
            self.first_time = False
            w = textSize.width() + 10
            h = textSize.height() + 10

        # Resize the interactable area where the text is displayed
        self.text_edit.setMinimumSize(w, h)
        self.text_edit.setMaximumSize(w, h)
        self.text_edit.resize(w, h)

        # Update the dimensions of the floating label widget, so that
        # the outline around it could be properly drawn
        self.floating_label.width = w
        self.floating_label.height = h
