# Library imports
import os
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
    def __init__(self, scene, window, pos=(0, 0)):
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
        :param title: set to grandchild class's default name "__class__.__name__ Block" when it is created
        :type title: str, optional
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``, defaults to (0,0)
        :type pos: tuple of 2-ints, optional
        """

        super().__init__()
        self.scene = scene
        self.window = window
        self.position = pos

        # Set block's orientation to be facing towards the right by default. If flipped is True, this means block is facing left
        self.flipped = False

        try:
            self.setDefaultTitle(self.title)
        except AttributeError:
            # When trying to set title of connector block, it will throw an attribute error
            # This is fine, as connector block isn't supposed to have a title
            # print("block.py -> Error occured while setting default title")
            pass

        # Lists that will contain the input/output sockets of the Block
        self.inputs = []
        self.outputs = []

        # Variable for controlling whether or not a ParamWindow should be
        # displayed for this instance of a Block
        self._param_visible = False

        # Initially, parameterWindow is set to None, later replaced by the ParamWindow class, if block should have one
        self.parameterWindow = None

        # Minimum spacing distance between Sockets
        self.socket_spacing = 20

        # print("creating block instance - after:")
        # [print(item) for item in self.__dict__.items()]
        # print("_______________________________________")

        # self._createBlock(self.inputsNum, self.outputsNum)

        # print("after block instance made:")
        # [print(item) for item in self.__dict__.items()]
        # print("_______________________________________")

    # Todo - update docstring and inline comments
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

        # * the graphics of the blocks are generated,
        # * the input and output sockets are created and linked to the block,
        # * the block information is stored within the Scene class,
        # * the blocks' graphical information is stored within the graphical section of the Scene class
        # * if the block has user-editable parameters, then a parameter window is generated for this block
        # if allowed_to_generate:
        self.grBlock = GraphicsBlock(self)

        self.makeInputSockets(inputs, LEFT)
        self.makeOutputSockets(outputs, RIGHT)

        self.scene.addBlock(self)
        self.scene.grScene.addItem(self.grBlock)

        self._createParamWindow()

        self.scene.has_been_modified = True

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
        # visibility based on the private 'self._param_visible' variable
        # (True - allowed to display, False - cannot be displayed).
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
            try:
                if self.input_names:
                    socket = Socket(
                        node=self,
                        index=counter,
                        position=position,
                        socket_type=socketType,
                        socket_label=self.input_names[counter],
                    )
                else:
                    socket = Socket(
                        node=self,
                        index=counter,
                        position=position,
                        socket_type=socketType,
                    )
            except (AttributeError, IndexError):
                socket = Socket(
                    node=self, index=counter, position=position, socket_type=socketType
                )
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
            try:
                if self.output_names:
                    socket = Socket(
                        node=self,
                        index=counter,
                        position=position,
                        socket_type=socketType,
                        socket_label=self.output_names[counter],
                    )
                else:
                    socket = Socket(
                        node=self,
                        index=counter,
                        position=position,
                        socket_type=socketType,
                    )
            except (AttributeError, IndexError):
                socket = Socket(
                    node=self, index=counter, position=position, socket_type=socketType
                )
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
        if self.parameterWindow:
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
        if (
            self.block_type == "PROD"
            or self.block_type == "SUM"
            or self.block_type == "Prod"
            or self.block_type == "Sum"
        ):

            # Iterates through user-editable parameters stored within the block and checks
            # if one by the name of 'Operations' or 'Signs' exists (these block types should
            # have them). These parameters hold characters (+,-,*,/) representing what signs
            # should be displayed and the order they should be displayed in (left to right
            # in the parameter, representing top to bottom when displayed on the block).
            # Parameter is represented as a list of 4 items:
            # parameter = [name, type, value, special_conditions]
            for parameter in self.parameters:
                # If parameter name is equal to:
                if parameter[0] == "ops" or parameter[0] == "signs":
                    index = 0

                    # print("\nblock: updatingSocketSigns()")
                    # [print(item) for item in self.__dict__.items()]
                    # print("_______________________________________\n")

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
                if increment is None:
                    self.setDefaultTitle(name, 1)
                # Else, this is more than a second instance of this block type, and
                # the increment would of already been set, and internally incremented.
                else:
                    self.setDefaultTitle(name, increment)

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
            y = (
                self.grBlock._padding
                + self.grBlock.edge_size
                + self.grBlock.title_height
                + index * self.socket_spacing
            )

        # Else, the position of the Socket is given to be on the RIGHT of the block,
        # * x is returned as the width of block.
        # * y is returned as above.
        elif position == RIGHT:
            x = self.grBlock.width
            y = (
                self.grBlock._padding
                + self.grBlock.edge_size
                + self.grBlock.title_height
                + index * self.socket_spacing
            )
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
            if self.inputs[i].position == LEFT:
                self.inputs[i].position = RIGHT
            else:
                self.inputs[i].position = LEFT
            # Grabs the coordinates for where this Socket should be drawn
            [x, y] = self.getSocketPosition(i, self.inputs[i].position)
            # And sets the position of the current socket to these coordinates
            self.inputs[i].grSocket.setPos(*[float(x), float(y)])

        # Iterates through every output Socket this Block has
        for i in range(0, len(self.outputs)):
            # Flips the position of the output sockets (RIGHT to LEFT, or LEFT to RIGHT)
            if self.outputs[i].position == RIGHT:
                self.outputs[i].position = LEFT
            else:
                self.outputs[i].position = RIGHT
            # Grabs the coordinates for where this Socket should be drawn
            [x, y] = self.getSocketPosition(i, self.outputs[i].position)
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
    def updateWireRoutingLogic(self):
        """
        Wire routing logic is automatically determined by bdedit when moving blocks,
        however users can adjust certain segments of these wires. When the user
        interacts with these segments, the wire routing logic follows the custom
        routing path. When blocks are moved again after wires segments are adjusted
        by the user, the wiring logic will revert to following the automatic routing
        logic. This method updates which wires should be drawn following the automatic
        routing logic.
        """
        for socket in self.inputs + self.outputs:
            for wire in socket.wires:
                if wire:
                    # If both blocks connected by these wires are selected, don't do
                    # anything, as both are being moved in respects to each other,
                    # so no need to update wiring logic.

                    start_block = wire.start_socket.node
                    end_block = wire.end_socket.node

                    if (
                        start_block.grBlock.isSelected()
                        and end_block.grBlock.isSelected()
                    ):
                        pass
                        # wire.grWire.customlogicOverride = True
                        # start_block.updateSocketPositions()
                        # end_block.updateSocketPositions()

                    # Otherwise if only one block is selected, update the wiring logic
                    # to be displayed based on the automatic wire routing logic.
                    else:
                        wire.grWire.customlogicOverride = False

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
        if DEBUG:
            print("> Removing Block", self)
        if DEBUG:
            print(" - removing all wires from sockets")
        for socket in self.inputs + self.outputs:
            for wire in socket.wires.copy():
                # for wire in socket.wires:
                if DEBUG:
                    print("    - removing from socket:", socket, "wire:", wire)
                wire.remove()

        # Remove the graphical representation of this block from the scene
        # This will also remove the associated graphical representation of the
        # blocks' sockets.
        if DEBUG:
            print(" - removing grBlock")
        self.scene.grScene.removeItem(self.grBlock)
        self.grBlock = None

        # Remove the blocks' parameter window if one existed
        if DEBUG:
            print(" - removing parameterWindow")
        if self.parameterWindow:
            self.window.removeWidget(self.parameterWindow)
            self.parameterWindow = None

        # Finally, call the removeBlock method from within the Scene, which
        # removes this block from the list of blocks stored in the Scene.
        if DEBUG:
            print(" - removing block from the scene")
        self.scene.removeBlock(self)
        if DEBUG:
            print(" - everything was done.")

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
        if self.block_type in ["Connector", "CONNECTOR"]:
            inputs, outputs, parameters = [], [], []
            for socket in self.inputs:
                inputs.append(socket.serialize())
            for socket in self.outputs:
                outputs.append(socket.serialize())
            return OrderedDict(
                [
                    ("id", self.id),
                    ("block_type", self.block_type),
                    ("pos_x", self.grBlock.scenePos().x()),
                    ("pos_y", self.grBlock.scenePos().y()),
                    ("inputs", inputs),
                    ("outputs", outputs),
                ]
            )
        else:
            inputs, outputs, parameters = [], [], []
            for socket in self.inputs:
                inputs.append(socket.serialize())
            for socket in self.outputs:
                outputs.append(socket.serialize())
            for parameter in self.parameters:
                parameters.append([parameter[0], parameter[2]])

            return OrderedDict(
                [
                    ("id", self.id),
                    ("block_type", self.block_type),
                    ("title", self.title),
                    ("pos_x", self.grBlock.scenePos().x()),
                    ("pos_y", self.grBlock.scenePos().y()),
                    ("width", self.width),
                    ("height", self.height),
                    ("flipped", self.flipped),
                    ("inputsNum", self.inputsNum),
                    ("outputsNum", self.outputsNum),
                    ("inputs", inputs),
                    ("outputs", outputs),
                    ("parameters", parameters),
                ]
            )

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
        self.id = data["id"]

        try:
            # The remaining parameters associated to this Block are mapped to itself
            # hashmap[data['id']] = self

            if self.block_type not in ["Connector", "CONNECTOR"]:
                self.title = data["title"]
                self.inputsNum = data["inputsNum"]
                self.outputsNum = data["outputsNum"]
                self.width = data["width"]
                self.height = data["height"]

                # If a model contains data on whether a block should be flipped, assign variable to that value
                # If error occurs, model doesn't contain this variable, so ignore
                try:
                    if data["flipped"]:
                        self.flipped = data["flipped"]
                except KeyError:
                    pass

            # The position of the Block within the Scene, are set accordingly.
            self.setPos(data["pos_x"], data["pos_y"])

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

            # The saved user-editable parameters associated with the Block, are written over the default ones
            # this instance of the block was created with, after reconstruction.
            # Iterator for parameters
            if self.block_type not in ["Connector", "CONNECTOR"]:
                i = 0

                for paramName, paramVal in data["parameters"]:
                    # If debug mode is enabled, this code will print to console to validate that the
                    # parameters are being overwritten into the same location they were previously stored in.
                    if DEBUG:
                        print("----------------------")
                    if DEBUG:
                        print("Cautionary check")
                    if DEBUG:
                        print(
                            "current value:",
                            [
                                self.parameters[i][0],
                                self.parameters[i][1],
                                self.parameters[i][2],
                            ],
                        )
                    if DEBUG:
                        print(
                            "setting to value:",
                            [paramName, self.parameters[i][1], paramVal],
                        )
                    self.parameters[i][0] = paramName
                    self.parameters[i][2] = paramVal

                    # If there are subsystem, outport or inport blocks with labels for their sockets, extract that information into self.input_names and self.output_names as needed
                    if self.block_type in ["SUBSYSTEM", "OUTPORT", "INPORT"]:

                        if paramName == "inport labels":
                            if paramVal:
                                self.input_names = [str(j) for j in paramVal]

                        if paramName == "outport labels":
                            if paramVal:
                                self.output_names = [str(j) for j in paramVal]

                    i += 1

            # And the saved (input and output) sockets are written into these lists respectively,
            # deserializing the socket-relevant information while doing so.
            for i, socket_data in enumerate(data["inputs"]):
                try:
                    if self.input_names:
                        new_socket = Socket(
                            node=self,
                            index=socket_data["index"],
                            position=socket_data["position"],
                            socket_type=socket_data["socket_type"],
                            socket_label=self.input_names[i],
                        )
                    else:
                        new_socket = Socket(
                            node=self,
                            index=socket_data["index"],
                            position=socket_data["position"],
                            socket_type=socket_data["socket_type"],
                        )
                except (AttributeError, IndexError):
                    new_socket = Socket(
                        node=self,
                        index=socket_data["index"],
                        position=socket_data["position"],
                        socket_type=socket_data["socket_type"],
                    )
                new_socket.deserialize(socket_data, hashmap)
                self.inputs.append(new_socket)

            self.updateSocketSigns()

            for i, socket_data in enumerate(data["outputs"]):
                try:
                    if self.output_names:
                        new_socket = Socket(
                            node=self,
                            index=socket_data["index"],
                            position=socket_data["position"],
                            socket_type=socket_data["socket_type"],
                            socket_label=self.output_names[i],
                        )
                    else:
                        new_socket = Socket(
                            node=self,
                            index=socket_data["index"],
                            position=socket_data["position"],
                            socket_type=socket_data["socket_type"],
                        )
                except (AttributeError, IndexError):
                    new_socket = Socket(
                        node=self,
                        index=socket_data["index"],
                        position=socket_data["position"],
                        socket_type=socket_data["socket_type"],
                    )
                new_socket.deserialize(socket_data, hashmap)
                self.outputs.append(new_socket)

            if self.block_type not in ["Connector", "CONNECTOR"]:
                if self.parameters:
                    self._createParamWindow()

            # print("block type, name: ", [self.block_type, self.title])
            # print("input sockets:")
            # for socket in self.inputs:
            #     if socket:
            #         print("socket, id:", [socket, id(socket)])
            # print()
            # print("output sockets:")
            # for socket in self.outputs:
            #     if socket:
            #         print("socket, id:", [socket, id(socket)])
            # print("----------------------")

            return True
        except (ValueError, NameError, IndexError):
            print(
                f"error deserializing block [{self.block_type}::{self.title}] - maybe JSON file has old function parameters"
            )


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
    return cls.__name__.strip("_").upper()
