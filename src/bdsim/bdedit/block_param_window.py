# Library imports
import ast
import math

# PyQt5 Imports
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap, QDesktopServices
from PyQt5.QtCore import Qt, QRect

# BdEdit imports
from bdsim.bdedit.Icons import *

# =============================================================================
#
#   Defining and setting global variables
#
# =============================================================================
# Socket positioning variables - used for determining what side of the block the
# socket should be drawn
LEFT = 1
RIGHT = 3

# Socket sign variables - used for logic associated with drawing symbols for the
# PROD and SUM blocks
PLUS = "+"
MINUS = "-"
MULTIPLY = "*"
DIVIDE = "/"

# Variable for enabling/disabling debug comments
DEBUG = False


# =============================================================================
#
#   Defining the ParamWindow Class, which holds information of how the parameter
#   window - that holds all the user-editable block parameters - appears. It also
#   contains the logic for creating the ParamWindow and the logic for sanity
#   checking the block parameters once they have been edited by the user.
#
# =============================================================================
class ParamWindow(QWidget):
    """
    The ``ParamWindow`` Class extends the ``QWidget`` Class from PyQt5.
    The ParamWindow Class controls:

    - how the parameter window appears visually,
    - where it is located within the BdEdit application window,
    - the displayed parameters from the Block the parameter window is related to,
    - sanity checking on user-edits to the Block parameters,
    - pop-up user feedback for successful or unsuccessful Block parameter edits.
    """

    # -----------------------------------------------------------------------------
    def __init__(self, block, parent=None):
        """
        This method initializes an instance of the ``ParamWindow`` Class.

        :param block: the Block this ParamWindow instance relates to
        :type block: ``Block``
        :param parent: the parent widget this ParamWindow belongs to (should be None)
        :type parent: None, optional
        """

        super().__init__(parent)

        # The Block this parameter window relates to is stored internally,
        # so are its parameters
        self.block = block
        self.parameters = self.block.parameters

        # Parameter_values is a list into which the text responses of the user
        # will be appended to, when they make changes to a Block parameter
        self.parameter_values = []

        # The parameter window will display vertically on the RHS of the BdEdit
        # application window, hence its layout manager will be a vertical one
        self.layout = QVBoxLayout()

        # Definition of with of the parameter window, and the lines holding
        # the block parameters inside it. The width is fixed to 300 pixels, scaled
        # to what 300 pixels should look like on 2560 screen width resolution
        self._parameter_line_width = 150
        self._width = 300 * self.block.window.scale
        self.setFixedWidth(self._width)

        # Variable to update title of model when parameter values have been changed,
        # to indicate that there is unsaved progress
        self.paramsWereChanged = False

        # Further initializing necessary parameter window settings, and calling
        # the method that will build the it
        self.initUI()
        self.buildParamWindow()

    # -----------------------------------------------------------------------------
    def initUI(self):
        """
        This method adds a 'Parameter Window' label to the ParamWindow, sets the
        alignment of items within the parameter window, sets the background to
        auto fill, and finally, sets the layout manager of the ParamWindow.
        """

        # The follow label is added to the parameter window, naming it
        # Items within the parameter window layout manager are set to align towards the top
        param_window_label = QLabel("<font size=8><b>Block settings</font>")
        param_window_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(param_window_label)
        self.layout.setAlignment(Qt.AlignTop)

        # Its background is filled
        self.setAutoFillBackground(True)
        self.setLayout(self.layout)

    # -----------------------------------------------------------------------------
    def displayDocumentationURL(self):
        """
        This method opens the url link associated with this blocks' documentation.
        """

        QDesktopServices.openUrl(QtCore.QUrl(self.block.block_url))

    # -----------------------------------------------------------------------------
    def closeQMessageBox(self):
        """
        This method closes a pop-up user-feedback message if one already exists
        within the parameter window. This prevents multiple messages from being
        displayed at the same time, and ensure the message the user sees, is the
        most relevant one.
        """

        # If a message widget already exists in the ParamWindow, remove it
        # ParamWindow (self) has several widgets already, some of which hold QLabels, QEditLines or a QPushButton
        # Iterate through all of ParamWindow's widgets
        for widget in self.children():
            # Grab the children of the ParamWindow's child widget
            widgets_children = widget.children()
            # Iterate through all this widget's children widgets
            for child in widgets_children:
                # If a child widget happens to be a QMessageBox, then remove that widget from the ParamWindow layout
                if child.__class__ == QMessageBox:
                    self.layout.removeWidget(widget)
                    break

    # -----------------------------------------------------------------------------
    def displayPopUpMessage(self, title, text, messageType):
        """
        This method displays a pop-up user-feedback message within the parameter window,
        notifying them of either a successful or unsuccessful update to the Blocks'
        parameters. This method will also trigger the message to auto-close, after 1.5
        seconds for a successful update, and after 5 seconds for an unsuccessful update.
        If at any point the user updates the Block parameters before this time is elapsed,
        the current (old) message will be removed and replaced by the most relevant message.
        An unsuccessful update attempt will also issue an error sound when the message is
        opened.

        :param title: the title of the message box displayed
        :type title: str
        :param text: the text that fills the body of the displayed message box
        :type text: str
        :param messageType: variable that calls what type of message to display ("Success", "Error")
        :type messageType: str
        """

        def closeMessage():
            self.timer.stop()
            self.message.close()

        # If a message box is already displayed within the ParamWindow, it will be closed
        self.closeQMessageBox()

        # Create a widget to wrap the QMessageBox into, that it may be displayed in the ParamWindow
        self.popUp = QWidget()
        self.popUp.layout = QVBoxLayout()
        self.message = QMessageBox(self)

        # Manually set the width of the QMessageBox layout to control text wrapping
        # The layout is a grid, so setting width of 1st row/column cell will set width of the widget
        self.message.item = self.message.layout().itemAtPosition(0, 1)
        self.message.item.widget().setFixedWidth(self.width() - 100)

        # If an error message - critical icon, if success message - green tick icon
        if messageType == "Error":
            self.message.setIcon(QMessageBox.Critical)
            self.message.setIconPixmap(QPixmap(":/Icons_Reference/Icons/error.png"))
            message_duration = 5
        elif messageType == "Success":
            self.message.setIconPixmap(QPixmap(":/Icons_Reference/Icons/success.png"))
            message_duration = 1.5

        # Set the title and text for the message
        self.message.setText("<font><b>" + title + "</font>")
        self.message.setInformativeText(text)
        # Set style (adding a black border around messagebox)
        self.message.setStyleSheet("QMessageBox { border : 1px solid black;}")
        # Set message modality to be non-blocking (by default, QMessageBox blocks other actions until closed)
        self.message.setWindowModality(Qt.NonModal)
        # Add the QMessageBox to the popUp widget, then add to the layout of the ParamWindow widget
        self.popUp.layout.addWidget(self.message)
        self.popUp.setLayout(self.popUp.layout)
        self.layout.addWidget(self.popUp)

        # Create timer to keep message opened for 5 seconds if error, 1.5 seconds if success
        self.timer = QtCore.QTimer()
        self.timer.setInterval(int(message_duration * 1000))
        self.timer.timeout.connect(closeMessage)
        self.timer.start()

    # -----------------------------------------------------------------------------
    def buildParamWindow(self):
        """
        This method handles the building of the ParamWindow instance. These instances
        will always look exactly the same in terms of the information they contain,
        however the Block parameters and the block type will vary depending on the Block
        this ParamWindow relates to.

        The ParamWindow is built by adding items into the QWidget that represents this
        parameter window. For each item added into the QWidget, a label is displayed on
        the left-hand-side, and either the non-editable value (label) is displayed on the
        right-hand-side, or an editable line is displayed and populated with the respective
        parameters' current value.

        The ParamWindow is populated by, first, adding a non-editable line displaying the
        selected Blocks' type. Next, the Blocks' current title is added with an editable
        line. Following this, each Block parameter looped through and added with an editable
        line in which the current value of the Block parameter is populated. Changing this
        value will prompt the sanity checking of the value entered, which is handled by
        the updateBlockParameters() method.
        """

        # Make the first row, which contains two labels for the block's type
        self.row1 = QWidget()
        self.row1.layout = QHBoxLayout()
        # Make a label of the block type
        self.block_type_label = QLabel("<font size=4><b>type: </font>")
        # Make an editable line for the type, and populate it with the current block type
        self.block_type = QLabel(
            "<font size=4>" + str(self.block.block_type) + " Block </font>"
        )
        # Set the width of the editable line to the above-defined width (150 pixels)
        self.block_type.setFixedWidth(self._parameter_line_width)
        # Add the label and editable line into our row widget
        self.row1.layout.addWidget(self.block_type_label, alignment=Qt.AlignCenter)
        self.row1.layout.addWidget(self.block_type, alignment=Qt.AlignCenter)

        # Add out type row widget to the layout of the parameter window
        self.row1.setLayout(self.row1.layout)
        self.layout.addWidget(self.row1)

        # Make the second row, which contains the label and editable line for the block's title
        self.row2 = QWidget()
        self.row2.layout = QHBoxLayout()

        # Make a label of the block title
        self.title_label = QLabel("<font size=4><b>name: </font>")
        # Make an editable line for the title, and populate it with the current block title
        self.title_line = QLineEdit(self.block.title)
        # Set the width of the editable line to the above-defined width (150 pixels)
        self.title_line.setFixedWidth(self._parameter_line_width)
        # Add the label and editable line into our row widget
        self.row2.layout.addWidget(self.title_label, alignment=Qt.AlignCenter)
        self.row2.layout.addWidget(self.title_line)

        # Add out title row widget to the layout of the parameter window
        self.row2.setLayout(self.row2.layout)
        self.layout.addWidget(self.row2)

        # If the block has parameters, build part of the paramWindow that displays those
        if self.parameters:
            # For each block parameter
            for parameter in self.parameters:
                # Create a QWidget that will represent the row that parameter is displayed in
                self.row_x = QWidget()
                self.row_x.layout = QHBoxLayout()

                # Make a label of that parameters' name
                self.label = QLabel(
                    "<font size=3><b>" + parameter[0] + ": " + "</font>"
                )
                try:
                    self.label.setToolTip(parameter[4])
                except IndexError:
                    print(parameter)

                # If the parameter type is a boolean, create the intractable space as a checkbox, otherwise
                # make an editable line for that parameter, and populate it with the parameters' current value
                if not issubclass(parameter[1], bool):
                    self.line = QLineEdit(str(parameter[2]))
                else:
                    try:
                        self.line = QCheckBox()
                        self.line.setChecked(parameter[2])
                    except TypeError:
                        print("bad thing")

                # Set the width of the editable line to the above-defined width (150 pixels)
                self.line.setFixedWidth(self._parameter_line_width)
                # Append the current value of the parameter into the following list (for later comparison)
                self.parameter_values.append(self.line)
                # Add the label and editable line into our row widget
                self.row_x.layout.addWidget(self.label, alignment=Qt.AlignCenter)
                self.row_x.layout.addWidget(self.line, alignment=Qt.AlignCenter)

                # Add out row widget to the layout of the parameter window
                self.row_x.setLayout(self.row_x.layout)
                self.layout.addWidget(self.row_x)

        # Finally add an update button, which will trigger the sanity checking of the
        # current values within the editable lines
        self.update_button = QPushButton("Update Parameters")
        self.update_button.clicked.connect(self.updateBlockParameters)
        self.layout.addWidget(self.update_button)

        # Add a button linked to the URL of this block's documentation
        self.block_url_Button = QPushButton("View documentation")
        self.block_url_Button.clicked.connect(self.displayDocumentationURL)
        self.layout.addWidget(self.block_url_Button)

    # -----------------------------------------------------------------------------
    def updateBlockParameters(self):
        """
        This method calls for each of the parameters within the parameter window to be
        sanity checked by the getSafeValue() method, which determines whether or not
        a provided value is compatible with the parameter type (defined in the Block
        Class) and is safe to override the current value. If that check is returned
        to be safe, this method will handle the updating of the Block parameters, as
        well as triggering a successful update attempt message.

        If the check is returned as not safe, meaning the given value is not compatible,
        an unsuccessful update attempt error message will be prompted, notifying the
        user of the incompatible parameter value they have set, and either what the
        compatible types or values are. This logic also applies when a user changes the
        blocks' title to one that already exists, which will cause a duplicate error
        message to display.

        Some parameters values directly affect the GraphicsBlock of the Block they relate
        to. For example, blocks that can have multiple input or output sockets, will
        have a parameter that controls how many of these sockets the block has. And once
        edited, this method will trigger an appropriate number of sockets to be created
        or deleted. This parameter can also affect the GraphicsBlock when too many sockets
        are created, requiring the block to be resized. The triggering of this resizing
        will also be issued from within this method.
        """

        # -----------------------------------------------------------------------------
        def makeBadInputErrorMsg(options):
            """
            This method returns the correct text that should be displayed within the body
            of the pop-up user-feedback message. The text that is displayed here is extracted
            from the associated extra-options as defined in the relating Block.

            :param options: the extra-options associated with this parameter (defined in this Block)
            :type options: list, of str, list
            :return: the formatted message to be displayed
            :rtype: str
            """

            # Start with an empty message
            message = ""
            # Num_options is the number of lists (of accepted keywords, types, range, symbol) inside the option list
            num_options = len(options)
            # Check the options that have been assigned to this parameter
            for option in options:
                # If the options consist keywords that this parameter is restricted to
                if option[0] == "keywords":
                    message += "one of <font><b>" + str(option[1]) + "</font>"
                # If the options consist of a range this parameters is restricted to
                elif option[0] == "range":
                    message += (
                        "a value between <font><b>"
                        + str(option[1][0])
                        + "</font> and <font><b>"
                        + str(option[1][1])
                        + "</font>"
                    )
                # If the options consist of additional types this parameter is restricted to
                elif option[0] == "type":
                    typeString = []
                    for optionType in option[1]:
                        typeString.append(optionType.__name__)
                    message += "of type <font><b>" + str(typeString) + "</font>"
                # If the options consist of certain sign characters this parameter is restricted to
                elif option[0] == "symbol":
                    message += "a combination of <font><b>" + str(option[1]) + "</font>"
                # If the options consists of a size restriction on how many elements are allowed in the list
                elif option[0] == "size":
                    message += (
                        "limited to a size of <font><b>" + str(option[1]) + "</font>"
                    )

                # If a parameter has multiple options (e.g. range and type restrictions)
                # separate the options with "or" until only 1 option remains
                if num_options > 1:
                    message += " or "
                    num_options -= 1

            return message

        # Update the title
        duplicate_title = []
        # UpdateName is returned as None if there are no issues with setting a title
        # If title is a duplicate, a list of ["@DuplicateName@", given_name] is returned
        updateName = self.block.setTitle(self.title_line.text())
        self.block.grBlock._draw_title = True
        if updateName:
            if updateName[0] == "@DuplicateName@":
                duplicate_title.append(updateName[1])
        else:
            self.paramsWereChanged = True

        # Iterator for loop
        i = -1

        # An error message can consist of an invalid_input (incorrect parameter type)
        # or a bad_input (incompatible with option restrictions), and initially these
        # are set to being empty. If parameters cannot be set due to errors, these will
        # be appended into these empty lists
        invalid_input, bad_inputs, bad_socket_labels = [], [], []

        # Check if the block has parameters, if so, go through the sanity checking of each parameter value
        if self.parameters:

            # For each definition of a parameter, in the blocks' defined parameters
            for [paramName, paramType, paramVal, paramOptions, _] in self.parameters:
                i += 1

                # If parameter type is boolean, then retrieve checked state of checkbox, otherwise
                # extract the text from the editable line as the value to set the parameter to
                if not issubclass(paramType, bool):
                    inputValue = self.parameter_values[i].text()
                else:
                    inputValue = str(self.parameter_values[i].isChecked())

                # If a value has been provided for that parameter, perform sanity checking on that input
                if inputValue:
                    if self.parameters[i][0] in ["nin", "ops", "signs", "nout"]:
                        inputInCompatibleFormat = self.getSafeValue(
                            inputValue, paramType, paramOptions
                        )
                    else:
                        if inputValue.startswith("="):
                            inputInCompatibleFormat = inputValue
                        else:
                            inputInCompatibleFormat = self.getSafeValue(
                                inputValue, paramType, paramOptions
                            )

                    # If in DEBUG mode, this code will return the name, type, current value of the parameter attempting to update
                    # and then for the value that will override the parameter, the value, type(of the value), and whether it is or isn't compatible
                    if DEBUG:
                        print(
                            "paramName, paramType, paramVal - inputValue, type, compatible",
                            [
                                paramName,
                                paramType,
                                paramVal,
                                "-",
                                inputValue,
                                type(inputValue),
                                inputInCompatibleFormat,
                            ],
                        )

                    # Once the sanity check has been performed, if the type is valid, check for parameter restrictions
                    if inputInCompatibleFormat != "@InvalidType@":

                        # If the sanity check returns that the parameter doesn't meet its restrictions
                        if inputInCompatibleFormat == "@BadFormat@":
                            # Append the parameter edited, and the parameter options, as a bad_input
                            bad_inputs.append([paramName, paramOptions])
                        else:

                            # Otherwise if both sanity checks pass, value is safe to update, so
                            # Check if the given value is different to what is already set as the param value
                            # If it is the same, don't update the value
                            if inputInCompatibleFormat == paramVal:
                                pass

                            # Otherwise update the value
                            else:
                                # Set the current parameter equal to edited parameter value
                                self.parameters[i][2] = inputInCompatibleFormat
                                self.paramsWereChanged = True

                                # If self.parameter relates to controlling the number of inputs a block has
                                if self.parameters[i][0] in ["nin", "ops", "signs"]:

                                    # Grab the number of required input sockets
                                    if self.parameters[i][0] == "nin":
                                        num_sockets = self.parameters[i][2]
                                    else:
                                        num_sockets = len(
                                            self.parameter_values[i].text()
                                        )

                                    # Don't do anything, if the provided number of input sockets matches the number the block already has,
                                    # or if the symbols (+,-,*,/) for the block haven't changed
                                    # if len(self.block.inputs) == num_sockets and inputInCompatibleFormat == paramVal:
                                    #     pass
                                    # else:
                                    # If the given number of input sockets matches the number the block already has, or if the number of
                                    # symbols (+,-,*,/) for the block hasn't changed
                                    if len(self.block.inputs) == num_sockets:
                                        # If the values of the signs hasn't changed, then don't do anything
                                        if inputInCompatibleFormat == paramVal:
                                            pass
                                        # If the values of the signs has changed (but the number of signs is still the same), just
                                        # update the signs without removing the wires
                                        else:
                                            # Split the socket signs by number of characters given
                                            chars = [
                                                char for char in inputInCompatibleFormat
                                            ]

                                            # Go through each of the chars from the string of symbols for this block's signs
                                            # and set the respective socket to that symbol
                                            for j, char in enumerate(chars):
                                                self.block.inputs[j].socket_sign = char

                                    else:
                                        # If the block already has input sockets, grab their orientation (LEFT / RIGHT) then delete
                                        # Else, draw input socket with default orientation (LEFT) and no need to delete as block has no input sockets
                                        if self.block.inputs:
                                            orientation = self.block.inputs[0].position
                                            # Remove all current input sockets
                                            self.block.inputs[0].removeSockets("Input")
                                        else:
                                            orientation = LEFT
                                        # Recreate input sockets to the number provided
                                        # If self.block is a SUM or PROD block, this will also update the input sockets' sign (+,_,*,/)
                                        self.block.inputsNum = num_sockets
                                        self.block.makeInputSockets(
                                            self.block.inputsNum, orientation
                                        )

                                # If self.parameter relates to controlling the number of outputs a block has
                                if self.parameters[i][0] in ["nout"]:
                                    # Grab number of required output sockets
                                    num_sockets = self.parameters[i][2]
                                    # If provided number of output sockets matches the number the block already has, don't do anything
                                    if len(self.block.outputs) == num_sockets:
                                        pass
                                    else:
                                        # If the block already has output sockets, grab their orientation (LEFT / RIGHT) then delete
                                        # Else, draw output socket with default orientation (RIGHT) and no need to delete as block has no output sockets
                                        if self.block.outputs:
                                            orientation = self.block.outputs[0].position
                                            # Remove all current output sockets
                                            self.block.outputs[0].removeSockets(
                                                "Output"
                                            )
                                        else:
                                            orientation = RIGHT
                                        # Recreate output sockets to the number provided
                                        self.block.outputsNum = num_sockets
                                        self.block.makeOutputSockets(
                                            self.block.outputsNum, orientation
                                        )

                                # If self.parameter relates to controlling the names of inport labels on subsystem blocks
                                if self.parameters[i][0] == "inport labels":
                                    # First check if labels are given for the sockets, if not, don't do anything special
                                    if self.parameters[i][2] is not None:
                                        input_length = len(self.parameters[i][2])
                                        if input_length > 0:
                                            # Find number of inputs controlled by nin
                                            found_nin = False
                                            for params in self.parameters:
                                                if params[0] == "nin":
                                                    num_nin_sockets = params[2]
                                                    found_nin = True
                                                    break
                                            # Check if nin parameter was found, if not, return error as we need to know how many sockets to draw
                                            if found_nin == False:
                                                print(
                                                    "Error: Cannot draw InPort labels as no 'nin' parameter was found to know how many sockets to draw."
                                                )
                                            else:
                                                # If nin parameter was found, check if number of given InPort labels matches number of sockets
                                                if input_length != num_nin_sockets:
                                                    bad_socket_labels.append(
                                                        [paramName, paramOptions]
                                                    )
                                                else:
                                                    # If parameter value hasn't changed, don't do anything
                                                    if (
                                                        inputInCompatibleFormat
                                                        == paramVal
                                                    ):
                                                        pass
                                                    else:
                                                        # If the block already has input sockets, grab their orientation (LEFT / RIGHT) then delete
                                                        # Else, draw input socket with default orientation (LEFT) and no need to delete as block has no input sockets
                                                        self.block.input_names = [
                                                            str(j)
                                                            for j in self.parameters[i][
                                                                2
                                                            ]
                                                        ]
                                                        if self.block.inputs:
                                                            for k, socket in enumerate(
                                                                self.block.inputs
                                                            ):
                                                                socket.updateSocketSign(
                                                                    self.block.input_names[
                                                                        k
                                                                    ]
                                                                )

                                    # Otherwise if the parameter value is None or [], then remove all the socket labels for a block if there are any.
                                    elif not self.parameters[i][2]:
                                        if self.block.inputs:
                                            if self.block.input_names:
                                                for socket in self.block.inputs:
                                                    socket.updateSocketSign(None)

                                # If self.parameter relates to controlling the names of outport labels on subsystem blocks
                                if self.parameters[i][0] == "outport labels":
                                    # First check if labels are given for the sockets, if not, don't do anything special
                                    if self.parameters[i][2] is not None:
                                        input_length = len(self.parameters[i][2])
                                        if input_length > 0:
                                            # Find number of outputs controlled by nout
                                            found_nout = False
                                            for params in self.parameters:
                                                if params[0] == "nout":
                                                    num_nout_sockets = params[2]
                                                    found_nout = True
                                                    break
                                            # Check if nout parameter was found, if not, return error as we need to know how many sockets to draw
                                            if found_nout == False:
                                                print(
                                                    "Error: Cannot draw OutPort labels as no 'nout' parameter was found to know how many sockets to draw."
                                                )
                                            else:
                                                # If nout parameter was found, check if number of given OutPort labels matches number of sockets
                                                if input_length != num_nout_sockets:
                                                    bad_socket_labels.append(
                                                        [paramName, paramOptions]
                                                    )
                                                else:
                                                    # If parameter value hasn't changed, don't do anything
                                                    if (
                                                        inputInCompatibleFormat
                                                        == paramVal
                                                    ):
                                                        pass
                                                    else:
                                                        # If the block already has output sockets, grab their orientation (LEFT / RIGHT) then delete
                                                        # Else, draw output socket with default orientation (RIGHT) and no need to delete as block has no output sockets
                                                        self.block.output_names = [
                                                            str(j)
                                                            for j in self.parameters[i][
                                                                2
                                                            ]
                                                        ]
                                                        if self.block.outputs:
                                                            for k, socket in enumerate(
                                                                self.block.outputs
                                                            ):
                                                                socket.updateSocketSign(
                                                                    self.block.output_names[
                                                                        k
                                                                    ]
                                                                )

                                    # Otherwise if the parameter value is None or [], then remove all the socket labels for a block if there are any.
                                    elif not self.parameters[i][2]:
                                        if self.block.outputs:
                                            if self.block.output_names:
                                                for socket in self.block.outputs:
                                                    socket.updateSocketSign(None)

                    # Else the edited value is of the wrong type, display an error message
                    else:
                        # Append the parameter edited, and the required type, as an invalid_input
                        invalid_input.append([paramName, paramType])

                # Else no value was given for that input, display an error message
                else:
                    # Append the parameter edited, and the required type, as an invalid_input
                    invalid_input.append([paramName, paramType])

        # Once all the parameters are sanity checked,
        # If the title has been set to a duplicate name, display a duplicate error message
        if duplicate_title:
            errorMessageText = ""
            errorMessageTitle = "Duplicate Block Title"
            errorMessageText += (
                "A block named '<font><b>"
                + duplicate_title[0]
                + "</font>' already exists, please choose another."
            )
            self.displayPopUpMessage(errorMessageTitle, errorMessageText, "Error")

        # If any parameters have been returned with invalid types, display an invalid type error message
        elif invalid_input:
            errorMessageText = ""
            errorMessageTitle = "Input Types Not Compatible"
            for incompatibleInputs in invalid_input:
                errorMessageText += (
                    "Expected '"
                    + "<font><b>"
                    + incompatibleInputs[0]
                    + "</font>' to be type <font><b>"
                    + incompatibleInputs[1].__name__
                    + "</font>"
                )
                errorMessageText += "<br>"
            self.displayPopUpMessage(errorMessageTitle, errorMessageText, "Error")

        # If any parameters don't meet their option restrictions, display a bad input error message
        elif bad_inputs:
            errorMessageText = ""
            errorMessageTitle = "Input Value Not Allowed"
            for badInput in bad_inputs:
                # Different error message based on type of option
                errorMessageText += (
                    "Parameter '" + "<font><b>" + badInput[0] + "</font>' must be "
                )
                errorMessageText += makeBadInputErrorMsg(badInput[1])
                errorMessageText += "<br>"
            self.displayPopUpMessage(errorMessageTitle, errorMessageText, "Error")

        # If labels are given for InPort, OutPort or SubSystem blocks which don't match the respective nin/nout value for number of sockets, display a bad socket label input error message
        elif bad_socket_labels:
            errorMessageText = ""
            errorMessageTitle = "Inconsistent Number of Given Socket Labels"
            for badSocketLabel in bad_socket_labels:
                # Different error message based on type of option
                errorMessageText += (
                    "Parameter '"
                    + "<font><b>"
                    + badSocketLabel[0]
                    + "</font>' must correspond to number of nin/nout sockets."
                )
            self.displayPopUpMessage(errorMessageTitle, errorMessageText, "Error")

        # Otherwise if there were no issues with updating the block parameters, display a success message, yay!
        else:
            successMessageText = "Successfully updated block parameter values!"
            successMessageTitle = "Success!"
            self.displayPopUpMessage(successMessageTitle, successMessageText, "Success")

        # If a parameter update has changed a value then update the title of the model,
        # to indicate that there is unsaved progress
        if self.paramsWereChanged:
            self.paramsWereChanged = False
            self.block.scene.has_been_modified = True
            self.block.scene.history.storeHistory("Block parameters updated")

        # Finally, notify the GraphicsBlock to update itself, should the number of sockets, or the block
        # height have been called to change
        self.block.grBlock.update()

    @staticmethod
    # -----------------------------------------------------------------------------
    def getSafeValue(inputValue, requiredType, requiredOptions):
        """
        This method takes an input value (which is the value a parameter is being checked
        if it can be updated to), and checks whether it matches an allowable type that
        has been defined for that parameter within the grandchild Block Class. If the
        input value doesn't match the required type, an invalid type str will be returned.
        If the input value does match the required type, it is further checked, whether
        it matches any further restrictions placed onto that parameter from within the
        grandchild Block Class. If the value doesn't meet the criteria of the restrictions,
        a bad input str will be returned. If the input does match the criteria of the
        restriction, it will be converted to the type it must be in and returned.

        :param inputValue: the value which the parameter would be updated to
        :type inputValue: str
        :param requiredType: the value type which is required for this parameter
        :type requiredType: type, determined by the grandchild Block Class
        :param requiredOptions: a list of restrictions placed onto this parameter
        :type requiredOptions: list
        :return: - str (if incompatible type or restriction criteria not met),
                 - requiredType (if compatible type and restrictions are met)
        :rtype: type, determined by the grandchild Block Class
        """

        # -----------------------------------------------------------------------------
        def isValueInOption(value, options):
            """
            This method checks whether the edited parameter value meets the option
            restrictions placed on it by the Block it was defined in. The option
            restrictions consist of a list equivalent to:

            - [["restriction type1" [restrictions]], ["restriction type2" [restrictions]]].

            The edited parameter is checked whether it meets the conditions of 'restrictions'
            for each 'restriction type'.

            :param value: the edited parameter value being checked
            :type value: any
            :param options: the list of restriction options placed on this parameter
            :type options: list
            :return: - value (if meets criteria of placed restriction),
                     - bad_format (if criteria is not met)
            :rtype: - any (if criteria met), - str (if criteria not met)
            """

            # If the parameter has restrictions placed on it
            if options:
                returnValue = "@BadFormat@"
                # For each restriction that is placed onto the parameter
                for option in options:

                    # If the placed restriction is a set of keywords,
                    if option[0] == "keywords":
                        # Check if the given value matches one of those keywords
                        if value.lower() in option[1]:
                            returnValue = value
                            break

                    # If the placed restriction is a range of values
                    elif option[0] == "range":
                        # Check if given value is within that range
                        if option[1][0] <= value <= option[1][1]:
                            returnValue = value
                            break

                    # If the placed restriction are additional accepted types
                    elif option[0] == "type":
                        # Check if the None is one of the accepted types
                        if type(None) in option[1]:
                            # If the value given is None, return None
                            if isinstance(value, str) and value.lower() in ["none"]:
                                returnValue = None
                                break

                        # Check if given value matches any accepted types
                        if type(value) in option[1]:
                            returnValue = value
                            break

                    # If the placed restriction are a set of allowable character symbol
                    elif option[0] == "symbol":
                        # Check if value is a string
                        if isinstance(value, str):
                            # First get the max possible wrong characters in this string
                            num_of_wrong_symbols = len(value)
                            # Check each character within the given value against the set of allowable characters
                            for sign in value:
                                # For every character in the set of allowable characters, reduce the number
                                # of wrong characters by 1
                                if sign in option[1]:
                                    num_of_wrong_symbols -= 1
                            # If all characters within the string match a set of allowable characters
                            if num_of_wrong_symbols == 0:
                                returnValue = value
                                break

                        # Otherwise return badformat
                        else:
                            returnValue = "@BadFormat@"
                            break

                    # If the placed restriction are to the number of elements the parameter can have
                    elif option[0] == "size":
                        # Try to evalute the param value, and catch if it is a string
                        try:
                            # If input isn't a word (is a tuple, list, dict, num) try to evaluate it
                            try:
                                param_val = eval(value)
                            # If a type error is thrown, then the input might already have been evaluated previously
                            except TypeError:
                                param_val = value

                            # Check if the size of parameter is measureable, if not then its an int or float
                            try:
                                param_length = len(param_val)
                                # If the size of the parameter meets one of the allowable sizes (e.g. 0, 2 or 4) then return the value
                                if param_length in option[1]:
                                    returnValue = value
                                else:
                                    returnValue = "@BadFormat@"
                                break
                            # If parameter isn't measureable, return bad format as param is an int/float, and size of a singular number cannot be checked
                            except TypeError:
                                returnValue = "@BadFormat@"
                                break

                        # If input is a word, evaluating it will try to match it to a variable name, which doesn't exist,
                        # so in this case, don't check the size restriction on this parameter value
                        except NameError:
                            pass

                # Return the value that has been set to be returned
                return returnValue

            # Else, if no restrictions are placed on this parameter, return the value
            else:
                return value

        try:
            # If input must be string, only strings can be accepted
            if issubclass(requiredType, str):
                # If the input is not a number, but an acceptable string
                if isinstance(inputValue, str):

                    # Check if no input has been given
                    if len(inputValue) == 0:
                        return "@InvalidType@"
                    else:
                        # return isValueInOption(inputValue.lower(), requiredOptions)
                        return isValueInOption(inputValue, requiredOptions)

                        # # Check if the input is made up of normal characters [a-zA-z0-9]
                        # if inputValue.isalnum():
                        #     return isValueInOption(inputValue.lower(), requiredOptions)
                        #
                        # # Otherwise the input has special characters (=,-,+,*,/,:,etc)
                        # else:
                        #     # Check if string contains '=', as this is restricted to variable name definitions, and is not allowed for regular strings
                        #     if "=" in inputValue:
                        #         outcome = isValueInOption(inputValue, requiredOptions)
                        #         if outcome == "@BadFormat@":
                        #             return outcome
                        #         else:
                        #             return "@InvalidType@"
                        #     else:
                        #         return isValueInOption(inputValue.lower(), requiredOptions)
                else:
                    return "@InvalidType@"

            # If input must be bool, only booleans can be accepted
            elif issubclass(requiredType, bool):
                # All input starts off as text, so True/False will be 'True'/'False'
                if isinstance(inputValue, str):
                    # Check if the string matches true/false, and return accordingly
                    if inputValue in ["True", "true"]:
                        return True
                    elif inputValue in ["False", "false"]:
                        return False
                    # Otherwise if string is None, check if this boolean parameter allows that type
                    elif inputValue.lower() in ["none"]:
                        return isValueInOption(inputValue.lower(), requiredOptions)
                    else:
                        return "@InvalidType@"
                else:
                    return "@InvalidType@"

            # If input must be int, floats can be converted to int
            elif issubclass(requiredType, int):
                # Try applying int() to the input value, if possible, check restrictions on value
                try:
                    requiredType(inputValue)
                    return isValueInOption(requiredType(inputValue), requiredOptions)
                except ValueError:
                    # If applying int() doesn't work but value is None, check if this is an allowable type
                    if inputValue.lower() in ["none"]:
                        return isValueInOption(inputValue, requiredOptions)
                    else:
                        return "@InvalidType@"

            # If input must be float, int can be converted to float
            elif issubclass(requiredType, float):
                # All inputValues come in as a string, so first check if this evaluated string is a float
                try:
                    evaluated_value = eval(inputValue)

                    # If value can be evaluated safely, check if the value is an instance of float
                    if isinstance(evaluated_value, float):
                        # If so, check further restrictions on this parameter, return the outcome
                        return isValueInOption(evaluated_value, requiredOptions)

                    # If value is not a float, but is none, check if this is an allowable type
                    elif inputValue.lower() in ["none"]:
                        return isValueInOption(inputValue, requiredOptions)

                    # If value is not a float, and None is not allowed, return invalid type
                    else:
                        try:
                            float_value = float(evaluated_value)
                            return isValueInOption(float_value, requiredOptions)
                        except (ValueError, TypeError):
                            return "@InvalidType@"

                # If any exceptions arise while trying to evaluate, then the value is incorrect
                except:
                    return "@InvalidType@"

            # If input must be a list, only list can be accepted
            elif (
                issubclass(requiredType, list)
                or issubclass(requiredType, tuple)
                or issubclass(requiredType, dict)
            ):
                try:
                    # If the input value can be evaluated as a list, tuple or dict, check restrictions on value
                    ast.literal_eval(inputValue)
                    if inputValue.lower() in ["none"]:
                        return isValueInOption(inputValue, requiredOptions)
                    else:
                        return isValueInOption(
                            ast.literal_eval(inputValue), requiredOptions
                        )
                except ValueError:
                    return "@InvalidType@"

            # If input can be of type 'any', allow any value to be saved. This will also process the 'callable' type, in the same way.
            elif issubclass(requiredType, type(any)):
                # Return the outcome of check this input against any restrictions for this parameter
                # Type any or callable should be allowed to pass through a string
                return isValueInOption(inputValue, requiredOptions)

        except Exception as e:
            print(e)
            print(
                "Fatal Error: Recent changes to a parameter have caused an unforseen error.\nKnown info about parameter causing the error: given value ->",
                inputValue,
                "expected type ->",
                requiredType,
                "parameter restrictions ->",
                requiredOptions,
            )
            return "@InvalidType@"
