import re
import inspect
import copy
import numpy as np
import importlib.util
from pathlib import Path

#import bdsim
#import roboticstoolbox

#from bdsim.bdedit.block import blockname, blocklist, SinkBlock, SourceBlock, FunctionBlock, TransferBlock, DiscreteBlock, GraphicBlock
from bdsim.bdedit.block import blockname, blocklist, Block
from examples import docstring_parser as parser

def import_blocks(scene, window):
# def import_blocks():

    block_list = parser.docstring_parser()
    block_library = []
    imported_block_groups = []

    for i, block in enumerate(block_list.items()):
        #if i == 0:
            # blocks is a dic of tuples
            # (block_type, {block_docstring_data})

            block_type = block[0].upper()   # Block type
            block_ds = block[1]     # Block docstring

            block_name = block_type.lower().capitalize() + " Block"
            block_classname = block_ds["classname"]
            block_icon = ":/Icons_Reference/Icons/" + block_type.lower() + ".png"
            block_parentclass = block_ds["blockclass"]
            block_path = block_ds["path"]

            # Grab number of input/output sockets for blocks, and whether those number of sockets are variable
            block_inputsNum = block_ds["nin"]
            block_outputsNum = block_ds["nout"]
            block_varinputs = block_ds["varinputs"]

            # Reconstruct URL from block type and path
            block_group = block_ds["module"].split('.')[-1]
            try:
                block_url = block_ds["url"]
            except KeyError:
                block_url = None
            #block_group = re.findall(r'blocks\\([a-z]*).py', str(block_path))[0]
            #block_url = "https://petercorke.github.io/bdsim/bdsim.blocks.html?highlight=" + block_type.lower() + "#bdsim.blocks." + block_group[0] + "." + block_type.capitalize() + ""

            block_parameters = []  # Once name, type, value, restrictions are extracted, this will be populated


            for param in block_ds["params"].items():
                # Extract parameter name
                param_name = param[0]

                # Extract parameter type
                # Split string based on white spaces
                # if one type - no white spaces
                # if multiple types - several white spaces
                try:
                    param_type_docstring = param[1][0].split()

                    # Remove any left over commas or dashes (shouldn't be needed for type)
                    for i, item in enumerate(param_type_docstring):
                        param_type_docstring[i] = item.strip(',-.')

                    # 1st value should be the type, with following values being either
                    # * other accepted types,
                    # * the optional keyword (also indicates if value should have a default),
                    # * or human readable string

                    # 1. go through each word in the split string, searching for likely terms (sequence, string, etc)
                    # 2. match found strings to their desired interpretation, sequence = list/tuple/range, string = str
                    # 3. create list of strings matched to required types
                    # 4. evaluate and assign first item from that list of types, as the param type
                    # 5. create list for holding found restrictions

                    # 5.
                    param_restrictions = []

                    # ---------------------------------------------------------------------------------------
                    # Section for extracting parameter type information (and restriction if relating to type)
                    # ---------------------------------------------------------------------------------------

                    # 3.
                    found_types = []
                    found_size_restrictions = []
                    found_range_restrictions = []
                    found_symbol_restrictions = []
                    found_keyword_restrictions = []
                    unexpected_format = []

                    # 1.
                    for item in param_type_docstring:
                        # Go through and try to evaluate the first type, if it works assign that as the param type
                        try:
                            # 2.
                            param_type = eval(item)

                            # Check first if evaluated item is an int (we expect to see a string, so throw error)
                            if isinstance(param_type, int) or isinstance(param_type, float):
                                unexpected_format.append(item)

                            # Otherwise, if item is in the form of a string, append that value to list of found types
                            else:
                                found_types.append(param_type)

                        # If evaluation fails - most likely human readible string instead of actual type
                        except:
                            regex_search = re.findall(r'array_like\([0-9]\)|array_like', item)

                            # If current word is array_like
                            if regex_search:

                                # Search each array_like word found in type docstring, looking for size restriction
                                for match in regex_search:
                                    element_restriction_match = re.findall(r'[0-9]', match)

                                    # If an element size restriction has been detected
                                    if element_restriction_match:

                                        # If size restriction is already entered, this will stop it from being entered multiple times
                                        restriction_to_insert = eval(element_restriction_match[0])
                                        if not restriction_to_insert in found_size_restrictions:
                                            found_size_restrictions.append(restriction_to_insert)

                                # If array_like has already been added, this will stop it from being entered multiple times
                                type_to_insert = type(np.array([]))
                                if not type_to_insert in found_types:
                                    found_types.append(type_to_insert)

                            elif item in ['string']:
                                found_types.append(str)

                            elif item in ['sequence', 'string']:
                                # 2.
                                found_types.append(list)
                                found_types.append(tuple)

                            elif item in ['optional', ' or ', ' of ', ' is ']:
                                # item is for human readability, ignore
                                # how should types where for eg. list of strings, list of x, be dealt with?
                                pass

                            else:
                                unexpected_format.append(item)

                    # 4.
                    # If any known types have been found, set the parameter type
                    if found_types:
                        # Extract first detected type as the default type
                        param_type = found_types[0]
                    else:
                        param_type = "Unexpected format for: type definition"

                    # -----------------------------------------------------------------------------------------
                    # Section for extracting parameter value information (and restriction if relating to value)
                    # -----------------------------------------------------------------------------------------

                    param_value = None

                    # Extract parameter value information
                    param_value_docstring = param[1][1].split()

                    # String docstring of commas
                    for i, item in enumerate(param_value_docstring):
                        param_value_docstring[i] = item.strip(',.')

                    # Parse the docstring ignoring words until finding a known "defaults to:"
                    for i in range(0, len(param_value_docstring) - 1):

                        if param_value_docstring[i] in ['range']:
                            # This parameter must be within a certain range, extract the provided range values
                            # These should be in the form of "range [a,b]"
                            # Hence we can check if evaluating the word after range gives a list of length 2

                            try:
                                next_item = eval(param_value_docstring[i + 1])

                                if isinstance(next_item, list) and len(next_item) == 2:
                                    # Add a,b of range to restriction items
                                    found_range_restrictions.append(next_item[0])
                                    found_range_restrictions.append(next_item[1])

                                    # Either not list or greater than 2, so unexpected format, return error
                                    found_range_restrictions.append("Unexpected format for: range restriction")
                            except:
                                # Word cannot be evaluated
                                found_range_restrictions.append("Unexpected format for: range restriction")

                        if param_value_docstring[i] in ['accepted'] and param_value_docstring[i + 1] in ['characters:']:
                            # Value is restricted to being certain characters, these are seperated by the word 'or'
                            # Iterate through every 2nd value after 'accepted characters:' (seperated by 'or')
                            for j in range(i + 2, len(param_value_docstring), 2):
                                # If special character (.isalnum() returns False), append to list of detected signs
                                if not param_value_docstring[j].isalnum():
                                    found_symbol_restrictions.append(param_value_docstring[j])

                                # If the next value isn't 'or', we have reached end of character list
                                if param_value_docstring[j + 1] not in ['or']:
                                    break

                        if param_value_docstring[i] in ['defaults'] and param_value_docstring[i + 1] in ['to']:
                            # Value only has 1 default, which should follow after the word to
                            # Try to evaluate value, if successful, this is some form of non string
                            try:
                                param_value = eval(param_value_docstring[i + 2])

                            # If unsuccesful, trying to eval a string, so set default value as str instead
                            except NameError:
                                param_value = param_value_docstring[i + 2]


                        elif param_value_docstring[i] in ['one'] and param_value_docstring[i + 1] in ['of:']:
                            # Value has list of possible options, parse list to find value after which is '[default]'
                            found_default_value = False

                            for j in range(i + 2, len(param_value_docstring)):
                                # Append found value (if not '[default]', to list of keyword restrictions)
                                if param_value_docstring[j] not in ['[default]']:
                                    found_keyword_restrictions.append(param_value_docstring[j].strip("'"))

                                # Check if this is the default value, (next value should say '[default]')
                                if not found_default_value and param_value_docstring[j + 1] in ['[default]']:
                                    # Default value found in list of possible values

                                    # Try to evaluate value, if successful, then some form of non string
                                    try:
                                        param_value = eval(param_value_docstring[j])

                                    # If unsuccesful, trying to eval a string, so set default value as str instead
                                    except NameError:
                                        param_value = param_value_docstring[j]

                                    found_default_value = True

                            # If no defualt value was found, return error
                            if not found_default_value:
                                param_value = "Unexpected format for: multiple values"

                            # Important break!
                            # Once the inner loop has gone through the remainder of the words from the docstring, and
                            # found the default value and the other keywords, we need to break out of the outer loop, to
                            # continue to the next parameter
                            break

                    # If any keyword restrictions were found
                    if found_keyword_restrictions:
                        restriction = ["keyword"]
                        # Append the found keyword restrictions into the restriction
                        restriction.append(found_keyword_restrictions)
                        param_restrictions.append(restriction)

                    # If any range restrictions were found
                    if found_range_restrictions:
                        restriction = ["range"]
                        # Append the found range restrictions into the restriction
                        restriction.append(found_range_restrictions)
                        param_restrictions.append(restriction)

                    # If any size restrictions were found
                    if found_size_restrictions:
                        restriction = ["size"]
                        # Append the found size restrictions into the restriction
                        restriction.append(found_size_restrictions)
                        param_restrictions.append(restriction)

                    # If any symbol restrictions were found
                    if found_symbol_restrictions:
                        restriction = ["symbol"]
                        # Append the found symbol restrictions into the restriction
                        restriction.append(found_symbol_restrictions)
                        param_restrictions.append(restriction)

                    # Check if parameter value is None, if so, add NoneType to type restriction
                    if param_value is None:
                        # If Nonetype has already been added, this will stop it from being entered multiple times
                        type_to_insert = type(None)
                        if not type_to_insert in found_types:
                            found_types.append(type_to_insert)

                    # If several types for a parameter are detected, create a parameter restriction accordingly
                    if len(found_types) > 1 or type(None) in found_types:
                        found_type_restrictions = []
                        for item in found_types:
                            found_type_restrictions.insert(0, item)
                        restriction = ["type"]
                        restriction.append(found_type_restrictions)

                        param_restrictions.append(restriction)

                    # Using the extracted information, contstruct the parameter list
                    block_parameters.append([param_name, param_type, param_value, param_restrictions])

                except:
                    print("@@@@@@@ Fatal error: Unable to parse parameter info, param not constructed " + block_type + ": -> " +param_name + ". @@@@@@")

            if not block_ds["params"]:
                print("\n\nThis block has no parameters: ", block_type, " param_docstring: ", block_ds["params"])
                block_parameters = [["dummy_parameter", str, None, []]]


            # -----------------------------------------------------------------------------------------------------
            # Section for importing block class from its module, and assigning to it the extracted information
            # -----------------------------------------------------------------------------------------------------

            try:
                def __block_init__(self):

                    Block.__init__(self, scene, window)

                    self.title = copy.copy(self.title)
                    self.block_type = copy.copy(self.block_type)
                    # self.block_group = block_group
                    self.parameters = copy.deepcopy(self.parameters)
                    self.inputsNum = copy.copy(self.inputsNum)
                    self.outputsNum = copy.copy(self.outputsNum)
                    self.icon = copy.copy(self.icon)
                    self.block_url = copy.copy(self.block_url)
                    # self.position = (0,0)
                    self.width = copy.copy(self.width)
                    self.height = copy.copy(self.height)

                    self._createBlock(self.inputsNum, self.outputsNum)


                # Dynamically create class for this block
                # Assign the extracted block variables to this block
                new_block_class = type(block_classname, (Block,), {
                    "__init__": __block_init__,
                    "numInputs": lambda self: self.inputsNum,
                    "numOutputs": lambda self: self.outputsNum,
                    "title": block_name,
                    "block_type": block_type,
                    # "block_group": block_class,
                    "parameters": block_parameters,
                    "inputsNum": block_inputsNum,
                    "outputsNum": block_outputsNum,
                    "icon": block_icon,
                    "block_url": block_url,
                    "width": 100,
                    "height": 100
                })

                # Add this block to blocklist
                blocklist.append(new_block_class)

                # If this block belongs to a new group of blocks, for which a list hasn't been made yet
                # then make a list in the block_library, to hold those blocks
                if block_parentclass not in imported_block_groups:
                    imported_block_groups.append(block_parentclass)
                    block_library.append([block_parentclass, []])

                # Add this block to the group of blocks it belongs to
                for i, group in enumerate(block_library):
                    # 1st element of group, will always be the group name (sinks, sources, functions, etc)
                    if group[0] == block_parentclass:
                        block_library[i][1].append([blockname(new_block_class), new_block_class])
                        break

                # -----------------------------------------------------------------------------------------------

                # # If this block belongs to a new group of blocks, for which a list hasn't been made yet
                # # then make a list in the block_library, to hold those blocks
                # if block_group not in imported_block_groups:
                #     imported_block_groups.append(block_group)
                #     block_library.append([block_group, []])
                #
                # # Add this block to the group of blocks it belongs to
                # for i, group in enumerate(block_library):
                #     # 1st element of group, will always be the group name (sinks, sources, functions, etc)
                #     if group[0] == block_group:
                #         #block_library[i][1].append([blockname(new_block_class), new_block_class, block_path])
                #         block_library[i][1].append([blockname(new_block_class), new_block_class])
                #         break

            except KeyError:
                print("Error: attempted to create a block class that isn't supported. Attempted class type: ", block_classname)

    return block_library

# # Print all sub-lists in block_library list
# [print(item) for item in import_blocks()]

# # Print all imported blocks
# for item in import_blocks():
#     print("block group:", item[0])
#     for block in item[1]:
#         print(block[0])
#     print()

# # Print certain class attributes from all imported blocks
# for item in import_blocks():
#     print("block group:", item[0])
#     for block in item[1]:
#         print("     block:", block[1].block_type)
#         print("          title:", block[1].title)
#         print("          icon path:", block[1].icon)
#         print("          nin:", block[1].inputsNum)
#         print("          nout:", block[1].outputsNum)
#         print("          width:", block[1].width)
#         print("          params:", block[1].parameters)
#         print()
#     print()