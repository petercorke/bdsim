# PyQt5 imports
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import QGraphicsView

# BdEdit imports
from .block import Block
from .block_graphics_wire import GraphicsWire
from .block_graphics_socket import GraphicsSocket
from .block_graphics_block import GraphicsBlock, GraphicsSocketBlock
from .block_wire import Wire, WIRE_TYPE_STEP, WIRE_TYPE_DIRECT, WIRE_TYPE_BEZIER

# =============================================================================
#
#   Defining and setting global variables
#
# =============================================================================
# Wire mode variables - used for determining what type of wire to draw
MODE_NONE = 1
MODE_WIRE_DRAG = 2
EDGE_DRAG_LIM = 10

# Variable for enabling/disabling debug comments
DEBUG = False


# =============================================================================
#
#   Defining the GraphicsView Class, which handles most auto detected
#   press/scroll/click/scroll/key events, and assigns logic to those actions as
#   needed.
# 
# =============================================================================
class GraphicsView(QGraphicsView):
    """
    The ``GraphicsView`` Class extends the ``QGraphicsView`` Class from PyQt5,
    and handles most of the user interactions with the ``Interface``, through
    press/scroll/click/scroll/key events. It also contains the logic for what Wire
    should be drawn and what Sockets it connects to. Here mouse click events
    are used to drag the wires from a start to a end socket, when click is
    dragged from a socket, the mode == MODE_WIRE_DRAG will be set to True and a
    Wire will follow the mouse until a end socket is set or mode == MODE_WIRE_DRAG
    is False and the Wire will be deleted.
    """
    # -----------------------------------------------------------------------------
    def __init__(self, grScene, parent=None):
        """
        This method creates an ``QGraphicsView`` instance and associates it to this
        ``GraphicsView`` instance.

        :param grScene: the ``GraphicsScene`` to which this ``GraphicsView`` belongs to
        :type grScene: GraphicsScene, required
        :param parent: the parent widget this GraphicsView belongs to (should be None)
        :type parent: None, optional
        """
        super().__init__(parent)

        # The GraphicsScene this GraphicsView belongs to, is assigned to an internal variable
        self.grScene = grScene

        # The GraphicsScene is initialized with some settings to make things draw smoother
        self.initUI()

        # The GraphicsScene this GraphicsView belongs to is connected
        self.setScene(self.grScene)

        # The drawing mode of the wire is initially set to MODE_NONE
        self.mode = MODE_NONE

        # Definitions of zoom related variables
        # The there are 10 zoom levels, with level 7 being the default level
        # Levels 8-10 zoom in, while levels 0-6 zoom out
        self._default_zoom_level = 7
        self.zoom = self._default_zoom_level
        self.zoomStep = 1
        self.zoomRange = [0, 10]

    # -----------------------------------------------------------------------------
    def initUI(self):
        """
        This method initializes the GraphicsScene with additional settings
        to make things draw smoother
        """
        self.setRenderHints(QPainter.Antialiasing | QPainter.HighQualityAntialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    # -----------------------------------------------------------------------------
    def closeParamWindows(self):
        """
        This method will close the parameter window used for changing the
        user-editable block variables.
        """

        # If there are Blocks within the Scene
        if len(self.grScene.scene.blocks) != 0:
            # Iterate through all the Blocks
            for block in self.grScene.scene.blocks:
                # And if that Block has a ParamWindow, close it
                if block.parameterWindow is not None:
                    block.parameterWindow.setVisible(False)
                    block._param_visible = False

    # -----------------------------------------------------------------------------
    def deleteSelected(self):
        """
        This method removes the selected Block or Wire from the scene.
        """

        # For each selected item within the GraphicsScene
        for item in self.grScene.selectedItems():
            # If the item is a Wire, remove it
            if isinstance(item, GraphicsWire):
                item.wire.remove()
            # Or if the item is a Block or Connector Block, remove it
            elif isinstance(item, GraphicsBlock) or isinstance(item, GraphicsSocketBlock):
                item.block.remove()

    # -----------------------------------------------------------------------------
    def flipBlockSockets(self):
        """
        This method flips the selected Block so that the input and output
        Sockets change sides.
        """

        # For each selected item within the GraphicsScene
        for item in self.grScene.selectedItems():
            # If the item is a Block or Connector Block, flip its sockets
            if isinstance(item, GraphicsBlock) or isinstance(item, GraphicsSocketBlock):
                item.block.updateSocketPositions()

    # -----------------------------------------------------------------------------
    def dist_click_release(self, event):
        """
        This method checks how for the cursor has moved. This is be used when the
        Wire is dragged, to check that wire has been dragged away from the start
        socket, so that when it is released on a socket we know its not the
        start socket.

        :param event: a mouse release event that has occurred with this GraphicsView
        :type event: QMouseEvent, automatically recognized by the inbuilt function
        :return: - True (if mouse has been released more than an defined distance from
                   the start_socket)
                 - False (if mouse has been released too close too the start_socket)
        :rtype: bool
        """

        # Measures that the cursor has moved a reasonable distance
        click_release_poss = self.mapToScene(event.pos())
        mouseMoved = click_release_poss - self.last_click_poss
        edgeThreshSqr = EDGE_DRAG_LIM * EDGE_DRAG_LIM

        return (mouseMoved.x() * mouseMoved.x() + mouseMoved.y() * mouseMoved.y()) > edgeThreshSqr

    # -----------------------------------------------------------------------------
    def getItemAtClick(self, event):
        """
        This method returns the object at the click location. It is used when
        checking what item within the GraphicsView has been clicked when starting
        to drag a wire.

        :param event: a mouse click event that has occurred with this GraphicsView
        :type event: QMouseEvent, automatically recognized by the inbuilt function
        :return: the item that has been clicked on (can be ``GraphicsBlock``,
                 ``GraphicsSocket``, ``GraphicsWireStep``, ``NoneType``), required
        :rtype: GraphicsBlock, GraphicsSocket, GraphicsWireStep or NoneType
        """
        pos = event.pos()
        obj = self.itemAt(pos)
        return obj

    # -----------------------------------------------------------------------------
    def intersectionTest(self):
        """
        This method initiates the checking of all Wires within the Scene for
        intersection points where they overlap.
        """
        # If there are wires within the Scene
        if len(self.grScene.scene.wires) > 0:
            # Call the first wire in the Scene to check the intersections
            # Calling the first wire will still check intersection points
            # of all wires, however since that code is located within the
            # Wire class, this is how it's accessed.
            self.grScene.scene.wires[0].checkIntersections()

    # -----------------------------------------------------------------------------
    def edgeDragStart(self, item):
        """
        This method starts drawing a Wire between two Blocks. It will
        construct a new ``Wire`` and set the start socket to the socket that
        has been clicked on, and the end socket to None. The end socket will
        be set when either another socket is clicked, or the mouse button is
        released over another socket. If neither happen, the wire will be deleted.

        :param item: the socket that has been clicked on
        :type item: GraphicsSocket, required
        """
        # If in DEBUG mode, the follow code will print the start and end
        # sockets that have been recognized, as being relevant to this wire.
        if DEBUG: print("socket is input socket:", item.socket.isInputSocket())
        if DEBUG: print("socket is output socket:", item.socket.isOutputSocket())

        # The start socket is extracted from the provided item
        self.drag_start_socket = item.socket
        # A step wire is made from the start socket, to nothing
        self.drag_wire = Wire(self.grScene.scene, item.socket, None, WIRE_TYPE_STEP)

        # If in DEBUG mode, the following code will print the wire that has
        # just been created
        if DEBUG: print('View::wireDragStart ~   dragwire:', self.drag_wire)

    # -----------------------------------------------------------------------------
    def edgeDragEnd(self, item):
        """
        This method is used for setting the end socket of the Wire. The place
        where the wire has been released will be checked, and if it is a
        ``GraphicSocket`` and is not the start socket then a Wire is completed.

        Next some check will be made to see that inputs are not connected to inputs
        and outputs are not connected to outputs. Additionally, Block Sockets will
        be checked to prevent multiple Wires from connecting to a single input socket.
        No such restriction is placed on the output sockets. This same logic is
        applied to Connector Blocks.

        If these conditions are met, the wire that was dragged will be deleted, and
        a new Wire will be created with the start socket from the block the wire
        drag started at, and the end socket being from the socket of the block the
        Wire was dragged to.

        If the above-mentioned conditions not met, the wire is simply removed.

        :param item: should be the socket that has been clicked on (however could
        be one of the following: ``GraphicsBlock``, ``GraphicsSocket``,
        ``GraphicsWireStep`` or ``NoneType``)
        :type item: GraphicsSocket, required
        :return: False (if the the Wire has been successfully drawn between Blocks)
        :rtype: bool
        """

        # The dragging mode of the wire is initially set to being None
        self.mode = MODE_NONE

        if DEBUG: print('View::edgeDragEnd ~ End dragging edge')
        # The previous wire (drag_wire) is removed
        self.drag_wire.remove()
        self.drag_wire = None

        # If the clicked item is a GraphicsSocket
        if type(item) is GraphicsSocket:
            # And the clicked socket is not the same socket the original wire started from
            if item.socket != self.drag_start_socket:
                
                # If we released dragging on a socket (other then the beginning socket)
                # We want to keep all the wires coming from target socket
                if not item.socket.is_multi_wire:
                    item.socket.removeAllEdges()

                # We want to keep all the wires coming from start socket
                if not self.drag_start_socket.is_multi_wire:
                    self.drag_start_socket.removeAllWires()

                # If the block is a socket block check the start socket of the
                # wire that ends in the socket block before connecting an end block,
                # so that 2 outputs or 2 inputs are not connected through the
                # Socket block
                
                if self.drag_start_socket.socket_type == 3:
                    if len(self.drag_start_socket.wires) > 0:
                        test = self.drag_start_socket.wires[0].start_socket.socket_type
                        if self.drag_start_socket.wires[0].start_socket.socket_type != item.socket.socket_type:
                            if item.socket.socket_type == 1:
                                if len(item.socket.wires) == 0:
                                    new_wire = Wire(self.grScene.scene, self.drag_start_socket, item.socket, WIRE_TYPE_STEP)
                            else:
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
                                new_wire = Wire(self.grScene.scene, self.drag_start_socket, item.socket, WIRE_TYPE_STEP)
                        else:
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

    # -----------------------------------------------------------------------------
    def keyPressEvent(self, event):
        """
        This is an inbuilt method of QGraphicsView, that is overwritten by
        ``GraphicsView`` to detect, and assign actions to the following key presses.

        - DEL or BACKSPACE: removes selected item from the Scene
        - F: flips the sockets on a Block or Connector Block
        - CTRL + S: previously connected to saving the Scene
        - CTRL + L: previously connected to loading a Scene file

        The saving and loading of a file using keys has since been disabled, as
        it used an old method for saving/loading JSON files which has since been
        overwritten in the Interface Class. However these key checks are still
        connected if future development should take place.

        :param event: key(s) press(es) that have been detected
        :type event: QKeyPressEvent, automatically recognized by the inbuilt function
        """

        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            self.deleteSelected()
            self.intersectionTest()
        elif event.key() == Qt.Key_F:
            self.flipBlockSockets()
        elif event.key() == Qt.Key_S and event.modifiers() & Qt.ControlModifier:
            pass
            # self.grScene.scene.saveToFile("graph_testing.json.txt")
        elif event.key() == Qt.Key_L and event.modifiers() & Qt.ControlModifier:
            pass
            # self.grScene.scene.loadFromFile("graph_testing.json.txt")
        else:
            super().keyPressEvent(event)

    # -----------------------------------------------------------------------------
    def mousePressEvent(self, event):
        """
        This is an inbuilt method of QGraphicsView, that is overwritten by
        ``GraphicsView`` to detect, and direct the Left, Middle and Right mouse
        button presses to methods that handle their associated logic.

        Additionally, when the Left mouse button is pressed anywhere in the
        ``GraphicsView``, any currently ``ParamWindow`` that relates to an active
        ``Block`` within the ``Scene`` will be closed.

        :param event: a mouse press event (Left, Middle or Right)
        :type event: QMousePressEvent, automatically recognized by the inbuilt function
        """

        if event.button() == Qt.MiddleButton:
            self.middleMouseButtonPress(event)
        elif event.button() == Qt.LeftButton:
            self.leftMouseButtonPress(event)
            self.closeParamWindows()
        elif event.button() == Qt.RightButton:
            self.rightMouseButtonPress(event)
        else:
            super().mousePressEvent(event)

    # -----------------------------------------------------------------------------
    def mouseReleaseEvent(self, event):
        """
        This is an inbuilt method of QGraphicsView, that is overwritten by
        ``GraphicsView`` to detect, and direct the Left, Middle and Right mouse
        button releases to methods that handle their associated logic.

        :param event: a mouse release event (Left, Middle or Right)
        :type event: QMouseReleaseEvent, required
        """

        if event.button() == Qt.MiddleButton:
            self.middleMouseButtonRelease(event)
        elif event.button() == Qt.LeftButton:
            self.leftMouseButtonRelease(event)
        elif event.button() == Qt.RightButton:
            self.rightMouseButtonRelease(event)
        else:
            super().mouseReleaseEvent(event)

    # -----------------------------------------------------------------------------
    def leftMouseButtonPress(self, event):
        """
        This method handles the logic associate with the Left mouse button press.
        It will always run the getItemAtClick method to return the item that
        has been clicked on.

        - If a GraphicsSocket is pressed on, then a draggable Wire will be started.
        - If a GraphicWire is pressed, then the active draggable Wire will be ended
          (when the wire is draggable, clicking off at a Socket, will register the
          clicked item as a GraphicsWire).

        Alternatively, the following logic is applied for selecting items.

        - If an empty space within the GraphicsView is pressed, a draggable net
          will appear, within which all items will be selected.
        - If left clicking while holding the SHIFT or CTRL key, this will incrementally
          select an item from within the GraphicsView. The items that are selectable
          are ``GraphicsBlock``, ``GraphicsWire`` or ``GraphicsSocketBlock`` (which is
          the Connector Block).


        Otherwise nothing is done with the left mouse press.

        :param event: a Left mouse button press
        :type event: QMousePressEvent, required
        :return: None to exit the method
        :rtype: NoneType
        """

        # Item that is clicked on is grabbed
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

    # -----------------------------------------------------------------------------
    def leftMouseButtonRelease(self, event):
        """
        This method handles the logic associate with the Left mouse button release.
        It will always run the getItemAtClick method to return the item that
        the mouse has been released from.

        - If a Wire was the item being dragged, it will check how far the Wire has
          moved, then an attempt to complete the Wire onto a Socket will be made.
          If no Socket is found, the Wire will be ended.

        Alternatively, the following logic is applied for selecting items.

        - If an empty space within the GraphicsView is released, if a draggable net
          was active, all items within that net will be selected.
        - If left clicking while holding the SHIFT or CTRL key, this will incrementally
          select an item from within the GraphicsView. The items that are selectable
          are ``GraphicsBlock``, ``GraphicsWire`` or ``GraphicsSocketBlock`` (which is
          the Connector Block).

        :param event: a Left mouse button release
        :type event: QMouseReleaseEvent, required
        :return: None to exit the method
        :rtype: NoneType
        """

        # Get item which we clicked
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

    # -----------------------------------------------------------------------------
    def rightMouseButtonPress(self, event):
        """
        This method handles the logic associate with the Right mouse button press.
        Currently no logic is linked to a right mouse press.

        :param event: the detected right mouse press event
        :type event: QMousePressEvent, required
        :return: the mouse press event is returned
        :rtype: QMousePressEvent
        """

        return super().mousePressEvent(event)

    # -----------------------------------------------------------------------------
    def rightMouseButtonRelease(self, event):
        """
        This method handles the logic associate with the Right mouse button release.
        Currently no logic is linked to a right mouse release.

        :param event: the detected right mouse release event
        :type event: QMousePressEvent, required
        :return: the mouse release event is returned
        :rtype: QMouseReleaseEvent
        """

        return super().mouseReleaseEvent(event)

    # -----------------------------------------------------------------------------
    def middleMouseButtonPress(self, event):
        """
        This method handles the logic associate with the Middle mouse button press
        (perhaps more intuitively understood as pressing the scroll wheel).
        When the scroll wheel is pressed, the mouse cursor will appear as a hand
        that pinches the GraphicsView, allowing the canvas to be dragged around.

        :param event: the detected middle mouse press event
        :type event: QMousePressEvent, required
        """

        releaseEvent = QMouseEvent(QEvent.MouseButtonRelease, event.localPos(), event.screenPos(),
                                   Qt.LeftButton, Qt.NoButton, event.modifiers())
        super().mouseReleaseEvent(releaseEvent)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        fakeEvent = QMouseEvent(event.type(), event.localPos(), event.screenPos(),
                                Qt.LeftButton, event.buttons() | Qt.LeftButton, event.modifiers())
        super().mousePressEvent(fakeEvent)

    # -----------------------------------------------------------------------------
    def middleMouseButtonRelease(self, event):
        """
        This method handles the logic associate with the Middle mouse button release
        (perhaps more intuitively understood as releasing the scroll wheel).
        When the scroll wheel is releasing, the mouse cursor will change back from
        appearing as a hand to the default mouse cursor (pointer arrow on Windows).

        :param event: the detected middle mouse release event
        :type event: QMouseReleaseEvent, required
        """
        fakeEvent = QMouseEvent(event.type(), event.localPos(), event.screenPos(),
                                Qt.LeftButton, event.buttons() & ~Qt.LeftButton, event.modifiers())
        super().mouseReleaseEvent(fakeEvent)
        self.setDragMode(QGraphicsView.NoDrag)

    # -----------------------------------------------------------------------------
    def wheelEvent(self, event):
        """
        This is an inbuilt method of QGraphicsView, that is overwritten by
        ``GraphicsView`` to assign logic to detected scroll wheel movement.

        - As the scroll wheel is moved up, this will make the zoom in on the work
          area of the ``GraphicsScene``.
        - As the scroll wheel is moved down, this will make the zoom out of the work
          area of the ``GraphicsScene``.

        :param event: the detected scroll wheel movement
        :type event: QWheelEvent, automatically recognized by the inbuilt function
        """

        # If scroll wheel vertical motion is detected to being upward
        if event.angleDelta().y() > 0:
            # Set the zoom factor to 1.25, and incrementally increase the zoom step
            zoomFactor = 1.25
            self.zoom += self.zoomStep

        # Else the scroll wheel is moved downwards
        else:
            # Set the zoom factor to 1/1.25, and incrementally decrease the zoom step
            zoomFactor = 0.8
            self.zoom -= self.zoomStep

        # If the current zoom is within the allowable zoom levels (0 to 10)
        # Scale the Scene (in the x and y) by the above-set zoomFactor
        if self.zoomRange[0]-1 <= self.zoom <= self.zoomRange[1]:
            self.scale(zoomFactor, zoomFactor)
        # Otherwise if the current zoom is below the lowest allowable zoom level (0)
        # Force the zoom level to the lowest allowable level
        elif self.zoom < self.zoomRange[0]-1:
            self.zoom = self.zoomRange[0]-1
        # Otherwise if the current zoom is above the highest allowable zoom level (10)
        # Force the zoom level to the highest allowable level
        elif self.zoom > self.zoomRange[1]:
            self.zoom = self.zoomRange[1]

    # -----------------------------------------------------------------------------
    def mouseMoveEvent(self, event):
        """
        This is an inbuilt method of QGraphicsView, that is overwritten by
        ``GraphicsView`` to assign logic to detected mouse movement.

        - If the wire is in dragging mode, the position the wire is drawn to
          will be updated to the mouse cursor as it is moved around.
        - Additionally, the code to check for intersection amongst wires will
          be run, and subsequently, if any are found, they will be automatically
          marked within the ``GraphicsScene`` Class.

        :param event: the detected mouse movement event
        :type event: QMouseMoveEvent, automatically recognized by the inbuilt function
        """
        super().mouseMoveEvent(event)

        # If the wire is in dragging mode
        if self.mode == MODE_WIRE_DRAG:
            # Grab the on-screen position of the mouse cursor
            pos = self.mapToScene(event.pos())
            # Set the point that the wire draws to, as the current x,y position of the mouse cursor
            self.drag_wire.grWire.setDestination(pos.x(), pos.y())
            # Call for the wire to be redrawn/updated accordingly
            self.drag_wire.grWire.update()

        # Call for the intersection code to be run
        self.intersectionTest()
