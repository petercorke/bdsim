"""
Connection blocks are in two categories:

1. Signal manipulation:
    - have inputs and outputs
    - have no state variables
    - are a subclass of ``FunctionBlock`` |rarr| ``Block``
2. Subsystem support
    - have inputs or outputs
    - have no state variables
    - are a subclass of ``SubsysytemBlock`` |rarr| ``Block``

"""

# The constructor of each class ``MyClass`` with a ``@block`` decorator becomes a method ``MYCLASS()`` of the BlockDiagram instance.

import importlib.util
import numpy as np
import copy

import bdsim
from bdsim.components import SubsystemBlock, SourceBlock, SinkBlock, FunctionBlock

# ------------------------------------------------------------------------ #
class Item(FunctionBlock):

    """
    :blockname:`ITEM`

    .. table::
       :align: left

    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | 1          | 1       | 0       |
    +------------+---------+---------+
    | dict       | any     |         |
    +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, item, **blockargs):
        """
        Selector item from a dictionary signal.

        :param item: name of dictionary item
        :type item: str
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: An ITEM block
        :rtype: Item instance

        For a dictionary type input signal, select one item as the output signal.
        For example::

            ITEM('xd')

        selects the ``xd`` item from the dictionary signal input to the block.

        A dictionary signal can serve a similar purpose to a "bus" in Simulink(R).

        This is somewhat like a demultiplexer :class:`DeMux` but allows for
        named heterogeneous data.

        :seealso: :class:`Dict`
        """

        super().__init__(**blockargs)
        self.item = item

    def output(self, t=None):
        # TODO, handle inputs that are vectors themselves
        assert isinstance(self.inputs[0], dict), "Input signal must be a dict"
        assert self.item in self.inputs[0], "Item is not in input dict"
        return [self.inputs[0][self.item]]


class Dict(FunctionBlock):

    """
    :blockname:`DICT`

    .. table::
       :align: left

    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | N          | 1       | 0       |
    +------------+---------+---------+
    | any        | dict    |         |
    +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, item, **blockargs):
        """
        Create a dictionary signal.

        :param keys: list of dictionary keys
        :type keys: list
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A DICT block
        :rtype: Dict instance

        Inputs are assigned to a dictionary signal, using the corresponding
        names from ``keys``.
        For example::

            DICT(['x', 'xd', 'xdd'])

        expects three inputs and assigns them to dictionary items ``x``, ``xd``, ``xdd`` of
        the output dictionary respectively.

        A dictionary signal can serve a similar purpose to a "bus" in Simulink(R).

        This is somewhat like a multiplexer :class:`Mux` but allows for
        named heterogeneous data.

        :seealso: :class:`Item` :class:`Mux`
        """

        super().__init__(**blockargs)
        self.item = item

    def output(self, t=None):
        # TODO, handle inputs that are vectors themselves
        assert isinstance(self.inputs[0], dict), "Input signal must be a dict"
        assert self.item in self.inputs[0], "Item is not in signal dict"
        return [self.inputs[0][self.item]]


# ------------------------------------------------------------------------ #
class Mux(FunctionBlock):
    """
    :blockname:`MUX`

    .. table::
       :align: left

    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | nin        | 1       | 0       |
    +------------+---------+---------+
    | float,     | A(M,)   |         |
    | A(N,)      | A(M,)   |         |
    +------------+---------+---------+
    """

    nin = -1
    nout = 1

    def __init__(self, nin=1, **blockargs):
        """
        Multiplex signals.

        :param nin: Number of input ports, defaults to 1
        :type nin: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A MUX block
        :rtype: Mux instance

        This block takes a number of scalar or 1D-array signals and concatenates
        them into a single 1-D array signal.  For example::

            MUX(2, inputs=(func1[2], sum3))

        multiplexes the outputs of blocks ``func1`` (port 2) and ``sum3`` into a
        single output vector as a 1D-array.

        :seealso: :class:`Dict`
        """
        super().__init__(nin=nin, **blockargs)

    def output(self, t=None):
        # TODO, handle inputs that are vectors themselves
        out = []
        for input in self.inputs:
            if isinstance(input, (int, float, bool)):
                out.append(input)
            elif isinstance(input, np.ndarray):
                out.extend(input.flatten().tolist())
        return [np.array(out)]


# ------------------------------------------------------------------------ #
class DeMux(FunctionBlock):
    """
    :blockname:`DEMUX`

    .. table::
       :align: left

    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | 1          | nout    | 0       |
    +------------+---------+---------+
    | float,     | float   |         |
    | A(nout,)   |         |         |
    +------------+---------+---------+
    """

    nin = 1
    nout = -1

    def __init__(self, nout=1, **blockargs):
        """
        Demultiplex signals.

        :param nout: number of outputs, defaults to 1
        :type nout: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A DEMUX block
        :rtype: DeMux instance

        This block has a single input port and ``nout`` output ports.  A 1D-array
        input signal (with ``nout`` elements) is routed element-wise to individual
        scalar output ports.

        """
        super().__init__(nout=nout, **blockargs)

    def output(self, t=None):
        # TODO, handle inputs that are vectors themselves
        assert (
            len(self.inputs[0]) == self.nout
        ), "Input width not equal to number of output ports"
        return list(self.inputs[0])


# ------------------------------------------------------------------------ #


class Index(FunctionBlock):
    """
    :blockname:`INDEX`

    .. table::
       :align: left

    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | 1          | 1       | 0       |
    +------------+---------+---------+
    | ndarray    | ndarray |         |
    +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, index=[], **blockargs):
        """
        Index an iterable signal.

        :param index: elements of input array, defaults to []
        :type index: list, slice or str, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: An INDEX block
        :rtype: Index instance

        The specified element(s) of the input iterable (list, string, etc.)
        are output.  The index can be an integer, sequence of integers, a Python slice
        object, or a string with Python slice notation, eg. ``"::-1"``.

        :seealso: :class:`Slice1` :class:`Slice2`
        """
        super().__init__(**blockargs)

        if isinstance(index, str):
            args = [None if a == "" else int(a) for a in index.split(":")]
            self.index = slice(*args)
        self.index = index

    def output(self, t=None):
        if len(self.index) == 1:
            return [self.inputs[0][self.index[0]]]
        else:
            return [np.r_[[self.inputs[0][i] for i in self.index]]]


# ------------------------------------------------------------------------ #


class SubSystem(SubsystemBlock):
    """
    :blockname:`SUBSYSTEM`

    .. table::
       :align: left

    +------------+------------+---------+
    | inputs     | outputs    |  states |
    +------------+------------+---------+
    | ss.in.nout | ss.out.nin | 0       |
    +------------+------------+---------+
    | any        | any        |         |
    +------------+------------+---------+
    """

    nin = -1
    nout = -1

    def __init__(self, subsys, nin=1, nout=1, **blockargs):
        """
        Instantiate a subsystem.

        :param subsys: Subsystem as either a filename or a ``BlockDiagram`` instance
        :type subsys: str or BlockDiagram

        :param nin: Number of input ports, defaults to 1
        :type nin: int, optional
        :param nout: Number of output ports, defaults to 1
        :type nout: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :raises ImportError: DESCRIPTION
        :raises ValueError: DESCRIPTION
        :return: A SUBSYSTEM block
        :rtype: SubSystem instance

        This block represents a subsystem in a block diagram.  The definition
        of the subsystem can be:

            - the name of a module which is imported and must contain only
              only ``BlockDiagram`` instance, or
            - a ``BlockDiagram`` instance

        The referenced block diagram must contain one or both of:

            - one ``InPort`` block, which has outputs but no inputs. These
              outputs are connected to the inputs to the enclosing ``SubSystem`` block.
            - one ``OutPort`` block, which has inputs but no outputs. These
              inputs are connected to the outputs to the enclosing ``SubSystem`` block.

        .. note::

        - The referenced block diagram is treated like a macro and copied into
          the parent block diagram at compile time. The ``SubSystem``, ``InPort`` and
          ``OutPort`` blocks are eliminated, that is, all hierarchical structure is
          lost.
        - The same subsystem can be used multiple times, its blocks and wires
           will be cloned.  Subsystems can also include subsystems.
        - The number of input and output ports is not specified, they are computed
          from the number of ports on the ``InPort`` and ``OutPort`` blocks within the
          subsystem.
        """
        super().__init__(**blockargs)

        if isinstance(subsys, str):
            # attempt to import the file
            try:
                module = importlib.import_module(subsys, package=".")
            except SyntaxError:
                print("-- syntax error in block definiton: " + subsys)
            except ModuleNotFoundError:
                print("-- module not found ", subsys)
            # get all the bdsim.BlockDiagram instances
            simvars = [
                name
                for name, ref in module.__dict__.items()
                if isinstance(ref, bdsim.BlockDiagram)
            ]
            if len(simvars) == 0:
                raise ImportError("no bdsim.Simulation instances in imported module")
            elif len(simvars) > 1:
                raise ImportError(
                    "multiple bdsim.Simulation instances in imported module"
                    + str(simvars)
                )
            subsys = module.__dict__[simvars[0]]
            self.ssvar = simvars[0]
        elif isinstance(subsys, bdsim.BlockDiagram):
            # use an in-memory diagram
            self.ssvar = None
        else:
            raise ValueError("argument must be filename or BlockDiagram instance")

        # check if valid input and output ports
        ninp = 0
        noutp = 0
        for b in subsys.blocklist:
            if b.type == "inport":
                ninp += 1
            elif b.type == "outport":
                noutp += 1

        if ninp > 1:
            raise ValueError("subsystem cannot have more than one INPORT block")
        if noutp > 1:
            raise ValueError("subsystem cannot have more than one OUTPORT block")
        if ninp + noutp == 0:
            raise ValueError("subsystem cannot have zero INPORT or OUTPORT blocks")

        # it's valid, make a deep copy
        self.subsystem = copy.deepcopy(subsys)

        # get references to the input and output port blocks
        self.inport = None
        self.outport = None
        for b in self.subsystem.blocklist:
            if b.type == "inport":
                self.inport = b
            elif b.type == "outport":
                self.outport = b

        self.ssname = subsys.name

        self.nin = ninp
        self.nout = noutp


# ------------------------------------------------------------------------ #


class InPort(SubsystemBlock):
    """
    :blockname:`INPORT`

    .. table::
       :align: left

    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | 0          | nout    | 0       |
    +------------+---------+---------+
    |            | any     |         |
    +------------+---------+---------+
    """

    nin = 0
    nout = -1

    def __init__(self, nout=1, **blockargs):
        """
        Input ports for a subsystem.

        :param nout: Number of output ports, defaults to 1
        :type nout: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: An INPORT block
        :rtype: InPort instance

        This block connects a subsystem to a parent block diagram.  Inputs to the
        parent-level ``SubSystem`` block appear as the outputs of this block.

        .. note:: Only one ``INPORT`` block can appear in a block diagram but it
            can have multiple ports.  This is different to Simulink(R) which
            would require multiple single-port input blocks.
        """
        super().__init__(nout=nout, **blockargs)

    def output(self, t=None):
        # signal feed through

        return self.inputs


# ------------------------------------------------------------------------ #


class OutPort(SubsystemBlock):
    """
    :blockname:`OUTPORT`

    .. table::
       :align: left

    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | nin        | 0       | 0       |
    +------------+---------+---------+
    | any        |         |         |
    +------------+---------+---------+
    """

    nin = -1
    nout = 0

    def __init__(self, nin=1, **blockargs):
        """
        Output ports for a subsystem.

        :param nin: Number of input ports, defaults to 1
        :type nin: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A OUTPORT block
        :rtype: OutPort instance

        This block connects a subsystem to a parent block diagram.  The the
        inputs of this block become the outputs of the parent-level ``SubSystem``
        block.

        .. note:: Only one ``OUTPORT`` block can appear in a block diagram but it
            can have multiple ports.  This is different to Simulink(R) which
            would require multiple single-port output blocks.
        """
        super().__init__(nin=nin, **blockargs)

    def output(self, t=None):
        # signal feed through
        return self.inputs


if __name__ == "__main__":  # pragma: no cover

    from pathlib import Path

    exec(
        open(
            Path(__file__).parent.parent.parent / "tests" / "test_connections.py"
        ).read()
    )
