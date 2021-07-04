# Library imports
import json
from collections import OrderedDict

# BdEdit imports
from bdsim.bdedit.block_socket import *
from bdsim.bdedit.block_param_window import ParamWindow
from bdsim.bdedit.block_graphics_block import GraphicsBlock

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

# List of auto-imported blocks
blocklist = []

# Variable for enabling/disabling debug comments
DEBUG = False


# =============================================================================
#
#   Defining the parent Block Class, which is inherited by all blocks
#
# =============================================================================
class Block(Serializable):
    """
    The ``Block`` Class extends the ``Serializable`` Class from BdEdit, and
    defines how a block is represented, and has all the necessary methods
    for creating, manipulating and interacting with a block.

    This class includes information about the blocks':

    - name;
    - type;
    - appearance;
    - on-screen positioning;
    - parameters, and their values;
    - number of inputs and outputs.
    """

    # -----------------------------------------------------------------------------
    def __init__(self, scene, window, name="Unnamed Block", pos=(0, 0)):
        """
        This method initializes an instance of the ``Block`` Class.
        It maps the following internal parameters of the block, initializing
        them to their defaults values. These are overwritten when an instance of
        the grandchild block is created. The parameters are defined as:


        - title: the name of the ``Block``.
          This defaults to the name of the name of the grandchild class, and
          is incremented if an instance with the same default name already exists.

        - type: the type of ``Block``.
          This defaults to the type of the grandchild class, and is determined
          through calling blockname(self.__class__) when a grandchild class is created.

        - icon: the icon for this ``Block``.
          This is a locally referenced string filepath, defined within the grandchild class.

        - inputs: a list of containing input ``Sockets`` relating to this ``Block``.
          The number of input sockets is restricted to 0 or n based on the inputsNum
          variable defined within the child class.

        - outputs: a list of containing output ``Sockets`` relating to this ``Block``.
          The number of output sockets is restricted to 0 or n based on the outputsNum
          variable defined within the child class.

        - parameters: a list of editable parameters relating to this ``Block``.
          This defaults to the list defined within the grandchild class, but follows
          the following structure of being a list of lists, where each 'lists' is a list
          defining the parameter as below:

          - parameters = ["name", type, value, [restrictions]]
            e.g. parameters = [["Gain", float, gain, []], ["Premul", bool, premul, []]]

          - name: is the name of the variable as a string
          - type: is the required type the variable should be (e.g. int, str, float)
          - value: is the default value the variable is set to should one not be provided
          - restrictions: is a list (can be list of lists) containing further restrictions
            applied to the parameter. These restrictions follow the following structure, of
            being a list with a string as the first list element, followed by a list of
            conditions being applied to the parameter as the second list element:

            - restriction = ["restriction name", [condition(s)]]

            - restriction name: can be only one of the following "keywords", "range", "type"
              or "signs".
            - condition(s): differ based on the restriction name used, and will be of the
              following format:

              - for keywords: a list of string words the parameter must exactly match to,
                e.g. ["keywords", ["sine", "square", "triangle"]]
              - for range: a list containing a min and max allowable value for this parameter,
                e.g. ["range", [0, 1000]] or ["range", [-math.inf, math.inf]]
              - for type: a list containing alternative types, with the last value repeating
                the initial type required for this parameter,
                e.g. ["type", [type(None), tuple]] (initial type = tuple) or ["type", [type(None), bool]] (initial type = bool)
              - for signs: a list containing each allowable character this parameter can match,
                e.g. ["signs", ["*", "/"]] or ["signs", ["+", "-"]]
                currently this is used for drawing signs along certain input sockets, so only these characters are supported,


        :param scene: a scene (or canvas) in which the Block is stored and
                      shown (or painted into). Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located
                       in the bdedit window. Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param name: set to grandchild class's default name "__class__.__name__ Block" when it is created
        :type name: str, optional
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``, defaults to (0,0)
        :type pos: tuple of 2-ints, optional
        """
        super().__init__()

        self.scene = scene
        self.window = window
        self.position = pos

        # Title and type of the block will be determined by the grandchild class
        self.title = name
        self.block_type = None

        # List will contain the user-editable parameters of the Block
        self.parameters = []
        # Local string file-path reference to the Blocks' icon
        self.icon = ''

        # Lists that will contain the input/output sockets of the Block
        self.inputs = []
        self.outputs = []

        # Variable for controlling whether or not a ParamWindow should be
        # displayed for this instance of a Block
        self._param_visible = False

        # Minimum spacing distance between Sockets
        self.socket_spacing = 20

    # -----------------------------------------------------------------------------
    def _createBlock(self, inputs, outputs):
        """
        This private method is inherited and called by the grandchild class, and
        should only be called once when the block is being created.

        It populates the block's internal parameters; calls for the block to be
        drawn; creates the input and output sockets of the block; adds it to be
        stored and drawn in the ``Scene``; and if the block has user-editable
        parameters, initializes the private _createParamWindow method to create a
        parameter window linked to editing this block instance's parameters.

        :param inputs: number of input ``Sockets`` to create for this ``Block``
        :type inputs: int, required
        :param outputs: number of output ``Sockets`` to create for this ``Block``
        :type outputs: int, required
        """

        # When a Block instance is created by the grandchild class, this variable determines if
        # that grandchild class is a subclass of one of the supported Block child classes (source, sink, etc)
        allowed_to_generate = \
            (isinstance(self, SourceBlock) and self.__class__ is not SourceBlock) or \
            (isinstance(self, SinkBlock) and self.__class__ is not SinkBlock) or \
            (isinstance(self, FunctionBlock) and self.__class__ is not FunctionBlock) or \
            (isinstance(self, TransferBlock) and self.__class__ is not TransferBlock) or \
            (isinstance(self, DiscreteBlock) and self.__class__ is not DiscreteBlock) or \
            (isinstance(self, INPORTBlock) and self.__class__ is not INPORTBlock) or \
            (isinstance(self, OUTPORTBlock) and self.__class__ is not OUTPORTBlock) or \
            (isinstance(self, SUBSYSTEMBlock) and self.__class__ is not SUBSYSTEMBlock)

        # If the variable 'allowed_to_generate' is true:
        # * the graphics of the blocks are generated,
        # * the input and output sockets are created and linked to the block,
        # * the block information is stored within the Scene class,
        # * the blocks' graphical information is stored within the graphical section of the Scene class
        # * if the block has user-editable parameters, then a parameter window is generated for this block
        if allowed_to_generate:
            self.grBlock = GraphicsBlock(self)

            self.makeInputSockets(inputs, LEFT)
            self.makeOutputSockets(outputs, RIGHT)

            self.scene.addBlock(self)
            self.scene.grScene.addItem(self.grBlock)

            if self.parameters:
                self._createParamWindow()

        # Otherwise if 'allowed_to_generate' is false:
        # A message signifying that this Block type is not supported, is printed to console.
        else:
            print("This type of block cannot be spawned.")

    # -----------------------------------------------------------------------------
    def _createParamWindow(self):
        """
            This private method takes no inputs, and should only be called once
            when generating a parameter window for it's associated block.

            It creates an instance of the ``ParamWindow`` class relating to
            this ``Block`` and references the 'self.window' variable stored within
            the ``Block`` class to make the parameter window part of the bdedit window.
        """

        # Creates a parameter window variable associated to this Block instance, and sets its
        # visibility based on the private 'self._param_visible' variable (True - allowed to display
        # False - cannot be displayed).
        self.parameterWindow = ParamWindow(self)
        self.parameterWindow.setVisible(self._param_visible)
        # ParamWindow instance is added to the application window
        self.window.addWidget(self.parameterWindow, 1, 10, 9, 1)

    # -----------------------------------------------------------------------------
    def makeInputSockets(self, inputs, position, socketType=INPUT):
        """
        This method is called to create a number of input ``Sockets`` for this ``Block``.

        :param inputs: number of input sockets to create
        :type inputs: int, required
        :param position: an enum representing the position of where to place
        the ``Socket`` on the ``Block`` currently only supports LEFT (1), or RIGHT (3).
        :type position: enumerate, required
        :param socketType: an enum representing the type of ``Socket`` to create.
        This is used for the graphics of the socket, but was also intended to be used
        to reduce two methods for creating input and output sockets, to a single method.
        :type socketType: enumerate, optional, defaults to INPUT(1)
        """

        # Input sockets are created, starting from index 0 to the number of 'inputs'
        # For each index:
        # * an instance of a Socket Class is created, which:
        #   ** relates this Socket instance to this Block instance
        #   ** sets the 'index' of this Socket as the current index (counter)
        #   ** sets the 'position' of this Socket to the given position (LEFT or RIGHT)
        #   ** sets the 'socketType' of this Socket to the given socketType (INPUT by default)
        # * the instance is appended to this Block's list of inputs
        counter = 0
        while counter < inputs:
            socket = Socket(node=self, index=counter, position=position, socket_type=socketType)
            counter += 1
            self.inputs.append(socket)

        # Some Blocks (PROD and SUM) have additional logic for drawing signs alongside
        # the input sockets. The method below is checks and applies that logic if required.
        self.updateSocketSigns()

    # -----------------------------------------------------------------------------
    def makeOutputSockets(self, outputs, position, socketType=OUTPUT):
        """
        This method is called to create a number of outputs ``Sockets`` for this ``Block``.

        :param outputs: number of output sockets to create
        :type outputs: int, required
        :param position: an enum representing the position of where to place
        the ``Socket`` on the ``Block`` currently only supports LEFT (1), or RIGHT (3).
        :type position: enumerate, required
        :param socketType: an enum representing the type of ``Socket`` to create.
        This is used for the graphics of the socket, but was also intended to be used
        to reduce two methods for creating input and output sockets, to a single method.
        :type socketType: enumerate, optional, defaults to OUTPUT(2)
        """

        # Output sockets are created, starting from index 0 to the number of 'outputs'
        # For each index:
        # * an instance of a Socket Class is created, which:
        #   ** relates this Socket instance to this Block instance
        #   ** sets the 'index' of this Socket as the current index (counter)
        #   ** sets the 'position' of this Socket to the given position (LEFT or RIGHT)
        #   ** sets the 'socketType' of this Socket to the given socketType (OUTPUT by default)
        # * the instance is appended to this Block's list of outputs
        counter = 0
        while counter < outputs:
            socket = Socket(node=self, index=counter, position=position, socket_type=socketType)
            counter += 1
            self.outputs.append(socket)

    # -----------------------------------------------------------------------------
    def toggleParamWindow(self):
        """
        This method toggles the visibility of the ``ParamWindow`` of this ``Block``
        """

        # Sets the visibility of the parameter window to opposite of what the
        # variable 'self._param_visible' is set to, and flips the boolean state of
        # that variable (True -> False, or False -> True)
        self.parameterWindow.setVisible(not self._param_visible)
        self._param_visible = not self._param_visible

    # -----------------------------------------------------------------------------
    def closeParamWindow(self):
        """
        This method closes the ``ParamWindow`` of this ``Block``
        """

        # Sets the visibility of the parameter window to False
        # and sets 'self._param_visible' False
        self.parameterWindow.setVisible(False)
        self._param_visible = False

    # -----------------------------------------------------------------------------
    def updateSocketSigns(self):
        """
        As some Blocks - namely the ``PROD`` and ``SUM`` Blocks - have additional logic for
        drawing signs (+,-,*,/) alongside the input sockets, this method updates
        these signs of the socket, if the block type is a ``PROD`` or ``SUM`` Block
        """

        # Checks if the block type is a Prod or Sum block
        if self.block_type == "Prod" or self.block_type == "Sum":

            # Iterates through user-editable parameters stored within the block and checks
            # if one by the name of 'Operations' or 'Signs' exists (these block types should
            # have them). These parameters hold characters (+,-,*,/) representing what signs
            # should be displayed and the order they should be displayed in (left to right
            # in the parameter, representing top to bottom when displayed on the block).
            # Parameter is represented as a list of 4 items:
            # parameter = [name, type, value, special_conditions]
            for parameter in self.parameters:

                # If parameter name is equal to:
                if parameter[0] == "Operations" or parameter[0] == "Signs":
                    index = 0

                    # Sets the socket_sign of Socket within the block, equal to the respective
                    # character (sign) stored within either the 'Operations' or 'Signs' parameter.
                    # Note, since this method is only ever called after the number of input sockets
                    # has been created, or after this number has been updated (when the user edits
                    # the number of signs to display), the number of input sockets will always
                    # exactly match the number of signs stored within the parameter.
                    for sign in parameter[2]:
                        self.inputs[index].socket_sign = sign
                        index += 1

    # -----------------------------------------------------------------------------
    def setFocusOfBlocks(self):
        """
        This method sends all ``Block`` instances within the ``Scene`` to back
        and then sends the currently selected ``Block`` instance to front.
        """

        # Iterates through each Block within block list stored in the Scene Class
        # and sets the graphical component of each block to a zValue of 0.
        for block in self.scene.blocks:
            block.grBlock.setZValue(0.0)

        # Then sets the graphical component of the currently selected block to a
        # zValue of 1, which makes it display above all other blocks on screen.
        self.grBlock.setZValue(1.0)

    # -----------------------------------------------------------------------------
    @property
    def pos(self):
        """
        This method is called to access the positional coordinates of this ``Block``
        in terms of where it is displayed within the ``Scene``

        :return: the (x,y) coordinates of this ``Block``
        :rtype: tuple (int, int)
        """
        return self.grBlock.pos()

    # -----------------------------------------------------------------------------
    def setPos(self, x, y):
        """
        This method is called to set the positional coordinates of this ``Block``
        in terms of where it is displayed within the ``Scene``

        :param x: the x coordinate of this ``Block``
        :type x: int, required
        :param y: the y coordinate of this ``Block``
        :type y: int, required
        """
        self.grBlock.setPos(x, y)

    # -----------------------------------------------------------------------------
    def setTitle(self, name=None):
        """
        This method is called to determine if a this ``Block`` can be named with the
        provided name. It applies logic to check if the given name of type `str`,
        and if no other ``Block`` instance already has the given name. If either of
        these conditions are not met, the user will be notified to provide a
        different name.

        :param name: given name to be set for this ``Block``, defaults to None if
        not provided
        :type name: str, optional
        :return: - nothing (if name successfully set);
                 - [duplicate error message, given name] (if duplicate found);
                 - invalid type error message (if name is not of type `str`).
        :rtype: - nothing (if name successfully set);
                - list of [str, str] (if duplicate found);
                - str (if name is not of type `str`).
        """

        # This method should only do something, if a name is given for the block
        # Hence, only do something if the name is not None
        if name is not None:
            # The name only needs to be checked to be updated if it's different
            # the this blocks' current name (title)
            if name != self.title:
                # If the given name is of type str
                if isinstance(name, str):
                    # Check if the given name already exists for any other block
                    duplicates = self.scene.checkForDuplicates(name)

                    # If the given name is not found to be a duplicate
                    if not duplicates:
                        # Set this blocks' title to the given name
                        self.title = name
                        return
                    # Else the given name is a duplicate
                    else:
                        # So return a list containing a duplicate error message and the given name
                        return ["@DuplicateName@", name]

                # Else, the type of the given name is invalid
                else:
                    return "@InvalidType@"

    # -----------------------------------------------------------------------------
    def setDefaultTitle(self, name, increment=None):
        """
        This method is called to give a block a generic name, and if that name
        already exists, to increment it by 1.

        :param name: the generic name to be given to this ``Block``
        :type name: str, required
        :param increment: the number to display next to the generic name, to make
        it unique. Defaults to None if this is the first instance of this block type.
        :type increment: int, optional
        """

        # Creates a temporary copy of the given name
        block_name = name

        # If the given name is of type str
        if isinstance(name, str):
            # If this isn't the first instance of this block type, increment will
            # be a number greater than 0, and this if statement will be run.
            if increment is not None:
                # The temporary copy of the given name has the increment added to it
                # to later check if that will make it unique
                block_name += " " + str(increment)
                # The increment is increased by one in case the previous line doesn't
                # make the name unique
                increment += 1

            # The copy of the given name is checked against being a duplicate
            duplicates = self.scene.checkForDuplicates(block_name)

            # If it is not a duplicate, the name of the current block is set to
            # the copy of the given name (this will be with an increment, or the
            # original given name if this is the first instance of this block type).
            if not duplicates:
                self.title = block_name
            # Else, it is a duplicate, and this method will call itself to increment
            # the given name and check against that name being a duplicate, until
            # a non-duplicate generic name is found.
            else:
                # If this is a second instance of this block type (hence the increment
                # would be None), this method calls itself with the increment set to 1
                if increment is None: self.setDefaultTitle(name, 1)
                # Else, this is more than a second instance of this block type, and
                # the increment would of already been set, and internally incremented.
                else: self.setDefaultTitle(name, increment)

    # -----------------------------------------------------------------------------
    def getSocketPosition(self, index, position):
        """
        This method is called to determine the coordinates of where a given ``Socket``
        should be positioned on the sides of the this ``Block``. The returned
        coordinates are in reference to the coordinates of this ``Block``.

        :param index: the index of this ``Socket`` in the list of sockets for this ``Block``
        :type index: int, required
        :param position: the (LEFT(1) or RIGHT(3)) side of the block this socket
        should be displayed on.
        :type position: enumerate, required
        :return: the [x,y] coordinates at which to place this ``Socket`` instance.
        :rtype: list of int, int
        """

        # If the position of the Socket is given to be on the LEFT of the block,
        # * x is returned as 0.
        # * y is returned as the index of this socket multiplied by the socket
        # spacing set within this block class, PLUS an offset, determined by the
        # height at which the block's title is placed below the block, and
        # the thickness of this block's outline, and how curved its corners are.
        if position == LEFT:
            x = 0
            y = self.grBlock._padding + self.grBlock.edge_size + self.grBlock.title_height + index * self.socket_spacing

        # Else, the position of the Socket is given to be on the RIGHT of the block,
        # * x is returned as the width of block.
        # * y is returned as above.
        elif position == RIGHT:
            x = self.grBlock.width
            y = self.grBlock._padding + self.grBlock.edge_size + self.grBlock.title_height + index * self.socket_spacing
        return [x, y]

    # -----------------------------------------------------------------------------
    def updateSocketPositions(self):
        """
        This method updates flips the position (LEFT or RIGHT) of where the
        input and output sockets needs to be placed within this ``Block``.
        After the positions of all the Blocks' sockets are updated,
        the updateConnectedEdges method is called to update the locations for
        where the wires connect to.
        """

        # Iterates through every input Socket this Block has
        for i in range(0, len(self.inputs)):
            # Flips the position of the input sockets (LEFT to RIGHT, or RIGHT to LEFT)
            if self.inputs[i].position == LEFT: self.inputs[i].position = RIGHT
            else: self.inputs[i].position = LEFT
            # Grabs the coordinates for where this Socket should be drawn
            [x, y] = self.getSocketPosition(i, self.inputs[i].position)
            # And sets the position of the current socket to these coordinates
            self.inputs[i].grSocket.setPos(*[float(x), float(y)])

        # Iterates through every output Socket this Block has
        for i in range(0, len(self.outputs)):
            # Flips the position of the output sockets (RIGHT to LEFT, or LEFT to RIGHT)
            if self.outputs[i].position == RIGHT: self.outputs[i].position = LEFT
            else: self.outputs[i].position = RIGHT
            # Grabs the coordinates for where this Socket should be drawn
            [x,y] = self.getSocketPosition(i, self.outputs[i].position)
            # And sets the position of the current socket to these coordinates
            self.outputs[i].grSocket.setPos(*[float(x), float(y)])

        self.updateConnectedEdges()

    # -----------------------------------------------------------------------------
    def updateConnectedEdges(self):
        """
        This method calls for any and all ``Wire`` instances that are connected to
        a ``Socket`` instance, to update where it is drawn TO and FROM.
        """

        # For each socket that exists in this block
        for socket in self.inputs + self.outputs:
            # Update the wire(s) connected to this socket
            for wire in socket.wires:
                wire.updatePositions()

    # -----------------------------------------------------------------------------
    def removeSockets(self, type):
        """
        This method removes all sockets of given type, associated with this ``Block``.

        :param type: the type of ``Socket`` to remove ("Input" for input type,
        "Output" for output type)
        :type type: str, required
        """

        # Depending on the given type, either the inputs or outputs list - stored within
        # the block - will be cleared.
        if type == "Input":
            self.inputs.clear()
        elif type == "Output":
            self.outputs.clear()

    # -----------------------------------------------------------------------------
    def remove(self):
        """
        This method is called to remove:

        - the selected ``Block`` instance;
        - any sockets associated with this Block;
        - any wires that were connected to this Blocks' sockets; and
        - the parameter window associated with this Block (if one existed).
        """

        # For each socket associated with this block, remove the connected wires
        if DEBUG: print("> Removing Block", self)
        if DEBUG: print(" - removing all wires from sockets")
        for socket in (self.inputs + self.outputs):
            for wire in socket.wires:
                wire.remove()

        # Remove the graphical representation of this block from the scene
        # This will also remove the associated graphical representation of the
        # blocks' sockets.
        if DEBUG: print(" - removing grBlock")
        self.scene.grScene.removeItem(self.grBlock)
        self.grBlock = None

        # Remove the blocks' parameter window if one existed
        if DEBUG: print(" - removing parameterWindow")
        if self.parameterWindow:
            self.window.removeWidget(self.parameterWindow)
            self.parameterWindow = None

        # Finally, call the removeBlock method from within the Scene, which
        # removes this block from the list of blocks stored in the Scene.
        if DEBUG: print(" - removing node from the scene")
        self.scene.removeBlock(self)
        if DEBUG: print(" - everything was done.")

    # -----------------------------------------------------------------------------
    @staticmethod
    def tuple_decoder(obj):
        """
        This method is called when deserializing a JSON file to generate a saved
        copy of the ``Scene`` with all the Blocks, Sockets and Wires. It's purpose
        is for decoding an encoded representation for a tuple (encoded with the
        ``TupleEncoder`` Class) when the JSON file was written. This decoder/encoder
        combination is required as JSON does not support saving under type tuple,
        and instead saves that information as a type list.

        This code has been adapted from: https://stackoverflow.com/a/15721641

        :param obj: the string object being decoded
        :type obj: Union [int, slice], required
        :return: the string object wrapped as a tuple (if decoded to have a __tuple__ key)
        the string object (otherwise)
        :rtype: - tuple (if decoded to have a __tuple__ key);
        - any (otherwise)
        """
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

    # -----------------------------------------------------------------------------
    def serialize(self):
        """
        This method is called to create an ordered dictionary of all of this Blocks'
        parameters - necessary for the reconstruction of this Block - as key-value
        pairs. This dictionary is later used for writing into a JSON file.

        :return: an ``OrderedDict`` of [keys, values] pairs of all essential ``Block``
                 parameters.
        :rtype: ``OrderedDict`` ([keys, values]*)
        """

        # Special encoder is an instance of TupleEncoder, which is used to encode any
        # parameter within this Block, that needs to be stored as type tuple.
        special_encoder = TupleEncoder()

        # The sockets associated with this block, have their own parameters that are
        # required for their reconstruction, so the serialize method within the
        # Socket class is called to package this information for each socket, also into
        # an OrderedDict. These ordered dictionaries are then stored in a temporary
        # inputs/outputs parameter and are returned as part of the OrderedDict of this Block.

        # Similarly, the user-editable parameters associated with this Block must be
        # remembered for the reconstruction of this block. However as some of them
        # need to be stored as tuples and JSON does not support this, hence the
        # TupleEncoder is used. Additionally, to reconstruct the Block's user-editable
        # parameters, only the name and value of these parameters are needed, as their
        # type and special_conditions should never change from their definition within
        # their Class. (As a reminder, parameter = [name, type, value, special_conditions])
        inputs, outputs, parameters = [], [], []
        for socket in self.inputs: inputs.append(socket.serialize())
        for socket in self.outputs: outputs.append(socket.serialize())
        for parameter in self.parameters: parameters.append([parameter[0], special_encoder.encode(parameter[2])])
        return OrderedDict([
            ('id', self.id),
            ('block_type', self.block_type),
            ('title', self.title),
            ('pos_x', self.grBlock.scenePos().x()),
            ('pos_y', self.grBlock.scenePos().y()),
            ('icon', self.icon),
            ('inputs', inputs),
            ('outputs', outputs),
            ('parameters', parameters)
        ])

    # -----------------------------------------------------------------------------
    def deserialize(self, data, hashmap={}):
        """
        This method is called to reconstruct a ``Block`` when loading a saved JSON
        file containing all relevant information to recreate the ``Scene`` with all
        its items.

        :param data: a Dictionary of essential information for reconstructing a ``Block``
        :type data: OrderedDict, required
        :param hashmap: a Dictionary for directly mapping the essential block parameters
                        to this instance of ``Block``, without having to individually map each parameter
        :type hashmap: Dict, required
        :return: True when completed successfully
        :rtype: Boolean
        """

        # The id of this Block is set to whatever was stored as its id in the JSON file.
        self.id = data['id']
        # The remaining parameters associated to this Block are mapped to itself
        hashmap[data['id']] = self
        # The position of the Block within the Scene, are set accordingly.
        self.setPos(data['pos_x'], data['pos_y'])

        # When block is drawn, by default it is created with its allocated number of input/output sockets.
        # When deserializing a block, we want the sockets to be in the locations where they were saved.
        # Hence, we must delete the default created input/output sockets to override them with the saved sockets.
        if self.inputs:
            # RemoveSockets is a method accessible only through a socket, while self.inputs is a list of sockets
            # 'removeSockets' removes all sockets associated with a block.
            self.inputs[0].removeSockets("Input")
        if self.outputs:
            # Same usage of 'removeSocket' as above
            self.outputs[0].removeSockets("Output")

        # The input and output lists for this Block are cleared
        self.inputs = []
        self.outputs = []

        # And the saved (input and output) sockets are written into these lists respectively,
        # deserializing the socket-relevant information while doing so.
        for socket_data in data['inputs']:
            new_socket = Socket(node=self, index=socket_data['index'], position=socket_data['position'], socket_type=socket_data['socket_type'])
            new_socket.deserialize(socket_data, hashmap)
            self.inputs.append(new_socket)

        for socket_data in data['outputs']:
            new_socket = Socket(node=self, index=socket_data['index'], position=socket_data['position'], socket_type=socket_data['socket_type'])
            new_socket.deserialize(socket_data, hashmap)
            self.outputs.append(new_socket)

        # The saved user-editable parameters associated with the Block written over the default
        # ones this instance of the block was created with after reconstruction.
        # Iterator for parameters
        i = 0
        for paramName, paramVal in data['parameters']:
            # If debug mode is enabled, this code will print to console to validate that the
            # parameters are being overwritten into the same location they were previously stored in.
            if DEBUG: print("----------------------")
            if DEBUG: print("Cautionary check")
            if DEBUG: print("current value:", [self.parameters[i][0], self.parameters[i][1], self.parameters[i][2]])
            if DEBUG: print("setting to value:", [paramName, self.parameters[i][1], self.tuple_decoder(paramVal)])
            self.parameters[i][0] = paramName
            self.parameters[i][2] = self.tuple_decoder(paramVal)
            i += 1

        self._createParamWindow()

        return True


# -----------------------------------------------------------------------------
def block(cls):
    """
    This method is called whenever a grandchild class of the ``Block`` is called,
    adding it to a list of usable blocks.

    This code has been adapted from: https://github.com/petercorke/bdsim/blob/bdedit/bdsim/components.py

    :param cls: the class of the ``Block`` Class's grandchild block Class.
    :type cls: Class, required
    """
    # If the given Block is a subclass of the Block Class, it is added to the
    # blocklist global variable
    if issubclass(cls, Block):
        blocklist.append(cls)
    # Otherwise an error message is printed to console
    else:
        print("Error: @block used on a non Block subclass")


# -----------------------------------------------------------------------------
def blockname(cls):
    """
    This method strips any underscores from a grandchild Class of the ``Block``
    Class, and capitalizes the Class.__name__ to be used as the the Class's name.

    This code has been adapted from: https://github.com/petercorke/bdsim/blob/bdedit/bdsim/bdsim.py

    :param cls: the class of the ``Block`` Class's grandchild block Class.
    :type cls: Class, required
    :return: a reformatted string of the block's class name
    :rtype: str
    """
    return cls.__name__.strip('_').upper()


# =============================================================================
#
#   Defining the TupleEncoder Class, which is used to encode block parameters
#   that need to be stored in JSON as tuples
#
# =============================================================================
class TupleEncoder(json.JSONEncoder):
    """
    This Class inherits JSONEncoder from the json library, and is used to encode
    user-editable parameters associated with a ``Block`` which need to be stored
    as a type tuple. This code is necessary as JSON does not support storing
    data as tuples. After the encoder has been used to serialize (save) the
    Block parameter data, when the Block is deserialized (loaded), this encoded
    representation of a tuple will be decoded and stored as a tuple.

    This code is adapted from: https://stackoverflow.com/a/15721641
    """

    def encode(self, item):
        """
        This method determines whether a given user-editable block parameter
        is of type tuple, and converts it to a dictionary with a "__tuple__"
        key with value `True` (signifying this parameter should be represented
        as a tuple), and an "item's" key with value `item` (this being the
        value of the user-editable parameter).

        :param item: the user-editable parameter's value
        :type item: any
        :return: - a Dictionary defined as above (if item is tuple);
                 - the item (otherwise)
        :rtype: - Dict (if item is tuple);
                - any (otherwise)
        """
        
        # If the item value is of type tuple, return the item value as a 
        # dictionary (as mentioned above)
        if isinstance(item, tuple):
            return {'__tuple__': True, 'items': item}
        # If the item is stored within a list, check if any items within
        # the list need to be encoded as a tuple, and if so, recursively
        # call this method to wrap those items in a dictionary (as above mentioned)
        elif isinstance(item, list):
            return [self.encode(e) for e in item]
        # If the item is stored within a dict, check if any items within
        # the dict need to be encoded as a tuple, and if so, recursively
        # call this method to wrap those items in a dictionary (as above mentioned)
        elif isinstance(item, dict):
            return {key: self.encode(value) for key, value in item.items()}
        # Otherwise, return the item 
        else:
            return item


# =============================================================================
#
#   Defining the subclass's of the Block Class, referred to as child class of
#   the Block Class. These are inherited by their child classes, which are
#   referred to as grandchild classes of the Block Class.
#
# =============================================================================
class SourceBlock(Block):
    """
    The ``SourceBlock`` Class is a subclass of ``Block``, and referred to as a
    child class of ``Block``. It inherits all the methods and parameters of its
    parent class and controls the number of input or output ``Sockets`` any
    subclass (referred to as a grandchild class of ``Block``) that inherits it has.
    """

    def __init__(self, scene, window, name="Unnamed Source Block", pos=(0, 0)):
        """
        This method initializes an instance of the ``SourceBlock`` Class.

        :param scene: inherited through ``Block``
        :type scene: ``Scene``, required
        :param window: inherited through ``Block``
        :type window: ``QGridLayout``, required
        :param name: overwritten to the name of grandchild class's block name,
        defaults to "Unnamed Source Block"
        :type name: str, optional
        :param pos: inherited through ``Block``
        :type pos: tuple of 2-ints, optional
        """
        super().__init__(scene, window, name, pos)

        # Sets the default number of input/output sockets to the values below
        # A value of 0 prevents this block from having the respective (input/output) sockets
        # A value of 1 allows this block to have 1 or more of the respective (input/output) sockets
        self.inputsNum = 0
        self.outputsNum = 1

    def numInputs(self):
        """
        This method returns the number of input sockets this Block has.

        :return: number of input sockets associated with this Block.
        :rtype: int
        """
        return self.inputsNum

    def numOutputs(self):
        """
        This method returns the number of output sockets this Block has.

        :return: number of input sockets associated with this Block.
        :rtype: int
        """
        return self.outputsNum


# =============================================================================
class SinkBlock(Block):
    """
    The ``SinkBlock`` Class is a subclass of ``Block``, and referred to as a
    child class of ``Block``. It inherits all the methods and parameters of its
    parent class and controls the number of input or output ``Sockets`` any
    subclass (referred to as a grandchild class of ``Block``) that inherits it has.
    """
    def __init__(self, scene, window, name="Unnamed Sink Block", pos=(0, 0)):
        """
        This method initializes an instance of the ``SinkBlock`` Class.

        :param scene: inherited through ``Block``
        :type scene: ``Scene``, required
        :param window: inherited through ``Block``
        :type window: ``QGridLayout``, required
        :param name: overwritten to the name of grandchild class's block name,
        defaults to "Unnamed Sink Block"
        :type name: str, optional
        :param pos: inherited through ``Block``
        :type pos: tuple of 2-ints, optional
        """
        super().__init__(scene, window, name, pos)

        # Sets the default number of input/output sockets to the values below
        # A value of 0 prevents this block from having the respective (input/output) sockets
        # A value of 1 allows this block to have 1 or more of the respective (input/output) sockets
        self.inputsNum = 1
        self.outputsNum = 0

    def numInputs(self):
        """
        This method returns the number of input sockets this Block has.

        :return: number of input sockets associated with this Block.
        :rtype: int
        """
        return self.inputsNum

    def numOutputs(self):
        """
        This method returns the number of output sockets this Block has.

        :return: number of input sockets associated with this Block.
        :rtype: int
        """
        return self.outputsNum


# =============================================================================
class FunctionBlock(Block):
    """
    The ``FunctionBlock`` Class is a subclass of ``Block``, and referred to as a
    child class of ``Block``. It inherits all the methods and parameters of its
    parent class and controls the number of input or output ``Sockets`` any
    subclass (referred to as a grandchild class of ``Block``) that inherits it has.
    """
    def __init__(self, scene, window, name="Unnamed Function Block", pos=(0, 0)):
        """
        This method initializes an instance of the ``FunctionBlock`` Class.

        :param scene: inherited through ``Block``
        :type scene: ``Scene``, required
        :param window: inherited through ``Block``
        :type window: ``QGridLayout``, required
        :param name: overwritten to the name of grandchild class's block name,
        defaults to "Unnamed Function Block"
        :type name: str, optional
        :param pos: inherited through ``Block``
        :type pos: tuple of 2-ints, optional
        """
        super().__init__(scene, window, name, pos)

        # Sets the default number of input/output sockets to the values below
        # A value of 0 prevents this block from having the respective (input/output) sockets
        # A value of 1 allows this block to have 1 or more of the respective (input/output) sockets
        self.inputsNum = 1
        self.outputsNum = 1

    def numInputs(self):
        """
        This method returns the number of input sockets this Block has.

        :return: number of input sockets associated with this Block.
        :rtype: int
        """
        return self.inputsNum

    def numOutputs(self):
        """
        This method returns the number of output sockets this Block has.

        :return: number of input sockets associated with this Block.
        :rtype: int
        """
        return self.outputsNum


# =============================================================================
class TransferBlock(Block):
    """
    The ``TransferBlock`` Class is a subclass of ``Block``, and referred to as a
    child class of ``Block``. It inherits all the methods and parameters of its
    parent class and controls the number of input or output ``Sockets`` any
    subclass (referred to as a grandchild class of ``Block``) that inherits it has.
    """
    def __init__(self, scene, window, name="Unnamed Transfer Block", pos=(0, 0)):
        """
        This method initializes an instance of the ``TransferBlock`` Class.

        :param scene: inherited through ``Block``
        :type scene: ``Scene``, required
        :param window: inherited through ``Block``
        :type window: ``QGridLayout``, required
        :param name: overwritten to the name of grandchild class's block name,
        defaults to "Unnamed Transfer Block"
        :type name: str, optional
        :param pos: inherited through ``Block``
        :type pos: tuple of 2-ints, optional
        """
        super().__init__(scene, window, name, pos)

        # Sets the default number of input/output sockets to the values below
        # A value of 0 prevents this block from having the respective (input/output) sockets
        # A value of 1 allows this block to have 1 or more of the respective (input/output) sockets
        self.inputsNum = 1
        self.outputsNum = 1

    def numInputs(self):
        """
        This method returns the number of input sockets this Block has.

        :return: number of input sockets associated with this Block.
        :rtype: int
        """
        return self.inputsNum

    def numOutputs(self):
        """
        This method returns the number of output sockets this Block has.

        :return: number of input sockets associated with this Block.
        :rtype: int
        """
        return self.outputsNum


# =============================================================================
class DiscreteBlock(Block):
    """
    The ``DiscreteBlock`` Class is a subclass of ``Block``, and referred to as a
    child class of ``Block``. It inherits all the methods and parameters of its
    parent class and controls the number of input or output ``Sockets`` any
    subclass (referred to as a grandchild class of ``Block``) that inherits it has.
    """
    def __init__(self, scene, window, name="Unnamed Discrete Block", pos=(0, 0)):
        """
        This method initializes an instance of the ``DiscreteBlock`` Class.

        :param scene: inherited through ``Block``
        :type scene: ``Scene``, required
        :param window: inherited through ``Block``
        :type window: ``QGridLayout``, required
        :param name: overwritten to the name of grandchild class's block name,
        defaults to "Unnamed Discrete Block"
        :type name: str, optional
        :param pos: inherited through ``Block``
        :type pos: tuple of 2-ints, optional
        """
        super().__init__(scene, window, name, pos)

        # Sets the default number of input/output sockets to the values below
        # A value of 0 prevents this block from having the respective (input/output) sockets
        # A value of 1 allows this block to have 1 or more of the respective (input/output) sockets
        self.inputsNum = 1
        self.outputsNum = 1

    def numInputs(self):
        """
        This method returns the number of input sockets this Block has.

        :return: number of input sockets associated with this Block.
        :rtype: int
        """
        return self.inputsNum

    def numOutputs(self):
        """
        This method returns the number of output sockets this Block has.

        :return: number of input sockets associated with this Block.
        :rtype: int
        """
        return self.outputsNum


# =============================================================================
class INPORTBlock(Block):
    """
    The ``INPORTBlock`` Class is a subclass of ``Block``, and referred to as a
    child class of ``Block``. It inherits all the methods and parameters of its
    parent class and controls the number of input or output ``Sockets`` any
    subclass (referred to as a grandchild class of ``Block``) that inherits it has.
    """
    def __init__(self, scene, window, name="Unnamed INPORT Block", pos=(0, 0)):
        """
        This method initializes an instance of the ``INPORTBlock`` Class.

        :param scene: inherited through ``Block``
        :type scene: ``Scene``, required
        :param window: inherited through ``Block``
        :type window: ``QGridLayout``, required
        :param name: overwritten to the name of grandchild class's block name,
                     defaults to "Unnamed INPORT Block"
        :type name: str, optional
        :param pos: inherited through ``Block``
        :type pos: tuple of 2-ints, optional
        """
        super().__init__(scene, window, name, pos)

        # Sets the default number of input/output sockets to the values below
        # A value of 0 prevents this block from having the respective (input/output) sockets
        # A value of 1 allows this block to have 1 or more of the respective (input/output) sockets
        self.inputsNum = 0
        self.outputsNum = 1

    def numInputs(self):
        """
        This method returns the number of input sockets this Block has.

        :return: number of input sockets associated with this Block.
        :rtype: int
        """
        return self.inputsNum

    def numOutputs(self):
        """
        This method returns the number of output sockets this Block has.

        :return: number of input sockets associated with this Block.
        :rtype: int
        """
        return self.outputsNum


# =============================================================================
class OUTPORTBlock(Block):
    """
    The ``OUTPORTBlock`` Class is a subclass of ``Block``, and referred to as a
    child class of ``Block``. It inherits all the methods and parameters of its
    parent class and controls the number of input or output ``Sockets`` any
    subclass (referred to as a grandchild class of ``Block``) that inherits it has.
    """
    def __init__(self, scene, window, name="Unnamed OUTPORT Block", pos=(0, 0)):
        """
        This method initializes an instance of the ``OUTPORTBlock`` Class.

        :param scene: inherited through ``Block``
        :type scene: ``Scene``, required
        :param window: inherited through ``Block``
        :type window: ``QGridLayout``, required
        :param name: overwritten to the name of grandchild class's block name,
        defaults to "Unnamed OUTPORT Block"
        :type name: str, optional
        :param pos: inherited through ``Block``
        :type pos: tuple of 2-ints, optional
        """
        super().__init__(scene, window, name, pos)

        # Sets the default number of input/output sockets to the values below
        # A value of 0 prevents this block from having the respective (input/output) sockets
        # A value of 1 allows this block to have 1 or more of the respective (input/output) sockets
        self.inputsNum = 1
        self.outputsNum = 0

    def numInputs(self):
        """
        This method returns the number of input sockets this Block has.

        :return: number of input sockets associated with this Block.
        :rtype: int
        """
        return self.inputsNum

    def numOutputs(self):
        """
        This method returns the number of output sockets this Block has.

        :return: number of input sockets associated with this Block.
        :rtype: int
        """
        return self.outputsNum


# =============================================================================
class SUBSYSTEMBlock(Block):
    """
    The ``SUBSYSTEMBlock`` Class is a subclass of ``Block``, and referred to as a
    child class of ``Block``. It inherits all the methods and parameters of its
    parent class and controls the number of input or output ``Sockets`` any
    subclass (referred to as a grandchild class of ``Block``) that inherits it has.
    """
    def __init__(self, scene, window, name="Unnamed SUBSYSTEM Block", pos=(0, 0)):
        """
        This method initializes an instance of the ``SUBSYSTEMBlock`` Class.

        :param scene: inherited through ``Block``
        :type scene: ``Scene``, required
        :param window: inherited through ``Block``
        :type window: ``QGridLayout``, required
        :param name: overwritten to the name of grandchild class's block name,
        defaults to "Unnamed SUBSYSTEM Block"
        :type name: str, optional
        :param pos: inherited through ``Block``
        :type pos: tuple of 2-ints, optional
        """
        super().__init__(scene, window, name, pos)

        # Sets the default number of input/output sockets to the values below
        # A value of 0 prevents this block from having the respective (input/output) sockets
        # A value of 1 allows this block to have 1 or more of the respective (input/output) sockets
        self.inputsNum = 1
        self.outputsNum = 1

    def numInputs(self):
        """
        This method returns the number of input sockets this Block has.

        :return: number of input sockets associated with this Block.
        :rtype: int
        """
        return self.inputsNum

    def numOutputs(self):
        """
        This method returns the number of output sockets this Block has.

        :return: number of input sockets associated with this Block.
        :rtype: int
        """
        return self.outputsNum
