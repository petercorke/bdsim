from bdedit.block_graphics_wire import *
from bdedit.interface_serialize import Serializable
from collections import OrderedDict
import time

WIRE_TYPE_DIRECT = 1
WIRE_TYPE_BEZIER = 2
WIRE_TYPE_STEP = 3

DEBUG = False

# =============================================================================
#
#	The Wire Class is used to define the Wires that connect the the blocks 
#	via the sockets, each wire has a start socket and a end socket and a  
#	wire type that defines how the wires will be drawn. The code also updates
#	the wires as the blocks are moved around so they stay connected.
#
# =============================================================================


class Wire(Serializable):
    def __init__(self, scene, start_socket=None, end_socket=None, wire_type=1):
        super().__init__()
        
        self.scene = scene
        
        # default init
        self._start_socket = None
        self._end_socket = None

        self.wire_coordinates = []
        self.horizontal_segments = []
        self.vertical_segments = []
        
        self.wirepath = None
        self.intersections = []
        self.intersectionsx = []
        self.intersectionsy = []
        self.wire_pointsx = []
        self.wire_pointsy = []
        


        self.start_socket = start_socket
        self.end_socket = end_socket
        self.wire_type = wire_type

        self.scene.addWire(self)
 
 
# =============================================================================
# 
# 	Gets the start socket of the wire.
# 
# =============================================================================
    
    @property
    def start_socket(self): return self._start_socket


# =============================================================================
# 
# 	Sets the start socket of the wire.
#
# =============================================================================


    @start_socket.setter
    def start_socket(self, value):

        # if we were assigned to some socket before, delete us from the socket
        if self._start_socket is not None:
            self._start_socket.removeWire(self)

        # assign new start socket
        self._start_socket = value
        # addEdge to the Socket class
        if self.start_socket is not None:
            self.start_socket.setConnectedEdge(self)
    
    
# =============================================================================
# 
# 	Gets the end socket of the wire.
# 
# =============================================================================   
    
    @property
    def end_socket(self): return self._end_socket

   
# =============================================================================
# 
# 	Sets the end socket of the wire.
# 
# =============================================================================

    @end_socket.setter
    def end_socket(self, value):
        # if we were assigned to some socket before, delete us from the socket
        if self._end_socket is not None:
            self._end_socket.removeWire(self)

        # assign new end socket
        self._end_socket= value
        # addEdge to the Socket class
        if self.end_socket is not None:
            self.end_socket.setConnectedEdge(self)


# =============================================================================
# 
# 	Returns the wire type of the wire.
#   
# =============================================================================

    @property
    def wire_type(self): return self._wire_type


# =============================================================================
# 
#	Sets the wire type, this will determine how the wire will be draw it 
#	will be set to the step but other line styles can be added here. 
#	They will call the corresponding GraphicsWire implementation that will 
#	do the drawing of the wire.
#     
# =============================================================================

    @wire_type.setter
    def wire_type(self, value):
        if hasattr(self, 'grWire') and self.grWire is not None:
            self.scene.grScene.removeItem(self.grWire)

        self._wire_type = value
        if self.wire_type == WIRE_TYPE_DIRECT:
            self.grWire = GraphicsWireDirect(self)
        elif self.wire_type == WIRE_TYPE_STEP:
            self.grWire = GraphicsWireStep(self)
        else:
            self.grWire = GraphicsWireBezier(self)

        self.scene.grScene.addItem(self.grWire)

        if self.start_socket is not None:
            self.updatePositions()


# =============================================================================
# 
# 	When the blocks are moved around the wires will be redrawn to the new 
# 	positions, this function will get the new positions of the socket and
# 	then redraw the wires with the new position.         
#             
# =============================================================================

    def updatePositions(self):
        source_pos_orientation = self.start_socket.position
        self.grWire.setSourceOrientation(source_pos_orientation)

        source_pos = self.start_socket.getSocketPosition()
        source_pos[0] += self.start_socket.node.grBlock.pos().x()
        source_pos[1] += self.start_socket.node.grBlock.pos().y()
        self.grWire.setSource(*source_pos)
        if self.end_socket is not None:
            destination_pos_orientation = self.end_socket.position
            self.grWire.setDestinationOrientation(destination_pos_orientation)

            end_pos = self.end_socket.getSocketPosition()
            end_pos[0] += self.end_socket.node.grBlock.pos().x()
            end_pos[1] += self.end_socket.node.grBlock.pos().y()
            self.grWire.setDestination(*end_pos)
        else:
            self.grWire.setDestination(*source_pos)
        self.grWire.update()
   
        

# =============================================================================
#	This will remove the wire from both the start and end socket 
# =============================================================================
   
    def remove_from_sockets(self):

        self.end_socket = None
        self.start_socket = None

# =============================================================================
# 
# 	Remove wire from the scene and the sockets
# 
# =============================================================================

    def remove(self):
        if DEBUG: print("# Removing Wire", self)
        if DEBUG: print(" - removing wire from all sockets", self)
        self.remove_from_sockets()
        if DEBUG: print(" - removing grWire")
        self.scene.grScene.removeItem(self.grWire)
        self.grWire = None
        if DEBUG: print(" - removing wire from scene")
        try:
            self.scene.removeWire(self)
        except ValueError:
            pass
        if DEBUG: print(" - everything is done.")

# =============================================================================
# 
# 	Returns an ordered dictionary of the wires' variables as key-value pairs, 
# 	for writing into a JSON file.
# 
# =============================================================================

    def serialize(self):
        return OrderedDict([
            ('id', self.id),
            ('start_socket', self.start_socket.id),
            ('end_socket', self.end_socket.id),
            ('wire_type', self.wire_type),
        ])
    

# =============================================================================
#
# 	The Wire data that is stored within a JSON file is read through, and the 
# 	keys-value pairs are matched to the variables of the wire.
# 
# =============================================================================

    def deserialize(self, data, hashmap={}):
        self.id = data['id']
        self.start_socket = hashmap[data['start_socket']]
        self.end_socket = hashmap[data['end_socket']]
        self.wire_type = data['wire_type']
        return True
    
    
# =============================================================================
#
# 	 Detail how this works Required
# 	
# 
# =============================================================================
    def checkIntersection2(self):
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
                            if j != i:

                                # Iterate through each horizontal segments of the wire being checked
                                for horizontal_segment in self.scene.wires[j].horizontal_segments:

                                    # In a vertical wire with points [(a1,b1), (a2,b2)], the horizontal coordinates will be
                                    # equal, hence the wire is essentially [(a,b1), (a,b2)]

                                    # In a horizontal wire with points [(x1,y1), (x2,y2)], the vertical coordinates will be
                                    # equal, hence the wire is essentially [(x1,y), (x2,y)]

                                    # If vertical points of wire with a vertical segment, are intersecting the y coordinate
                                    # of a horizontal segment of the wire being checked against
                                    # Essentially checking if b1 <= y <= b2 (if y is between b1 and b2)
                                    if vertical_segment[0][1] <= horizontal_segment[0][1] <= vertical_segment[1][1] or \
                                       vertical_segment[0][1] >= horizontal_segment[0][1] >= vertical_segment[1][1]:
                                        if DEBUG: print("y coords of vert segment within y coord of horizontal seg")

                                        # There may be a possible intersection, so now
                                        # check if the horizontal points of wire with a vertical segment, intersects through
                                        # the x coordinate of a horizontal segment of the wire being checked against
                                        # Essentially checking if x1 <= a <= x2 (if a is between x1 and x2)
                                        if horizontal_segment[0][0] <= vertical_segment[0][0] <= horizontal_segment[1][0] or \
                                           horizontal_segment[0][0] >= vertical_segment[0][0] >= horizontal_segment[1][0]:
                                            if DEBUG: print("x coord of vert segment within x coords of horizontal seg")

                                            # An intersection is found, append the point to the wire's list of intersections
                                            # The intersection point is (a, y)
                                            # (a -> x coord from vertical segment, y -> y coord from horizontal segment)
											
                                            # Append intersection point into list of intersection points
                                            if (vertical_segment[0][0], horizontal_segment[0][1]) not in self.scene.intersection_list:
                                                self.scene.intersection_list.append((vertical_segment[0][0], horizontal_segment[0][1]))

# =============================================================================
#
# 	This function will check for intersections in the wires by first looking at
#  	the scene and then for every wire it will compare it to every other wire to 
#  	see whether they share any of the same x and y coordinates, if they do these
#  	will be stored in the wire property intersectionsx and intersectionsy.  
# 
# =============================================================================

    def checkintersection(self):
        #For every wire in the scene compair it to every other wire that is not
        #Its self.
        numeWires=0
        checkedagainst = 0
        self.setWirePoints()

        for Wires in self.scene.wires:
            numeWires += 1
            wire1 = Wires       
            wire2 = None
            index = 0
            Current_block = 0
            checkedagainst = 0
            for Wire in self.scene.wires:

                if Wire.end_socket != None:
                    wire2 = Wire
                    checkedagainst += 1
                    # check if Wires are the same
                    if wire1 == wire2:
                        checkedagainst -= 1
                        wire2 = None

                # Check that there is a second wire to compair to
                if wire2 != None:
                    # For every point on the first wire dose it match any point
                    # on the second
                    i = 0
                    i2 = 0

                    
                    while i < len(wire1.wire_pointsx):
                        i2 = 0
                        while i2 < len( wire2.wire_pointsx):
                            if wire1.wire_pointsx[i] == wire2.wire_pointsx[i2]:
                                if wire1.wire_pointsy[i] == wire2.wire_pointsy[i2]:
                                    
                                    # If points match store the coordinates in 
                                    # wires intersectionsx and intersectionsy
                                    wire1.intersectionsx.append(wire1.wire_pointsx[i])
                                    wire1.intersectionsy.append(wire1.wire_pointsy[i])

                            i2+=1
                        i+=1
                    

            #Call the update function to redaw the wires so that the points 
            # marking intersections will be drawn in.
            wire1.updatePositions()
        
# =============================================================================
# 
# 	The function will look at the scene and for every wire it will get the start
# 	end points as well as the points were the wire goes from vertical to 
# 	horizontal, it will then take these and make a list of the x and a list of 
# 	the y coordinates for every point on the wire. If these lists exist they will
# 	be cleared as well as the lists that store points of intersection.
#
# =============================================================================

    def setWirePoints(self):
        for Wire in self.scene.wires:

            i = 0
            
            Wire.intersectionsx.clear()
            Wire.intersectionsy.clear() 
            
            Wire.wire_pointsx.clear() 
            Wire.wire_pointsy.clear() 
            
            
            while i < len(Wire.grWire.wire_coordinates)-1:
                coord_1 = Wire.grWire.wire_coordinates[i]
                coord_2 = Wire.grWire.wire_coordinates[i+1]

                if coord_1[1] == coord_2[1]:
                    i2 = 0 
                    dist = coord_2[0] - coord_1[0]
                    point = coord_2[0]
                    if dist < 0:
                        while(i2 > dist):
                            point += 1
                            Wire.wire_pointsx.append(point)
                            Wire.wire_pointsy.append(coord_1[1])
                            i2 -= 1
                        
                    elif dist > 0:
                        while(i2 < dist):
                            point -= 1
                            Wire.wire_pointsx.append(point)
                            Wire.wire_pointsy.append(coord_1[1])
                            i2 += 1
                    i += 1
                elif coord_1[0] == coord_2[0]:
                    i2 = 0 
                    dist = coord_2[1] - coord_1[1]
                    point = coord_2[1]
                    if dist < 0:
                        while(i2 > dist):
                            point += 1                           
                            Wire.wire_pointsx.append(coord_1[0])
                            Wire.wire_pointsy.append(point)
                            i2 -= 1
                    elif dist > 0:
                        while(i2 < dist):
                            point -= 1
                            Wire.wire_pointsx.append(coord_1[0])
                            Wire.wire_pointsy.append(point)
                            i2 += 1
                    i += 1