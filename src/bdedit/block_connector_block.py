# BdEdit imports
from bdsim.bdedit.block import *
from bdsim.bdedit.block_socket import *
from bdsim.bdedit.block_graphics_block import *


# =============================================================================
#
#   Defining the Connector Class, which allows for the redirecting of Wires
#   to create more neater Block Diagrams.
#
# =============================================================================
class Connector(Block):
    """
    The ``Connector`` Class is a subclass of ``Block``, and referred to as a
    child class of ``Block``. It inherits all the methods and variables of its
    parent class to behave as a Block. It allows for wires to be more neatly
    redirected, acting as a node through which the wires can be moved around
    more freely within the work area.

    The idea of this Connector block was for it to be a single socket which
    allows a wire to be redirected through it, however currently it works by
    mimicking a Block that only has 1 input and 1 output socket. The same socket
    logic that applies to a Block, also applies to the Connector Block.

    That being:

    - an input: can only have 1 Wire connecting into it
    - an output: can have n Wires connecting into it
    """

    # -----------------------------------------------------------------------------
    def __init__(self, scene, window, title="Unnamed Connector Block"):
        """
        This method initializes an instance of the ``Connector`` Block Class.

        :param scene: inherited through ``Block``
        :type scene: ``Scene``, required
        :param window: inherited through ``Block``
        :type window: ``QGridLayout``, required
        :param title: defaults to "Unnamed Connector Block"
        :type title: str, optional
        :param pos: inherited through ``Block``
        :type pos: tuple of 2-ints, optional
        """

        super().__init__(scene, window)

        # Same variables inherited from the Block class
        self.scene = scene
        self.window = window

        # No block title as the Connector Blocks have no name, as
        # this type of block is more of a tool than a Block
        # self.position = pos
        # The Connector Block doesn't have its own subclass like the other Block types,
        # hence some of the variables are defined in this class level, these being:
        # * the block type
        # * the block dimensions (width, height)
        # * the grBlock (graphical representation of how this block looks)
        # * the number of spawned input and output sockets (1 of each)
        # * the paramWindow is disabled (this block doesn't have a paramWindow, as it is a tool)
        self.block_type = blockname(self.__class__)
        self.width = 13
        self.height = 12

        self.title = ""
        self.parameters = []
        self.block_url = ""

        self.icon = ""
        self.flipped = False
        self.flipped_icon = ""

        self.inputsNum = 1
        self.outputsNum = 1

        self.grBlock = GraphicsConnectorBlock(self)

        self.makeInputSockets(self.inputsNum, LEFT, socketType=INPUT)
        self.makeOutputSockets(self.outputsNum, RIGHT, socketType=OUTPUT)

        self.parameterWindow = None

        # The Connector block is automatically stored into the Scene,
        # and visually added into the GraphicsScene
        self.scene.addBlock(self)
        self.scene.grScene.addItem(self.grBlock)

        self.scene.has_been_modified = True
