from bdedit.block import SinkBlock, block, blockname


@block
# Child class 1: Print Block
class Print(SinkBlock):
    """
    The ``Print`` Class is a subclass of ``SinkBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 1, allowing this class to have any number of inputs
    - outputsNum: 0, not allowing this class to have any outputs

    The title, type, variables and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, fmt=None, name="Print Block", pos=(0, 0)):
        """
        This method creates a ``Print`` Block, which is a subclassed as |rarr| ``SinkBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 100

        This method also overwrites the title, type, variables and icon variables inherited from the ``Block`` Class.

        - title: defaults to "Print Block"
        - type: defaults to "Print"
        - icon: set to local reference of a Print icon
        - variables: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +-----------+--------+----------+----------------------------------------------------+
           | name      | type   | value    |                    restrictions                    |
           +-----------+--------+----------+----------------------------------------------------+
           | "Format"  | str    | fmt      |            [["type", [type(None), str]]]           |
           +-----------+--------+----------+----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param fmt: format
        :type fmt: str, optional, defaults to None
        :param name: name of the block
        :type name: str, optional, defaults to "Print Block"
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``
        :type pos: tuple of 2-ints, optional, defaults to (0,0)
        """
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = blockname(self.__class__)

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
    """
    The ``Stop`` Class is a subclass of ``SinkBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 1, allowing this class to have any number of inputs
    - outputsNum: 0, not allowing this class to have any outputs

    The title, type, variables and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, stop=None, name="Stop Block", pos=(0, 0)):
        """
        This method creates a ``Stop`` Block, which is a subclassed as |rarr| ``SinkBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 100

        This method also overwrites the title, type, variables and icon variables inherited from the ``Block`` Class.

        - title: defaults to "Stop Block"
        - type: defaults to "Stop"
        - icon: set to local reference of a Stop icon
        - variables: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +-----------+--------+----------+----------------------------------------------------+
           | name      | type   | value    |                    restrictions                    |
           +-----------+--------+----------+----------------------------------------------------+
           | "Stop"    | str    | stop     |            [["type", [type(None), str]]]           |
           +-----------+--------+----------+----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param stop: stop
        :type stop: str, optional, defaults to None
        :param name: name of the block
        :type name: str, optional, defaults to "Stop Block"
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``
        :type pos: tuple of 2-ints, optional, defaults to (0,0)
        """
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = blockname(self.__class__)

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
    """
    The ``Scope`` Class is a subclass of ``SinkBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 1, allowing this class to have any number of inputs
    - outputsNum: 0, not allowing this class to have any outputs

    The title, type, variables and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, nin=1, styles=None, scale='auto', labels=None, grid=[], name="Scope Block", pos=(0, 0)):
        """
        This method creates a ``Scope`` Block, which is a subclassed as |rarr| ``SinkBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 100

        This method also overwrites the title, type, variables and icon variables inherited from the ``Block`` Class.

        - title: defaults to "Scope Block"
        - type: defaults to "Scope"
        - icon: set to local reference of a Scope icon
        - variables: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +------------------+--------+------------------+-----------------------------------------------------+
           | name             | type   | value            |                    restrictions                     |
           +------------------+--------+------------------+-----------------------------------------------------+
           | "No. of inputs"  | int    | nin              | [["range", [0, 1000]], ["type", [type(None), int]]] |
           +------------------+--------+------------------+-----------------------------------------------------+
           | "Styles"         | str    | styles           |          [["type", [type(None), str]]]              |
           +------------------+--------+------------------+-----------------------------------------------------+
           | "Scale"          | str    | scale            |                        []                           |
           +------------------+--------+------------------+-----------------------------------------------------+
           | "Labels"         | list   | labels           |          [["type", [type(None), list]]]             |
           +------------------+--------+------------------+-----------------------------------------------------+
           | "Grid"           | list   | grid             |          [["type", [type(None), list]]]             |
           +------------------+--------+------------------+-----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param nin: number of inputs
        :type nin: int, optional, defaults to 1
        :param styles: styles
        :type styles: str, optional, defaults to None
        :param scale: scale
        :type scale: str, optional, defaults to 'auto'
        :param labels: labels
        :type labels: list, optional, defaults to None
        :param grid: grid
        :type grid: list, optional, defaults to []
        :param name: name of the block
        :type name: str, optional, defaults to "Scope Block"
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``
        :type pos: tuple of 2-ints, optional, defaults to (0,0)
        """
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = blockname(self.__class__)

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
