from bdedit.block_graphics_socket import GraphicsSocket
from bdedit.interface_serialize import Serializable
from collections import OrderedDict

LEFT = 1
TOP = 2
RIGHT = 3
BOTTOM = 4

INPUT = 1
OUTPUT = 2
CONNECTOR = 3

# PLUS = "+"
# MINUS = "-"
# MULTIPLY = "*"
# DIVIDE = "/"

DEBUG = False

# The socket class that connects the wires to the blocks and tells the sockets
# were on the blocks they will be drawn.

 
class Socket(Serializable):
    def __init__(self, node, index=0, position=LEFT, socket_type=INPUT, multi_wire=True):
        super().__init__()

        self.node = node
        self.index = index
        self.position = position
        self.socket_type = socket_type
        self.socket_sign = None
        self.is_multi_wire = multi_wire
        self.grSocket = GraphicsSocket(self)
        
        self.grSocket.setPos(*self.node.getSocketPosition(index, position))
        
        self.wires = []

    def __str__(self):
        return "<Socket %s..%s>" % (hex(id(self))[2:5], hex(id(self))[-3:])

    def getSocketPosition(self):
        res = self.node.getSocketPosition(self.index, self.position)
        return res
    
    def setConnectedEdge(self, wire):
        self.wires.append(wire)

    def hasEdge(self):
        return self.wires is not None
        
    def removeWire(self, wire):
        if wire in self.wires: self.wires.remove(wire)
        else: print("Socket remove edge not in list")
        
    def removeAllWires(self):
        while self.wires:
            wire = self.wires.pop(0)
            wire.remove()

    def isInputSocket(self):
        isInputSocket = False
        for socket in self.node.inputs:
            if self.id == socket.id:
                isInputSocket = True
                break
        return isInputSocket

    def isOutputSocket(self):
        isOutputSocket = False
        for socket in self.node.outputs:
            if self.id == socket.id:
                isOutputSocket = True
                break
        return isOutputSocket

    def removeSockets(self, type):
        if DEBUG: print("# Removing "+type+" Sockets", self)
        if DEBUG: print(" - removing grSockets")

        # This allows one method to be used for deleting input OR output sockets
        if type == "Input":
            socketTypes = self.node.inputs
        elif type == "Output":
            socketTypes = self.node.outputs

        for socket in socketTypes:
            socket.grSocket.setParentItem(None)
            socket.grSocket = None
            if socket.hasEdge():
                for wire in socket.wires:
                    wire.remove()

        self.node.removeSockets(type)
        if DEBUG: print(" - everything is done.")

    def serialize(self):
        return OrderedDict([
            ('id', self.id),
            ('index', self.index),
            ('multi_wire', self.is_multi_wire),
            ('position', self.position),
            ('socket_type', self.socket_type),
        ])

    def deserialize(self, data, hashmap={}):
        self.id = data['id']
        # self.is_multi_wire = data['multi_wire']
        hashmap[data['id']] = self

        return True
