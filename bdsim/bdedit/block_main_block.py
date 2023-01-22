# BdEdit imports
from bdsim.bdedit.block import *
from bdsim.bdedit.block_socket import *
from bdsim.bdedit.block_graphics_block import *


# =============================================================================
#
#   Defining the Main Block Class, which allows for the loaded/built model to
#   be invoked as a subprocess when that model is run
#
# =============================================================================
# Todo - update doc string
class Main(Block):
    """ """

    # -----------------------------------------------------------------------------
    def __init__(self, scene, window, file_name=None, name="Main Block", pos=(0, 0)):
        """ """

        super().__init__(scene, window)

        # Same variables inherited from the Block class
        self.scene = scene
        self.window = window

        self.block_type = blockname(self.__class__)
        self.width = 100
        self.height = 100

        self.setDefaultTitle(name)

        self.parameters = [["file name", str, file_name, []]]

        self.block_url = ""
        self.icon = ":/Icons_Reference/Icons/main.png"
        self.flipped = False
        self.flipped_icon = os.path.join(
            os.path.splitext(self.icon)[0] + "_flipped.png"
        )

        self.inputsNum = 0
        self.outputsNum = 0

        self.grBlock = GraphicsBlock(self)

        self.parameterWindow = None

        # The Main block is automatically stored into the Scene,
        # and visually added into the GraphicsScene
        self.scene.addBlock(self)
        self.scene.grScene.addItem(self.grBlock)

        self._createParamWindow()

        self.scene.has_been_modified = True
