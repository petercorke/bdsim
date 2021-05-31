from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# This parent class will draw wires between 2 given points this class implemented
# in the child class based the type of line wanted.

LEFT = 1
TOP = 2
RIGHT = 3
BOTTOM = 4

DEBUG = False


# =============================================================================
# 
# 	The GraphicsWire class will draw wires between 2 given points this percent 
# 	class is implemented by different classes based on the type of wire being 
# 	drawn. This class takes a wire as an input and then looks for the positions 
# 	of the start and end socket, then based on these connects them with a wire
# 	of the selected type. It is also used to redraw the wires when they are  
# 	moved around and if a wire is selected it will redraw the wire thicker and 
# 	in a different colour.
#
# =============================================================================

class GraphicsWire(QGraphicsPathItem):
    def __init__(self, edge):
        super().__init__()

        self.wire = edge
        self.wire_coordinates = []
        self.horizontal_segments = []
        self.vertical_segments = []


        self._color = QColor("#001000")
        self._color_selected = QColor("#00ff00")
        self._color_inter = QColor("#E0E0E0") # THIS NEEDS TO BE THE SAME AS THE BACKGROUND
        self._color_inter_light = QColor("#E0E0E0")
        self._color_inter_dark = QColor("#999999")
        self._color_line = QColor("#ff0000")
        self._pen = QPen(self._color)
        self._pen_inter = QPen(self._color_inter)
        self._pen_inter_light = QPen(self._color_inter_light)
        self._pen_inter_dark = QPen(self._color_inter_dark)
        self._pen_selected = QPen(self._color_selected)
        self._pen.setWidth(5)
        self._pen_inter.setWidth(10)
        self._pen_inter_light.setWidth(15)
        self._pen_inter_dark.setWidth(15)
        self._pen_selected.setWidth(8)


        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setZValue(-1)

        self.posSource = [0, 0]
        self.posDestination = [100, 100]

        self.posSource_Orientation = None
        self.posDestination_Orientation = None


# =============================================================================
# 
#     Sets the point where the line will start from, based on the position of
#     the start socket object.
# 
# =============================================================================

    def setSource(self, x, y):
        self.posSource = [x, y]

# =============================================================================
# 
# 	Sets the point where the line will end, based on the position of the end 
# 	socket object.
#  
# =============================================================================

    def setDestination(self, x, y):
        self.posDestination = [x, y]

# =============================================================================
# 
# 	Accesses the position of the start socket (1 - drawn Left on the block,
#	2 - drawn right on the block), and sets the orientation of the start socket
# 	(that is stored within the wire) as such.    
# 
# =============================================================================

    def setSourceOrientation(self, orientation):
        self.posSource_Orientation = orientation

# =============================================================================
# 
# 	Accesses the position of the end socket (1 - drawn Left on the block,
#	2 - drawn right on the block), and sets the orientation of the end socket
# 	(that is stored within the wire) as such.   
# 
# =============================================================================

    def setDestinationOrientation(self, orientation):
        self.posDestination_Orientation = orientation

# =============================================================================
# 
# 	Sets up the painter object and draws the line based on the path that will
# 	be set by the specific implementation of GraphicsWire that is calling paint. 
# 	Before the wire is drawn self.wire.intersectionsx is checked and if there 
# 	are intersections with this wire the markers that indicate the intersection  
# 	will be drawn first so that the wire can be drawn over them. Them the 
# 	painter will select the way the wire will be drawn depending on whether or  
# 	not the wire is selected.
# 
# =============================================================================

    def paint(self, painter, styles, widget=None):
        
        painter.setPen(self._color_inter)
        painter.setPen(self._pen_inter)
        
        # Check the background colour and change the marks to match
        if self.wire.scene.grScene.mode == 'Light':
            
            painter.setPen(self._color_inter_light)
            painter.setPen(self._pen_inter_light)
        elif self.wire.scene.grScene.mode == 'Dark':
            
            painter.setPen(self._color_inter_dark)
            painter.setPen(self._pen_inter_dark)
        
        # for each intersection draw a mark that matches the background
        if len(self.wire.intersectionsx) > 0:
            i = 0
            while(i<len(self.wire.intersectionsx)):
                
                x = self.wire.intersectionsx[i]
                y = self.wire.intersectionsy[i]
                # painter.drawEllipse(x-7.5, y-7.5, 15, 15)
                painter.drawRect(x-6, y-6, 12, 12)
                i += 1
        #update position and draw it on top of the intersection marks
        self.updatePath()

        painter.setPen(self._pen if not self.isSelected() else self._pen_selected)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self.path())
        

# =============================================================================
# 
# 	Raise Not Implemented as this method is to be over written by child 
#         
# =============================================================================

    def updatePath(self):
        raise NotImplemented("This method is to be over written by child class")
               
# =============================================================================
# 
# 	This method goes through the wire_coordinates and determines the horizontal 
# 	and vertical line segments.
# 
# =============================================================================

    def updateLineSegments(self):
        # If the wire coordinates exist
        if self.wire_coordinates:
            self.horizontal_segments.clear()
            self.vertical_segments.clear()
            for counter in range(0, len(self.wire_coordinates)-1):
                # Line segments always alternate, from horizontal to vertical to horizontal etc.
                # Even iterations of coordinate points are always the beginning to horizontal segments
                # Append a line represented as ((x1,y2),(x2,y2)) to either horizontal or vertical line segment list
                if counter % 2 == 0:
                    self.horizontal_segments.append((self.wire_coordinates[counter], (self.wire_coordinates[counter+1])))
                else:
                    self.vertical_segments.append((self.wire_coordinates[counter], (self.wire_coordinates[counter+1])))

# =============================================================================
#     
# 	This method checks if the list of wire coordinates has changed and needs to 
# 	be updated
# 
# =============================================================================

    def updateWireCoordinates(self, new_coordinates):
        # Update current wire coordinates, if the new coordinates are different
        # Also update the horizontal and vertical line segments
        if new_coordinates != self.wire_coordinates:
            self.wire_coordinates.clear()
            self.wire_coordinates = new_coordinates
            self.updateLineSegments()

            # print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
            # print("coordinates:", [self.wire_coordinates])
            # print("\nhorizontal lines:", [self.horizontal_segments])
            # print("\nvertical lines:", [self.vertical_segments])
            # print("-------------------------------------------------------")

# =============================================================================
# 
#  	The direct class will draw a straight line between two sockets,
#  	it will take the shortest distance and will go through other blocks 
#  	etc to do so.
#  
# =============================================================================


class GraphicsWireDirect(GraphicsWire):
    def updatePath(self):
        path = QPainterPath(QPointF(self.posSource[0], self.posSource[1]))
        path.lineTo(self.posDestination[0], self.posDestination[1])
        # self.path = path
        self.setPath(path)

# =============================================================================
# 
# 	Will draw a quadratic Bezier line from one point to another using an 
# 	equation to define the curve of the line based on the x and y coordinates.
# 	Looks good going from left to right but will draw incorrectly if the blocks
# 	are moved past each other or if the block is flipped.
#
# =============================================================================        

class GraphicsWireBezier(GraphicsWire):
    def updatePath(self):
        s = self.posSource
        d = self.posDestination
        dist = (d[0] - s[0]) * 0.5
        if s[0] > d[0]:
            dist *= -1
        path = QPainterPath(QPointF(self.posSource[0], self.posSource[1]))
        path.cubicTo(s[0] + dist, s[1], d[0] - dist, d[1]-dist, self.posDestination[0], self.posDestination[1])
        self.setPath(path)


# =============================================================================
# 
# 	DETAILED DISCRIPTION WILL BE ADDED THIS WEEK
#
# =============================================================================

class GraphicsWireStep(GraphicsWire):
    def updatePath(self):

        temporary_wire_coordinates = []
        wire_completed = False

        block_padding = 20
        title_height = self.wire.start_socket.node.grBlock.title_height - 5

        sx = self.posSource[0]
        sy = self.posSource[1]
        dx = self.posDestination[0]
        dy = self.posDestination[1]
        xDist = (dx - sx) / 2

        s_index = self.wire.start_socket.index + 1
        source_block_width = self.wire.start_socket.node.width
        source_block_height = self.wire.start_socket.node.height
        # Start_socket/end_socket offset from top/left of block
        s_Offset = self.wire.start_socket.getSocketPosition()

        # Destination_block & Source_block = node of end_socket and start_socket respectively
        if self.wire.end_socket is not None:
            d_index = self.wire.end_socket.index + 1
            destination_block_width = self.wire.end_socket.node.width
            destination_block_height = self.wire.end_socket.node.height
            d_Offset = self.wire.end_socket.getSocketPosition()
        else:
            d_index = 0
            destination_block_width = 0
            destination_block_height = 0
            d_Offset = [0, 0]

        path = QPainterPath(QPointF(sx, sy))
        temporary_wire_coordinates.clear()
        temporary_wire_coordinates.append((sx, sy))

        # If two sockets haven't been connected yet
        if self.wire.end_socket is None:
            # Don't do anything, start and end points of the path have already been defined, so a straight line will be drawn
            pass

        # If sockets are both on the same side (both coming out of the left or right)
        elif self.posSource_Orientation == self.posDestination_Orientation:

            # Start socket is left of end socket
            if sx < dx:
                # Continue path from source
                # Destination_block & Source_block are kept the same
                pass

            # Start socket is equal to or right of end socket
            else:
                # Use the same logic as for above, but swap positions of start socket with end socket
                sx, sy = self.posDestination[0], self.posDestination[1]
                dx, dy = self.posSource[0], self.posSource[1]

                # Destination_block & Source_block = node of start_socket and end_socket respectively
                d_index = self.wire.start_socket.index + 1
                destination_block_width = self.wire.start_socket.node.width
                destination_block_height = self.wire.start_socket.node.height

                # Switch the indexes of the sockets
                if self.wire.end_socket is not None:
                    s_index = self.wire.end_socket.index + 1
                    source_block_width = self.wire.end_socket.node.width
                    source_block_height = self.wire.end_socket.node.height
                else:
                    s_index = 0
                    source_block_width = 0
                    source_block_height = 0

                # Restart path from destination
                # path.clear()
                path = QPainterPath(QPointF(sx, sy))
                temporary_wire_coordinates.clear()
                temporary_wire_coordinates.append((sx, sy))

            # End socket is on RHS of destination block
            if self.posDestination_Orientation == RIGHT:
                # xDist is from RHS of source block, to LHS of destination block
                xDist = (dx - destination_block_width - sx) / 2

                # Top of the destination block is above source block
                # Should be dy > sy, but graphics view draws the y-axis inverted
                if dy - d_Offset[1] - (d_index * block_padding) < sy:

                    # Bottom of destination block is above top of source block OR
                    # LHS of destination block is further left than RHS of source block

                    # Wire from multiple sockets spaced from bottom of destination block at index (no overlap)
                    if (dy - d_Offset[1] + destination_block_height + title_height + (d_index * block_padding) < sy) or (sx + xDist <= sx + (block_padding / 2)):
                        if DEBUG: print("Wire style: A")
                        # Draw C (inverted equivalent) line from S up to D, clipped to RHS of destination block
                        # ----------------------
                        #       (d-block)-<-|
                        #                   |
                        #  (s-block)->------|
                        # ----------------------
                        path.lineTo(dx + (d_index * block_padding), sy)
                        path.lineTo(dx + (d_index * block_padding), dy)

                        temporary_wire_coordinates.append((dx + (d_index * block_padding), sy))
                        temporary_wire_coordinates.append((dx + (d_index * block_padding), dy))

                    # Bottom of destination block is equal to or below top of source block
                    else:
                        if DEBUG: print("Wire style: B")
                        # Draw wrapped line between source and destination block, then above and around destination block
                        # --------------------------------
                        #              |---------------|
                        #              |               |
                        #              |   (d-block)-<-|
                        #              |
                        #  (s-block)->-|
                        # --------------------------------
                        path.lineTo(sx + xDist, sy)
                        path.lineTo(sx + xDist, dy - d_Offset[1] - (d_index * block_padding))
                        path.lineTo(dx + d_index * block_padding, dy - d_Offset[1] - (d_index * block_padding))
                        path.lineTo(dx + d_index * block_padding, dy)

                        temporary_wire_coordinates.append((sx + xDist, sy))
                        temporary_wire_coordinates.append((sx + xDist, dy - d_Offset[1] - (d_index * block_padding)))
                        temporary_wire_coordinates.append(
                            (dx + d_index * block_padding, dy - d_Offset[1] - (d_index * block_padding)))
                        temporary_wire_coordinates.append((dx + d_index * block_padding, dy))

                # Top of destination block is equal to or below source block socket
                else:
                    if DEBUG: print("Wire style: C")
                    # Draw C (inverted equivalent) line from S down to D, clipped to RHS of destination block
                    # ------------------------
                    #   (s-block)->---------|
                    #                       |
                    #           (d-block)-<-|
                    # ------------------------
                    path.lineTo(dx + d_index * block_padding, sy)
                    path.lineTo(dx + d_index * block_padding, dy)

                    temporary_wire_coordinates.append((dx + d_index * block_padding, sy))
                    temporary_wire_coordinates.append((dx + d_index * block_padding, dy))

            # Destination socket is on LHS of block
            else:
                # xDist is from RHS of source block, to LHS of destination block
                xDist = (dx - (sx + source_block_width)) / 2

                # Should be sy > dy, but graphics view draws the y-axis inverted
                # Top of source block is above destination block
                if sy - s_Offset[1] - (s_index * block_padding) < dy:
                    # Bottom of source block is above top of destination block OR
                    # RHS of source block further left than LHS of destination block

                    # Wire from multiple sockets spaced from bottom of source block at index (no overlap)
                    if (sy - s_Offset[1] + source_block_height + title_height + (s_index * block_padding) < dy) or (dx + xDist <= dx + (block_padding / 2)):
                        if DEBUG: print("Wire style: D")
                        # Draw C line from S down to D, clipped to LHS of source block
                        # ----------------------
                        #  |--<-(s-block)
                        #  |
                        #  |----->-(d-block)
                        # ----------------------
                        path.lineTo(sx - (s_index * block_padding), sy)
                        path.lineTo(sx - (s_index * block_padding), dy)

                        temporary_wire_coordinates.append((sx - (s_index * block_padding), sy))
                        temporary_wire_coordinates.append((sx - (s_index * block_padding), dy))

                    # Bottom of source block is equal to or below top of destination block
                    else:
                        if DEBUG: print("Wire style: E")
                        # Draw wrapped line above and around the source block, then between the source and destination block
                        # --------------------------------
                        #  |---------------|
                        #  |               |
                        #  |-<-(s-block)   |
                        #                  |
                        #                  |->-(d-block)
                        # --------------------------------
                        path.lineTo(sx - s_index * block_padding, sy)
                        path.lineTo(sx - s_index * block_padding, sy - s_Offset[1] - (s_index * block_padding))
                        path.lineTo(sx + source_block_width + xDist, sy - s_Offset[1] - (s_index * block_padding))
                        path.lineTo(sx + source_block_width + xDist, dy)

                        temporary_wire_coordinates.append((sx - s_index * block_padding, sy))
                        temporary_wire_coordinates.append(
                            (sx - s_index * block_padding, sy - s_Offset[1] - (s_index * block_padding)))
                        temporary_wire_coordinates.append(
                            (sx + source_block_width + xDist, sy - s_Offset[1] - (s_index * block_padding)))
                        temporary_wire_coordinates.append((sx + source_block_width + xDist, dy))

                # Top of source block is equal to or below destination block
                else:
                    if DEBUG: print("Wire style: F")
                    # Draw C line from S up to D, clipped to LHS of source block
                    # --------------------
                    # |------->-(d-block)
                    # |
                    # |-<-(s-block)
                    # --------------------
                    path.lineTo(sx - s_index * block_padding, sy)
                    path.lineTo(sx - s_index * block_padding, dy)

                    temporary_wire_coordinates.append((sx - s_index * block_padding, sy))
                    temporary_wire_coordinates.append((sx - s_index * block_padding, dy))

            # Update boolean that wire is completed, as to get here, the end point of the wire must be dropped
            wire_completed = True

        # Otherwise sockets are on different sides (out from left into right, or out of right into left)
        elif self.posSource_Orientation != self.posDestination_Orientation:

            # Start socket is on LHS of source block
            if self.posSource_Orientation == LEFT:
                # Continue path from source
                # Destination_block & Source_block are kept the same
                xDist = (sx - dx) / 2

            # Start socket is on RHS of source block
            else:
                # Use the same logic as for above, but swap positions of start socket with end socket
                sx, sy = self.posDestination[0], self.posDestination[1]
                dx, dy = self.posSource[0], self.posSource[1]

                # Destination_block & Source_block = node of start_socket and end_socket respectively
                d_index = self.wire.start_socket.index + 1
                destination_block_width = self.wire.start_socket.node.width
                destination_block_height = self.wire.start_socket.node.height
                d_Offset = self.wire.start_socket.getSocketPosition()

                # Switch the indexes of the sockets
                if self.wire.end_socket is not None:
                    s_index = self.wire.end_socket.index + 1
                    source_block_width = self.wire.end_socket.node.width
                    source_block_height = self.wire.end_socket.node.height
                    s_Offset = self.wire.end_socket.getSocketPosition()
                else:
                    s_index = 0
                    source_block_width = 0
                    source_block_height = 0
                    s_Offset = [0, 0]

                # Restart path from destination
                # path.clear() 
                path = QPainterPath(QPointF(sx, sy))

                temporary_wire_coordinates.clear()
                temporary_wire_coordinates.append((sx, sy))

            # Source block (start socket) is right of destination block (end socket)
            if sx > dx:
                if DEBUG: print("Wire style: G")
                # Draw normal step line
                # ---------------------------
                #              |-<-(s-block)
                #              |
                #  (d-block)-<-|
                # ---------------------------
                path.lineTo(sx - xDist, sy)
                path.lineTo(sx - xDist, dy)

                temporary_wire_coordinates.append((sx - xDist, sy))
                temporary_wire_coordinates.append((sx - xDist, dy))

            # Source block (start socket) is equal to or left of destination block (end socket)
            else:

                # Source block is above destination block
                if sy - s_Offset[1] - (s_index * block_padding) < dy - d_Offset[1] - (d_index * block_padding):
                    # Distance between bottom of source block and top of destination block
                    yDist = ((dy - d_Offset[1]) - (sy - s_Offset[1] + source_block_height + title_height)) / 2

                    # Bottom of source block is above top of destination block OR
                    # --
                    if (sy - s_Offset[1] + source_block_height + title_height) < (dy - d_Offset[1] - block_padding):
                        if DEBUG: print("Wire style: H")
                        # Draw S line
                        #  |---<-(s-block)
                        #  |
                        #  |--------------|
                        #                 |
                        #    (d-block)-<--|
                        # ------------------
                        path.lineTo(sx - (s_index * block_padding), sy)
                        path.lineTo(sx - (s_index * block_padding), dy - d_Offset[1] - yDist)
                        path.lineTo(dx + (d_index * block_padding), dy - d_Offset[1] - yDist)
                        path.lineTo(dx + (d_index * block_padding), dy)

                        temporary_wire_coordinates.append((sx - (s_index * block_padding), sy))
                        temporary_wire_coordinates.append((sx - (s_index * block_padding), dy - d_Offset[1] - yDist))
                        temporary_wire_coordinates.append((dx + (d_index * block_padding), dy - d_Offset[1] - yDist))
                        temporary_wire_coordinates.append((dx + (d_index * block_padding), dy))

                    # Bottom of source block is at level with or below top of destination block
                    else:

                        # RHS of destination block is further left than RHS of source block
                        if (dx + block_padding) < (sx + source_block_width + block_padding):
                            if DEBUG: print("Wire style: I")
                            # Draw line going around the top of the source block, clipped to RHS of source block + padding
                            # --------------------------------------------------
                            #     |--------------|            |--------------|
                            #     |              |            |              |
                            #     |-<-(s-block)  |     or     |-<-(s-block)  |
                            #  (d-block)-<-------|               (d-block)-<-|
                            # --------------------------------------------------
                            path.lineTo(sx - (s_index * block_padding), sy)
                            path.lineTo(sx - (s_index * block_padding), sy - s_Offset[1] - (s_index * block_padding))
                            path.lineTo(sx + source_block_width + (s_index * block_padding),
                                        sy - s_Offset[1] - (s_index * block_padding))
                            path.lineTo(sx + source_block_width + (s_index * block_padding), dy)

                            temporary_wire_coordinates.append((sx - (s_index * block_padding), sy))
                            temporary_wire_coordinates.append(
                                (sx - (s_index * block_padding), sy - s_Offset[1] - (s_index * block_padding)))
                            temporary_wire_coordinates.append((sx + source_block_width + (s_index * block_padding),
                                                               sy - s_Offset[1] - (s_index * block_padding)))
                            temporary_wire_coordinates.append((sx + source_block_width + (s_index * block_padding), dy))
                            # path.lineTo(sx + source_block_width + block_padding, sy - s_Offset[1] - (s_index * block_padding))
                            # path.lineTo(sx + source_block_width + block_padding, dy)

                        # RHS of destination block is equal to or right of RHS of source block
                        else:
                            if DEBUG: print("Wire style: J")
                            # Draw line going around the top of the source block, clipped to RHS of destination block + padding
                            # -------------------------------------------------------------------------
                            #  |-----------------------------|           |---------------------------|
                            #  |                             |           |                           |
                            #  |-<-(s-block)                 |    or     |-<-(s-block)   (d-block)-<-|
                            #                    (d-block)-<-|
                            # -------------------------------------------------------------------------
                            path.lineTo(sx - (s_index * block_padding), sy)
                            path.lineTo(sx - (s_index * block_padding), sy - s_Offset[1] - (s_index * block_padding))
                            path.lineTo(dx + (d_index * block_padding), sy - s_Offset[1] - (s_index * block_padding))
                            path.lineTo(dx + (d_index * block_padding), dy)

                            temporary_wire_coordinates.append((sx - (s_index * block_padding), sy))
                            temporary_wire_coordinates.append(
                                (sx - (s_index * block_padding), sy - s_Offset[1] - (s_index * block_padding)))
                            temporary_wire_coordinates.append(
                                (dx + (d_index * block_padding), sy - s_Offset[1] - (s_index * block_padding)))
                            temporary_wire_coordinates.append((dx + (d_index * block_padding), dy))

                # Source block is below destination block
                else:
                    # Distance between top of source block and bottom of destination block
                    yDist = ((sy - s_Offset[1]) - (dy - d_Offset[1] + destination_block_height + title_height)) / 2

                    # Top of source block is below bottom of destination block OR
                    # --
                    if (sy - s_Offset[1] - block_padding) > (dy - d_Offset[1] + destination_block_height + title_height):
                        if DEBUG: print("Wire style: K")
                        # Draw Z line
                        # -----------------------
                        #        (d-block)-<--|
                        #                     |
                        #  |------------------|
                        #  |
                        #  |-<-(s-block)
                        # -----------------------
                        path.lineTo(sx - (s_index * block_padding), sy)
                        path.lineTo(sx - (s_index * block_padding), sy - yDist - s_Offset[1])
                        path.lineTo(dx + (s_index * block_padding), sy - yDist - s_Offset[1])
                        path.lineTo(dx + (s_index * block_padding), dy)

                        temporary_wire_coordinates.append((sx - (s_index * block_padding), sy))
                        temporary_wire_coordinates.append((sx - (s_index * block_padding), sy - yDist - s_Offset[1]))
                        temporary_wire_coordinates.append((dx + (s_index * block_padding), sy - yDist - s_Offset[1]))
                        temporary_wire_coordinates.append((dx + (s_index * block_padding), dy))

                    # Top of source block is at level with or above bottom of destination block
                    else:

                        # LHS of destination is further left than LHS of source block
                        if (dx - destination_block_width - block_padding) < (sx - block_padding):
                            if DEBUG: print("Wire style: L")
                            # Draw line going around the top of the destination block, clipped to the LHS of destination block minus padding
                            # ------------------------
                            #  |--------------|
                            #  |              |
                            #  |  (d-block)-<-|
                            #  |
                            #  |----------<-(s-block)
                            # ------------------------
                            path.lineTo(dx - destination_block_width - (s_index * block_padding), sy)
                            path.lineTo(dx - destination_block_width - (s_index * block_padding), dy - d_Offset[1] - (d_index * block_padding))
                            path.lineTo(dx + d_index * block_padding, dy - d_Offset[1] - (d_index * block_padding))
                            path.lineTo(dx + d_index * block_padding, dy)

                            temporary_wire_coordinates.append(
                                (dx - destination_block_width - (s_index * block_padding), sy))
                            temporary_wire_coordinates.append((dx - destination_block_width - (s_index * block_padding),
                                                               dy - d_Offset[1] - (d_index * block_padding)))
                            temporary_wire_coordinates.append(
                                (dx + d_index * block_padding, dy - d_Offset[1] - (d_index * block_padding)))
                            temporary_wire_coordinates.append((dx + d_index * block_padding, dy))

                        # LHS of destination is equal to or right of LHS of source block
                        else:
                            if DEBUG: print("Wire style: M")
                            # Draw line going around the top of the destination block, clipped to the LHS of source block minus padding
                            # ----------------------
                            #  |----------------|
                            #  |                |
                            #  |    (d-block)-<-|
                            #  |
                            #  |-<-(s-block)
                            # ----------------------
                            path.lineTo(sx - s_index * block_padding, sy)
                            path.lineTo(sx - s_index * block_padding, dy - d_Offset[1] - (d_index * block_padding))
                            path.lineTo(dx + d_index * block_padding, dy - d_Offset[1] - (d_index * block_padding))
                            path.lineTo(dx + d_index * block_padding, dy)

                            temporary_wire_coordinates.append((sx - s_index * block_padding, sy))
                            temporary_wire_coordinates.append(
                                (sx - s_index * block_padding, dy - d_Offset[1] - (d_index * block_padding)))
                            temporary_wire_coordinates.append(
                                (dx + d_index * block_padding, dy - d_Offset[1] - (d_index * block_padding)))
                            temporary_wire_coordinates.append((dx + d_index * block_padding, dy))

            # Update boolean that wire is completed, as to get here, the end point of the wire must be dropped
            wire_completed = True

        else:
            if DEBUG: print("Wire style: N")
            # ---------------------------
            # draw line as:
            #              |-<-(s-block)
            #              |
            #  (d-block)-<-|
            # ---------------------------
            path.lineTo(sx - xDist, sy)
            path.lineTo(sx - xDist, dy)

            temporary_wire_coordinates.append((sx - xDist, sy))
            temporary_wire_coordinates.append((sx - xDist, dy))

        # Finish the path to the destination
        path.lineTo(dx, dy)
        temporary_wire_coordinates.append((dx, dy))

        self.setPath(path)

        # If the wire has been dropped on a destination socket (and is not being dragged around), update its coordinates
        if wire_completed:
            self.updateWireCoordinates(temporary_wire_coordinates)

