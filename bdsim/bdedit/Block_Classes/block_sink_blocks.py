from bdedit.block import SinkBlock, block


@block
# Child class 1: Print Block
class Print(SinkBlock):
    def __init__(self, scene, window, fmt=None, name: str="Print Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = self.__class__.__name__

        self.variables = [
            ["Format", str, fmt, [["type", [type(None), str]]]]
        ]

        self.icon = ":/Icons_Reference/Icons/print.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 2: Stop Block
class Stop(SinkBlock):
    def __init__(self, scene, window, stop=None, name="Stop Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = self.__class__.__name__

        # This should be type TYPE ??
        self.variables = [
            ["Stop", str, stop, [["type", [type(None), str]]]],
        ]

        self.icon = ":/Icons_Reference/Icons/stop.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 3: Scope Block
class Scope(SinkBlock):
    def __init__(self, scene, window, nin=None, styles=None, scale='auto', labels=None, grid=True, name="Scope Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = self.__class__.__name__

        # How should these be type checked?
        self.variables = [
            ["No. of inputs", int, nin, [["range", [0, 1000]], ["type", [type(None), int]]]],
            ["Styles", str, styles, [["type", [type(None), str]]]],
            ["Scale", str, scale, []],
            ["Labels", list, labels, [["type", [type(None), list]]]],
            ["Grid", list, grid, [["type", [type(None), list]]]]
        ]

        self.icon = ":/Icons_Reference/Icons/scope.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)


