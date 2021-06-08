from bdedit.block import SourceBlock, block, blockname


@block
# Child class 1: Constant Block
class Constant(SourceBlock):
    """
    The ``Constant`` Class is a subclass of ``SourceBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 0, not allowing this class to have any inputs
    - outputsNum: 1, allowing this class to have any number of outputs

    The title, type, variables and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, value=None, name="Constant Block", pos=(0, 0)):
        """
        This method creates a ``Constant`` Block, which is a subclassed as |rarr| ``SourceBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 100

        This method also overwrites the title, type, variables and icon variables inherited from the ``Block`` Class.

        - title: defaults to "Constant Block"
        - type: defaults to "Constant"
        - icon: set to local reference of a Constant icon
        - variables: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +----------+--------+----------+----------------------------------------------------+
           | name     | type   | value    |                    restrictions                    |
           +----------+--------+----------+----------------------------------------------------+
           | "Value"  | any    | value    |        [["type", [type(None), type(any)]]]         |
           +----------+--------+----------+----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param value: value
        :type value: any, optional, defaults to None
        :param name: name of the block
        :type name: str, optional, defaults to "Constant Block"
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``
        :type pos: tuple of 2-ints, optional, defaults to (0,0)
        """
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = blockname(self.__class__)

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
    """
    The ``Step`` Class is a subclass of ``SourceBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 0, not allowing this class to have any inputs
    - outputsNum: 1, allowing this class to have any number of outputs

    The title, type, variables and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, step_time=1.0, initial_value=0.0, final_value=1.0, name="Step Block", pos=(0, 0)):
        """
        This method creates a ``Step`` Block, which is a subclassed as |rarr| ``SourceBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 100

        This method also overwrites the title, type, variables and icon variables inherited from the ``Block`` Class.

        - title: defaults to "Step Block"
        - type: defaults to "Step"
        - icon: set to local reference of a Step icon
        - variables: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +------------------+--------+----------------+----------------------------------------------------+
           | name             | type   | value          |                    restrictions                    |
           +------------------+--------+----------------+----------------------------------------------------+
           | "Step_time"      | float  | step_time      |                         []                         |
           +------------------+--------+----------------+----------------------------------------------------+
           | "Initial_value"  | float  | initial_value  |                         []                         |
           +------------------+--------+----------------+----------------------------------------------------+
           | "Final_value"    | float  | final_value    |                         []                         |
           +------------------+--------+----------------+----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param step_time: step time
        :type step_time: float, optional, defaults to 1.0
        :param initial_value: initial value
        :type initial_value: float, optional, defaults to 0.0
        :param final_value: final value
        :type final_value: float, optional, defaults to 1.0
        :param name: name of the block
        :type name: str, optional, defaults to "Step Block"
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``
        :type pos: tuple of 2-ints, optional, defaults to (0,0)
        """
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = blockname(self.__class__)

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
    """
    The ``Waveform`` Class is a subclass of ``SourceBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 0, not allowing this class to have any inputs
    - outputsNum: 1, allowing this class to have any number of outputs

    The title, type, variables and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, wave='square', freq=1.0, unit='Hz', amplitude=0.0, offset=0.0, phase=0.0, minimum=0.0, maximum=1.0, duty=0.5, name="Waveform Block", pos=(0, 0)):
        """
        This method creates a ``Waveform`` Block, which is a subclassed as |rarr| ``SourceBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 100

        This method also overwrites the title, type, variables and icon variables inherited from the ``Block`` Class.

        - title: defaults to "Waveform Block"
        - type: defaults to "Waveform"
        - icon: set to local reference of a Waveform icon
        - variables: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +------------------+--------+----------------+----------------------------------------------------+
           | name             | type   | value          |                    restrictions                    |
           +------------------+--------+----------------+----------------------------------------------------+
           | "Wave"           | str    | wave           |   [["keywords", ["sine", "square", "triangle"]]]   |
           +------------------+--------+----------------+----------------------------------------------------+
           | "Freq"           | float  | freq           |                         []                         |
           +------------------+--------+----------------+----------------------------------------------------+
           | "Unit"           | str    | unit           |         [["keywords", ["hz", "rad/s"]]]            |
           +------------------+--------+----------------+----------------------------------------------------+
           | "Amplitude"      | float  | amplitude      |                         []                         |
           +------------------+--------+----------------+----------------------------------------------------+
           | "Offset"         | float  | offset         |                         []                         |
           +------------------+--------+----------------+----------------------------------------------------+
           | "Phase"          | float  | phase          |                [["range", [0, 1]]]                 |
           +------------------+--------+----------------+----------------------------------------------------+
           | "Min"            | float  | minimum        |                         []                         |
           +------------------+--------+----------------+----------------------------------------------------+
           | "Max"            | float  | maximum        |                         []                         |
           +------------------+--------+----------------+----------------------------------------------------+
           | "Duty"           | float  | duty           |                [["range", [0, 1]]]                 |
           +------------------+--------+----------------+----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param wave: wave
        :type wave: str, optional, defaults to 'square'
        :param freq: freq
        :type freq: float, optional, defaults to 1.0
        :param unit: unit
        :type unit: str, optional, defaults to 'Hz'
        :param amplitude: amplitude
        :type amplitude: float, optional, defaults to 0.0
        :param offset: offset
        :type offset: float, optional, defaults to 0.0
        :param phase: phase
        :type phase: float, optional, defaults to 0.0
        :param minimum: minimum
        :type minimum: float, optional, defaults to 0.0
        :param maximum: maximum
        :type maximum: float, optional, defaults to 1.0
        :param duty: duty
        :type duty: float, optional, defaults to 0.5
        :param name: name of the block
        :type name: str, optional, defaults to "Waveform Block"
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``
        :type pos: tuple of 2-ints, optional, defaults to (0,0)
        """
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = blockname(self.__class__)

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
    """
    The ``Piecewise`` Class is a subclass of ``SourceBlock``, and referred to as a
    grandchild class of ``Block``. It inherits all the methods and variables of its
    parent, and grandparent class, defining some of these variables to make the class unique.

    The inputsNum and outputsNum variables inherited from the parent class are:

    - inputsNum: 0, not allowing this class to have any inputs
    - outputsNum: 1, allowing this class to have any number of outputs

    The title, type, variables and icon variables inherited from the grandparent class are
    overwritten here to this Blocks' unique values.
    """
    def __init__(self, scene, window, seq=[], name="Piecewise Block", pos=(0, 0)):
        """
        This method creates a ``Piecewise`` Block, which is a subclassed as |rarr| ``SourceBlock`` |rarr| ``Block``.
        This method sets the dimensions of this block to being:

        - width: 100
        - height: 100

        This method also overwrites the title, type, variables and icon variables inherited from the ``Block`` Class.

        - title: defaults to "Piecewise Block"
        - type: defaults to "Piecewise"
        - icon: set to local reference of a Piecewise icon
        - variables: set according to the list structure outlined in ``Block``.

        .. table::
           :align: left

           +------------------+--------+----------------+----------------------------------------------------+
           | name             | type   | value          |                    restrictions                    |
           +------------------+--------+----------------+----------------------------------------------------+
           | "Sequence"       | list   | seq            |                         []                         |
           +------------------+--------+----------------+----------------------------------------------------+

        :param scene: a scene in which the Block is stored and shown. Provided by the ``Interface``.
        :type scene: ``Scene``, required
        :param window: layout information of where all ``Widgets`` are located in the bdedit window.
                       Provided by the ``Interface``.
        :type window: ``QGridLayout``, required
        :param seq: sequence
        :type seq: list, optional, defaults to []
        :param name: name of the block
        :type name: str, optional, defaults to "Piecewise Block"
        :param pos: (x,y) coordinates of the block's positioning within the ``Scene``
        :type pos: tuple of 2-ints, optional, defaults to (0,0)
        """
        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = blockname(self.__class__)

        self.variables = [
            ["Sequence", list, seq, []]
        ]

        self.icon = ":/Icons_Reference/Icons/piecewise.png"
        self.width = 100
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)
