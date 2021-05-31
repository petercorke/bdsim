from bdedit.block_graphics_wire import *
from bdedit.interface_serialize import Serializable
from collections import OrderedDict

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
        self.intersection = []
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