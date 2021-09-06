# Library imports
import json
from collections import OrderedDict

# BdEdit imports
# from bdsim.bdedit.floating_label_graphics import
from bdsim.bdedit.interface_serialize import Serializable

class Floating_Text(Serializable):
    def __init__(self, scene, window, content='text', pos=(0,0)):
        super().__init__()

        self.scene = scene
        self.window = window
        self.content = content
        self.position = pos

        self.grContent = QGraphicsProxyWidget(self)
