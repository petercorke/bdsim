# Library imports
import os
import fnmatch

# PyQt5 imports
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

# BdEdit imports
from bdsim.bdedit.block import *
from bdsim.bdedit.Icons import *
from bdsim.bdedit.grouping_box import *
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

        # # Set file extension for screenshots. PDF (default) PNG if specified from command line args
        # self.screenshot_extension_format = 'pdf'

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
        # self.setGeometry(100, 100, resolution.width() - 200, resolution.height() - 200)  # Interface will be same size as desktop screen, minus 100 pixels from all sides
        # self.setGeometry(resolution.width() / 4, resolution.height() / 4, resolution.width() / 2, resolution.height() / 2)  # Interface will be half the size of the desktop screen, and centered in the screen
        # self.setGeometry(100, 100, resolution.width() / 2, resolution.height() / 2)  # Interface will be half the size of the desktop screen, and displayed 100 pixels down and right from top left corner of the screen
        main_window.setGeometry(
            100, 100, int(resolution.width() / 2), int(resolution.height() / 2)
        )  # Interface will be half the size of the desktop screen, and displayed 100 pixels down and right from top left corner of the screen

        # Layout manager is defined and set for the application layout. This will handle
        # the positioning of each application component.
        self.layout = QGridLayout()  # Contains all the widgets
        self.layout.setContentsMargins(0, 0, 0, 0)  # Removes the border
        self.setLayout(self.layout)

        # Different screen resolutions result in varying sizes of the library browser
        # and parameter window panels. To compensate for this, the preferred dimensions
        # of these panels as seen on the screen while being developed (2560 resolution
        # width) have been scaled to other screen sizes.
        self.layout.scale = int(2560 / resolution.width())

        # An instance of the Scene class is created, providing it the resolution of the
        # desktop screen and the application layout manager.
        self.scene = Scene(resolution, self.layout, main_window)

        # Since the Scene itself is only a class and doesn't have a 'visual' representation,
        # it will create a 'grScene' variable, that will be responsible for handling everything
        # graphical related. This 'grScene' is fed into an instance of a GraphicsView, which
        # handles visual updates to the 'grScene' (e.g. updating the Scene when Blocks are
        # deleted, or when wires are moved around)
        self.canvasView = GraphicsView(self.scene.grScene, main_window, self)

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

        # ___________________________ Library Browser Setup ___________________________
        # The library browser will be displayed along the left-hand side of the interface,
        # items should be displayed vertically within it, hence the vertical layout manager.
        self.libraryBrowser.layout = QVBoxLayout(self.libraryBrowser)

        # Adding icon for the tool above the library browser
        self.tool_logo = QLabel()
        self.tool_logo.setPixmap(
            QPixmap(":/Icons_Reference/Icons/bdsim_logo2.png").scaledToWidth(
                230 * self.layout.scale
            )
        )
        # self.tool_logo.setPixmap(QPixmap(":/Icons_Reference/Icons/bdsim_logo2.png").scaledToHeight(40 * self.layout.scale))
        self.libraryBrowser.layout.addWidget(self.tool_logo)
        self.libraryBrowser.layout.setAlignment(
            self.tool_logo, Qt.AlignmentFlag.AlignHCenter
        )

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
        self.canvasItems_button = QPushButton(" + Canvas Items")
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
        self.grouping_box_button = QPushButton("Grouping Box")

        self.connector_block_button.setVisible(False)
        self.main_block_button.setVisible(False)
        self.text_item_button.setVisible(False)
        self.grouping_box_button.setVisible(False)

        # These buttons are then connected to creating their respective instances within the Scene
        self.connector_block_button.clicked.connect(
            lambda checked: Connector(self.scene, self.layout, "Connector Block")
        )
        self.main_block_button.clicked.connect(
            lambda checked: Main(self.scene, self.layout)
        )
        self.text_item_button.clicked.connect(
            lambda checked: Floating_Label(self.scene, self.layout, main_window)
        )
        self.grouping_box_button.clicked.connect(
            lambda checked: Grouping_Box(self.scene, self.layout)
        )

        # Set up secondary connection to these buttons, to update scene history when they are added to the scene
        self.connector_block_button.clicked.connect(
            lambda checked, desc="Added connector block to scene": self.scene.history.storeHistory(
                desc
            )
        )
        self.main_block_button.clicked.connect(
            lambda checked, desc="Added main block to scene": self.scene.history.storeHistory(
                desc
            )
        )
        self.text_item_button.clicked.connect(
            lambda checked, desc="Added text label to scene": self.scene.history.storeHistory(
                desc
            )
        )
        self.grouping_box_button.clicked.connect(
            lambda checked, desc="Added grouping box to scene": self.scene.history.storeHistory(
                desc
            )
        )

        # Adding the buttons to the library browser's layout manager
        self.libraryBrowserBox.layout.addWidget(self.text_item_button)
        self.libraryBrowserBox.layout.addWidget(self.main_block_button)
        self.libraryBrowserBox.layout.addWidget(self.grouping_box_button)
        self.libraryBrowserBox.layout.addWidget(self.connector_block_button)

        # This for loop goes through each block type (sink, source, function) that was auto
        # imported (and stored into self.blockLibrary at the Interface's initialization).
        for sub_class_group in self.blockLibrary:

            group_of_buttons = []

            # Grab each group that blocks belong to, and create a library panel button for those groups
            cleaned_class_group = (
                sub_class_group[0][:-1]
                if sub_class_group[0].endswith("s")
                else sub_class_group[0]
            )
            group_button = QPushButton(
                " + " + cleaned_class_group.capitalize() + " Blocks"
            )

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
                button.clicked.connect(
                    lambda checked, blockClass=class_block[1]: blockClass()
                )
                button.clicked.connect(
                    lambda checked, desc="Added imported block to scene": self.scene.history.storeHistory(
                        desc
                    )
                )
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

        # For example, the canvas view is added to cell in the 0th row, and 1st column,
        # then stretched vertically by 10 row (to row 11),
        # and stretched horizontally by 9 columns (to column 10)
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
        Wire(
            scene,
            scene.blocks[startBlock].outputs[startSocket],
            scene.blocks[endBlock].inputs[endSocket],
            wire_type=3,
        )

    # Todo - add doc comment for this
    # -----------------------------------------------------------------------------
    def sortBlockLibrary(self):
        for sub_list in self.blockLibrary:
            # Sort the blocks within each sublist (functions, sources, sinks, etc) in alphabetical order
            sub_list[1].sort(key=lambda x: x[0])

        # Then sort the groups in alphabetical order too
        self.blockLibrary.sort(key=lambda x: x[0])

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
            self.canvasItems_button.setText(" -  Canvas Items")
        else:
            self.canvasItems_button.setText(" + Canvas Items")

        # When toggling, the variable that represents the current hidden/expanded
        # state of the list section, is flipped to the opposite boolean value of itself
        # If True -> False, If False -> True
        self.canvas_items_hidden = not self.canvas_items_hidden
        # And the associated buttons are set to being visible/invisible depending
        # on that variable.
        self.connector_block_button.setVisible(
            not self.connector_block_button.isVisible()
        )
        self.main_block_button.setVisible(not self.main_block_button.isVisible())
        self.text_item_button.setVisible(not self.text_item_button.isVisible())
        self.grouping_box_button.setVisible(not self.grouping_box_button.isVisible())

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
        def find_boundaries(L, T, R, B, left, top, right, btm):
            if L < left:
                left = L
            if T < top:
                top = T
            if R > right:
                right = R
            if B > btm:
                btm = B
            return [left, top, right, btm]

        # Define initial dimensions of screenshot (if no blocks in scene)
        top, btm, left, right = 0, 0, 0, 0
        spacer = 50  # half a typical block's width

        # Go through each block in scene, to find the top/bottom/left/right-most blocks
        for block in self.scene.blocks:
            b_left = block.grBlock.pos().x()
            b_top = block.grBlock.pos().y()
            b_right = b_left + block.width
            b_btm = b_top + block.height

            [left, top, right, btm] = find_boundaries(
                b_left, b_top, b_right, b_btm, left, top, right, btm
            )

            # if b_left < left: left = b_left
            # if b_top < top: top = b_top
            # if b_right > right: right = b_right
            # if b_btm > btm: btm = b_btm

        # Then go through each floating text item, grouping box, and wire segments
        for floating_text in self.scene.floating_labels:
            f_left = floating_text.grContent.pos().x()
            f_top = floating_text.grContent.pos().y()
            f_rect = floating_text.grContent.boundingRect()
            f_right = f_left + f_rect.width()
            f_btm = f_top + f_rect.height()

            [left, top, right, btm] = find_boundaries(
                f_left, f_top, f_right, f_btm, left, top, right, btm
            )
            # print("floating label - rect, left, top, right, btm:", [f_rect, f_left, f_top, f_right, f_btm])

        for gbox in self.scene.grouping_boxes:
            g_left = gbox.grGBox.pos().x()
            g_top = gbox.grGBox.pos().y()
            g_rect = gbox.grGBox.boundingRect()
            g_right = g_left + g_rect.width()
            g_btm = g_top + g_rect.height()

            [left, top, right, btm] = find_boundaries(
                g_left, g_top, g_right, g_btm, left, top, right, btm
            )

            # print("grouping box - rect, left, top, right, btm:", [g_rect, g_left, g_top, g_right, g_btm])

        for wire in self.scene.wires:
            w_rect = wire.grWire.boundingRect()
            w_left = w_rect.left()
            w_top = w_rect.top()
            w_right = w_left + w_rect.width()
            w_btm = w_top + w_rect.height()

            [left, top, right, btm] = find_boundaries(
                w_left, w_top, w_right, w_btm, left, top, right, btm
            )

            # print("wire - rect, left, top, right, btm:", [w_rect, w_left, w_top, w_right, w_btm])

        if DEBUG:
            print(
                "Left most:",
                left,
                " | Top most:",
                top,
                " | Right most:",
                right,
                " | Bottom most:",
                btm,
            )

        # Return the rect (x,y, width, height) that all these blocks occupy
        width = (right + spacer) - (left - spacer)
        height = (btm + spacer) - (top - spacer)
        return [left - spacer, top - spacer, width, height]

    # -----------------------------------------------------------------------------
    def save_image(self, picture_path, picture_name=None, picture_format=None):
        """
        This method takes a filename and saves a snapshot of all the items within
        the ``Scene`` into it. Currently the resolution of this image is set to
        4K resolution (3840 x 2160).

        :param picture_path: path where the given model is saved, and where the image will be saved
        :type picture_path: path, required
        :param picture_name: name of screenshot, same as model name if not given
        :type picture_name: str, optional
        """

        print("Rendering image")

        # Creates an image, of defined resolution quality
        ratio = 3
        output_image = QImage(
            int(self.scene.scene_width * ratio),
            int(self.scene.scene_height * ratio),
            QImage.Format_RGBA64,
        )

        # Then a painter is initialized to that image
        painter = QPainter(output_image)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # The canvas is rendered by the above-defined painter (into the image)
        self.scene.grScene.render(painter)
        painter.end()

        # Grab the dimensions of the space all blocks within the screen occupy
        [x, y, width, height] = self.grab_screenshot_dimensions()

        # ensure number of bytes in row (width*3) is a multiple of 4
        width += (width * 3) % 4
        # Scale the dimensions from above, to the image
        rect = QRect(
            int(output_image.width() / 2 + (x * ratio)),
            int(output_image.height() / 2 + (y * ratio)),
            int(width * ratio),
            int(height * ratio),
        )

        # Crop the image to area of interest
        output_image = output_image.copy(rect)
        # by default this is in QImage.Format_RGBA64 = 26 format, convert
        # 8-bit RGB pixels
        #  see https://doc.qt.io/qt-5/qimage.html
        output_image = output_image.convertToFormat(QImage.Format_RGB888)

        save_path = self.getScreenshotName(picture_path, picture_name, picture_format)

        # use PIL to do the PDF printing
        from PIL import Image

        bytes = output_image.bits().asstring(output_image.sizeInBytes())
        img_PIL = Image.frombuffer(
            "RGB",
            (output_image.width(), output_image.height()),
            bytes,
            "raw",
            "RGB",
            0,
            1,
        )
        img_PIL.save(save_path)
        # # And the image is saved under the given file name, as a PDF
        print("Screenshot saved --> ", save_path)

    # -----------------------------------------------------------------------------
    def getScreenshotName(self, picture_path, picture_name, picture_format=None):
        """ """

        # If picture_name is None, save screenshot under same name as model file.
        # Extract directory of model file and save screenshot in same place, suffixed with .pdf by default
        # If picture_format is given, this overrides the default file type. This can only happen if user selects file type when exporting image from menubar
        if picture_name is None:
            name_to_save = (
                os.path.join(
                    os.path.splitext(os.path.basename(picture_path))[0] + ".pdf"
                )
                if picture_format is None
                else os.path.join(
                    os.path.splitext(os.path.basename(picture_path))[0]
                    + "."
                    + picture_format
                )
            )
        # If picture name is given, use this name when saving screenshot
        else:
            name_to_save = (
                os.path.join(picture_name)
                if picture_format is None
                else os.path.join(picture_name + "." + picture_format)
            )

        # Find all other images in the current directory (files ending with .png)
        # as bdedit only saves images with .png extensions
        # HACK
        images_in_dir = []
        dir_list = os.listdir(os.path.dirname(picture_path))
        for img in fnmatch.filter(dir_list, "*.pdf"), fnmatch.filter(dir_list, "*.png"):
            images_in_dir.append(img)

        # Check if saving current model under the model name would create a duplicate
        no_duplicates = True
        for image in images_in_dir:
            if name_to_save == image:
                no_duplicates = False
                break
        # HACK
        # no_duplicates = True

        # If no duplicates are found, save screenshot under current model name
        if no_duplicates:
            return os.path.join(os.path.dirname(picture_path), name_to_save)
        else:
            print(
                "Handle not yet implemented. Saving screenshot would override existing screenshot with same name."
            )

    # def getScreenshotName(self, picture_path, increment=None):
    #     """
    #     This function takes a path of where the current model is saved, and searches
    #     if there are any screenshots in this path with the same name as the model.
    #     If a duplicate name is detected, the given picture_name is incremented
    #     with a -N, where N is a unique integer.
    #
    #     :param picture_path: path of model to extract name from
    #     :type picture_path: path, required
    #     :param increment: integer which makes filename unique. Incremented internally.
    #     :type increment: int, optional
    #     """
    #
    #     # Given the filepath where to save the picture, find the basename of the screenshot
    #     if increment is None:
    #         name_to_save = os.path.join(os.path.splitext(os.path.basename(picture_path))[0] + ".pdf")
    #     else:
    #         name_to_save = os.path.join(os.path.splitext(os.path.basename(picture_path))[0] + "-" + str(increment)) + ".pdf"
    #         increment += 1
    #
    #     # Find all other images in the current directory (files ending with .png)
    #     # as bdedit only saves images with .png extensions
    #     # HACK
    #     images_in_dir = []
    #     print('Picture path:', picture_path)
    #     dir_list = os.listdir(os.path.dirname(picture_path))
    #     for img in fnmatch.filter(dir_list, "*.pdf"):
    #         images_in_dir.append(img)
    #
    #     # Check if saving current model under the model name would create a duplicate
    #     no_duplicates = True
    #     for image in images_in_dir:
    #         if name_to_save == image:
    #             no_duplicates = False
    #             break
    #     #HACK
    #     # no_duplicates = True
    #
    #     # If no duplicates are found, save screenshot under current model name
    #     if no_duplicates:
    #         return os.path.join(os.path.dirname(picture_path), name_to_save)
    #     else:
    #         if increment is None: return self.getScreenshotName(picture_path, 1)
    #         else: return self.getScreenshotName(picture_path, increment)

    # -----------------------------------------------------------------------------
    def updateSceneDimensions(self):
        """
        This method updates the dimensions of the scene based on current window
        size (will change as the application window is resized).
        """
        # The largest size the scene can be is:
        # the difference between the max zoom out level (zoomRange[max_zoom_out, max_zoom_in]) and default zoom
        # multiplied by the zoom out factor
        multiplier = (
            abs(self.canvasView.zoomRange[0] - self.canvasView._default_zoom_level)
            * 0.8
        )

        # Only update if canvas dimensions have changed from what they were previously set to
        if (
            self.width() * multiplier != self.scene.getSceneWidth() * multiplier
            or self.height() * multiplier != self.scene.getSceneHeight() * multiplier
        ):
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
