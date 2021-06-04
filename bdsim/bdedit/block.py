from bdedit.block_graphics_block import GraphicsBlock
from bdedit.block_param_window import ParamWindow
from bdedit.block_socket import *
from collections import OrderedDict
import json

LEFT = 1
TOP = 2
RIGHT = 3
BOTTOM = 4

INPUT = 1
OUTPUT = 2

blocklist = []

DEBUG = False


class Block(Serializable):
    def __init__(self, scene, window, name="Unnamed Block", pos=(0, 0)):
        super().__init__()

        self.scene = scene
        self.window = window

        self.title = name
        self.position = pos
        self.block_type = None

        self.variables = []
        self.icon = ''
        self.inputs = []
        self.outputs = []

        self._param_visible = False

        self.socket_spacing = 20

    def __str__(self):
        return "<Edge %s..%s>" % (hex(id(self))[2:5], hex(id(self))[-3:])

    def _createBlock(self, inputs, outputs):
        allowed_to_generate = \
            (isinstance(self, SourceBlock) and self.__class__ is not SourceBlock) or \
            (isinstance(self, SinkBlock) and self.__class__ is not SinkBlock) or \
            (isinstance(self, FunctionBlock) and self.__class__ is not FunctionBlock) or \
            (isinstance(self, TransferBlock) and self.__class__ is not TransferBlock) or \
            (isinstance(self, DiscreteBlock) and self.__class__ is not DiscreteBlock) or \
            (isinstance(self, INPORTBlock) and self.__class__ is not INPORTBlock) or \
            (isinstance(self, OUTPORTBlock) and self.__class__ is not OUTPORTBlock) or \
            (isinstance(self, SUBSYSTEMBlock) and self.__class__ is not SUBSYSTEMBlock)

        if allowed_to_generate:
            self.grBlock = GraphicsBlock(self)

            self.makeInputSockets(inputs, LEFT)
            self.makeOutputSockets(outputs, RIGHT)

            self.scene.addBlock(self)
            self.scene.grScene.addItem(self.grBlock)

            if self.variables:
                self._createParamWindow()
        else:
            print("This type of block cannot be spawned.")

    def _createParamWindow(self):
        self.parameterWindow = ParamWindow(self)
        self.parameterWindow.setVisible(self._param_visible)
        self.window.addWidget(self.parameterWindow, 1, 10, 9, 1)  # Adds paramWindow to window

    def makeInputSockets(self, inputs, position, socketType=INPUT):
        counter = 0
        while counter < inputs:
            socket = Socket(node=self, index=counter, position=position, socket_type=socketType)
            counter += 1
            self.inputs.append(socket)

        self.updateSocketSigns()

    def makeOutputSockets(self, outputs, position, socketType=OUTPUT):
        counter = 0
        while counter < outputs:
            socket = Socket(node=self, index=counter, position=position, socket_type=socketType)
            counter += 1
            self.outputs.append(socket)

    def toggleParamWindow(self):
        self.parameterWindow.setVisible(not self._param_visible)
        self._param_visible = not self._param_visible

    def closeParamWindow(self):
        self.parameterWindow.setVisible(False)
        self._param_visible = False

    # Updates the sign of the socket (+,-,*,/) if the block type is a Prod or Sum block
    def updateSocketSigns(self):
        if self.block_type == "Prod" or self.block_type == "Sum":
            # Update the signs of each input socket that corresponds to the signs given when making the block
            for variable in self.variables:
                if variable[0] == "Operations" or variable[0] == "Signs":
                    index = 0
                    for sign in variable[2]:
                        self.inputs[index].socket_sign = sign
                        index += 1

    # Sends all blocks to back then sends currently selected block to front
    def setFocusOfBlocks(self):
        for block in self.scene.blocks:
            block.grBlock.setZValue(0.0)
        self.grBlock.setZValue(1.0)

    @property
    def pos(self):
        return self.grBlock.pos()

    def setPos(self, x, y):
        self.grBlock.setPos(x, y)

    def setTitle(self, name=None):
        if name is not None:
            if name != self.title:
                if isinstance(name, str):
                    duplicates = self.scene.checkForDuplicates(name)

                    if not duplicates:
                        self.title = name
                        return
                    else:
                        # print("Block name already exists, please choose another")
                        return ["@DuplicateName@", name]
                else:
                    # print("Block name must be a string")
                    return "@InvalidType@"

    def setDefaultTitle(self, name, increment=None):
        block_name = name
        if isinstance(name, str):
            if increment is not None:
                block_name += " " + str(increment)
                increment += 1

            duplicates = self.scene.checkForDuplicates(block_name)

            if not duplicates:
                self.title = block_name
            else:
                if increment is None: self.setDefaultTitle(name, 1)
                else: self.setDefaultTitle(name, increment)

    def getSocketPosition(self, index, position):
        if position == LEFT:
            x = 0
            y = self.grBlock._padding + self.grBlock.edge_size + self.grBlock.title_height + index * self.socket_spacing
        elif position == RIGHT:
            x = self.grBlock.width
            y = self.grBlock._padding + self.grBlock.edge_size + self.grBlock.title_height + index * self.socket_spacing
        return [x, y]

    def updateSocketPositions(self):
        for i in range(0, len(self.inputs)):
            if self.inputs[i].position == LEFT: self.inputs[i].position = RIGHT
            else: self.inputs[i].position = LEFT
            [x, y] = self.getSocketPosition(i, self.inputs[i].position)
            self.inputs[i].grSocket.setPos(*[float(x), float(y)])

        for i in range(0, len(self.outputs)):
            if self.outputs[i].position == RIGHT: self.outputs[i].position = LEFT
            else: self.outputs[i].position = RIGHT
            [x,y] = self.getSocketPosition(i, self.outputs[i].position)
            self.outputs[i].grSocket.setPos(*[float(x), float(y)])

        self.updateConnectedEdges()

    def updateConnectedEdges(self):
        for socket in self.inputs + self.outputs:
            for wire in socket.wires:
                wire.updatePositions()

    def removeSockets(self, type):
        if type == "Input":
            self.inputs.clear()
        elif type == "Output":
            self.outputs.clear()

    def remove(self):
        if DEBUG: print("> Removing Block", self)
        if DEBUG: print(" - removing all wires from sockets")
        for socket in (self.inputs + self.outputs):
            for wire in socket.wires:
                wire.remove()
            # if socket.hasEdge():
                # if DEBUG: print("     - removing from socket:", socket, "wire:", socket.wires)
                # socket.wires.remove()
                
        if DEBUG: print(" - removing grBlock")
        self.scene.grScene.removeItem(self.grBlock)
        self.grBlock = None
        if DEBUG: print(" - removing parameterWindow")
        if self.parameterWindow:
            self.window.removeWidget(self.parameterWindow)
            self.parameterWindow = None
        if DEBUG: print(" - removing node from the scene")
        self.scene.removeBlock(self)
        if DEBUG: print(" - everything was done.")

    # Code adapted from https://stackoverflow.com/a/15721641
    # Decodes objects encoded with the TupleEncoder class
    @staticmethod
    def tuple_decoder(obj):
        # If an object is iterable (is a str, list, dict, tuple)
        try:
            # Decoder checks if the object has a '__tuple__' key
            if '__tuple__' in obj:
                # If so, converts items of that object into a tuple
                return tuple(obj['items'])
            else:
                # Otherwise returns the item
                return obj
        # Otherwise if object isn't iterable (is a int, float, boolean)
        except TypeError:
            return obj

    def serialize(self):
        special_encoder = TupleEncoder()
        inputs, outputs, variables = [], [], []
        for socket in self.inputs: inputs.append(socket.serialize())
        for socket in self.outputs: outputs.append(socket.serialize())
        for variable in self.variables: variables.append([variable[0], special_encoder.encode(variable[2])])
        return OrderedDict([
            ('id', self.id),
            ('block_type', self.block_type),
            ('title', self.title),
            ('pos_x', self.grBlock.scenePos().x()),
            ('pos_y', self.grBlock.scenePos().y()),
            ('icon', self.icon),
            ('inputs', inputs),
            ('outputs', outputs),
            ('variables', variables)
        ])

    def deserialize(self, data, hashmap={}):
        self.id = data['id']
        hashmap[data['id']] = self

        self.setPos(data['pos_x'], data['pos_y'])

        self.title = data['title']
        self.block_type = data['block_type']
        self.icon = data['icon']

        # When block is drawn, by default it is created with its allocated number of input/output sockets
        # When deserializing a block, we want the sockets to be in the locations where they were saved
        # Delete the default created input/output sockets to override with saved sockets
        if self.inputs:
            # RemoveSockets is a method accessible only through a socket, while self.inputs is a list of sockets
            # removeSockets removes all sockets associated with a block.
            self.inputs[0].removeSockets("Input")
        if self.outputs:
            # Same usage of removeSocket as above
            self.outputs[0].removeSockets("Output")

        self.inputs = []
        self.outputs = []

        for socket_data in data['inputs']:
            new_socket = Socket(node=self, index=socket_data['index'], position=socket_data['position'], socket_type=socket_data['socket_type'])
            new_socket.deserialize(socket_data, hashmap)
            self.inputs.append(new_socket)

        for socket_data in data['outputs']:
            new_socket = Socket(node=self, index=socket_data['index'], position=socket_data['position'], socket_type=socket_data['socket_type'])
            new_socket.deserialize(socket_data, hashmap)
            self.outputs.append(new_socket)

        # Iterator for variables
        i = 0
        for varName, varVal in data['variables']:
            if DEBUG: print("----------------------")
            if DEBUG: print("Cautionary check")
            if DEBUG: print("current value:", [self.variables[i][0], self.variables[i][1], self.variables[i][2]])
            if DEBUG: print("setting to value:", [varName, self.variables[i][1], self.tuple_decoder(varVal)])
            self.variables[i][0] = varName
            self.variables[i][2] = self.tuple_decoder(varVal)
            i += 1

        self._createParamWindow()

        return True


# Code adapted from https://stackoverflow.com/a/15721641
# JSON doesn't store tuples, hence this encoder converts a tuple into a dict with a '__tuple__' variable.
# Upon reading this variable, the decoder will convert the items in that dict into a tuple
class TupleEncoder(json.JSONEncoder):
    def encode(self, item):
        if isinstance(item, tuple):
            return {'__tuple__': True, 'items': item}
        elif isinstance(item, list):
            return [self.encode(e) for e in item]
        elif isinstance(item, dict):
            return {key: self.encode(value) for key, value in item.items()}
        else:
            return item


def block(cls):
    if issubclass(cls, Block):
        blocklist.append(cls)
    else:
        print("Error: @block used on a non Block subclass")


def blockname(cls):
    return cls.__name__.strip('_').upper()


class SourceBlock(Block):
    def __init__(self, scene, window, name="Unnamed Source Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.inputsNum = 0
        self.outputsNum = 1

    def numInputs(self):
        print(self.inputsNum)
        return self.inputsNum

    def numOutputs(self):
        print(self.outputsNum)
        return self.outputsNum


class SinkBlock(Block):
    def __init__(self, scene, window, name="Unnamed Sink Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.inputsNum = 1
        self.outputsNum = 0

    def numInputs(self):
        print(self.inputsNum)
        return self.inputsNum

    def numOutputs(self):
        print(self.outputsNum)
        return self.outputsNum


class FunctionBlock(Block):
    def __init__(self, scene, window, name="Unnamed Function Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.inputsNum = 1
        self.outputsNum = 1

    def numInputs(self):
        print(self.inputsNum)
        return self.inputsNum

    def numOutputs(self):
        print(self.outputsNum)
        return self.outputsNum


class TransferBlock(Block):
    def __init__(self, scene, window, name="Unnamed Transfer Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.inputsNum = 1
        self.outputsNum = 1

    def numInputs(self):
        print(self.inputsNum)
        return self.inputsNum

    def numOutputs(self):
        print(self.outputsNum)
        return self.outputsNum
    
    
class DiscreteBlock(Block):
    def __init__(self, scene, window, name="Unnamed Discrete Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.inputsNum = 1
        self.outputsNum = 1

    def numInputs(self):
        print(self.inputsNum)
        return self.inputsNum

    def numOutputs(self):
        print(self.outputsNum)
        return self.outputsNum


class INPORTBlock(Block):
    def __init__(self, scene, window, name="Unnamed INPORT Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.inputsNum = 0
        self.outputsNum = 1

    def numInputs(self):
        print(self.inputsNum)
        return self.inputsNum

    def numOutputs(self):
        print(self.outputsNum)
        return self.outputsNum


class OUTPORTBlock(Block):
    def __init__(self, scene, window, name="Unnamed OUTPORT Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.inputsNum = 1
        self.outputsNum = 0

    def numInputs(self):
        print(self.inputsNum)
        return self.inputsNum

    def numOutputs(self):
        print(self.outputsNum)
        return self.outputsNum


class SUBSYSTEMBlock(Block):
    def __init__(self, scene, window, name="Unnamed SUBSYSTEM Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.inputsNum = 1
        self.outputsNum = 1

    def numInputs(self):
        print(self.inputsNum)
        return self.inputsNum

    def numOutputs(self):
        print(self.outputsNum)
        return self.outputsNum
