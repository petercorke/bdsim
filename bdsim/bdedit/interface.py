# Library imports
import os
import inspect
import importlib.util
from pathlib import Path

# PyQt5 imports
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5 import QtPrintSupport

# BdEdit imports
from bdsim.bdedit.block import *
from bdsim.bdedit.Icons import *
from bdsim.bdedit.block_wire import Wire
from bdsim.bdedit.block_importer import *
from bdsim.bdedit.floating_label import *
from bdsim.bdedit.block_main_block import *
from bdsim.bdedit.interface_scene import Scene
from bdsim.bdedit.block_connector_block import *
from bdsim.bdedit.interface_graphics_view import GraphicsView

# =============================================================================
#
#   Defining and setting global variables and methods
#
# =============================================================================
# Variable for enabling/disabling debug comments
DEBUG = False

# =============================================================================
#
#   Defining the Interface Class, which houses all the application appearance
#   logic, and connects all other classes together.
#
# =============================================================================
class Interface(QWidget):
    """
    The ``Interface`` Class extends the ``QWidget`` Class from PyQt5, and houses
    the necessary methods for controlling how the application appears. It also
    connects the other Classes to allow for Block Diagrams to be constructed.

    This class includes information about the:

    - toolbar, its buttons and their connections
    - library Browser menu, its buttons and their connections
    - scene, its appearance (Background and Foreground) and its items (Blocks, Sockets, Wires)
    - application layout, in terms of where the toolbar, library Browser, scene and
      parameter window is displayed.

    Note, the toolbar, library Browser, scene and parameter window will be referred
    to as application components.
    """

    # -----------------------------------------------------------------------------
    def __init__(self, resolution, debug=False, parent=None):
        """
        This method initializes an instance of the ``Interface``.

        :param resolution: the desktop screen resolution of the user
        :type resolution: PyQt5.QtCore.QRect(0, 0, screen_width, screen_height), required
        :param parent: the parent widget this interface belongs to (should be None)
        :type parent: None, optional
        """
        super().__init__(parent)

        # The toolbar and library browser widgets are initialized
        # self.toolBar = QWidget()
        self.libraryBrowser = QWidget()

        # LibraryBrowserBox is wrapped by LibraryBrowser, as this allows the items within
        # the libraryBrowser to be scrollable
        self.libraryBrowserBox = QGroupBox()

        # The Scene interface is called to be initialized
        self.initUI(resolution, debug, parent)

    # -----------------------------------------------------------------------------
    def initUI(self, resolution, debug, main_window):
        """
        This method is responsible for controlling the size of the application window.
        It is also responsible for each application component, in terms of:

        - setting its dimensions ;
        - setting its position within the application layout;
        - creating its relevant buttons and connecting them to desired actions;
        - populating it with the created buttons; and
        - spacing out these buttons within the application component itself.

        :param resolution: the desktop screen resolution of the user
        :type resolution: PyQt5.QtCore.QRect(0, 0, screen_width, screen_height), required
        :return: a QWidget that is displayed within the application from bdEdit.py
        :rtype: QWidget
        """

        # _______________________________ Initial Setup _______________________________
        # Sets interface's (application window's) resolution. Several options available:
        #self.setGeometry(100, 100, resolution.width() - 200, resolution.height() - 200)  # Interface will be same size as desktop screen, minus 100 pixels from all sides
        #self.setGeometry(resolution.width() / 4, resolution.height() / 4, resolution.width() / 2, resolution.height() / 2)  # Interface will be half the size of the desktop screen, and centered in the screen
        #self.setGeometry(100, 100, resolution.width() / 2, resolution.height() / 2)  # Interface will be half the size of the desktop screen, and displayed 100 pixels down and right from top left corner of the screen
        main_window.setGeometry(100, 100, resolution.width() / 2, resolution.height() / 2)  # Interface will be half the size of the desktop screen, and displayed 100 pixels down and right from top left corner of the screen

        # Layout manager is defined and set for the application layout. This will handle
        # the positioning of each application component.
        self.layout = QGridLayout()  # Contains all the widgets
        self.layout.setContentsMargins(0, 0, 0, 0)  # Removes the border
        self.setLayout(self.layout)

        # Different screen resolutions result in varying sizes of the library browser
        # and parameter window panels. To compensate for this, the preferred dimensions
        # of these panels as seen on the screen while being developed (2560 resolution
        # width) have been scaled to other screen sizes.
        self.layout.scale = 2560 / resolution.width()

        # An instance of the Scene class is created, providing it the resolution of the
        # desktop screen and the application layout manager.
        self.scene = Scene(resolution, self.layout)

        # Since the Scene itself is only a class and doesn't have a 'visual' representation,
        # it will create a 'grScene' variable, that will be responsible for handling everything
        # graphical related. This 'grScene' is fed into an instance of a GraphicsView, which
        # handles visual updates to the 'grScene' (e.g. updating the Scene when Blocks are
        # deleted, or when wires are moved around)
        self.canvasView = GraphicsView(self.scene.grScene, self)

        # Import all the blocks that bdedit can see, and sort the list in alphabetical order
        self.blockLibrary = import_blocks(self.scene, self.layout)
        self.sortBlockLibrary()

        # if debug:
        # print("\nfrom self.blockLibrary")
        # for group in self.blockLibrary:
        #     for block_cls in group[1]:
        #         for variables in block_cls[1].__dict__.items():
        #             if variables[0] in ["parameters"]:
        #                 print("('" + variables[0] + "',")
        #                 for param in variables[1]:
        #                     print("     ", param)
        #             else:
        #                 print(variables)
        #         print()
        #
        # print("\n----------------------------------\n")

        # print("\nfrom blocklist")
        # for block_cls in blocklist:
        #     for items in block_cls.__dict__.items():
        #         print(items)
        #     print()

        # _______________________________ Toolbar Setup _______________________________
        # A fixed height is set for the toolbar
        # self.toolBar.setFixedHeight(50)
        #
        # # Buttons are created (and named) that will populate the toolbar
        # self.newFile_button = QPushButton('New File')
        # self.openFile_button = QPushButton('Open File')
        # self.save_button = QPushButton('Save')
        # self.saveAs_button = QPushButton('Save As')
        # self.simulate_button = QPushButton('Simulate')
        # self.run_button = QPushButton('Run')
        # self.screenshot_button = QPushButton('Screenshot')
        # self.grid_mode = QWidget()
        # self.toggle_connector_block_visibility_checkbox = QCheckBox("Hide Connector Blocks", self)
        # self.alignLeft = QPushButton("Left")
        # self.alignCenter = QPushButton("Center")
        # self.alignRight = QPushButton("Right")
        #
        # # Each widget must have a layout manager which controls how items are
        # # positioned within it. The grid_mode widget will consist of a label
        # # and a drop down menu, hence it's layout will be horizontal.
        # self.grid_mode.layout = QHBoxLayout()
        # self.grid_mode_label = QLabel('Grid Mode')
        # # Drop down menu is created for choosing grid mode (Light, Dark, Off)
        # self.grid_mode_options = QComboBox()
        # self.grid_mode_options.addItem("Light")
        # self.grid_mode_options.addItem("Dark")
        # self.grid_mode_options.addItem("Off")
        #
        # # Both the label and the drop down menu are added to the grid_mode widget's
        # # layout manager, and its layout is set to this manager.
        # self.grid_mode.layout.addWidget(self.grid_mode_label)
        # self.grid_mode.layout.addWidget(self.grid_mode_options)
        # self.grid_mode.setLayout(self.grid_mode.layout)
        #
        # # As mentioned above, each widget must have a layout manager. Since the
        # # toolbar will be displayed along the top of the interface, items should
        # # be displayed horizontally, hence the horizontal layout manager.
        # self.toolBar.layout = QHBoxLayout()
        # # The borders of the layout are removed.
        # self.toolBar.layout.setContentsMargins(0, 0, 0, 0)
        #
        # # The above-created buttons are populated into the toolbar
        # self.toolBar.layout.addWidget(self.newFile_button)
        # self.toolBar.layout.addWidget(self.openFile_button)
        # self.toolBar.layout.addWidget(self.save_button)
        # self.toolBar.layout.addWidget(self.saveAs_button)
        # self.toolBar.layout.addWidget(self.run_button)
        # self.toolBar.layout.addWidget(self.screenshot_button)
        # self.toolBar.layout.addWidget(self.grid_mode)
        # self.toolBar.layout.addWidget(self.toggle_connector_block_visibility_checkbox)
        # self.toolBar.layout.addWidget(self.alignLeft)
        # self.toolBar.layout.addWidget(self.alignCenter)
        # self.toolBar.layout.addWidget(self.alignRight)
        #
        # # The above-created buttons are connected to desired actions
        # self.newFile_button.clicked.connect(lambda: main_window.newFile())  # self.scene.clear() removes all items from the scene
        # self.save_button.clicked.connect(lambda: main_window.saveToFile())  # self.saveToFile() initiates a prompt to save the current scene
        # self.openFile_button.clicked.connect(lambda: main_window.loadFromFile())  # self.loadFromFile() initiates a prompt to choose a scene file to load
        # self.saveAs_button.clicked.connect(lambda: main_window.saveAsToFile())
        # self.run_button.clicked.connect(lambda: main_window.runButton())
        # self.screenshot_button.clicked.connect(lambda: self.save_image('Scene Picture'))    # self.save_image creates an image of the current scene, saved as 'Scene Picture'
        # self.grid_mode_options.currentIndexChanged.connect(lambda: self.updateColorMode())  # self.updateColorMode() updates the background mode of the scene
        # self.toggle_connector_block_visibility_checkbox.stateChanged.connect(self.clickBox)
        #
        # self.alignLeft.clicked.connect( lambda: self.setFloatingTextAlignment("AlignLeft") )
        # self.alignCenter.clicked.connect( lambda: self.setFloatingTextAlignment("AlignCenter")  )
        # self.alignRight.clicked.connect( lambda: self.setFloatingTextAlignment("AlignRight")  )
        #
        # # Finally, the toolbar items are set to be aligned within the horizontal center of the toolbar
        # self.toolBar.layout.setAlignment(Qt.AlignHCenter)
        # self.toolBar.setLayout(self.toolBar.layout)

        # ___________________________ Library Browser Setup ___________________________
        # The library browser will be displayed along the left-hand side of the interface,
        # items should be displayed vertically within it, hence the vertical layout manager.
        self.libraryBrowser.layout = QVBoxLayout(self.libraryBrowser)

        # Adding icon for the tool above the library browser
        self.tool_logo = QLabel()
        self.tool_logo.setPixmap(QPixmap(":/Icons_Reference/Icons/bdsim_logo2.png").scaledToWidth(230 * self.layout.scale))
        # self.tool_logo.setPixmap(QPixmap(":/Icons_Reference/Icons/bdsim_logo2.png").scaledToHeight(40 * self.layout.scale))
        self.libraryBrowser.layout.addWidget(self.tool_logo)
        self.libraryBrowser.layout.setAlignment(self.tool_logo, Qt.AlignmentFlag.AlignHCenter)

        # The follow label is added to the library browser, naming it
        # self.libraryBrowser.layout.addWidget(QLabel('<font size=8><b>Library Browser</font>'))

        # The library browser box makes the items inside of it scrollable, so all the relevant
        # buttons will be added into this widget. This widget will also have a vertical layout
        # manager. Then this widget will be wrapped by the library browser (will go inside it),
        # in order to position where it is displayed in the application window.
        self.libraryBrowserBox.layout = QVBoxLayout()

        # Remove whitespace between buttons within the library browser panel
        self.libraryBrowserBox.layout.setSpacing(2)

        # Make a button for canvas items. These items are like the auto-imported blocks,
        # but are created from definitions in bdedit, rather than from external libraries
        self.canvasItems_button = QPushButton(' + Canvas Items')
        self.canvasItems_button.setStyleSheet("QPushButton { text-align: left }")
        self.canvasItems_button.clicked.connect(self.toggleCanvasItems)
        self.canvas_items_hidden = True

        # A list is created to hold all the buttons that will create Blocks within the Scene
        self.list_of_scrollbar_buttons = []

        # This set of blocks are definited internally within bdedit. Currently they include:
        # the connector block, the main block, and the text item. As they are definied by
        # bdedit, rather than having their definitions come from an external library, the
        # buttons for these items must also be manually created within bdedit.
        self.libraryBrowserBox.layout.addWidget(self.canvasItems_button)
        self.connector_block_button = QPushButton("Connector Block")
        self.main_block_button = QPushButton("Main Block")
        self.text_item_button = QPushButton("Text Item")

        self.connector_block_button.setVisible(False)
        self.main_block_button.setVisible(False)
        self.text_item_button.setVisible(False)

        # These buttons are then connected to creating their respective instances within the Scene
        self.connector_block_button.clicked.connect(lambda checked: Connector(self.scene, self.layout, "Connector Block"))
        self.main_block_button.clicked.connect(lambda checked: Main(self.scene, self.layout))
        self.text_item_button.clicked.connect(lambda checked: Floating_Label(self.scene, self.layout))

        # Adding the buttons to the library browser's layout manager
        self.libraryBrowserBox.layout.addWidget(self.connector_block_button)
        self.libraryBrowserBox.layout.addWidget(self.main_block_button)
        self.libraryBrowserBox.layout.addWidget(self.text_item_button)

        # This for loop goes through each block type (sink, source, function) that was auto
        # imported (and stored into self.blockLibrary at the Interface's initialization).
        for sub_class_group in self.blockLibrary:

            group_of_buttons = []

            # Grab the each group that blocks belong to, and create a library panel button for those groups
            cleaned_class_group = sub_class_group[0][:-1] if sub_class_group[0].endswith('s') else sub_class_group[0]
            group_button = QPushButton(" + " + cleaned_class_group.capitalize() + " Blocks")

            # Buttons' text alignment is set to be left-aligned
            group_button.setStyleSheet("QPushButton { text-align: left }")

            # The following variables control the '+,-' sign displayed alongside each
            # hide-able/expandable list section within the library browser. If below it is
            # defined as True, the button will be '+' when hidden and '-' when expanded. Setting to
            # False will reverse this logic. Setting it to False, WILL NOT make the list
            # sections display in expanded mode by default. This is controlled further down with setVisible.
            group_button.is_hidden = True
            group_button.clicked.connect(self.toggle_sub_buttons)
            group_of_buttons.append((group_button, cleaned_class_group.capitalize()))

            self.libraryBrowserBox.layout.addWidget(group_button)

            list_of_sub_buttons = []

            # Go through each class block in the 2nd element of the group of blocks, and create buttons to spawn each
            # of those blocks into bdedit
            for class_block in sub_class_group[1]:

                # Make a button with the name of the block type
                button = QPushButton(class_block[0])
                # Set the button to be invisible by default (for the list's to be hidden)
                button.setVisible(False)
                # Connect button to calling a new instance of the block type class
                button.clicked.connect(lambda checked, blockClass=class_block[1]: blockClass())
                # Add button to list of scrollbar buttons for reference of what buttons should be
                # affected when expanding/hiding the list sections
                list_of_sub_buttons.append((button, class_block[1]))
                # self.list_of_scrollbar_buttons.append((button, class_block[1]))
                # Add the button to the library browser box layout (the scrollable widget)
                self.libraryBrowserBox.layout.addWidget(button)

            group_of_buttons.append(list_of_sub_buttons)
            self.list_of_scrollbar_buttons.append(group_of_buttons)

        # All the button items are set to align to the top of the libraryBrowserBox
        self.libraryBrowserBox.layout.addStretch()
        self.libraryBrowserBox.layout.setAlignment(Qt.AlignTop)
        self.libraryBrowserBox.setLayout(self.libraryBrowserBox.layout)

        # A scroll area is defined and applied to the libraryBrowserBox. Its dimensions
        # are set to allow for resizing, however the minimum height of the scroll area
        # is set to 300 pixels.
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.libraryBrowserBox)
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumHeight(300)

        # The width of the libraryBrowser widget is set to 250 pixels, and it the scroll
        # area is added to the libraryBrowser widget and set to align to the top of this widget.
        self.libraryBrowser.setFixedWidth(250 * self.layout.scale)
        self.libraryBrowser.layout.addWidget(self.scroll)
        self.libraryBrowser.layout.setAlignment(Qt.AlignTop)
        self.libraryBrowser.setLayout(self.libraryBrowser.layout)


        # _________ Application components added to application layout manager ___________
        # Refer to technical documentation for visualising how these components are
        # organised within the grid layout.
        # Each component is added to the grid layout,
        # * at an initial cell position within that grid, denoted by the first two ints
        # ** (which represent the y, then x coordinate of the cell),
        # * then is stretched by a number of cells, denoted by the last two ints
        # ** (which represent how many cells to stretch vertically, then how many cells to stretch horizontally)

        # For example, the toolbar is added to cell in the 0th row, and 1st column,
        # then stretched vertically by 1 row (to row 2),
        # and stretched horizontally by 9 columns (to column 10)
        # self.layout.addWidget(self.toolBar, 0, 1, 1, 9)
        # self.layout.addWidget(self.libraryBrowser, 0, 0, 10, 1)
        # self.layout.addWidget(self.canvasView, 1, 1, 9, 9)

        self.layout.addWidget(self.libraryBrowser, 0, 0, 10, 1)
        self.layout.addWidget(self.canvasView, 0, 1, 10, 9)

    # -----------------------------------------------------------------------------
    @pyqtSlot()
    def on_click(self, scene):
        """
        This method creates a ``Wire`` instance from the ``Socket`` that was clicked
        on, to the mouse pointer.

        :param scene: the scene within which the ``Block`` and ``Socket`` are located
        :type scene: Scene, required
        """

        # The start block (which has the start socket) and the end block (which has
        # the end socket) are grabbed.
        startBlock, endBlock, startSocket, endSocket = self.get_Input()
        # And a wire is made between those two points. When the wire is being dragged
        # from a Socket to another socket, the endSocket (and endBlock) are considered
        # as the location of the mouse pointer.
        Wire(scene, scene.blocks[startBlock].outputs[startSocket], scene.blocks[endBlock].inputs[endSocket], wire_type=3)

    # Todo - add doc comment for this
    # -----------------------------------------------------------------------------
    def sortBlockLibrary(self):
        for sub_list in self.blockLibrary:
            # Sort the blocks within each sublist (functions, sources, sinks, etc) in alphabetical order
            sub_list[1].sort(key=lambda x: x[0])

        # Then sort the groups in alphabetical order too
        self.blockLibrary.sort(key=lambda x: x[0])

    # -----------------------------------------------------------------------------
    def updateColorMode(self):
        """
        This method is called to update the color mode with which the ``Scene``
        background should be displayed. The options are:

        - Light: light gray grid lines, with dark outlines for blocks
        - Dark: dark gray grid lines, with light outlines for blocks
        - Off: no grid lines, with dark outlines for blocks
        """

        # The mode of the Scene is called to be updated to whatever value was
        # selected from the grid_mode dropdown menu (Light, Dark, Off)
        self.scene.grScene.updateMode(self.grid_mode_options.currentText())
        # For each block within the Scene, the mode of their outline is also updated
        for eachBlock in self.scene.blocks:
            # If the block has a mode (Connector Blocks do not)
            if not (eachBlock.block_type == "CONNECTOR" or eachBlock.block_type == "Connector"):
                eachBlock.grBlock.updateMode(self.grid_mode_options.currentText())

    # -----------------------------------------------------------------------------
    def clickBox(self, state):
        """
        This method is called when the toolbar checkbox for toggling the visiblity
        of the connector blocks is triggered. It toggles between the connector
        blocks being displayed and hidden.
        :param state: the state of the checkbox (clicked, unclicked)
        :type state: int
        """

        if state == QtCore.Qt.Checked:
            # Set variable for hiding connector blocks to True
            self.scene.hide_connector_blocks = True
        else:
            # Set variable for hiding connector blocks to False
            self.scene.hide_connector_blocks = False

    # Todo - add main block into here
    # -----------------------------------------------------------------------------
    def toggleCanvasItems(self):
        """
        This method toggles hiding/expanding all Canvas related Items.
        Currently these include only the ``Connector Block``.
        """

        # If the list section button is set to be hidden, the associated sign
        # will be displayed as '-', otherwise it will be displayed as '+' if expanded
        if self.canvas_items_hidden:
            self.canvasItems_button.setText(' -  Canvas Items')
        else:
            self.canvasItems_button.setText(' + Canvas Items')

        # When toggling, the variable that represents the current hidden/expanded
        # state of the list section, is flipped to the opposite boolean value of itself
        # If True -> False, If False -> True
        self.canvas_items_hidden = not self.canvas_items_hidden
        # And the associated buttons are set to being visible/invisible depending
        # on that variable.
        self.connector_block_button.setVisible(not self.connector_block_button.isVisible())
        self.main_block_button.setVisible(not self.main_block_button.isVisible())
        self.text_item_button.setVisible(not self.text_item_button.isVisible())

    # Todo - update doc string comments
    # -----------------------------------------------------------------------------
    def toggle_sub_buttons(self):
        # Go through list of buttons in the scroll bar
        for group in self.list_of_scrollbar_buttons:
            # Find the button group button that was pressed (functions, sink, source, etc)
            # group looks like - [[QPushButton_for_functions, "functions"], [all relevant buttons]]
            group_button = group[0][0]
            if group_button == self.sender():
                # If the list section button is set to be hidden, the associated sign
                # will be displayed as '-', otherwise it will be displayed as '+' if expanded
                if group_button.is_hidden:
                    group_button.setText(group_button.text().replace("+", "- "))
                else:
                    group_button.setText(group_button.text().replace("- ", "+"))

                # When toggling, the variable that represents the current hidden/expanded
                # state of the list section, is flipped to the opposite boolean value of itself
                # If True -> False, If False -> True
                group_button.is_hidden = not group_button.is_hidden

                # Go through all relevant buttons and hide/show them
                # group[1] looks like - [[QPushButton_for_block1, "block1"],[QPushButton_for_block2, "block2"], ...]
                for button_tuple in group[1]:
                    button_tuple[0].setVisible(not button_tuple[0].isVisible())

        # Code for debugging
        # for group in self.list_of_scrollbar_buttons:
        #     print("group:", group[0][1], "\t", group[0][0])
        #     for item in group[1]:
        #         print("\titem:", item[1], "\t", item[0])
        #     print("___________________________")
    
    # Todo, update documentation of this function
    # -----------------------------------------------------------------------------
    def grab_screenshot_dimensions(self):
        # Define initial dimensions of screenshot (if no blocks in scene)
        top, btm, left, right = 0,0,0,0
        spacer = 50 # half a typical block's width

        # Go through each block in scene, to find the top/bottom/left/right-most blocks
        for block in self.scene.blocks:
            b_left = block.grBlock.pos().x()
            b_top = block.grBlock.pos().y()
            b_right = b_left + block.width
            b_btm = b_top + block.height

            if b_left < left: left = b_left
            if b_top < top: top = b_top
            if b_right > right: right = b_right
            if b_btm > btm: btm = b_btm

        if DEBUG: print("Left most:", left, " | Top most:", top, " | Right most:", right, " | Bottom most:", btm)

        # Return the rect (x,y, width, height) that all these blocks occupy
        width = (right + spacer) - (left - spacer)
        height = (btm + spacer) - (top - spacer)
        return [left - spacer, top - spacer, width, height]

    # -----------------------------------------------------------------------------
    def save_image(self, picture_name):
        """
        This method takes a filename and saves a snapshot of all the items within
        the ``Scene`` into it. Currently the resolution of this image is set to
        4K resolution (3840 x 2160).

        :param picture_name: the name under which the image will be saved
        :type picture_name: str, required
        """

        print("Rendering image")

        # Creates an image, of defined resolution quality
        ratio = 3
        output_image = QImage(self.scene.scene_width * ratio, self.scene.scene_height * ratio, QImage.Format_RGBA64)

        # Then a painter is initialized to that image
        painter = QPainter(output_image)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # The canvas is rendered by the above-defined painter (into the image)
        self.scene.grScene.render(painter)
        painter.end()

        # Grab the dimensions of the space all blocks within the sceen occupy
        [x, y, width, height] = self.grab_screenshot_dimensions()
        # Scale the dimensions from above, to the image
        rect = QRect(output_image.width()/2 + (x * ratio), output_image.height()/2 + (y * ratio), width * ratio, height * ratio)

        # Crop the image to area of interest
        output_image = output_image.copy(rect)

        # And the image is saved under the given file name, as a png
        output_image.save(picture_name + ".png")
        print("Screenshot saved --> ", picture_name + ".png")

    # -----------------------------------------------------------------------------
    def updateSceneDimensions(self):
        """
        This method updates the dimensions of the scene based on current window
        size (will change as the application window is resized).
        """
        # The largest size the scene can be is:
        # the difference between the max zoom out level (zoomRange[max_zoom_out, max_zoom_in]) and default zoom
        # multiplied by the zoom out factor
        multiplier = abs(self.canvasView.zoomRange[0] - self.canvasView._default_zoom_level) * 0.8

        # Only update if canvas dimensions have changed from what they were previously set to
        if self.width() * multiplier != self.scene.getSceneWidth() * multiplier or \
           self.height() * multiplier != self.scene.getSceneHeight() * multiplier:
            self.scene.setSceneWidth((self.width()) * multiplier)
            self.scene.setSceneHeight((self.height()) * multiplier)
            self.scene.updateSceneDimensions()

    # -----------------------------------------------------------------------------
    # Update the canvas's dimension if its size has changed (if window has been resized)
    def resizeEvent(self, event):
        """
        This is an inbuilt method of QWidget, that is overwritten by ``Interface``
        to update the dimensions of the ``Scene`` when the application window has
        been resized.

        :param event: an interaction event that has occurred with this QWidget
        :type event: QResizeEvent, automatically recognized by the inbuilt function
        """
        self.updateSceneDimensions()
