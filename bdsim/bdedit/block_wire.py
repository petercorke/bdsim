# Library imports
import time
import copy
from collections import OrderedDict

# BdEdit imports
from bdsim.bdedit.block_graphics_wire import *
from bdsim.bdedit.interface_serialize import Serializable

# =============================================================================
#
#   Defining and setting global variables
#
# =============================================================================
# Wire type variables for choosing between the 3 possible wire styles
WIRE_TYPE_DIRECT = 1
WIRE_TYPE_BEZIER = 2
WIRE_TYPE_STEP = 3

# Variable for enabling/disabling debug comments
DEBUG = False
DEBUG_OVERLAP = False


# =============================================================================
#
#   Defining the Wire Class, which is used to define the Wires that connect the
#   blocks via the sockets, each wire has a start socket and a end socket and a
#   wire type that defines how the wires will be drawn. The code also updates
#   the wires as the blocks are moved around so they stay connected.
#
# =============================================================================
class Wire(Serializable):
    """
    The ``Wire`` Class extends the ``Serializable`` Class from BdEdit, and
    defines how a wire is represented, and has all the necessary methods
    for creating, manipulating and interacting with a wire. This class connects
    start and end sockets to a created wire. The style of wire being drawn is
    also controlled by this Class:

    - a straight wire will have type DIRECT(1),
    - a curved or wave-like wire will have type BEZIER(2),
    - a stepped wire will have type STEP(3)

    This class includes information about the wires':

    - style;
    - end_socket;
    - start_socket;
    - point-to-point coordinates;
    - horizontal and vertical line segments;
    - intersection points with other wires (has been disabled).

    """

    # -----------------------------------------------------------------------------
    def __init__(self, scene, start_socket=None, end_socket=None, wire_type=3):
        """
        This method initializes an instance of the ``Wire`` Class.

        :param scene: a scene (or canvas) in which the Wire is stored and shown (or painted into). Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param start_socket: the start Socket of this Wire
        :type start_socket: Socket, optional, defaults to None (automatically set)
        :param end_socket: the end Socket of this Wire
        :type end_socket: Socket, optional, defaults to None (automatically set)
        :param wire_type: the wire style of this Wire (DIRECT(1), BEZIER(2), STEP(3))
        :type wire_type: enumerate, optional, defaults to STEP(3) (automatically set)
        """

        super().__init__()

        self.scene = scene

        # By default the Wire starts with no sockets, these are automatically
        # set by decorators when a Wire instance is created
        self._start_socket = None
        self._end_socket = None

        self.start_socket = start_socket
        self.end_socket = end_socket
        self.wire_type = wire_type

        self.wire_coordinates = []
        self.horizontal_segments = []
        self.vertical_segments = []
        self.intersections = []

        # Once created, the wire is added to the Scene
        self.scene.addWire(self)

    # -----------------------------------------------------------------------------
    @property
    def start_socket(self):
        """
        This method is a decorate that gets the start socket of this Wire.

        :return: the start Socket of this Wire
        :rtype: Socket
        """

        return self._start_socket

    # -----------------------------------------------------------------------------
    @start_socket.setter
    def start_socket(self, value):
        """
        This method is a decorator that sets the start socket of this Wire to the
        given value (which is a Socket).

        :param value: the Socket being assigned
        :type value: Socket
        """

        # If this wire was assigned to some socket before, delete this wire instance from that socket
        if self._start_socket is not None:
            self._start_socket.removeWire(self)

        # Assign a new start socket for this wire
        self._start_socket = value

        # Add this wire to the associated Socket (in the Socket Class)
        if self.start_socket is not None:
            self.start_socket.setConnectedEdge(self)

    # -----------------------------------------------------------------------------
    @property
    def end_socket(self):
        """
        This method is a decorate that gets the end socket of this Wire.

        :return: the end Socket of this Wire
        :rtype: Socket
        """

        return self._end_socket

    # -----------------------------------------------------------------------------
    @end_socket.setter
    def end_socket(self, value):
        """
        This method is a decorator that sets the end socket of this Wire to the
        given value (which is a Socket).

        :param value: the Socket being assigned
        :type value: Socket
        """

        # If this wire was assigned to some socket before, delete this wire instance from that socket
        if self._end_socket is not None:
            self._end_socket.removeWire(self)

        # Assign a new start socket for this wire
        self._end_socket = value

        # Add this wire to the associated Socket (in the Socket Class)
        if self.end_socket is not None:
            self.end_socket.setConnectedEdge(self)

    # -----------------------------------------------------------------------------
    @property
    def wire_type(self):
        """
        This method is a decorate that gets the wire type (or style) of this Wire.

        :return: the style of this Wire (DIRECT(1), BEZIER(2), STEP(3))
        :rtype: enumerate
        """

        return self._wire_type

    # -----------------------------------------------------------------------------
    @wire_type.setter
    def wire_type(self, value):
        """
        This method is a decorator that sets the wire type (or style) of this Wire to the
        given value (which is an enum). This method will determine how the wire is drawn.
        By default the wire type is set to draw STEP(3) wires, however other line styles
        can also be added here. The wire type dictate which corresponding GraphicsWire
        class is called to draw the wire.

        :param value: the wire type this Wire is being set to
        :type value: enumerate
        """

        # If this was already previously assigned, remove its GraphicsWire
        if hasattr(self, "grWire") and self.grWire is not None:
            self.scene.grScene.removeItem(self.grWire)

        # Assign a new wire type for this wire
        self._wire_type = value

        # Depending on the updated wire_type of this Wire, create a
        # instance of a GraphicsWire for this Wire
        if self.wire_type == WIRE_TYPE_DIRECT:
            self.grWire = GraphicsWireDirect(self)
        elif self.wire_type == WIRE_TYPE_STEP:
            self.grWire = GraphicsWireStep(self)
        else:
            self.grWire = GraphicsWireBezier(self)

        # Add the wire to the GraphicsScene
        self.scene.grScene.addItem(self.grWire)

        # If a start socket has been assigned, update where the Wire is drawn from
        if self.start_socket is not None:
            self.updatePositions()

    def setFocusOfWire(self):
        """
        This method sends all ``Wire`` instances within the ``Scene`` to back
        and then sends the currently selected ``Wire`` instance to front.
        """

        # Iterates through each wire within wire list stored in the Scene Class
        # and sets the graphical component of each wire to a zValue of -2.
        for wire in self.scene.wires:
            wire.grWire.setZValue(-2)

        # Then sets the graphical component of the currently selected wire to a
        # zValue of -1, which makes it display above all other wires on screen.
        self.grWire.setZValue(-1)

    # -----------------------------------------------------------------------------
    def updatePositions(self):
        """
        This method grabs the new positions of sockets on blocks as they are moved
        around within the scene, in order to determine the positions which the
        wire should connect. The redrawing of the wire to these positions will also
        be handled within this method.
        """

        # Grabs the current position (LEFT/RIGHT) of the starting socket
        # and sets the associated source (start) socket orientation (position) within
        # the GraphicsWire Class
        source_pos_orientation = self.start_socket.position
        self.grWire.setSourceOrientation(source_pos_orientation)

        # Grabs the position of the start socket and splits it into x,y coordinates
        # then assigns the position of the source (start) socket to these coordinates
        source_pos = self.start_socket.getSocketPosition()
        source_pos[0] += self.start_socket.node.grBlock.pos().x()
        source_pos[1] += self.start_socket.node.grBlock.pos().y()
        self.grWire.setSource(*source_pos)

        # If an end socket has been set for this wire, the same logic as above will
        # be applied, otherwise the destination (end) socket will be set to the coordinates
        # of the source (start) socket. This will be fixed when the wire is completed and remade.
        if self.end_socket is not None:
            destination_pos_orientation = self.end_socket.position
            self.grWire.setDestinationOrientation(destination_pos_orientation)

            end_pos = self.end_socket.getSocketPosition()
            end_pos[0] += self.end_socket.node.grBlock.pos().x()
            end_pos[1] += self.end_socket.node.grBlock.pos().y()
            self.grWire.setDestination(*end_pos)
        else:
            self.grWire.setDestination(*source_pos)

        # The wire is called to be updated
        self.grWire.update()

    # -----------------------------------------------------------------------------
    def remove_from_sockets(self):
        """
        This method will un-assign the start and end sockets of this Wire.
        """

        self.end_socket = None
        self.start_socket = None

    # -----------------------------------------------------------------------------
    def remove(self):
        """
        This method will remove the selected Wire from the Scene, un-assign
        the Sockets that related to it, and remove the Wire from these Sockets.
        """

        if self in self.scene.wires:
            if DEBUG:
                print("# Removing Wire", self)
            if DEBUG:
                print(" - hiding grWire")
            self.grWire.hide()

            if DEBUG:
                print(" - removing grWire")
            self.scene.grScene.removeItem(self.grWire)

            if DEBUG:
                print(" - removing wire from all sockets", self)
            self.remove_from_sockets()

            if DEBUG:
                print(" - removing wire from scene")
            try:
                self.scene.removeWire(self)
            except ValueError as e:
                print("Error removing wire:", e)
                pass

            if DEBUG:
                print(" - updating wire intersection points")
            if self.scene.wires:
                self.scene.wires[0].checkIntersections()

            if DEBUG:
                print(" - everything is done.")
        else:
            if DEBUG:
                print("# Wire already removed")

    # -----------------------------------------------------------------------------
    def serialize(self):
        """
        This method is called to create an ordered dictionary of all of this Wires'
        parameters - necessary for the reconstruction of this Wire - as key-value
        pairs. This dictionary is later used for writing into a JSON file.

        :return: an ``OrderedDict`` of [keys, values] pairs of all essential ``Wire``
                 parameters.
        :rtype: OrderedDict, ([keys, values]*)
        """

        if self.grWire.customlogicOverride:
            wire_coords = copy.copy(self.wire_coordinates)
        else:
            wire_coords = []

        return OrderedDict(
            [
                ("id", self.id),
                ("start_socket", self.start_socket.id),
                ("end_socket", self.end_socket.id),
                ("wire_type", self.wire_type),
                ("custom_routing", self.grWire.customlogicOverride),
                ("wire_coordinates", wire_coords),
            ]
        )

    # -----------------------------------------------------------------------------
    def deserialize(self, data, hashmap={}):
        """
        This method is called to reconstruct a ``Wire`` when loading a saved JSON
        file containing all relevant information to recreate the ``Scene`` with all
        its items.

        :param data: a Dictionary of essential information for reconstructing a ``Wire``
        :type data: OrderedDict, required
        :param hashmap: a Dictionary for directly mapping the essential wire variables
                        to this instance of ``Wire``, without having to individually map each variable
        :type hashmap: Dict, required
        :return: True when completed successfully
        :rtype: Boolean
        """

        # The id, and other variables of this Wire are set to whatever was stored
        # as its id and other variables in the JSON file.
        self.id = data["id"]
        # self.start_socket = data['start_socket']
        # self.end_socket = data['end_socket']
        self.start_socket = hashmap[data["start_socket"]]
        self.end_socket = hashmap[data["end_socket"]]
        self.wire_type = data["wire_type"]

        # For newer custom routing logic. If custom_routing exists within the saved JSON
        # data, and that variable is true, override the current wire_coordiantes of the wire
        # to the ones saved in the file.
        try:
            if data["custom_routing"]:
                self.grWire.customlogicOverride = data["custom_routing"]
                try:
                    if data["wire_coordinates"]:
                        # Wire coordinates is supposed to be a list of tuples, but in JSON they
                        # are stored as a list of lists. So convert the points to tuples
                        new_wire_coordinates = []
                        for point in data["wire_coordinates"]:
                            new_wire_coordinates.append(tuple(point))
                        self.grWire.updateWireCoordinates(new_wire_coordinates)
                except KeyError:
                    pass
        except KeyError:
            pass

        return True

    # -----------------------------------------------------------------------------
    def checkIntersections(self):
        """
        This method checks all active wires in the scene for intersections with other
        wires. This method will be called any time a mouse movement is detected in
        the GraphicsView class, which will cause the GraphicsScene to draw points
        at these intersections to separate the wires.

        To reduce computation for finding these intersection points, only vertical
        line segments of wires are checked for intersections. This is because an
        intersection point can only occur when a horizontal line segment of one wire
        meets a vertical line segment of another wire, and every single wire has a
        horizontal segment (as sockets are drawn on the LEFT or RIGHT sides of a Block).

        When this method is called, the current intersection points are deleted, as
        all wires are checked against in this method, and as such, any new (or previous)
        intersection points will be appended into a list of intersection points that
        is stored within the GraphicsScene Class.
        """

        # Clear the intersection list stored within the scene of any previous intersection points
        self.scene.intersection_list.clear()

        # Grab the number of wires currently in the scene
        number_of_wires = len(self.scene.wires)

        # If there are more than 1 wires, check for overlapping
        if number_of_wires > 1:

            # Iterate through each wire in list of wires
            for i in range(0, number_of_wires):

                # If the wire has a vertical segment, check intersections against other wires
                # Else ignore (as wire only has horizontal segments, and these cant create an intersection point
                # unless a vertical line passes through them)

                wire_has_vert = self.scene.wires[i].vertical_segments
                if wire_has_vert:

                    # Check each vertical segment against horizontal segments of other wires
                    for vertical_segment in wire_has_vert:

                        for j in range(0, number_of_wires):

                            # If j==i this means the same wire is being checked, ignore checking this wire (cannot overlap with itself)
                            if j == i:
                                pass
                            # Or if wire 'j' starts from the same socket as 'i', ignore this wire
                            elif (
                                self.scene.wires[j].start_socket
                                == self.scene.wires[i].start_socket
                            ):
                                pass
                            else:

                                # Iterate through each horizontal segments of the wire being checked
                                for horizontal_segment in self.scene.wires[
                                    j
                                ].horizontal_segments:

                                    # In a vertical wire with points [(a1,b1), (a2,b2)], the horizontal coordinates will be
                                    # equal, hence the wire is essentially [(a,b1), (a,b2)]

                                    # In a horizontal wire with points [(x1,y1), (x2,y2)], the vertical coordinates will be
                                    # equal, hence the wire is essentially [(x1,y), (x2,y)]

                                    # If vertical points of wire with a vertical segment, are intersecting the y coordinate
                                    # of a horizontal segment of the wire being checked against
                                    # Essentially checking if b1 <= y <= b2 (if y is between b1 and b2)
                                    if (
                                        vertical_segment[0][1]
                                        <= horizontal_segment[0][1]
                                        <= vertical_segment[1][1]
                                        or vertical_segment[0][1]
                                        >= horizontal_segment[0][1]
                                        >= vertical_segment[1][1]
                                    ):
                                        if DEBUG_OVERLAP:
                                            print(
                                                "y coords of vert segment within y coord of horizontal seg"
                                            )

                                        # There may be a possible intersection, so now
                                        # check if the horizontal points of wire with a vertical segment, intersects through
                                        # the x coordinate of a horizontal segment of the wire being checked against
                                        # Essentially checking if x1 <= a <= x2 (if a is between x1 and x2)
                                        if (
                                            horizontal_segment[0][0]
                                            <= vertical_segment[0][0]
                                            <= horizontal_segment[1][0]
                                            or horizontal_segment[0][0]
                                            >= vertical_segment[0][0]
                                            >= horizontal_segment[1][0]
                                        ):
                                            if DEBUG_OVERLAP:
                                                print(
                                                    "x coord of vert segment within x coords of horizontal seg"
                                                )

                                            # The intersection point is (a, y)
                                            # (a -> x coord from vertical segment, y -> y coord from horizontal segment)

                                            # An intersection is found, append the point to the wire's list of intersections
                                            # self.intersections.append((vertical_segment[0][0], horizontal_segment[0][1]))

                                            # Append intersection point into list of intersection points (stored within the scene)
                                            if (
                                                vertical_segment[0][0],
                                                horizontal_segment[0][1],
                                            ) not in self.scene.intersection_list:
                                                self.scene.intersection_list.append(
                                                    (
                                                        vertical_segment[0][0],
                                                        horizontal_segment[0][1],
                                                    )
                                                )
