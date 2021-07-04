# import bdsim.bdsim.bdedit
from bdsim.bdedit.block import INPORTBlock, OUTPORTBlock, SUBSYSTEMBlock, block, blockname

@block
# Child class 1: INPORT Block
class INPORT(INPORTBlock):
    """
    The ``INPORT`` Class is a subclass of ``INPORTBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 0, not allowing this class to have any inputs
    - outputsNum: 1, allowing this class to have any number of outputs

    The title, type, parameters and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, nout=1, name="INPORT Block", pos=(0, 0)):
        """
        This method creates a ``INPORT`` Block, which is a subclassed as |rarr| ``INPORTBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 150

        This method also overwrites the title, type, parameters and icon variables inherited from the ``Block`` Class.

        - title: defaults to "INPORT Block"
        - type: defaults to "INPORT"
        - icon: set to local reference of a INPORT icon
        - parameters: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +------------------+--------+------------------+----------------------------------------------------+
           | name             | type   | value            |                    restrictions                    |
           +------------------+--------+------------------+----------------------------------------------------+
           | "nout"           | int    | nout             |             [["range", [0, 1000]]]                 |
           +------------------+--------+------------------+----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param nout: number of outputs
        :type nout: int, optional, defaults to 1
        :param name: name of the block
        :type name: str, optional, defaults to "INPORT Block"
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``
        :type pos: tuple of 2-ints, optional, defaults to (0,0)
        """
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = blockname(self.__class__)

        self.parameters = [
            ["nout", int, nout, [["range", [0, 1000]]]]
        ]

        self.icon = None
        self.width = 100
        self.height = 150

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 2: OUTPORT Block
class OUTPORT(OUTPORTBlock):
    """
    The ``OUTPORT`` Class is a subclass of ``OUTPORTBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 1, allowing this class to have any number of inputs
    - outputsNum: 0, not allowing this class to have any outputs

    The title, type, parameters and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, nin=1, name="OUTPORT Block", pos=(0, 0)):
        """
        This method creates a ``OUTPORT`` Block, which is a subclassed as |rarr| ``OUTPORTBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 150

        This method also overwrites the title, type, parameters and icon variables inherited from the ``Block`` Class.

        - title: defaults to "OUTPORT Block"
        - type: defaults to "OUTPORT"
        - icon: set to local reference of a OUTPORT icon
        - parameters: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +------------------+--------+------------------+----------------------------------------------------+
           | name             | type   | value            |                    restrictions                    |
           +------------------+--------+------------------+----------------------------------------------------+
           | "nin"            | int    | nin              |             [["range", [0, 1000]]]                 |
           +------------------+--------+------------------+----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param nin: number of inputs
        :type nin: int, optional, defaults to 1
        :param name: name of the block
        :type name: str, optional, defaults to "OUTPORT Block"
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``
        :type pos: tuple of 2-ints, optional, defaults to (0,0)
        """
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = blockname(self.__class__)

        self.parameters = [
            ["nin", int, nin, [["range", [0, 1000]]]]
        ]

        self.icon = None
        self.width = 100
        self.height = 150

        self._createBlock(self.inputsNum, self.outputsNum)


@block
# Child class 3: SUBSYSTEM Block
class SUBSYSTEM(SUBSYSTEMBlock):
    """
    The ``SUBSYSTEM`` Class is a subclass of ``SUBSYSTEMBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 1, allowing this class to have any number of inputs
    - outputsNum: 1, allowing this class to have any number of outputs

    The title, type, parameters and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, hierarchy_file=None, name="SUBSYSTEM Block", pos=(0, 0)):
        """
        This method creates a ``SUBSYSTEM`` Block, which is a subclassed as |rarr| ``SUBSYSTEMBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 200
        - height: 150

        This method also overwrites the title, type, parameters and icon variables inherited from the ``Block`` Class.

        - title: defaults to "SUBSYSTEM Block"
        - type: defaults to "SUBSYSTEM"
        - icon: set to local reference of a SUBSYSTEM icon
        - parameters: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +------------------+--------+------------------+----------------------------------------------------+
           | name             | type   | value            |                    restrictions                    |
           +------------------+--------+------------------+----------------------------------------------------+
           | "hierarchy_file" | str    | hierarchy_file   |           [["type", [type(None), str]]]            |
           +------------------+--------+------------------+----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param hierarchy_file: string filepath to block diagram representing an SUBSYSTEM block
        :type hierarchy_file: str, optional, defaults to None
        :param name: name of the block
        :type name: str, optional, defaults to "SUBSYSTEM Block"
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``
        :type pos: tuple of 2-ints, optional, defaults to (0,0)
        """
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = blockname(self.__class__)

        self.parameters = [
            ["hierarchy_file", str, hierarchy_file, [["type", [type(None), str]]]]
        ]

        self.icon = None
        self.width = 200
        self.height = 150

        self._createBlock(self.inputsNum, self.outputsNum)