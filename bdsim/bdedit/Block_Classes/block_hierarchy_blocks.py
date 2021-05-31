from bdedit.block import INPORTBlock, OUTPORTBlock, SUBSYSTEMBlock, block

@block
# Child class 1: INPORT Block
class INPORT(INPORTBlock):
    def __init__(self, scene, window, hierarchy_file=None, nout=1, name="INPORT Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = self.__class__.__name__

        self.variables = [
            ["hierarchy_file", str, hierarchy_file, [["type", [type(None), str]]]],
            ["No. of outputs", int, nout, [["range", [0, 1000]]]]
        ]

        self.icon = None  # ":/Icons_Reference/Icons/dintegrator.png"
        self.width = 100
        self.height = 150

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 2: OUTPORT Block
class OUTPORT(OUTPORTBlock):
    def __init__(self, scene, window, hierarchy_file=None, nin=1, name="OUTPORT Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = self.__class__.__name__

        self.variables = [
            ["hierarchy_file", str, hierarchy_file, [["type", [type(None), str]]]],
            ["No. of inputs", int, nin, [["range", [0, 1000]]]]
        ]

        self.icon = None  # ":/Icons_Reference/Icons/dlti_siso.png"
        self.width = 100
        self.height = 150

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 3: SUBSYSTEM Block
class SUBSYSTEM(SUBSYSTEMBlock):
    def __init__(self, scene, window, hierarchy_file=None, name="SUBSYSTEM Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = self.__class__.__name__

        self.variables = [
            ["hierarchy_file", str, hierarchy_file, [["type", [type(None), str]]]]
        ]

        self.icon = None  # ":/Icons_Reference/Icons/dlti_ss.png"
        self.width = 200
        self.height = 150

        self._createBlock(self.inputsNum, self.outputsNum)