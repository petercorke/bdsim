from bdedit.block import FunctionBlock, block
import math


@block
# Child class 1: Clip Block
class Clip(FunctionBlock):
    def __init__(self, scene, window, minimum=-math.inf, maximum=math.inf, name="Clip Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)
        
        self.block_type = self.__class__.__name__

        self.variables = [
            ["Min", float, minimum, [["range", [-math.inf, math.inf]]]],
            ["Max", float, maximum, [["range", [-math.inf, math.inf]]]]
        ]

        self.icon = ":/Icons_Reference/Icons/clip.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 2: Function Block
class Function(FunctionBlock):
    def __init__(self, scene, window, function="Provide Function?", nin=1, nout=1, dictionary=False, args=(), kwargs={}, name="Function Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)
        
        self.block_type = self.__class__.__name__

        # How to sanity check function input?
        self.variables = [
            ["Function", str, function, []],
            ["No. of inputs", int, nin, [["range", [0, 1000]]]],
            ["No. of outputs", int, nout, [["range", [0, 1000]]]],
            ["Dict", bool, dictionary, []],
            ["Args", tuple, args, []],
            ["Kwargs", dict, kwargs, []]
        ]

        # Will need to be changed for param to update nin and nout
        # this will only set nin and nout on button spawn
        self.inputsNum = nin
        self.outputsNum = nout

        self.icon = ":/Icons_Reference/Icons/function.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 3: Gain Block
class Gain(FunctionBlock):
    def __init__(self, scene, window, gain=0, premul=False, name="Gain Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)
        
        self.block_type = self.__class__.__name__

        self.variables = [
            ["Gain", float, gain, []],
            ["Premul", bool, premul, []]
        ]

        self.icon = ":/Icons_Reference/Icons/gain.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 4: Interpolate Block
class Interpolate(FunctionBlock):
    def __init__(self, scene, window, x_array=None, y_array=None, xy_array=None, time=False, kind='linear', name="Interpolate Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)
        
        self.block_type = self.__class__.__name__

        self.variables = [
            ["X", tuple, x_array, [["type", [type(None), tuple]]]],
            ["Y", tuple, y_array, [["type", [type(None), tuple]]]],
            ["XY", list, xy_array, [["type", [type(None), list]]]],
            ["Time", bool, time, []],
            ["Kind", str, kind, [["keywords", ["linear", "nearest neighbor", "cubic spline", "shape-preserving", "biharmonic", "thin-plate spline"]]]]
        ]

        self.icon = ":/Icons_Reference/Icons/interpolate.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 5: Prod Block
class Prod(FunctionBlock):
    def __init__(self, scene, window, ops="**", matrix=False, name="Prod Block", pos=(0,0)):
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)
        
        self.block_type = self.__class__.__name__

        self.variables = [
            ["Operations", str, ops, [["signs", ["*", "/"]]]],
            ["Matrix", bool, matrix, []]
        ]

        # this will need to be updated from param window
        # Will also need to draw the sockets differently based on sign
        self.inputsNum = len(ops)

        self.icon = None  # ":/Icons_Reference/Icons/prod.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 6: Sum Block
class Sum(FunctionBlock):
    def __init__(self, scene, window, signs='++', angles=False, name="Sum Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)
        
        self.block_type = self.__class__.__name__

        self.variables = [
            ["Signs", str, signs, [["signs", ["+", "-"]]]],
            ["Angles", bool, angles, []]
        ]

        # this will need to be updated from param window
        # Will also need to draw the sockets differently based on sign
        self.inputsNum = len(signs)

        self.icon = None  # ":/Icons_Reference/Icons/sum.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)
