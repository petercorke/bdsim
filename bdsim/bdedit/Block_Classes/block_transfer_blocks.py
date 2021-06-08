from bdedit.block import TransferBlock, block, blockname

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

    The title, type, variables and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, x_initial=[0], minimum=None, maximum=None, name="Integrator Block", pos=(0, 0)):
        """
        This method creates a ``Integrator`` Block, which is a subclassed as |rarr| ``TransferBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 100

        This method also overwrites the title, type, variables and icon variables inherited from the ``Block`` Class.

        - title: defaults to "Integrator Block"
        - type: defaults to "Integrator"
        - icon: set to local reference of a Integrator icon
        - variables: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +--------+--------+----------+----------------------------------------------------+
           | name   | type   | value    |                    restrictions                    |
           +--------+--------+----------+----------------------------------------------------+
           | "X_0"  | list   | x_initial|                         []                         |
           +--------+--------+----------+----------------------------------------------------+
           | "Min"  | float  | minimum  |         [["type", [type(None), float]]]            |
           +--------+--------+----------+----------------------------------------------------+
           | "Max"  | float  | maximum  |         [["type", [type(None), float]]]            |
           +--------+--------+----------+----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param x_initial: intial x value
        :type x_initial: list, optional, defaults to [0]
        :param minimum: minimum
        :type minimum: float, optional, defaults to None
        :param maximum: maximum
        :type maximum: float, optional, defaults to None
        :param name: name of the block
        :type name: str, optional, defaults to "Integrator Block"
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``
        :type pos: tuple of 2-ints, optional, defaults to (0,0)
        """
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = blockname(self.__class__)

        self.variables = [
            ["X_0", list, x_initial, []],
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
    """
    The ``LTI_SISO`` Class is a subclass of ``TransferBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 1, allowing this class to have any number of inputs
    - outputsNum: 1, allowing this class to have any number of outputs

    The title, type, variables and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, n=[1], d=[1, 1], x_initial=None, verbose=False, name="LTI_SISO Block", pos=(0, 0)):
        """
        This method creates a ``LTI_SISO`` Block, which is a subclassed as |rarr| ``TransferBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 100

        This method also overwrites the title, type, variables and icon variables inherited from the ``Block`` Class.

        - title: defaults to "LTI_SISO Block"
        - type: defaults to "LTI_SISO"
        - icon: set to local reference of a LTI_SISO icon
        - variables: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +-----------+--------+----------+----------------------------------------------------+
           | name      | type   | value    |                    restrictions                    |
           +-----------+--------+----------+----------------------------------------------------+
           | "N"       | list   |    n     |                         []                         |
           +-----------+--------+----------+----------------------------------------------------+
           | "D"       | list   |    d     |                         []                         |
           +-----------+--------+----------+----------------------------------------------------+
           | "X_0"     | list   | x_initial|         [["type", [type(None), list]]]             |
           +-----------+--------+----------+----------------------------------------------------+
           | "Verbose" | bool   | verbose  |         [["type", [type(None), bool]]]             |
           +-----------+--------+----------+----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param n: N
        :type n: list, optional, defaults to [1]
        :param d: D
        :type d: list, optional, defaults to [1,1]
        :param x_initial: initial x value
        :type x_initial: list, optional, defaults to None
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
    """
    The ``LTI_SS`` Class is a subclass of ``TransferBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 1, allowing this class to have any number of inputs
    - outputsNum: 1, allowing this class to have any number of outputs

    The title, type, variables and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, a=None, b=None, c=None, x_initial=None, verbose=False, name="LTI_SS Block", pos=(0, 0)):
        """
        This method creates a ``LTI_SS`` Block, which is a subclassed as |rarr| ``TransferBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 100

        This method also overwrites the title, type, variables and icon variables inherited from the ``Block`` Class.

        - title: defaults to "LTI_SS Block"
        - type: defaults to "LTI_SS"
        - icon: set to local reference of a LTI_SS icon
        - variables: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +-----------+--------+----------+----------------------------------------------------+
           | name      | type   | value    |                    restrictions                    |
           +-----------+--------+----------+----------------------------------------------------+
           | "A"       | float  |    a     |         [["type", [type(None), float]]]            |
           +-----------+--------+----------+----------------------------------------------------+
           | "B"       | float  |    b     |         [["type", [type(None), float]]]            |
           +-----------+--------+----------+----------------------------------------------------+
           | "C"       | float  |    c     |         [["type", [type(None), float]]]            |
           +-----------+--------+----------+----------------------------------------------------+
           | "X_0"     | list   | x_initial|         [["type", [type(None), list]]]             |
           +-----------+--------+----------+----------------------------------------------------+
           | "Verbose" | bool   | verbose  |         [["type", [type(None), bool]]]             |
           +-----------+--------+----------+----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param a: A
        :type a: float, optional, defaults to None
        :param b: B
        :type b: float, optional, defaults to None
        :param c: C
        :type c: float, optional, defaults to None
        :param x_initial: initial x value
        :type x_initial: list, optional, defaults to None
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