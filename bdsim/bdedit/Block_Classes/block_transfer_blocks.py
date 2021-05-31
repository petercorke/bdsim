from bdedit.block import TransferBlock, block

@block
# Child class 1: Integrator Block
class Integrator(TransferBlock):
    def __init__(self, scene, window, x_intial=[0], minimum=None, maximum=None, name="Integrator Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = self.__class__.__name__

        self.variables = [
            ["X_0", list, x_intial, []],
            ["Min", float, minimum, [["type", [type(None), float]]]],
            ["Max", float, maximum, [["type", [type(None), float]]]]
        ]

        self.icon = ":/Icons_Reference/Icons/integrator_B.png"
        # self.icon = ":/Icons_Reference/Icons/integrator_L.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 2: LTI_SISO Block
class LTI_SISO(TransferBlock):
    def __init__(self, scene, window, n=[1], d=[1, 1], x_initial=None, verbose=False, name="LTI_SISO Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = self.__class__.__name__

        self.variables = [
            ["N", list, n, []],
            ["D", list, d, []],
            ["X_0", list, x_initial, [["type", [type(None), list]]]],
            ["Verbose", bool, verbose, [["type", [type(None), bool]]]]
        ]

        self.icon = ":/Icons_Reference/Icons/lti_siso_B.png"
        # self.icon = ":/Icons_Reference/Icons/lti_siso_L.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 3: LTI_SS Block
class LTI_SS(TransferBlock):
    def __init__(self, scene, window, a=None, b=None, c=None, x_initial=None, verbose=False, name="LTI_SS Block", pos=(0, 0)):
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = self.__class__.__name__

        self.variables = [
            ["A", float, a, [["type", [type(None), float]]]],
            ["B", float, b, [["type", [type(None), float]]]],
            ["C", float, c, [["type", [type(None), float]]]],
            ["X_0", list, x_initial, [["type", [type(None), list]]]],
            ["Verbose", bool, verbose, [["type", [type(None), bool]]]]
        ]

        self.icon = ":/Icons_Reference/Icons/lti_ss.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)