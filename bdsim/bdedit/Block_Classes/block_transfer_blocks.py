import bdsim.bdedit
from bdsim.bdedit.block import TransferBlock, block, blockname

@block
# Child class 1: Integrator Block
class Integrator(TransferBlock):
    """
    The ``Integrator`` Class is a subclass of ``TransferBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 1, allowing this class to have any number of inputs
    - outputsNum: 1, allowing this class to have any number of outputs

    The title, type, parameters and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, x0=[0], minimum=None, maximum=None, name="Integrator Block", pos=(0, 0)):
        """
        This method creates a ``Integrator`` Block, which is a subclassed as |rarr| ``TransferBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 100

        This method also overwrites the title, type, parameters and icon variables inherited from the ``Block`` Class.

        - title: defaults to "Integrator Block"
        - type: defaults to "Integrator"
        - icon: set to local reference of a Integrator icon
        - parameters: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +--------+--------+----------+----------------------------------------------------+
           | name   | type   | value    |                    restrictions                    |
           +--------+--------+----------+----------------------------------------------------+
           | "x0"   | list   | x0       |                         []                         |
           +--------+--------+----------+----------------------------------------------------+
           | "min"  | float  | minimum  |         [["type", [type(None), float]]]            |
           +--------+--------+----------+----------------------------------------------------+
           | "max"  | float  | maximum  |         [["type", [type(None), float]]]            |
           +--------+--------+----------+----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param x0: initial state
        :type x0: list, optional, defaults to [0]
        :param minimum: minimum value of state
        :type minimum: float, optional, defaults to None
        :param maximum: maximum value of state
        :type maximum: float, optional, defaults to None
        :param name: name of the block
        :type name: str, optional, defaults to "Integrator Block"
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``
        :type pos: tuple of 2-ints, optional, defaults to (0,0)
        """
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = blockname(self.__class__)

        self.parameters = [
            ["x0", list, x0, []],
            ["min", float, minimum, [["type", [type(None), float]]]],
            ["max", float, maximum, [["type", [type(None), float]]]]
        ]

        self.icon = ":/Icons_Reference/Icons/integrator_B.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 2: LTI_SISO Block
class LTI_SISO(TransferBlock):
    """
    The ``LTI_SISO`` Class is a subclass of ``TransferBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 1, allowing this class to have any number of inputs
    - outputsNum: 1, allowing this class to have any number of outputs

    The title, type, parameters and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, N=[1], D=[1, 1], x0=None, verbose=False, name="LTI_SISO Block", pos=(0, 0)):
        """
        This method creates a ``LTI_SISO`` Block, which is a subclassed as |rarr| ``TransferBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 100

        This method also overwrites the title, type, parameters and icon variables inherited from the ``Block`` Class.

        - title: defaults to "LTI_SISO Block"
        - type: defaults to "LTI_SISO"
        - icon: set to local reference of a LTI_SISO icon
        - parameters: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +-----------+--------+----------+----------------------------------------------------+
           | name      | type   | value    |                    restrictions                    |
           +-----------+--------+----------+----------------------------------------------------+
           | "N"       | list   |    N     |                         []                         |
           +-----------+--------+----------+----------------------------------------------------+
           | "D"       | list   |    D     |                         []                         |
           +-----------+--------+----------+----------------------------------------------------+
           | "xo"      | list   |    x0    |         [["type", [type(None), list]]]             |
           +-----------+--------+----------+----------------------------------------------------+
           | "verbose" | bool   | verbose  |         [["type", [type(None), bool]]]             |
           +-----------+--------+----------+----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param N: numerator coefficients
        :type N: list, optional, defaults to [1]
        :param D: denominator coefficients
        :type D: list, optional, defaults to [1,1]
        :param x0: initial states
        :type x0: list, optional, defaults to None
        :param verbose: verbose
        :type verbose: bool, optional, defaults to False
        :param name: name of the block
        :type name: str, optional, defaults to "LTI_SISO Block"
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``
        :type pos: tuple of 2-ints, optional, defaults to (0,0)
        """
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = blockname(self.__class__)

        self.parameters = [
            ["N", list, N, []],
            ["D", list, D, []],
            ["x0", list, x0, [["type", [type(None), list]]]],
            ["verbose", bool, verbose, [["type", [type(None), bool]]]]
        ]

        self.icon = ":/Icons_Reference/Icons/lti_siso_B.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 3: LTI_SS Block
class LTI_SS(TransferBlock):
    """
    The ``LTI_SS`` Class is a subclass of ``TransferBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 1, allowing this class to have any number of inputs
    - outputsNum: 1, allowing this class to have any number of outputs

    The title, type, parameters and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, A=None, B=None, C=None, x0=None, verbose=False, name="LTI_SS Block", pos=(0, 0)):
        """
        This method creates a ``LTI_SS`` Block, which is a subclassed as |rarr| ``TransferBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 100

        This method also overwrites the title, type, parameters and icon variables inherited from the ``Block`` Class.

        - title: defaults to "LTI_SS Block"
        - type: defaults to "LTI_SS"
        - icon: set to local reference of a LTI_SS icon
        - parameters: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +-----------+--------+----------+----------------------------------------------------+
           | name      | type   | value    |                    restrictions                    |
           +-----------+--------+----------+----------------------------------------------------+
           | "A"       | float  |    A     |         [["type", [type(None), float]]]            |
           +-----------+--------+----------+----------------------------------------------------+
           | "B"       | float  |    B     |         [["type", [type(None), float]]]            |
           +-----------+--------+----------+----------------------------------------------------+
           | "C"       | float  |    C     |         [["type", [type(None), float]]]            |
           +-----------+--------+----------+----------------------------------------------------+
           | "x0"      | list   |   x0     |         [["type", [type(None), list]]]             |
           +-----------+--------+----------+----------------------------------------------------+
           | "verbose" | bool   | verbose  |         [["type", [type(None), bool]]]             |
           +-----------+--------+----------+----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param A: A
        :type A: float, optional, defaults to None
        :param B: B
        :type B: float, optional, defaults to None
        :param C: C
        :type C: float, optional, defaults to None
        :param x0: initial states
        :type x0: list, optional, defaults to None
        :param verbose: verbose
        :type verbose: bool, optional, defaults to False
        :param name: name of the block
        :type name: str, optional, defaults to "LTI_SS Block"
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``
        :type pos: tuple of 2-ints, optional, defaults to (0,0)
        """
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = blockname(self.__class__)

        self.parameters = [
            ["A", float, A, [["type", [type(None), float]]]],
            ["B", float, B, [["type", [type(None), float]]]],
            ["C", float, C, [["type", [type(None), float]]]],
            ["x0", list, x0, [["type", [type(None), list]]]],
            ["verbose", bool, verbose, [["type", [type(None), bool]]]]
        ]

        self.icon = ":/Icons_Reference/Icons/lti_ss.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)