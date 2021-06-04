from pathlib import Path
import os
import importlib.util
import inspect

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from bdedit.interface_scene import Scene
from bdedit.interface_graphics_view import GraphicsView
from bdedit.block import *
from bdedit.block_wire import Wire
from bdedit.block_socket_block import *
from bdedit.Icons import *

DEBUG = False


def importBlocks():
    block_path = [Path(__file__).parent / 'Block_Classes']
    nblocks = len(blocklist)
    blocks = []
    for path in block_path:
        if not path.exists():
            print("Provided path does not exist")
            continue

        for file in path.iterdir():
            if file.name.endswith('.py'):
                sub_class_blocks = []
                spec = importlib.util.spec_from_file_location(file.name, file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for cls in blocklist[nblocks:]:
                    sub_class_blocks.append([blockname(cls), cls, file])

                blocks.append(sub_class_blocks)
                nblocks = len(blocklist)

    return blocks


class Interface(QWidget):
    def __init__(self, resolution, parent=None):
        super().__init__(parent)

        self.blockLibrary = importBlocks()

        self.toolBar = QWidget()
        self.libraryBrowser = QWidget()
        self.libraryBrowserBox = QGroupBox()

        self.filename = None

        self.initUI(resolution)

    def initUI(self, resolution):
        # =============================================================================================================
        # Sets interface's resolution
        # self.setGeometry(100, 100, resolution.width() - 200, resolution.height() - 200)  # Size of desktop screen minus 200 pixels from width and height
        self.setGeometry(100, 100, resolution.width() / 2, resolution.height() / 2)  # Smaller screen
        #self.setGeometry(resolution.width() / 4, resolution.height() / 4, resolution.width() / 2, resolution.height() / 2)  # Smaller screen

        # Defines the layouts for parts of the interface
        self.layout = QGridLayout()  # Contains all the widgets
        self.layout.setContentsMargins(0, 0, 0, 0)  # Removes the border
        self.setLayout(self.layout)

        # Different screen resolutions result in varying sizes of the library browser and parameter window panels
        # To compensate for this, the preferred dimensions of these panels as seen on the screen while being developed (2560 resolution width)
        # have been scaled to other screen sizes.
        self.layout.scale = 2560 / resolution.width()

        # create graphics scene
        self.scene = Scene(resolution, self.layout)

        # Create graphics view
        self.canvasView = GraphicsView(self.scene.grScene, self)

        # ===================================== Toolbar ======================================
        self.toolBar.setFixedHeight(50)

        self.newFile_button = QPushButton('New File')
        self.openFile_button = QPushButton('Open File')
        self.save_button = QPushButton('Save')
        self.saveAs_button = QPushButton('Save As')
        self.simulate_button = QPushButton('Simulate')
        self.run_button = QPushButton('Run')
        self.screenshot_button = QPushButton('Screenshot')
        self.grid_mode = QWidget()

        # Drop down menu for choosing grid mode (Light, Dark, Off)
        self.grid_mode.layout = QHBoxLayout()
        self.grid_mode_label = QLabel('Grid Mode')
        self.grid_mode_options = QComboBox()
        self.grid_mode_options.addItem("Light")
        self.grid_mode_options.addItem("Dark")
        self.grid_mode_options.addItem("Off")

        self.grid_mode.layout.addWidget(self.grid_mode_label)
        self.grid_mode.layout.addWidget(self.grid_mode_options)
        self.grid_mode.setLayout(self.grid_mode.layout)

        self.toolBar.layout = QHBoxLayout()
        self.toolBar.layout.setContentsMargins(0, 0, 0, 0)

        self.toolBar.layout.addWidget(self.newFile_button)
        self.toolBar.layout.addWidget(self.openFile_button)
        self.toolBar.layout.addWidget(self.save_button)
        self.toolBar.layout.addWidget(self.saveAs_button)
        self.toolBar.layout.addWidget(self.run_button)
        self.toolBar.layout.addWidget(self.screenshot_button)
        self.toolBar.layout.addWidget(self.grid_mode)

        self.newFile_button.clicked.connect(lambda: self.scene.clear())
        self.save_button.clicked.connect(lambda: self.saveToFile())
        self.openFile_button.clicked.connect(lambda: self.loadFromFile())
        self.saveAs_button.clicked.connect(lambda: self.saveAsToFile())
        self.screenshot_button.clicked.connect(lambda: self.save_image('Scene Picture'))
        self.grid_mode_options.currentIndexChanged.connect(lambda: self.updateColorMode())

        self.toolBar.layout.setAlignment(Qt.AlignHCenter)
        self.toolBar.setLayout(self.toolBar.layout)

        # ===================================== libraryBrowser ======================================
        # Add buttons to layout in order
        self.libraryBrowser.layout = QVBoxLayout(self.libraryBrowser)
        self.libraryBrowser.layout.addWidget(QLabel('<font size=8><b>Library Browser</font>'))
        self.libraryBrowserBox.layout = QVBoxLayout()

        self.canvas_items_expanded = True
        self.source_blocks_expanded = True
        self.sink_blocks_expanded = True
        self.function_blocks_expanded = True
        self.transfer_blocks_expanded = True
        self.discrete_blocks_expanded = True
        self.subsystem_blocks_expanded = True

        self.canvasItems_button = QPushButton(' + Canvas Items')
        self.sourceBlocks_button = QPushButton(' + Source Blocks')
        self.sinkBlocks_button = QPushButton(' + Sink Blocks')
        self.functionBlocks_button = QPushButton(' + Function Blocks')
        self.transferBlocks_button = QPushButton(' + Transfer Blocks')
        self.discreteBlocks_button = QPushButton(' + Discrete Blocks')
        self.subsystemBlocks_button = QPushButton(' + Subsystem Blocks')

        self.canvasItems_button.setStyleSheet("QPushButton { text-align: left }")
        self.sourceBlocks_button.setStyleSheet("QPushButton { text-align: left }")
        self.sinkBlocks_button.setStyleSheet("QPushButton { text-align: left }")
        self.functionBlocks_button.setStyleSheet("QPushButton { text-align: left }")
        self.transferBlocks_button.setStyleSheet("QPushButton { text-align: left }")
        self.discreteBlocks_button.setStyleSheet("QPushButton { text-align: left }")
        self.subsystemBlocks_button.setStyleSheet("QPushButton { text-align: left }")

        self.canvasItems_button.clicked.connect(self.toggleCanvasItems)
        self.sourceBlocks_button.clicked.connect(self.toggleSourceBlocks)
        self.sinkBlocks_button.clicked.connect(self.toggleSinkBlocks)
        self.functionBlocks_button.clicked.connect(self.toggleFunctionBlocks)
        self.transferBlocks_button.clicked.connect(self.toggleTransferBlocks)
        self.discreteBlocks_button.clicked.connect(self.toggleDiscreteBlocks)
        self.subsystemBlocks_button.clicked.connect(self.toggleSubSystemBlocks)

        self.list_of_scrollbar_buttons = []

        # Create space for canvas items button
        self.libraryBrowserBox.layout.addWidget(self.canvasItems_button)
        self.connector_block_button = QPushButton("Connector Block")
        self.connector_block_button.setVisible(False)
        self.connector_block_button.clicked.connect(lambda checked: Connector(self.scene, self.layout, "Connector Block"))
        self.libraryBrowserBox.layout.addWidget(self.connector_block_button)

        # For each type of child class blocks imported (sink, source, function)
        for sub_class_group in self.blockLibrary:
            sourceBlocksAdded = False
            sinkBlocksAdded = False
            functionBlocksAdded = False
            transferBlocksAdded = False
            discreteBlocksAdded = False
            subsystemBlocksAdded = False
            # Add a button to expand/minimise the class of blocks
            # All blocks in each group of blocks are in the same class, so if the first is a sink/source/function
            # the rest will also belong to the same class
            if not sourceBlocksAdded:
                if issubclass(sub_class_group[0][1], SourceBlock):
                    self.libraryBrowserBox.layout.addWidget(self.sourceBlocks_button)
                    sourceBlocksAdded = True
                    
            if not sinkBlocksAdded:
                if issubclass(sub_class_group[0][1], SinkBlock):
                    self.libraryBrowserBox.layout.addWidget(self.sinkBlocks_button)
                    sinkBlocksAdded = True

            if not functionBlocksAdded:
                if issubclass(sub_class_group[0][1], FunctionBlock):
                    self.libraryBrowserBox.layout.addWidget(self.functionBlocks_button)
                    functionBlocksAdded = True

            if not transferBlocksAdded:
                if issubclass(sub_class_group[0][1], TransferBlock):
                    self.libraryBrowserBox.layout.addWidget(self.transferBlocks_button)
                    transferBlocksAdded = True

            if not discreteBlocksAdded:
                if issubclass(sub_class_group[0][1], DiscreteBlock):
                    self.libraryBrowserBox.layout.addWidget(self.discreteBlocks_button)
                    discreteBlocksAdded = True

            if not subsystemBlocksAdded:
                if issubclass(sub_class_group[0][1], (INPORTBlock, OUTPORTBlock, SUBSYSTEMBlock)):
                    self.libraryBrowserBox.layout.addWidget(self.subsystemBlocks_button)
                    subsystemBlocksAdded = True

            # Add each block type that is imported
            for sub_class_block in sub_class_group:
                # Make a scrollbar button with the name of the block type
                button = QPushButton(sub_class_block[0])
                button.setVisible(False)
                # Connect button to calling a new instance of the block type class
                button.clicked.connect(lambda checked, blockClass=sub_class_block[1], scene=self.scene, layout=self.layout: blockClass(scene, layout))
                # Add button to list of scrollbar buttons for reference when expanding/hiding block sub classes
                self.list_of_scrollbar_buttons.append((button, sub_class_block[1]))
                # Add the button to the scrollbar layout
                self.libraryBrowserBox.layout.addWidget(button)

        self.libraryBrowserBox.layout.addStretch()
        self.libraryBrowserBox.layout.setAlignment(Qt.AlignTop)
        self.libraryBrowserBox.setLayout(self.libraryBrowserBox.layout)

        self.scroll = QScrollArea()
        self.scroll.setWidget(self.libraryBrowserBox)
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumHeight(300)

        # Set the scrollbar layout
        self.libraryBrowser.setFixedWidth(250 * self.layout.scale)
        self.libraryBrowser.layout.addWidget(self.scroll)
        self.libraryBrowser.layout.setAlignment(Qt.AlignTop)
        self.libraryBrowser.setLayout(self.libraryBrowser.layout)

        # ========================= Add Widgets / View to self.layout =========================
        self.layout.addWidget(self.toolBar, 0, 1, 1, 9)
        self.layout.addWidget(self.libraryBrowser, 0, 0, 10, 1)
        self.layout.addWidget(self.canvasView, 1, 1, 9, 9)

        self.setWindowTitle("bdedit")
        self.setWindowIcon(QIcon(":/Icons_Reference/Icons/bdsim_icon.png"))
        self.show()

    @pyqtSlot()
    def on_click(self, scene):
        # print('PyQt5 button click')
        startBlock, endBlock, startSocket, endSocket = self.get_Input()
        Wire(scene, scene.blocks[startBlock].outputs[startSocket], scene.blocks[endBlock].inputs[endSocket], wire_type=2)

    def loadFromFile(self):
        fname, filter = QFileDialog.getOpenFileName(self)
        if fname == '':
            return

        if os.path.isfile(fname):
            self.scene.loadFromFile(fname)

    def saveToFile(self):
        if self.filename is None: return self.saveAsToFile()
        self.scene.saveToFile(self.filename)

    def saveAsToFile(self):
        file_types = "JSON files (*.json);;all files(*.*)"
        fname, _ = QFileDialog.getSaveFileName(self, 'untitled.json', filter=file_types)
        if fname == '':
            return

        self.filename = fname
        self.saveToFile()

    def updateColorMode(self):
        self.scene.grScene.updateMode(self.grid_mode_options.currentText())
        for eachBlock in self.scene.blocks:
            eachBlock.grBlock.updateMode(self.grid_mode_options.currentText())

    def toggleCanvasItems(self):
        if self.canvas_items_expanded:
            self.canvasItems_button.setText(' -  Canvas Items')
        else:
            self.canvasItems_button.setText(' + Canvas Items')

        self.canvas_items_expanded = not self.canvas_items_expanded
        self.connector_block_button.setVisible(not self.connector_block_button.isVisible())

    def toggleSourceBlocks(self):
        if self.source_blocks_expanded:
            self.sourceBlocks_button.setText(' -  Source Blocks')
        else:
            self.sourceBlocks_button.setText(' + Source Blocks')

        self.source_blocks_expanded = not self.source_blocks_expanded

        for button_tuple in self.list_of_scrollbar_buttons:
            if issubclass(button_tuple[1], SourceBlock):
                button_tuple[0].setVisible(not button_tuple[0].isVisible())

    def toggleSinkBlocks(self):
        if self.sink_blocks_expanded:
            self.sinkBlocks_button.setText(' -  Sink Blocks')
        else:
            self.sinkBlocks_button.setText(' + Sink Blocks')

        self.sink_blocks_expanded = not self.sink_blocks_expanded

        for button_tuple in self.list_of_scrollbar_buttons:
            if issubclass(button_tuple[1], SinkBlock):
                button_tuple[0].setVisible(not button_tuple[0].isVisible())

    def toggleFunctionBlocks(self):
        if self.function_blocks_expanded:
            self.functionBlocks_button.setText(' -  Function Blocks')
        else:
            self.functionBlocks_button.setText(' + Function Blocks')

        self.function_blocks_expanded = not self.function_blocks_expanded

        for button_tuple in self.list_of_scrollbar_buttons:
            if issubclass(button_tuple[1], FunctionBlock):
                button_tuple[0].setVisible(not button_tuple[0].isVisible())

    def toggleTransferBlocks(self):
        if self.transfer_blocks_expanded:
            self.transferBlocks_button.setText(' -  Transfer Blocks')
        else:
            self.transferBlocks_button.setText(' + Transfer Blocks')

        self.transfer_blocks_expanded = not self.transfer_blocks_expanded

        for button_tuple in self.list_of_scrollbar_buttons:
            if issubclass(button_tuple[1], TransferBlock):
                button_tuple[0].setVisible(not button_tuple[0].isVisible())

    def toggleDiscreteBlocks(self):
        if self.discrete_blocks_expanded:
            self.discreteBlocks_button.setText(' -  Discrete Blocks')
        else:
            self.discreteBlocks_button.setText(' + Discrete Blocks')

        self.discrete_blocks_expanded = not self.discrete_blocks_expanded

        for button_tuple in self.list_of_scrollbar_buttons:
            if issubclass(button_tuple[1], DiscreteBlock):
                button_tuple[0].setVisible(not button_tuple[0].isVisible())

    def toggleSubSystemBlocks(self):
        if self.subsystem_blocks_expanded:
            self.subsystemBlocks_button.setText(' -  Subsystem Blocks')
        else:
            self.subsystemBlocks_button.setText(' + Subsystem Blocks')

        self.subsystem_blocks_expanded = not self.subsystem_blocks_expanded

        for button_tuple in self.list_of_scrollbar_buttons:
            if issubclass(button_tuple[1], (INPORTBlock, OUTPORTBlock, SUBSYSTEMBlock)):
                button_tuple[0].setVisible(not button_tuple[0].isVisible())

    def save_image(self, picture_name):
        output_image = QImage(3840, 2160, QImage.Format_RGBA64_Premultiplied)
        painter = QPainter(output_image)
        painter.setRenderHint(QPainter.Antialiasing, True)
        self.canvasView.render(painter)
        painter.end()
        #  .saveAsToFile()
        output_image.save(picture_name+".png")
        # output_image.save(picture_name+".svg")
        print("succeeded")

    # Updates the dimensions of the scene based on current window size (will change as window is resized)
    def updateSceneDimensions(self):
        # The largest size the scene can be is:
        # the difference between the max zoom out level (zoomRange[max_zoom_out, max_zoom_in]) and default zoom
        # multiplied by the zoom out factor
        multiplier = abs(self.canvasView.zoomRange[0] - self.canvasView._default_zoom_level) * 0.8

        # Only update if canvas dimensions have changed to what they were previously set to
        if self.width() * multiplier != self.scene.getSceneWidth() * multiplier or \
           self.height() * multiplier != self.scene.getSceneHeight() * multiplier:
            self.scene.setSceneWidth((self.width()) * multiplier)
            self.scene.setSceneHeight((self.height()) * multiplier)
            self.scene.updateSceneDimensions()

    # Update the canvas's dimension if its size has changed (if window has been resized)
    def resizeEvent(self, event):
        self.updateSceneDimensions()
