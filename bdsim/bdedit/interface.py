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
from bdsim.bdedit.block_connector_block import *
from bdsim.bdedit.interface_scene import Scene
from bdsim.bdedit.interface_graphics_view import GraphicsView
from bdsim.bdedit.block_importer import *

# =============================================================================
#
#   Defining and setting global variables and methods
#
# =============================================================================
# Variable for enabling/disabling debug comments
DEBUG = False

# def importBlocks():
#     """
#     This method is called at the beginning of an ``Interface`` instance, to auto
#     import all grandchild Classes of the ``Block`` class from a locally referenced
#     dictionary called `Block_Classes`.
#
#     This code is adapted from: https://github.com/petercorke/bdsim/blob/bdedit/bdsim/bdsim.py
#
#     :return: a list of imported blocks
#     :rtype: list
#     """
#
#     # The filepath is locally defined, by navigating from this file, up to the parent directory
#     # and then to the 'Block_Classes' directory.
#     block_path = [Path(__file__).parent / 'Block_Classes']
#
#     # A blocks list is initialized to being empty, and the number of currently imported blocks is stored
#     blocks = []
#     nblocks = len(blocklist)
#
#     # For each file located within the referenced directory
#     for path in block_path:
#         # If the given filepath exists, proceed with the code, otherwise skip that file and continue
#         # to the next
#         if not path.exists():
#             print("Provided path does not exist")
#             continue
#
#         # For each file in the referenced directory
#         for file in path.iterdir():
#             # Look only at python files
#             if file.name.endswith('.py'):
#                 # Create a temporary list that will store all the grandchild class blocks within this file
#                 sub_class_blocks = []
#
#                 # Extract and import the given modules (Grandchild Classes)
#                 # As these classes are imported, they each have an '@block' decorator which
#                 # automatically adds that class into the 'blocklist' variable
#                 spec = importlib.util.spec_from_file_location(file.name, file)
#                 module = importlib.util.module_from_spec(spec)
#                 spec.loader.exec_module(module)
#
#                 # For each class that was just added into the 'blocklist' variable
#                 # (nblocks: -> From the previous number of blocks in blocklist, to the end of the current length
#                 # of blocklist)
#                 for cls in blocklist[nblocks:]:
#                     # Append the name of the class, the class import itself, and the filepath to that module
#                     sub_class_blocks.append([blockname(cls), cls, file])
#
#                 # Finally append the imported classes into the 'blocks' list, and update the number of blocks
#                 # variable to the current length of blocklist
#                 blocks.append(sub_class_blocks)
#                 nblocks = len(blocklist)
#
#     return blocks


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

        # A copy of the imported block classes is stored within the Scene for later use
        # when calling those classes to create Blocks into the Scene
        #self.blockLibrary = importBlocks()
        #self.blockLibrary = import_blocks()

        # The toolbar and library browser widgets are initialized
        self.toolBar = QWidget()
        self.libraryBrowser = QWidget()

        # LibraryBrowserBox is wrapped by LibraryBrowser, as this allows the items within
        # the libraryBrowser to be scrollable
        self.libraryBrowserBox = QGroupBox()

        # # The name of the current interface Scene is initially set to None, this is then
        # # overwritten when the Scene is saved
        # self.filename = "untitled.bd"

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
        # self.setGeometry(resolution.width() / 4, resolution.height() / 4, resolution.width() / 2, resolution.height() / 2)  # Interface will be half the size of the desktop screen, and centered in the screen
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

        self.blockLibrary = import_blocks(self.scene, self.layout)

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
        self.toolBar.setFixedHeight(50)

        # Buttons are created (and named) that will populate the toolbar
        self.newFile_button = QPushButton('New File')
        self.openFile_button = QPushButton('Open File')
        self.save_button = QPushButton('Save')
        self.saveAs_button = QPushButton('Save As')
        self.simulate_button = QPushButton('Simulate')
        self.run_button = QPushButton('Run')
        self.screenshot_button = QPushButton('Screenshot')
        self.grid_mode = QWidget()
        self.toggle_connector_block_visibility_checkbox = QCheckBox("Hide Connector Blocks", self)

        # Each widget must have a layout manager which controls how items are
        # positioned within it. The grid_mode widget will consist of a label
        # and a drop down menu, hence it's layout will be horizontal.
        self.grid_mode.layout = QHBoxLayout()
        self.grid_mode_label = QLabel('Grid Mode')
        # Drop down menu is created for choosing grid mode (Light, Dark, Off)
        self.grid_mode_options = QComboBox()
        self.grid_mode_options.addItem("Light")
        self.grid_mode_options.addItem("Dark")
        self.grid_mode_options.addItem("Off")

        # Both the label and the drop down menu are added to the grid_mode widget's
        # layout manager, and its layout is set to this manager.
        self.grid_mode.layout.addWidget(self.grid_mode_label)
        self.grid_mode.layout.addWidget(self.grid_mode_options)
        self.grid_mode.setLayout(self.grid_mode.layout)

        # As mentioned above, each widget must have a layout manager. Since the
        # toolbar will be displayed along the top of the interface, items should
        # be displayed horizontally, hence the horizontal layout manager.
        self.toolBar.layout = QHBoxLayout()
        # The borders of the layout are removed.
        self.toolBar.layout.setContentsMargins(0, 0, 0, 0)

        # The above-created buttons are populated into the toolbar
        self.toolBar.layout.addWidget(self.newFile_button)
        self.toolBar.layout.addWidget(self.openFile_button)
        self.toolBar.layout.addWidget(self.save_button)
        self.toolBar.layout.addWidget(self.saveAs_button)
        self.toolBar.layout.addWidget(self.run_button)
        self.toolBar.layout.addWidget(self.screenshot_button)
        self.toolBar.layout.addWidget(self.grid_mode)
        self.toolBar.layout.addWidget(self.toggle_connector_block_visibility_checkbox)

        # The above-created buttons are connected to desired actions
        self.newFile_button.clicked.connect(lambda: main_window.newFile())  # self.scene.clear() removes all items from the scene
        self.save_button.clicked.connect(lambda: main_window.saveToFile())  # self.saveToFile() initiates a prompt to save the current scene
        self.openFile_button.clicked.connect(lambda: main_window.loadFromFile())  # self.loadFromFile() initiates a prompt to choose a scene file to load
        self.saveAs_button.clicked.connect(lambda: main_window.saveAsToFile())
        # self.newFile_button.clicked.connect(lambda: self.scene.clear())     # self.scene.clear() removes all items from the scene
        # self.save_button.clicked.connect(lambda: self.saveToFile())         # self.saveToFile() initiates a prompt to save the current scene
        # self.openFile_button.clicked.connect(lambda: self.loadFromFile())   # self.loadFromFile() initiates a prompt to choose a scene file to load
        # self.saveAs_button.clicked.connect(lambda: self.saveAsToFile())     # self.saveAsToFile() initiates a prompt to save the current scene under a different name
        self.screenshot_button.clicked.connect(lambda: self.save_image('Scene Picture'))    # self.save_image creates an image of the current scene, saved as 'Scene Picture'
        # self.screenshot_button.clicked.connect(lambda: self.grab_screenshot_dimensions())
        self.grid_mode_options.currentIndexChanged.connect(lambda: self.updateColorMode())  # self.updateColorMode() updates the background mode of the scene
        self.toggle_connector_block_visibility_checkbox.stateChanged.connect(self.clickBox)

        # Finally, the toolbar items are set to be aligned within the horizontal center of the toolbar
        self.toolBar.layout.setAlignment(Qt.AlignHCenter)
        self.toolBar.setLayout(self.toolBar.layout)

        # ___________________________ Library Browser Setup ___________________________
        # The library browser will be displayed along the left-hand side of the interface,
        # items should be displayed vertically within it, hence the vertical layout manager.
        self.libraryBrowser.layout = QVBoxLayout(self.libraryBrowser)
        # The follow label is added to the library browser, naming it
        self.libraryBrowser.layout.addWidget(QLabel('<font size=8><b>Library Browser</font>'))
        # The library browser box makes the items inside of it scrollable, so all the relevant
        # buttons will be added into this widget. This widget will also have a vertical layout
        # manager. Then this widget will be wrapped by the library browser (will go inside it),
        # in order to position where it is displayed in the application window.
        self.libraryBrowserBox.layout = QVBoxLayout()

        # The following variables control the '+,-' sign displayed alongside each
        # hide-able/expandable list section within the library browser. If below they are
        # defined as True, they will be '+' when hidden and '-' when expanded. Setting to
        # False will reverse this logic. Setting these to False, WILL NOT make the list
        # sections display in expanded mode by default. This is controlled further down.
        self.canvas_items_hidden = True
        self.source_blocks_hidden = True
        self.sink_blocks_hidden = True
        self.function_blocks_hidden = True
        self.transfer_blocks_hidden = True
        self.discrete_blocks_hidden = True
        self.subsystem_blocks_hidden = True

        # Buttons for hiding/expanding the list sections in the library browser,
        # are created and named
        self.canvasItems_button = QPushButton(' + Canvas Items')
        self.sourceBlocks_button = QPushButton(' + Source Blocks')
        self.sinkBlocks_button = QPushButton(' + Sink Blocks')
        self.functionBlocks_button = QPushButton(' + Function Blocks')
        self.transferBlocks_button = QPushButton(' + Transfer Blocks')
        self.discreteBlocks_button = QPushButton(' + Discrete Blocks')
        self.subsystemBlocks_button = QPushButton(' + Subsystem Blocks')

        # The alignment of the above-button's text are set to be left-aligned
        self.canvasItems_button.setStyleSheet("QPushButton { text-align: left }")
        self.sourceBlocks_button.setStyleSheet("QPushButton { text-align: left }")
        self.sinkBlocks_button.setStyleSheet("QPushButton { text-align: left }")
        self.functionBlocks_button.setStyleSheet("QPushButton { text-align: left }")
        self.transferBlocks_button.setStyleSheet("QPushButton { text-align: left }")
        self.discreteBlocks_button.setStyleSheet("QPushButton { text-align: left }")
        self.subsystemBlocks_button.setStyleSheet("QPushButton { text-align: left }")

        # The above-created buttons are connected to methods that handle hiding/expanding
        # the buttons that appear within the respective list sections
        self.canvasItems_button.clicked.connect(self.toggleCanvasItems)
        # self.sourceBlocks_button.clicked.connect(self.toggleSourceBlocks)
        # self.sinkBlocks_button.clicked.connect(self.toggleSinkBlocks)
        # self.functionBlocks_button.clicked.connect(self.toggleFunctionBlocks)
        # self.transferBlocks_button.clicked.connect(self.toggleTransferBlocks)
        # self.discreteBlocks_button.clicked.connect(self.toggleDiscreteBlocks)
        # self.subsystemBlocks_button.clicked.connect(self.toggleSubSystemBlocks)

        # A list is created to hold all the buttons that will create Blocks within the Scene
        self.list_of_scrollbar_buttons = []

        # The connector block is defined internally within the code, and will always be
        # included as a usable block, so it is imported manually. The button that creates
        # the connector block within the scene is created below. This button is set to
        # initially be invisible (this is what controls whether the lists sections are
        # expanded or hidden by default. Setting setVisible(False) will make the lists hidden,
        # and setVisible(True) will make the lists expanded).
        self.libraryBrowserBox.layout.addWidget(self.canvasItems_button)
        self.connector_block_button = QPushButton("Connector Block")
        self.connector_block_button.setVisible(False)
        # This button is then connected to creating an instance of the Connector class within
        # the Scene
        self.connector_block_button.clicked.connect(lambda checked: Connector(self.scene, self.layout, "Connector Block"))
        # And the button is added to the library browser's layout manager
        self.libraryBrowserBox.layout.addWidget(self.connector_block_button)

        # This for loop goes through each block type (sink, source, function) that was
        # imported (and stored into self.blockLibrary at the Interface's initialization).
        for sub_class_group in self.blockLibrary:

            group_of_buttons = []

            # Grab the each group that blocks belong to, and create a library panel button for those groups
            cleaned_class_group = sub_class_group[0][:-1] if sub_class_group[0].endswith('s') else sub_class_group[0]
            #button_name = cleaned_class_group + "_button"
            # self.button_name = QPushButton(" + " + cleaned_class_group.capitalize() + " Blocks")
            # self.button_name.setStyleSheet("QPushButton { text-align: left }")
            # self.libraryBrowserBox.layout.addWidget(self.button_name)

            group_button = QPushButton(" + " + cleaned_class_group.capitalize() + " Blocks")
            group_button.setStyleSheet("QPushButton { text-align: left }")
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
                #button.setVisible(False)
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

            # # Variables set for identifying whether or not all the grandchild class blocks
            # # were added into the library browser layout, into their respective list section.
            # sourceBlocksAdded = False
            # sinkBlocksAdded = False
            # functionBlocksAdded = False
            # transferBlocksAdded = False
            # discreteBlocksAdded = False
            # subsystemBlocksAdded = False
            #
            #
            # # The above defined buttons for hiding/expanding the list sections, are added at
            # # the start of each import of blocks from the same group. E.g. if sub_class_group
            # # is of SourceBlock blocks, the hiding/expanding button for this list section will
            # # be added first, followed by the buttons for each of the SourceBlock blocks. The
            # # above variables are also set to True, signifying that all necessary buttons for
            # # this sub_class_group of buttons have been added.
            #
            # # All blocks in each group of blocks are in the same class, so if the first is a
            # # sink/source/function the rest will also belong to the same class
            # if not sourceBlocksAdded:
            #     if issubclass(sub_class_group[0][1], SourceBlock):
            #         self.libraryBrowserBox.layout.addWidget(self.sourceBlocks_button)
            #         sourceBlocksAdded = True
            #
            # if not sinkBlocksAdded:
            #     if issubclass(sub_class_group[0][1], SinkBlock):
            #         self.libraryBrowserBox.layout.addWidget(self.sinkBlocks_button)
            #         sinkBlocksAdded = True
            #
            # if not functionBlocksAdded:
            #     if issubclass(sub_class_group[0][1], FunctionBlock):
            #         self.libraryBrowserBox.layout.addWidget(self.functionBlocks_button)
            #         functionBlocksAdded = True
            #
            # if not transferBlocksAdded:
            #     if issubclass(sub_class_group[0][1], TransferBlock):
            #         self.libraryBrowserBox.layout.addWidget(self.transferBlocks_button)
            #         transferBlocksAdded = True
            #
            # if not discreteBlocksAdded:
            #     if issubclass(sub_class_group[0][1], DiscreteBlock):
            #         self.libraryBrowserBox.layout.addWidget(self.discreteBlocks_button)
            #         discreteBlocksAdded = True
            #
            # if not subsystemBlocksAdded:
            #     if issubclass(sub_class_group[0][1], (INPORTBlock, OUTPORTBlock, SUBSYSTEMBlock)):
            #         self.libraryBrowserBox.layout.addWidget(self.subsystemBlocks_button)
            #         subsystemBlocksAdded = True
            #
            # # After the hiding/expanding button has been added according to the sub_class_group,
            # # a button for each block within that group is added to the library browser layout.
            # for sub_class_block in sub_class_group:
            #     # Make a button with the name of the block type
            #     button = QPushButton(sub_class_block[0])
            #     # Set the button to be invisible by default (for the list's to be hidden)
            #     button.setVisible(False)
            #     # Connect button to calling a new instance of the block type class
            #     button.clicked.connect(lambda checked, blockClass=sub_class_block[1], scene=self.scene, layout=self.layout: blockClass(scene, layout))
            #     # Add button to list of scrollbar buttons for reference of what buttons should be
            #     # affected when expanding/hiding the list sections
            #     self.list_of_scrollbar_buttons.append((button, sub_class_block[1]))
            #     # Add the button to the library browser box layout (the scrollable widget)
            #     self.libraryBrowserBox.layout.addWidget(button)

        # for block_buttons in self.list_of_scrollbar_buttons:
        #     print(id(block_buttons[0]), block_buttons)

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

        # ________ Application components added to application layout manager _________
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
        self.layout.addWidget(self.toolBar, 0, 1, 1, 9)
        self.layout.addWidget(self.libraryBrowser, 0, 0, 10, 1)
        self.layout.addWidget(self.canvasView, 1, 1, 9, 9)

        # Sets the stylesheet for how tool tips should be displayed
        # self.setStyleSheet("""QToolTip {
        #                     background-color: #33393B;
        #                     color: white;
        #                     border: 1px solid black;
        #                     }""")
        # self.setStyleSheet("""QToolTip {
        #                     background-color: #E0E0E0;
        #                     color: black;
        #                     border: 1px solid black;
        #                     }""")

        # Finally the application window is named, its icon is set, and it is shown.
        # self.setWindowTitle("bdedit - " + self.filename)
        # self.setWindowIcon(QIcon(":/Icons_Reference/Icons/bdsim_icon.png"))
        # self.show()

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

    # Todo update documentation for this func
    # -----------------------------------------------------------------------------
    # def updateApplicationName(self, filepath):
    #     self.filename = os.path.basename(filepath)
    #     self.setWindowTitle("bdedit - " + self.filename)

    # # -----------------------------------------------------------------------------
    # def loadFromFilePath(self, filepath):
    #     """
    #     This method is only used when loading a file from the command line. It will
    #     check if the file at the given path exists, and if so, will load its contents.
    #     """
    #
    #     # Check if file at given path exists, if so, run the deserializing method
    #     if os.path.isfile(filepath):
    #         self.scene.loadFromFile(filepath)
    #
    # # -----------------------------------------------------------------------------
    # def loadFromFile(self):
    #     """
    #     This method opens a QFileDialog window, prompting the user to select a file
    #     to load from.
    #     """
    #
    #     # The filename of the selected file is grabbed
    #     fname, filter = QFileDialog.getOpenFileName(self)
    #     if fname == '':
    #         return
    #
    #     # And the method for deserializing from a file is called, feeding in the
    #     # extracted filename from above
    #     if os.path.isfile(fname):
    #         self.updateApplicationName(fname)
    #         self.scene.loadFromFile(fname)
    #
    # # -----------------------------------------------------------------------------
    # def saveToFile(self):
    #     """
    #     This method calls the method from within the ``Scene`` to save a copy of the
    #     current Scene, with all its items under a file with the current filename. If
    #     this is the first time a user is saving their file, they will be prompted to
    #     name the file and to choose where it will be saved.
    #     """
    #
    #     if "untitled" in self.filename: return self.saveAsToFile()
    #     self.scene.saveToFile(self.filename)
    #
    # # -----------------------------------------------------------------------------
    # def saveAsToFile(self):
    #     """
    #     This method opens a QFileDialog window, prompting the user to enter a name
    #     under which the current file will be saved. This file will automatically be
    #     given a .json file type.
    #     """
    #
    #     # The allowable file types are defined below
    #     # file_types = "JSON files (*.json);;all files(*.*)"
    #     file_types = "JSON files (*.json);;bdedit files(*.bd)"
    #     fname, _ = QFileDialog.getSaveFileName(self, 'untitled.bd', filter=file_types)
    #
    #     # The filename is extracted from the QFileDialog
    #     if fname == '':
    #         return
    #
    #     # The filename of the scene is stored as a variable inside the Interface, and
    #     # the self.saveToFile method is called (which will call the self.scene.saveToFile
    #     # method from within the Scene, which will serialize the contents of the Scene
    #     # into a JSON file with the provided file name).
    #     self.filename = fname
    #     self.saveToFile()

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

    # Todo - update doc string comments
    # -----------------------------------------------------------------------------
    def toggle_sub_buttons(self):
        pass
        # browser_button_map = {
        #     ""
        #
        # }

    # # -----------------------------------------------------------------------------
    # def toggleSourceBlocks(self):
    #     """
    #     This method toggles hiding/expanding all ``Source Blocks``.
    #     These depend on the Blocks defined within the auto-imported files.
    #     """
    #
    #     # If the list section button is set to be hidden, the associated sign
    #     # will be displayed as '-', otherwise it will be displayed as '+' if expanded
    #     if self.source_blocks_hidden:
    #         self.sourceBlocks_button.setText(' -  Source Blocks')
    #     else:
    #         self.sourceBlocks_button.setText(' + Source Blocks')
    #
    #     # When toggling, the variable that represents the current hidden/expanded
    #     # state of the list section, is flipped to the opposite boolean value of itself
    #     # If True -> False, If False -> True
    #     self.source_blocks_hidden = not self.source_blocks_hidden
    #
    #     # For each list section, its buttons will be contained within the list_of_scrollbar_buttons
    #     # variable, so that list is parsed and all buttons which are a subclass of SourceBlock
    #     # are set to being visible/invisible depending on the variable above.
    #     for button_tuple in self.list_of_scrollbar_buttons:
    #         if issubclass(button_tuple[1], SourceBlock):
    #             button_tuple[0].setVisible(not button_tuple[0].isVisible())
    #
    # # -----------------------------------------------------------------------------
    # def toggleSinkBlocks(self):
    #     """
    #     This method toggles hiding/expanding all ``Sink Blocks``.
    #     These depend on the Blocks defined within the auto-imported files.
    #     """
    #
    #     # If the list section button is set to be hidden, the associated sign
    #     # will be displayed as '-', otherwise it will be displayed as '+' if expanded
    #     if self.sink_blocks_hidden:
    #         self.sinkBlocks_button.setText(' -  Sink Blocks')
    #     else:
    #         self.sinkBlocks_button.setText(' + Sink Blocks')
    #
    #     # When toggling, the variable that represents the current hidden/expanded
    #     # state of the list section, is flipped to the opposite boolean value of itself
    #     # If True -> False, If False -> True
    #     self.sink_blocks_hidden = not self.sink_blocks_hidden
    #
    #     # For each list section, its buttons will be contained within the list_of_scrollbar_buttons
    #     # variable, so that list is parsed and all buttons which are a subclass of SinkBlock
    #     # are set to being visible/invisible depending on the variable above.
    #     for button_tuple in self.list_of_scrollbar_buttons:
    #         if issubclass(button_tuple[1], SinkBlock):
    #             button_tuple[0].setVisible(not button_tuple[0].isVisible())
    #
    # # -----------------------------------------------------------------------------
    # def toggleFunctionBlocks(self):
    #     """
    #     This method toggles hiding/expanding all ``Function Blocks``.
    #     These depend on the Blocks defined within the auto-imported files.
    #     """
    #
    #     # If the list section button is set to be hidden, the associated sign
    #     # will be displayed as '-', otherwise it will be displayed as '+' if expanded
    #     if self.function_blocks_hidden:
    #         self.functionBlocks_button.setText(' -  Function Blocks')
    #     else:
    #         self.functionBlocks_button.setText(' + Function Blocks')
    #
    #     # When toggling, the variable that represents the current hidden/expanded
    #     # state of the list section, is flipped to the opposite boolean value of itself
    #     # If True -> False, If False -> True
    #     self.function_blocks_hidden = not self.function_blocks_hidden
    #
    #     # For each list section, its buttons will be contained within the list_of_scrollbar_buttons
    #     # variable, so that list is parsed and all buttons which are a subclass of FunctionBlock
    #     # are set to being visible/invisible depending on the variable above.
    #     for button_tuple in self.list_of_scrollbar_buttons:
    #         if issubclass(button_tuple[1], FunctionBlock):
    #             button_tuple[0].setVisible(not button_tuple[0].isVisible())
    #
    # # -----------------------------------------------------------------------------
    # def toggleTransferBlocks(self):
    #     """
    #     This method toggles hiding/expanding all ``Transfer Blocks``.
    #     These depend on the Blocks defined within the auto-imported files.
    #     """
    #
    #     # If the list section button is set to be hidden, the associated sign
    #     # will be displayed as '-', otherwise it will be displayed as '+' if expanded
    #     if self.transfer_blocks_hidden:
    #         self.transferBlocks_button.setText(' -  Transfer Blocks')
    #     else:
    #         self.transferBlocks_button.setText(' + Transfer Blocks')
    #
    #     # When toggling, the variable that represents the current hidden/expanded
    #     # state of the list section, is flipped to the opposite boolean value of itself
    #     # If True -> False, If False -> True
    #     self.transfer_blocks_hidden = not self.transfer_blocks_hidden
    #
    #     # For each list section, its buttons will be contained within the list_of_scrollbar_buttons
    #     # variable, so that list is parsed and all buttons which are a subclass of TransferBlock
    #     # are set to being visible/invisible depending on the variable above.
    #     for button_tuple in self.list_of_scrollbar_buttons:
    #         if issubclass(button_tuple[1], TransferBlock):
    #             button_tuple[0].setVisible(not button_tuple[0].isVisible())
    #
    # # -----------------------------------------------------------------------------
    # def toggleDiscreteBlocks(self):
    #     """
    #     This method toggles hiding/expanding all ``Discrete Blocks``.
    #     These depend on the Blocks defined within the auto-imported files.
    #     """
    #
    #     # If the list section button is set to be hidden, the associated sign
    #     # will be displayed as '-', otherwise it will be displayed as '+' if expanded
    #     if self.discrete_blocks_hidden:
    #         self.discreteBlocks_button.setText(' -  Discrete Blocks')
    #     else:
    #         self.discreteBlocks_button.setText(' + Discrete Blocks')
    #
    #     # When toggling, the variable that represents the current hidden/expanded
    #     # state of the list section, is flipped to the opposite boolean value of itself
    #     # If True -> False, If False -> True
    #     self.discrete_blocks_hidden = not self.discrete_blocks_hidden
    #
    #     # For each list section, its buttons will be contained within the list_of_scrollbar_buttons
    #     # variable, so that list is parsed and all buttons which are a subclass of DiscreteBlock
    #     # are set to being visible/invisible depending on the variable above.
    #     for button_tuple in self.list_of_scrollbar_buttons:
    #         if issubclass(button_tuple[1], DiscreteBlock):
    #             button_tuple[0].setVisible(not button_tuple[0].isVisible())
    #
    # # -----------------------------------------------------------------------------
    # def toggleSubSystemBlocks(self):
    #     """
    #     This method toggles hiding/expanding all ``SubSystem Blocks``.
    #     These depend on the Blocks defined within the auto-imported files.
    #     """
    #
    #     # If the list section button is set to be hidden, the associated sign
    #     # will be displayed as '-', otherwise it will be displayed as '+' if expanded
    #     if self.subsystem_blocks_hidden:
    #         self.subsystemBlocks_button.setText(' -  Subsystem Blocks')
    #     else:
    #         self.subsystemBlocks_button.setText(' + Subsystem Blocks')
    #
    #     # When toggling, the variable that represents the current hidden/expanded
    #     # state of the list section, is flipped to the opposite boolean value of itself
    #     # If True -> False, If False -> True
    #     self.subsystem_blocks_hidden = not self.subsystem_blocks_hidden
    #
    #     # For each list section, its buttons will be contained within the list_of_scrollbar_buttons
    #     # variable, so that list is parsed and all buttons which are a subclass of INPORTBlock,
    #     # OUTPUTBlock or SUBSYSTEMBlock are set to being visible/invisible depending on the variable above.
    #     for button_tuple in self.list_of_scrollbar_buttons:
    #         if issubclass(button_tuple[1], (INPORTBlock, OUTPORTBlock, SUBSYSTEMBlock)):
    #             button_tuple[0].setVisible(not button_tuple[0].isVisible())
    
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

        # path = QtCore.QDir("/tmp")
        #
        # printer = QtPrintSupport.QPrinter()
        # printer.setOutputFormat(QtPrintSupport.QPrinter.PdfFormat)
        # printer.setOutputFileName(path.absoluteFilePath(picture_name+".pdf"))
        # printer.setFullPage(True)

        #print("Rendering large image, this might take a minute")
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
        output_image.save(picture_name+".png")
        print("Screenshot successfully rendered and saved")

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
