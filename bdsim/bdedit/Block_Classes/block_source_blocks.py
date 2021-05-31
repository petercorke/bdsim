from bdedit.block import SourceBlock, block


@block
# Child class 1: Constant Block
class Constant(SourceBlock):
    def __init__(self, scene, window, value=None, name="Constant Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = self.__class__.__name__

        self.variables = [
            ["Value", type(any), value, [["type", [type(None), type(any)]]]]
        ]

        self.icon = ":/Icons_Reference/Icons/constant.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 2: Step Block
class Step(SourceBlock):
    def __init__(self, scene, window, step_time=1.0, initial_value=0.0, final_value=1.0, name="Step Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = self.__class__.__name__

        self.variables = [
            ["Step_time", float, step_time, []],
            ["Initial_value", float, initial_value, []],
            ["Final_value", float, final_value, []]
        ]

        self.icon = ":/Icons_Reference/Icons/step.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 3: Waveform Block
class Waveform(SourceBlock):
    def __init__(self, scene, window, wave='square', freq=1.0, unit='Hz', amplitude=0.0, offset=0.0, phase=0.0, minimum=0.0, maximum=1.0, duty=0.5, name="Waveform Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = self.__class__.__name__

        self.variables = [
            ["Wave", str, wave, [["keywords", ["sine", "square", "triangle"]]]],
            ["Freq", float, freq, []],
            ["Unit", str, unit, [["keywords", ["hz", "rad/s"]]]],
            ["Amplitude", float, amplitude, []],
            ["Offset", float, offset, []],
            ["Phase", float, phase, [["range", [0, 1]]]],
            ["Min", float, minimum, []],
            ["Max", float, maximum, []],
            ["Duty", float, duty, [["range", [0, 1]]]]
        ]

        self.icon = ":/Icons_Reference/Icons/waveform.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 4: Piecewise Block
class Piecewise(SourceBlock):
    def __init__(self, scene, window, seq=[], name="Piecewise Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = self.__class__.__name__

        self.variables = [
            ["Sequence", list, seq, []]
        ]

        self.icon = ":/Icons_Reference/Icons/piecewise.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)
