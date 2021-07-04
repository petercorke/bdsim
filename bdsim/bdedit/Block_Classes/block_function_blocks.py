import math
import bdsim.bdedit
from bdsim.bdedit.block import FunctionBlock, block, blockname


@block
# Child class 1: Clip Block
class Clip(FunctionBlock):
    """
    The ``Clip`` Class is a subclass of ``FunctionBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 1, allowing this class to have any number of inputs
    - outputsNum: 1, allowing this class to have any number of outputs

    The title, type, parameters and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, minimum=-math.inf, maximum=math.inf, name="Clip Block", pos=(0, 0)):
        """
        This method creates a ``Clip`` Block, which is a subclassed as |rarr| ``FunctionBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 100

        This method also overwrites the title, type, parameters and icon variables inherited from the ``Block`` Class.

        - title: defaults to "Clip Block"
        - type: defaults to "Clip"
        - icon: set to local reference of a Clip icon
        - parameters: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +--------+--------+----------+----------------------------------------------------+
           | name   | type   | value    |                    restrictions                    |
           +--------+--------+----------+----------------------------------------------------+
           | "min"  | float  | minimum  |         [["range", [-math.inf, math.inf]]]         |
           +--------+--------+----------+----------------------------------------------------+
           | "max"  | float  | maximum  |         [["range", [-math.inf, math.inf]]]         |
           +--------+--------+----------+----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param minimum: minimum value
        :type minimum: float, optional, defaults to -math.inf
        :param maximum: maximum value
        :type maximum: float, optional, defaults to math.inf
        :param name: name of the block
        :type name: str, optional, defaults to "Clip Block"
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``
        :type pos: tuple of 2-ints, optional, defaults to (0,0)
        """
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = blockname(self.__class__)

        self.parameters = [
            ["min", float, minimum, [["range", [-math.inf, math.inf]]]],
            ["max", float, maximum, [["range", [-math.inf, math.inf]]]]
        ]

        self.icon = ":/Icons_Reference/Icons/clip.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 2: Function Block
class Function(FunctionBlock):
    """
    The ``Function`` Class is a subclass of ``FunctionBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 1, allowing this class to have any number of inputs
    - outputsNum: 1, allowing this class to have any number of outputs

    The title, type, parameters and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, func="Provide Function", nin=1, nout=1, dictionary=False, args=(), kwargs={}, name="Function Block", pos=(0, 0)):
        """
        This method creates a ``Function`` Block, which is a subclassed as |rarr| ``FunctionBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 100

        This method also overwrites the title, type, parameters and icon variables inherited from the ``Block`` Class.

        - title: defaults to "Function Block"
        - type: defaults to "Function"
        - icon: set to local reference of a Function icon
        - parameters: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +------------------+--------+------------+----------------------------------------------------+
           | name             | type   | value      |                    restrictions                    |
           +------------------+--------+------------+----------------------------------------------------+
           | "func"           | str    | func       |                         []                         |
           +------------------+--------+------------+----------------------------------------------------+
           | "nin"            | int    | nin        |               [["range", [0, 1000]]]               |
           +------------------+--------+------------+----------------------------------------------------+
           | "nout"           | int    | nout       |               [["range", [0, 1000]]]               |
           +------------------+--------+------------+----------------------------------------------------+
           | "dict"           | bool   | dictionary |                         []                         |
           +------------------+--------+------------+----------------------------------------------------+
           | "args"           | tuple  | args       |                         []                         |
           +------------------+--------+------------+----------------------------------------------------+
           | "kwargs"         | dict   | kwargs     |                         []                         |
           +------------------+--------+------------+----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param func: a function
        :type func: str, optional, defaults to "Provide Function"
        :param nin: number of inputs
        :type nin: int, optional, defaults to 1
        :param nout: number of outputs
        :type nout: int, optional, defaults to 1
        :param dictionary: pass in a reference to a dictionary instance
        :type dictionary: bool, optional, defaults to False
        :param args: extra positional arguments passed to the function
        :type args: tuple, optional, defaults to ()
        :param kwargs: extra keyword arguments passed to the function
        :type kwargs: dict, optional, defaults to {}
        :param name: name of the block
        :type name: str, optional, defaults to "Function Block"
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``
        :type pos: tuple of 2-ints, optional, defaults to (0,0)
        """
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)
        
        self.block_type = blockname(self.__class__)

        self.parameters = [
            ["func", str, func, []],
            ["nin", int, nin, [["range", [0, 1000]]]],
            ["nout", int, nout, [["range", [0, 1000]]]],
            ["dict", bool, dictionary, []],
            ["args", tuple, args, []],
            ["kwargs", dict, kwargs, []]
        ]

        self.inputsNum = nin
        self.outputsNum = nout

        self.icon = ":/Icons_Reference/Icons/function.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 3: Gain Block
class Gain(FunctionBlock):
    """
    The ``Gain`` Class is a subclass of ``FunctionBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 1, allowing this class to have any number of inputs
    - outputsNum: 1, allowing this class to have any number of outputs

    The title, type, parameters and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, K=0, premul=False, name="Gain Block", pos=(0, 0)):
        """
        This method creates a ``Gain`` Block, which is a subclassed as |rarr| ``FunctionBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 100

        This method also overwrites the title, type, parameters and icon variables inherited from the ``Block`` Class.

        - title: defaults to "Gain Block"
        - type: defaults to "Gain"
        - icon: set to local reference of a Gain icon
        - parameters: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +----------+--------+----------+----------------------------------------------------+
           | name     | type   | value    |                    restrictions                    |
           +----------+--------+----------+----------------------------------------------------+
           | "K"      | float  |   K      |                         []                         |
           +----------+--------+----------+----------------------------------------------------+
           | "premul" | bool   | premul   |                         []                         |
           +----------+--------+----------+----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param K: gain value
        :type K: float, optional, defaults to 0
        :param premul: premultiply by constant
        :type premul: bool, optional, defaults to False
        :param name: name of the block
        :type name: str, optional, defaults to "Gain Block"
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``
        :type pos: tuple of 2-ints, optional, defaults to (0,0)
        """
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)
        
        self.block_type = blockname(self.__class__)

        self.parameters = [
            ["K", float, K, []],
            ["premul", bool, premul, []]
        ]

        self.icon = ":/Icons_Reference/Icons/gain.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 4: Interpolate Block
class Interpolate(FunctionBlock):
    """
    The ``Interpolate`` Class is a subclass of ``FunctionBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 1, allowing this class to have any number of inputs
    - outputsNum: 1, allowing this class to have any number of outputs

    The title, type, parameters and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, x_array=None, y_array=None, xy_array=None, time=False, kind='linear', name="Interpolate Block", pos=(0, 0)):
        """
        This method creates a ``Interpolate`` Block, which is a subclassed as |rarr| ``FunctionBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 100

        This method also overwrites the title, type, parameters and icon variables inherited from the ``Block`` Class.

        - title: defaults to "Interpolate Block"
        - type: defaults to "Interpolate"
        - icon: set to local reference of a Interpolate icon
        - parameters: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +--------+--------+----------+-----------------------------------------------------------------------------------------------------------------------+
           | name   | type   | value    |                                                 restrictions                                                          |
           +--------+--------+----------+-----------------------------------------------------------------------------------------------------------------------+
           | "x"    | tuple  | x_array  |                                       [["type", [type(None), tuple]]]                                                 |
           +--------+--------+----------+-----------------------------------------------------------------------------------------------------------------------+
           | "y"    | tuple  | y_array  |                                       [["type", [type(None), tuple]]]                                                 |
           +--------+--------+----------+-----------------------------------------------------------------------------------------------------------------------+
           | "xy"   | list   | xy_array |                                       [["type", [type(None), list]]]                                                  |
           +--------+--------+----------+-----------------------------------------------------------------------------------------------------------------------+
           | "time" | bool   | time     |                                                      []                                                               |
           +--------+--------+----------+-----------------------------------------------------------------------------------------------------------------------+
           | "kind" | str    | kind     | [["keywords", ["linear", "nearest neighbor", "cubic spline", "shape-preserving", "biharmonic", "thin-plate spline"]]] |
           +--------+--------+----------+-----------------------------------------------------------------------------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param x_array: x values of function
        :type x_array: tuple, optional, defaults to None
        :param y_array: y values of function
        :type y_array: tuple, optional, defaults to None
        :param xy_array: combined x- and y-values of function
        :type xy_array: list, optional, defaults to None
        :param time: x new is simulation time
        :type time: bool, optional, defaults to False
        :param kind: interpolation method
        :type kind: str, optional, defaults to 'linear'
        :param name: name of the block
        :type name: str, optional, defaults to "Interpolate Block"
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``
        :type pos: tuple of 2-ints, optional, defaults to (0,0)
        """
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)
        
        self.block_type = blockname(self.__class__)

        self.parameters = [
            ["x", tuple, x_array, [["type", [type(None), tuple]]]],
            ["y", tuple, y_array, [["type", [type(None), tuple]]]],
            ["xy", list, xy_array, [["type", [type(None), list]]]],
            ["time", bool, time, []],
            ["kind", str, kind, [["keywords", ["linear", "nearest neighbor", "cubic spline", "shape-preserving", "biharmonic", "thin-plate spline"]]]]
        ]

        self.icon = ":/Icons_Reference/Icons/interpolate.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 5: Prod Block
class Prod(FunctionBlock):
    """
    The ``Prod`` Class is a subclass of ``FunctionBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 1, allowing this class to have any number of inputs
    - outputsNum: 1, allowing this class to have any number of outputs

    The title, type, parameters and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, ops="**", matrix=False, name="Prod Block", pos=(0,0)):
        """
        This method creates a ``Prod`` Block, which is a subclassed as |rarr| ``FunctionBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 100

        This method also overwrites the title, type, parameters and icon variables inherited from the ``Block`` Class.

        - title: defaults to "Prod Block"
        - type: defaults to "Prod"
        - icon: set to local reference of a Prod icon
        - parameters: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +--------------+--------+----------+----------------------------------------------------+
           | name         | type   | value    |                    restrictions                    |
           +--------------+--------+----------+----------------------------------------------------+
           | "ops"        | str    | ops      |               [["signs", ["*", "/"]]]              |
           +--------------+--------+----------+----------------------------------------------------+
           | "matrix"     | bool   | matrix   |                         []                         |
           +--------------+--------+----------+----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param ops: operations associated with input ports * or /
        :type ops: str, optional, defaults to "**"
        :param matrix: matrix
        :type matrix: bool, optional, defaults to False
        :param name: name of the block
        :type name: str, optional, defaults to "Prod Block"
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``
        :type pos: tuple of 2-ints, optional, defaults to (0,0)
        """
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)
        
        self.block_type = blockname(self.__class__)

        self.parameters = [
            ["ops", str, ops, [["signs", ["*", "/"]]]],
            ["matrix", bool, matrix, []]
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
    """
    The ``Sum`` Class is a subclass of ``FunctionBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 1, allowing this class to have any number of inputs
    - outputsNum: 1, allowing this class to have any number of outputs

    The title, type, parameters and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, signs='++', angles=False, name="Sum Block", pos=(0, 0)):
        """
        This method creates a ``Sum`` Block, which is a subclassed as |rarr| ``FunctionBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 100

        This method also overwrites the title, type, parameters and icon variables inherited from the ``Block`` Class.

        - title: defaults to "Sum Block"
        - type: defaults to "Sum"
        - icon: set to local reference of a Sum icon
        - parameters: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +-----------+--------+----------+----------------------------------------------------+
           | name      | type   | value    |                    restrictions                    |
           +-----------+--------+----------+----------------------------------------------------+
           | "signs"   | str    | signs    |               [["signs", ["+", "-"]]]              |
           +-----------+--------+----------+----------------------------------------------------+
           | "angles"  | bool   | angles   |                         []                         |
           +-----------+--------+----------+----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param signs: signs associated with input ports, + or -
        :type signs: str, optional, defaults to "++"
        :param angles: the signals are angles, wrap to [-pi, pi]
        :type angles: bool, optional, defaults to False
        :param name: name of the block
        :type name: str, optional, defaults to "Sum Block"
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``
        :type pos: tuple of 2-ints, optional, defaults to (0,0)
        """
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)
        
        self.block_type = blockname(self.__class__)

        self.parameters = [
            ["signs", str, signs, [["signs", ["+", "-"]]]],
            ["angles", bool, angles, []]
        ]

        # this will need to be updated from param window
        # Will also need to draw the sockets differently based on sign
        self.inputsNum = len(signs)

        self.icon = None  # ":/Icons_Reference/Icons/sum.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)
