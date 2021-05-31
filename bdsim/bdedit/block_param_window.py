from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPixmap

from bdedit.Icons import *
import ast

LEFT = 1
RIGHT = 3

PLUS = "+"
MINUS = "-"
MULTIPLY = "*"
DIVIDE = "/"


DEBUG = False


class ParamWindow(QWidget):
    def __init__(self, block, parent=None):
        super().__init__(parent)
        self.block = block
        self.variables = self.block.variables
        self.parameter_values = []
        self.layout = QVBoxLayout()

        self._parameter_line_width = 150
        self._yOffset = 20
        self._width = 300 * self.block.window.scale
        self._xOffset = self.block.scene.sceneWidth()//2 - self._width
        self._height = self.block.scene.sceneHeight()//2 - self._yOffset
        self.setFixedWidth(self._width)

        self.initUI()
        self.buildParamWindow()

    def initUI(self):
        self.layout.addWidget(QLabel('<font size=8><b>Parameter Window</font>'))
        self.layout.setAlignment(Qt.AlignTop)
        self.setGeometry(QRect(0, 0, self._width, self._height))
        self.move(self._xOffset, self._yOffset)
        self.setAutoFillBackground(True)
        self.setLayout(self.layout)

    def closeQMessageBox(self):
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

    def displayPopUpMessage(self, title, text, messageType):
        def closeMessage():
            self.timer.stop()
            self.message.close()

        self.closeQMessageBox()

        # Create a widget to wrap the QMessageBox into, that it may be displayed in the ParamWindow
        self.popUp = QWidget()
        self.popUp.layout = QVBoxLayout()
        self.message = QMessageBox(self)

        # Manually set the width of the QMessageBox layout to control text wrapping
        # The layout is a grid, so setting width of 1st row/column cell will set width of the widget
        self.message.item = self.message.layout().itemAtPosition(0, 1)
        self.message.item.widget().setFixedWidth(self.width()-100)

        # If an error message - critical icon, if success message - green tick icon
        if messageType == "Error":
            self.message.setIcon(QMessageBox.Critical)
            message_duration = 5
        elif messageType == 'Success':
            self.message.setIconPixmap(QPixmap(":/Icons_Reference/Icons/Success_Icon.png"))
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
        self.timer.setInterval(message_duration*1000)
        self.timer.timeout.connect(closeMessage)
        self.timer.start()

    def buildParamWindow(self):
        # Make the first row, which contains two labels for the block's type
        self.row1 = QWidget()
        self.row1.layout = QHBoxLayout()
        self.block_type_label = QLabel('<font size=4><b>Block Type: </font>')
        self.block_type = QLabel('<font size=4>' + str(self.block.block_type) + ' Block </font>')
        self.block_type.setFixedWidth(self._parameter_line_width)
        self.row1.layout.addWidget(self.block_type_label, alignment=Qt.AlignCenter)
        self.row1.layout.addWidget(self.block_type, alignment=Qt.AlignCenter)

        self.row1.setLayout(self.row1.layout)
        self.layout.addWidget(self.row1)

        # Make the second row, which contains the label and editable line for the block's title
        self.row2 = QWidget()
        self.row2.layout = QHBoxLayout()

        self.title_label = QLabel('<font size=4><b>Title: </font>')
        self.title_line = QLineEdit(self.block.title)
        self.title_line.setFixedWidth(self._parameter_line_width)
        self.row2.layout.addWidget(self.title_label, alignment=Qt.AlignCenter)
        self.row2.layout.addWidget(self.title_line)

        self.row2.setLayout(self.row2.layout)
        self.layout.addWidget(self.row2)

        for variable in self.variables:
            self.row_x = QWidget()
            self.row_x.layout = QHBoxLayout()

            self.label = QLabel('<font size=3><b>'+variable[0]+": "+'</font>')
            self.line = QLineEdit(str(variable[2]))
            self.line.setFixedWidth(self._parameter_line_width)
            self.parameter_values.append(self.line)
            self.row_x.layout.addWidget(self.label, alignment=Qt.AlignCenter)
            self.row_x.layout.addWidget(self.line)

            self.row_x.setLayout(self.row_x.layout)
            self.layout.addWidget(self.row_x)

        self.update_button = QPushButton('Update Parameters')
        self.update_button.clicked.connect(self.updateBlockParameters)
        self.layout.addWidget(self.update_button)

    def updateBlockParameters(self):

        def makeBadInputErrorMsg(options):
            # Start with an empty message
            message = ""
            # Num_options is the number of lists (of accepted keywords, types, range) inside the option list
            num_options = len(options)
            for option in options:
                if option[0] == "keywords":
                    message += "one of <font><b>" + str(option[1]) + "</font>"
                elif option[0] == "range":
                    message += "a value between <font><b>" + str(option[1][0]) + "</font> and <font><b>" + str(option[1][1]) + "</font>"
                elif option[0] == "type":
                    typeString = []
                    for optionType in option[1]:
                        typeString.append(optionType.__name__)
                    message += "of type <font><b>" + str(typeString) + "</font>"
                elif option[0] == "signs":
                    message += "a combination of <font><b>" + str(option[1]) + "</font>"

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

        # Iterator for loop
        i = -1
        invalid_input, bad_inputs = [], []

        for [varName, varType, varVal, varOptions] in self.variables:
            i += 1
            inputValue = self.parameter_values[i].text()

            # If a value has been provided for that variable, perform sanity checking on that input
            if inputValue:
                inputInCompatibleFormat = self.getSafeValue(inputValue, varType, varOptions)
                if DEBUG: print("varName, varType, varVal - inputValue, type, compatible", [varName, varType, varVal, '-', inputValue, type(inputValue), inputInCompatibleFormat])
                if inputInCompatibleFormat != "@InvalidType@":
                    if inputInCompatibleFormat == "@BadFormat@":
                        bad_inputs.append([varName, varOptions])
                    else:
                        # Set varVal equal to input
                        self.variables[i][2] = inputInCompatibleFormat

                        # If self.variable relates to controlling the number of inputs a block has
                        if self.variables[i][0] in ["No. of inputs", "Operations", "Signs"]:
                            # Grab the number of required input sockets
                            if self.variables[i][0] == "No. of inputs":
                                num_sockets = self.variables[i][2]
                            else:
                                num_sockets = len(self.parameter_values[i].text())
                            # Don't do anything, if the provided No. input sockets matches the number the block already has,
                            # or if the signs (+,-,*,/) for the block haven't changed
                            if len(self.block.inputs) == num_sockets and inputInCompatibleFormat == varVal:
                                pass
                            else:
                                # If the block already has input sockets, grab their orientation then delete
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
                                self.block.makeInputSockets(self.block.inputsNum, orientation)

                        # If self.variable relates to controlling the number of outputs a block has
                        if self.variables[i][0] in ["No. of outputs"]:
                            # Grab number of required output sockets
                            num_sockets = self.variables[i][2]
                            # If provided number of output sockets matches the number the block already has, don't do anything
                            if len(self.block.outputs) == num_sockets:
                                pass
                            else:
                                # If the block already has output sockets, grab their orientation then delete
                                # Else, draw output socket with default orientation (RIGHT) and no need to delete as block has no output sockets
                                if self.block.outputs:
                                    orientation = self.block.outputs[0].position
                                    # Remove all current output sockets
                                    self.block.outputs[0].removeSockets("Output")
                                else:
                                    orientation = RIGHT
                                # Recreate output sockets to the number provided
                                self.block.outputsNum = num_sockets
                                self.block.makeOutputSockets(self.block.outputsNum, orientation)

                else:
                    invalid_input.append([varName, varType])

            # Else no value was given for that input, display an error message
            else:
                invalid_input.append([varName, varType])

        if duplicate_title:
            errorMessageText = ""
            errorMessageTitle = "Duplicate Block Title"
            errorMessageText += "A block named '<font><b>" + duplicate_title[0] + "</font>' already exists, please choose another."
            self.displayPopUpMessage(errorMessageTitle, errorMessageText, "Error")

        elif invalid_input:
            errorMessageText = ""
            errorMessageTitle = "Input Types Not Compatible"
            for incompatibleInputs in invalid_input:
                errorMessageText += "Expected '" + "<font><b>" + incompatibleInputs[0] + "</font>' to be type <font><b>" + incompatibleInputs[1].__name__ + "</font>"
                errorMessageText += "<br>"
            self.displayPopUpMessage(errorMessageTitle, errorMessageText, "Error")

        elif bad_inputs:
            errorMessageText = ""
            errorMessageTitle = "Input Value Not Allowed"
            for badInput in bad_inputs:
                # Different error message based on type of option
                errorMessageText += "Variable '" + "<font><b>" + badInput[0] + "</font>' must be "
                errorMessageText += makeBadInputErrorMsg(badInput[1])
                errorMessageText += "<br>"
            self.displayPopUpMessage(errorMessageTitle, errorMessageText, "Error")

        else:
            successMessageText = "Successfully updated block parameter values!"
            successMessageTitle = "Success!"
            self.displayPopUpMessage(successMessageTitle, successMessageText, "Success")

        self.block.grBlock.update()

    @staticmethod
    def getSafeValue(inputValue, requiredType, requiredOptions):
        def isValueInOption(value, options):
            #print("val, val type, op:", [value, type(value), options])
            if options:
                returnValue = "@BadFormat@"
                for option in options:
                    if option[0] == "keywords":
                        if value.lower() in option[1]:
                            returnValue = value; break
                    elif option[0] == "range":
                        if option[1][0] <= value <= option[1][1]:
                            returnValue = value; break
                    elif option[0] == "type":
                        if type(None) in option[1]:
                            if isinstance(value, str) and value.lower() in ['none']:
                                returnValue = None
                                break
                        if type(value) in option[1]:
                            returnValue = value
                            break
                    elif option[0] == "signs":
                        num_of_wrong_signs = len(value)
                        for sign in value:
                            if sign in option[1]:
                                num_of_wrong_signs -= 1
                        if num_of_wrong_signs == 0:
                            returnValue = value; break
                return returnValue
            else:
                return value

        #print('input value, req type, options:', [inputValue, requiredType, requiredOptions])

        # If input must be string, only strings can be accepted
        if issubclass(requiredType, str):
            # If input can be converted to float (or int), cannot be accepted
            try:
                float(inputValue); return "@InvalidType@"
            except ValueError:
                if isinstance(inputValue, str):
                    if len(inputValue) == 0: return "@InvalidType@"
                    elif inputValue.lower() in ["none"]: return None
                    else: return isValueInOption(inputValue.lower(), requiredOptions)
                else: return "@InvalidType@"

        # If input must be bool, only booleans can be accepted
        elif issubclass(requiredType, bool):
            if isinstance(inputValue, str):
                if inputValue in ["True", "true"]: return True
                elif inputValue in ["False", "false"]: return False
                elif inputValue.lower() in ["none"]: return isValueInOption(requiredType(inputValue), requiredOptions)
                else: return "@InvalidType@"
            else: return "@InvalidType@"

        # If input must be int, floats can be converted to int
        elif issubclass(requiredType, int):
            try: requiredType(inputValue); return isValueInOption(requiredType(inputValue), requiredOptions)
            except ValueError:
                if inputValue.lower() in ["none"]: return isValueInOption(inputValue, requiredOptions)
                else: return "@InvalidType@"

        # If input must be float, int can be converted to float
        elif issubclass(requiredType, float):
            try: requiredType(inputValue); return isValueInOption(requiredType(inputValue), requiredOptions)
            except ValueError:
                if inputValue.lower() in ["none"]: return isValueInOption(inputValue, requiredOptions)
                else: return "@InvalidType@"

        # If input must be a list, only list can be accepted
        elif issubclass(requiredType, list) or issubclass(requiredType, tuple) or issubclass(requiredType, dict):
            try:
                # If the input value can be evaluated as a list, tuple or dict, check if appropriate input
                ast.literal_eval(inputValue)
                if isinstance(ast.literal_eval(inputValue), requiredType): return isValueInOption(ast.literal_eval(inputValue), requiredOptions)
                elif inputValue.lower() in ["none"]: return isValueInOption(inputValue, requiredOptions)
                else: return "@InvalidType@"
            except ValueError: return "@InvalidType@"

        # If input can be of type any, allow any value to be saved
        elif issubclass(requiredType, type(any)):
            try:
                # If the input can be evaluated, check if appropriate input
                ast.literal_eval(inputValue); return ast.literal_eval(inputValue)
            except ValueError:
                if inputValue.lower() in ["none"]: return isValueInOption(inputValue, requiredOptions)
                else: return "@InvalidType@"
