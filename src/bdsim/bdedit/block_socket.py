# Library imports
from collections import OrderedDict

# BdEdit imports
from bdsim.bdedit.interface_serialize import Serializable
from bdsim.bdedit.block_graphics_socket import GraphicsSocket

# =============================================================================
#
#   Defining and setting global variables
#
# =============================================================================
# Socket positioning variables (in relation to where they're drawn on the block)
LEFT = 1
TOP = 2
RIGHT = 3
BOTTOM = 4

# Socket type classification variables
INPUT = 1
OUTPUT = 2
CONNECTOR = 3

# Variable for enabling/disabling debug comments
DEBUG = False


# =============================================================================
#
#   Defining the Socket Class, which controls the type of Socket drawn, its
#   position within the Block it relates to, and allows for Wires to connect
#   to the Block through these Sockets.
#
# =============================================================================
class Socket(Serializable):
    """
    The ``Socket`` Class extends the ``Serializable`` Class from BdEdit, and
    defines how a socket is represented, and has all the necessary methods
    for creating, manipulating and interacting with a socket. This class allows
    for Wires to be connected to Blocks, while also controlling where on the
    Block the Sockets are drawn, and how they appear.

    This class includes information about the sockets':

    - type;
    - index;
    - position;
    - appearance;
    - parent Block; and
    - connected wire(s).
    """

    # -----------------------------------------------------------------------------
    def __init__(
        self,
        node,
        index=0,
        position=LEFT,
        socket_type=INPUT,
        multi_wire=True,
        socket_label=None,
    ):
        """
        This method initializes an instance of the ``Socket`` Class.

        :param node: the associated Block this Socket relates to
        :type node: Block, required
        :param index: the height (along the side of the Block) this Socket should be drawn at
        :type index: int, optional, defaults to 0
        :param position: the side ( LEFT(1) or RIGHT(3) ) this Socket should be drawn on
        :type position: enumerate, optional, defaults to LEFT(1)
        :param socket_type: this Socket's type (INPUT(1) or OUTPUT(2))
        :type socket_type: enumerate, optional, defaults to INPUT(1)
        :param multi_wire: boolean of whether this Socket has multiple wires
        :type multi_wire: bool, optional, defaults to True
        """
        super().__init__()

        self.node = node
        self.index = index
        self.position = position
        self.socket_type = socket_type
        self.socket_sign = socket_label
        self.is_multi_wire = multi_wire
        self.grSocket = GraphicsSocket(self)

        self.grSocket.setPos(*self.node.getSocketPosition(index, position))

        self.wires = []

    # -----------------------------------------------------------------------------
    def getSocketPosition(self):
        """
        This method retrieves and returns the [x,y] coordinates for where the
        current Socket should be drawn.

        :return: the [x,y] coordinates at which to place this Socket.
        :rtype: list of int, int
        """

        res = self.node.getSocketPosition(self.index, self.position)
        return res

    # -----------------------------------------------------------------------------
    def setConnectedEdge(self, wire):
        """
        This method adds the given wire to the list of Wires that are connected to
        this Socket.

        :param wire: the wire connecting to this Socket
        :type wire: Wire, required
        """

        self.wires.append(wire)

    # -----------------------------------------------------------------------------
    def hasEdge(self):
        """
        This method returns True if the current Socket has Wires connected to it,
        and False if no Wires are connected to it.

        :return: - True (If wires are connected to this Socket)
                 - False (If no wires are connected to this Socket)
        :rtype: bool
        """

        return self.wires is not None

    # -----------------------------------------------------------------------------
    def removeWire(self, wire):
        """
        This method removes the given Wire from the list of Wires connected to this
        Socket, if it is connected to this Socket.

        :param wire: the wire to be removed
        :type wire: Wire, required
        """

        if wire in self.wires:
            self.wires.remove(wire)
        else:
            print("Socket remove edge not in list")

    # -----------------------------------------------------------------------------
    def removeAllWires(self):
        """
        This method removes all Wires connected to this Socket.
        """

        # While there are Wires in this Socket's list of Wires, remove the first Wire
        while self.wires:
            wire = self.wires.pop(0)
            wire.remove()

    # -----------------------------------------------------------------------------
    def isInputSocket(self):
        """
        This method returns True if the current Socket is an input socket.

        :return: - True (If current Socket is an input Socket)
                 - False (If current Socket is not an input Socket)
        :rtype: bool
        """

        isInputSocket = False
        # Compare the id of the current socket against the id's of sockets
        # within the associated Blocks' list of input sockets
        for socket in self.node.inputs:
            # If current socket is in that list, it is an input socket
            if self.id == socket.id:
                isInputSocket = True
                break
        return isInputSocket

    # -----------------------------------------------------------------------------
    def isOutputSocket(self):
        """
        This method returns True if the current Socket is an output socket.

        :return: - True (If current Socket is an output Socket)
                 - False (If current Socket is not an output Socket)
        :rtype: bool
        """
        isOutputSocket = False
        # Compare the id of the current socket against the id's of sockets
        # within the associated Blocks' list of output sockets
        for socket in self.node.outputs:
            # If current socket is in that list, it is an output socket
            if self.id == socket.id:
                isOutputSocket = True
                break
        return isOutputSocket

    # -----------------------------------------------------------------------------
    def updateSocketSign(self, value):
        """
        This method updates the value of the socket label assigned to this socket.
        As none but a select few blocks (SubSystem, OutPort, InPort) support dynamic
        updating of the socket labels, this method should not be used  unless it is
        for one of the mentioned blocks.

        :param value: new value to assign for socket label
        :type value: str, int, None or []
        """
        try:
            self.socket_sign = value
        except Exception:
            self.socket_sign = None

    # -----------------------------------------------------------------------------
    def removeSockets(self, type):
        """
        This method removes all of the input or output Sockets, relating to this
        Block, as specified by the type.

        This method removes all sockets of given type, associated with this ``Block``.

        :param type: the type of Socket to remove ("Input" or "Output")
        :type type: str, required
        """

        # If in DEBUG mode, this code will return the type of Socket that has just
        # been removed, and that the socket removal process has started. When this
        # process is finished, a done message will be printed.
        if DEBUG:
            print("# Removing " + type + " Sockets", self)
        if DEBUG:
            print(" - removing grSockets")

        # This allows one method to be used for deleting input OR output sockets
        if type == "Input":
            socketTypes = self.node.inputs
        elif type == "Output":
            socketTypes = self.node.outputs

        # For each socket within the list determined by either Input or Output
        # socket type
        for socket in socketTypes:
            # Remove the graphics parent item (the associated graphics block class)
            # Remove the graphics socket class
            socket.grSocket.setParentItem(None)
            socket.grSocket = None
            # If this socket has any wires attached to it, remove them
            if socket.hasEdge():
                for wire in socket.wires:
                    wire.remove()

        # Finally remove the socket class from the associated block
        self.node.removeSockets(type)

        if DEBUG:
            print(" - everything is done.")

    # -----------------------------------------------------------------------------
    def serialize(self):
        """
        This method is called to create an ordered dictionary of all of this Sockets'
        parameters - necessary for the reconstruction of this Socket - as key-value
        pairs. This dictionary is later used for writing into a JSON file.

        :return: an ``OrderedDict`` of [keys, values] pairs of all essential ``Socket``
                 parameters.
        :rtype: ``OrderedDict`` ([keys, values]*)
        """

        return OrderedDict(
            [
                ("id", self.id),
                ("index", self.index),
                ("multi_wire", self.is_multi_wire),
                ("position", self.position),
                ("socket_type", self.socket_type),
            ]
        )

    # -----------------------------------------------------------------------------
    def deserialize(self, data, hashmap={}):
        """
        This method is called to reconstruct a ``Socket`` when loading a saved JSON
        file containing all relevant information to recreate the ``Scene`` with all
        its items.

        :param data: a Dictionary of essential information for reconstructing a ``Socket``
        :type data: OrderedDict, required
        :param hashmap: a Dictionary for directly mapping the essential socket variables
                        to this instance of ``Socket``, without having to individually map each variable
        :type hashmap: Dict, required
        :return: True when completed successfully
        :rtype: Boolean
        """

        # The id of this Socket is set to whatever was stored as its id in the JSON file.
        self.id = data["id"]
        # The remaining variables associated to this Socket are mapped to itself
        hashmap[data["id"]] = self

        return True
