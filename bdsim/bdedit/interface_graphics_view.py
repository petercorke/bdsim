from PyQt5.QtWidgets import QGraphicsView
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from bdedit.block import Block
from bdedit.block_graphics_wire import GraphicsWire
from bdedit.block_graphics_socket import GraphicsSocket
from bdedit.block_graphics_block import GraphicsBlock, GraphicsSocketBlock
from bdedit.block_wire import Wire, WIRE_TYPE_DIRECT, WIRE_TYPE_BEZIER, WIRE_TYPE_STEP

MODE_NONE = 1
MODE_WIRE_DRAG = 2
EDGE_DRAG_LIM = 10
DEBUG = False

# =============================================================================
# 
# GraphicsView will handle many of the press/click events as well as containing
# the logic for draw wires and how they can connect. Here mouse click events
# are used to drag the wires from a start to a end socket, when click is
# dragged from a socket mode == MODE_WIRE_DRAG will be set to true and a
# wire will follow the mouse till a end socket is set or mode == MODE_WIRE_DRAG
# is false and the wire will be deleted.
# 
# =============================================================================


class GraphicsView(QGraphicsView):
    def __init__(self, grScene, parent=None):
        super().__init__(parent)

        self.grScene = grScene

        self.initUI()

        self.setScene(self.grScene)

        self.mode = MODE_NONE

        self._default_zoom_level = 7
        self.zoom = self._default_zoom_level
        self.zoomStep = 1
        self.zoomRange = [0, 10]
        
# =============================================================================
# Initialize the UI        
# =============================================================================

    def initUI(self):
        self.setRenderHints(QPainter.Antialiasing | QPainter.HighQualityAntialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)


# =============================================================================
# This will shut the parameter window used for editing the block properties.
# =============================================================================

    def closeParamWindows(self):
        if len(self.grScene.scene.blocks) != 0:
            for block in self.grScene.scene.blocks:
                if block.parameterWindow is not None:
                    block.parameterWindow.setVisible(False)
                    block._param_visible = False
   
                    
# =============================================================================
# Removes the selected block or wire from the scene.                    
# =============================================================================

    def deleteSelected(self):
        for item in self.grScene.selectedItems():
            if isinstance(item, GraphicsWire):
                item.wire.remove()
            elif isinstance(item, GraphicsBlock) or isinstance(item, GraphicsSocketBlock):
                item.block.remove()


# =============================================================================
# Flip the block so that the input and output sockets change sides
# =============================================================================

    def flipBlockSockets(self):
        for item in self.grScene.selectedItems():
            if isinstance(item, GraphicsBlock) or isinstance(item, GraphicsSocketBlock):
                item.block.updateSocketPositions()
                
                
# =============================================================================
# Checks how for the cursor has moved, this will be used when the wire is dragged to check that wire has been dragged away from the start socket so that when it is released on a socket we know its not the start socket.  
# =============================================================================

    def dist_click_release(self, event):
        # ___________________measures that the cursor has moved a reasonable distance___________________________
        click_release_poss = self.mapToScene(event.pos())
        mouseMoved = click_release_poss - self.last_click_poss
        edgeThreshSqr = EDGE_DRAG_LIM * EDGE_DRAG_LIM

        return (mouseMoved.x() * mouseMoved.x() + mouseMoved.y() * mouseMoved.y()) > edgeThreshSqr


# =============================================================================
# Returns the object at the click location, it will be used to check what has been clicked when starting to drag a wire. 
# =============================================================================

    def getItemAtClick(self, event):
        pos = event.pos()
        obj = self.itemAt(pos)
        return obj

# =============================================================================
# Initiates the checking of intersection points of all wires within the scene.
# =============================================================================		
		
    def intersectionTest(self):
        # checking for intersections is being done here
        if len(self.grScene.scene.wires) > 0:
            self.grScene.scene.wires[0].checkIntersection2()

# =============================================================================
# 
#  Start drawing a wire between two blocks, it will construct a new wire and
#  set the start socket to the socket that has been clicked on and the end 
#  socket to none. The end socket will be set when another socket is ether 
#  clicked or the mouse button is released over another socket, if nether 
#  happen the wire will be deleted.
# 
# =============================================================================
 
    def edgeDragStart(self, item):
        
        if DEBUG: print("socket is input socket:", item.socket.isInputSocket())
        if DEBUG: print("socket is output socket:", item.socket.isOutputSocket())
        
        self.drag_start_socket = item.socket
        self.drag_wire = Wire(self.grScene.scene, item.socket, None, WIRE_TYPE_STEP)
        if DEBUG: print('View::wireDragStart ~   dragwire:', self.drag_wire)


# =============================================================================
# 
# This will be used to set the end socket, the place where the wire has been 
# released will be checked and if it is a graphic socket and is not the start 
# socket then we can add the wire. Next some check will be made to see that 
# inputs are not connected to inputs and outputs are not connected to outputs,
#  that blocks don’t have more than one wire connected to a input but outputs
#  can and that connector blocks cant be used to brake any of these rules.
#  If these conditions are passed the  wire that was dragged will be deleted
#  and a new wire will be created with the start socket being the block the 
#  drag started at and the end socket being the socket the wire was dragged 
#  to, if the conditions not met the wire is simply removed.
# 
# =============================================================================

    def edgeDragEnd(self, item):
        
        
        self.mode = MODE_NONE

        if DEBUG: print('View::edgeDragEnd ~ End dragging edge')
        self.drag_wire.remove()
        self.drag_wire = None



        if type(item) is GraphicsSocket:
            if item.socket != self.drag_start_socket:
                
                # if we released dragging on a socket (other then the beginning socket)

                # we wanna keep all the wires coming from target socket
                if not item.socket.is_multi_wire:
                    item.socket.removeAllEdges()

                # we want to keep all the wires coming from start socket
                if not self.drag_start_socket.is_multi_wire:
                    self.drag_start_socket.removeAllWires()

                # If the block is a socket block check the start socket of the
                # wire that ends in the socket block before connecting a end block
                # so that 2 outputs or 2 inputs are not connected through the
                # Socket block
                
                if self.drag_start_socket.socket_type == 3:
                    if len(self.drag_start_socket.wires) > 0:
                        test = self.drag_start_socket.wires[0].start_socket.socket_type
                        # print("the start socket of the other wire is",test)
                        if self.drag_start_socket.wires[0].start_socket.socket_type != item.socket.socket_type:
                            if item.socket.socket_type == 1:
                                if len(item.socket.wires) == 0:
                                    # new_wire = Wire(self.grScene.scene, self.drag_start_socket, item.socket, WIRE_TYPE_DIRECT)
                                    new_wire = Wire(self.grScene.scene, self.drag_start_socket, item.socket, WIRE_TYPE_STEP)
                            else:
                                # new_wire = Wire(self.grScene.scene, self.drag_start_socket, item.socket, WIRE_TYPE_DIRECT)
                                new_wire = Wire(self.grScene.scene, self.drag_start_socket, item.socket, WIRE_TYPE_STEP)
                
                # Socket block can have multi outputs only and not multi inputs
                elif item.socket.socket_type == 3:
                    if len(item.socket.wires) > 0:
                        i = len(self.drag_start_socket.wires)
                        if i >= 1:
                            self.drag_start_socket.wires[i-1].remove()
                    else:
                        if item.socket.socket_type == 1:
                            if len(item.socket.wires) == 0:
                                # new_wire = Wire(self.grScene.scene, self.drag_start_socket, item.socket, WIRE_TYPE_DIRECT)
                                new_wire = Wire(self.grScene.scene, self.drag_start_socket, item.socket, WIRE_TYPE_STEP)
                        else:
                            # new_wire = Wire(self.grScene.scene, self.drag_start_socket, item.socket, WIRE_TYPE_DIRECT)
                            new_wire = Wire(self.grScene.scene, self.drag_start_socket, item.socket, WIRE_TYPE_STEP)

                # Cannot connect a input to a input or a output to a output
                # Input sockets can not have multiple wires

                # Wire can only be drawn if start and end sockets are different (input to output, or output to input)
                elif self.drag_start_socket.socket_type != item.socket.socket_type:
                    # Additional logic to ensure the input socket (either at start or end of the wire) only has a single
                    # wire coming into it
                    if item.socket.socket_type == 1:
                        if len(item.socket.wires) == 0:
                            new_wire = Wire(self.grScene.scene, self.drag_start_socket, item.socket, WIRE_TYPE_STEP)

                    elif self.drag_start_socket.socket_type == 1:
                        if len(self.drag_start_socket.wires) == 0:
                            new_wire = Wire(self.grScene.scene, self.drag_start_socket, item.socket, WIRE_TYPE_STEP)

                    # Otherwise draw a wire between the two sockets
                    else:
                        new_wire = Wire(self.grScene.scene, self.drag_start_socket, item.socket, WIRE_TYPE_STEP)

                if DEBUG: print("created wire")
                
                if DEBUG: print('View::edgeDragEnd ~ everything done.')
                return False
# =============================================================================
# 
# Here key press events are detected, there are 4 key press we use here, the 
# delete key will be used for deleting blocks and wires, the F key is used to
# flip blocks and the S and L keys are used to save and load. When one of these
# keys is pressed the associated function will be called. 
# 
# =============================================================================

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            self.deleteSelected()
            self.intersectionTest()
        elif event.key() == Qt.Key_F:
            self.flipBlockSockets()
        elif event.key() == Qt.Key_S and event.modifiers() & Qt.ControlModifier:
            self.grScene.scene.saveToFile("graph_testing.json.txt")
        elif event.key() == Qt.Key_L and event.modifiers() & Qt.ControlModifier:
            self.grScene.scene.loadFromFile("graph_testing.json.txt")
        else:
            super().keyPressEvent(event)


# =============================================================================
# 
# Here mouse press events will be detected and their respective functions
# called.
# 
# =============================================================================

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.middleMouseButtonPress(event)
        elif event.button() == Qt.LeftButton:
            self.leftMouseButtonPress(event)
            self.closeParamWindows()
        elif event.button() == Qt.RightButton:
            self.rightMouseButtonPress(event)
        else:
            super().mousePressEvent(event)
            

# =============================================================================
# 
# These functions will be called when the mouse button is released.
# 
# =============================================================================

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.middleMouseButtonRelease(event)
        elif event.button() == Qt.LeftButton:
            self.leftMouseButtonRelease(event)
        elif event.button() == Qt.RightButton:
            self.rightMouseButtonRelease(event)
        else:
            super().mouseReleaseEvent(event)
            
# =============================================================================
#             
#   The left mouse button press will run getItemAtClick and call the 
#   appropriate function base on the item returned. If a graphics Socket 
#   is clicked then start dragging a wire, if it’s a graphic wire it will 
#   end the dragging wire and try and set the end socket, otherwise the 
#   event is ignored.
# 
# =============================================================================

    def leftMouseButtonPress(self, event):
        item = self.getItemAtClick(event)

        self.last_click_poss = self.mapToScene(event.pos())

        if isinstance(item, GraphicsBlock) or isinstance(item, GraphicsWire) or isinstance(item, GraphicsSocketBlock) or item is None:
            if event.modifiers() & Qt.ShiftModifier:
                event.ignore()
                fakeEvent = QMouseEvent(QEvent.MouseButtonPress, event.localPos(), event.screenPos(),
                                        Qt.LeftButton, event.buttons() | Qt.LeftButton,
                                        event.modifiers() | Qt.ControlModifier)
                super().mousePressEvent(fakeEvent)
                return

        if type(item) is GraphicsSocket:

            if self.mode == MODE_NONE:
                self.mode = MODE_WIRE_DRAG
                self.edgeDragStart(item)
                return

            if self.mode == MODE_WIRE_DRAG:
                res = self.edgeDragEnd(item)
                if res:
                    return

        if issubclass(item.__class__, GraphicsWire):
            if self.mode == MODE_WIRE_DRAG:
                res = self.edgeDragEnd(item)
                if res:
                    return

        super().mousePressEvent(event)
        
# =============================================================================
#         
# On the release of the left mouse button getItemAtClick is called to check what
# the mouse wase released on if a wire is being dragged it will check how
# far the wire has moved then end the drag and try to connect a socket.
# Then the check intersection code will be run to check for and mark wire
# intersections.  
#         
# =============================================================================

    def leftMouseButtonRelease(self, event):
        # get item which we clicked
        item = self.getItemAtClick(event)

        if isinstance(item, GraphicsBlock) or isinstance(item, GraphicsWire) or isinstance(item, GraphicsSocketBlock) or item is None:
            if event.modifiers() & Qt.ShiftModifier:
                event.ignore()
                fakeEvent = QMouseEvent(event.type(), event.localPos(), event.screenPos(),
                                        Qt.LeftButton, Qt.NoButton,
                                        event.modifiers() | Qt.ControlModifier)
                super().mouseReleaseEvent(fakeEvent)
                return

        if self.mode == MODE_WIRE_DRAG:
            if self.dist_click_release(event):
                res = self.edgeDragEnd(item)
                if res:
                    return

        super().mouseReleaseEvent(event)



# =============================================================================
# nothing is linked to a right mouse click
# =============================================================================

    def rightMouseButtonPress(self, event):
        return super().mousePressEvent(event)
    
    
# =============================================================================
# nothing is linked to a right mouse Release  
# =============================================================================

    def rightMouseButtonRelease(self, event):
        return super().mouseReleaseEvent(event)
    
    
# =============================================================================
#  NOT SURE WHATS HAPPENING HERE   
# =============================================================================

    def middleMouseButtonPress(self, event):
        releaseEvent = QMouseEvent(QEvent.MouseButtonRelease, event.localPos(), event.screenPos(),
                                   Qt.LeftButton, Qt.NoButton, event.modifiers())
        super().mouseReleaseEvent(releaseEvent)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        fakeEvent = QMouseEvent(event.type(), event.localPos(), event.screenPos(),
                                Qt.LeftButton, event.buttons() | Qt.LeftButton, event.modifiers())
        super().mousePressEvent(fakeEvent)

# =============================================================================
#  NOT SURE WHATS HAPPENING HERE   
# =============================================================================

    def middleMouseButtonRelease(self, event):
        fakeEvent = QMouseEvent(event.type(), event.localPos(), event.screenPos(),
                                Qt.LeftButton, event.buttons() & ~Qt.LeftButton, event.modifiers())
        super().mouseReleaseEvent(fakeEvent)
        self.setDragMode(QGraphicsView.NoDrag)


# =============================================================================
# 
# The mouse wheel is used for zooming in and out on the work area
#  
# =============================================================================
  
    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            zoomFactor = 1.25
            self.zoom += self.zoomStep
        else:
            zoomFactor = 0.8
            self.zoom -= self.zoomStep

        if self.zoomRange[0]-1 <= self.zoom <= self.zoomRange[1]:
            self.scale(zoomFactor, zoomFactor)
        elif self.zoom < self.zoomRange[0]-1:
            self.zoom = self.zoomRange[0]-1
        elif self.zoom > self.zoomRange[1]:
            self.zoom = self.zoomRange[1]
            
            
# =============================================================================
#             
# If a wire is dragging then as the mouse moves the wire will be redrawn with
# the coordinates of the mouse.
# 
# =============================================================================
    
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

        if self.mode == MODE_WIRE_DRAG:
            pos = self.mapToScene(event.pos())
            self.drag_wire.grWire.setDestination(pos.x(), pos.y())
            self.drag_wire.grWire.update()

        self.intersectionTest()
