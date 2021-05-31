from bdedit.block import *
from bdedit.block_graphics_block import *
from bdedit.block_socket import *


class Connector(Block):
    def __init__(self, scene, window, name="Unnamed Connector Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.scene = scene
        self.window = window

        self.block_type = self.__class__.__name__

        self.position = pos
        self.parameterWindow = None

        self.width = 13
        self.height = 12

        self.grBlock = GraphicsSocketBlock(self)

        self.makeInputSockets(1, LEFT, socketType=INPUT)
        self.makeOutputSockets(1, RIGHT, socketType=OUTPUT)

        # self.makeInputSockets(1, LEFT, socketType=CONNECTOR)

        self.scene.addBlock(self)
        self.scene.grScene.addItem(self.grBlock)
            

 

            
      

