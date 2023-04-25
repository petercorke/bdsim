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

    Select item from a dictionary signal.

    :inputs: 1
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - 0
            - dict
            - ``D``
        *   - Output
            - 0
            - any
            - ``D[i]``

    For a dictionary type input signal, select one item as the output signal.
    For example::

        item = bd.ITEM("xd")

    selects the ``xd`` item from the dictionary signal input to the block.

    This is somewhat like a demultiplexer :class:`DeMux` but allows for
    named heterogeneous data.
    A dictionary signal can serve a similar purpose to a "bus" in Simulink(R).

    :seealso: :class:`Dict`
    """

    nin = 1
    nout = 1

    def __init__(self, item, **blockargs):
        """
        :param item: name of dictionary item
        :type item: str
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """

        super().__init__(**blockargs)
        self.item = item

    def output(self, t, inports, x):
        input = inports[0]
        # TODO, handle inputs that are vectors themselves
        assert isinstance(input, dict), "Input signal must be a dict"
        assert self.item in input, "Item is not in input dict"
        return [input[self.item]]


class Dict(FunctionBlock):

    """
    :blockname:`DICT`

    Create a dictionary signal.

    :inputs: N
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - i
            - any
            - :math:`x_i`
        *   - Output
            - 0
            - dict
            - ``{key: x[i] for i, key in enumerate(keys)}``

    Inputs are assigned to a dictionary signal, using the corresponding
    names from ``keys``.
    For example::

        dd = bd.DICT(["x", "xd", "xdd"])

    expects three inputs and assigns them to dictionary items ``x``, ``xd``, ``xdd`` of
    the output dictionary respectively.

    This is somewhat like a multiplexer :class:`Mux` but allows for named heterogeneous
    data.  A dictionary signal can serve a similar purpose to a "bus" in Simulink(R).


    :seealso: :class:`Item` :class:`Mux`
    """

    nin = 1
    nout = 1

    def __init__(self, keys, **blockargs):
        """
        :param keys: list of dictionary keys
        :type keys: list
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """

        super().__init__(**blockargs)
        self.keys = keys

    def output(self, t, inports, x):
        return {key: inports[i] for i, key in enumerate(self.keys)}


# ------------------------------------------------------------------------ #
class Mux(FunctionBlock):
    """
    :blockname:`MUX`

    Multiplex signals.

    :inputs: N
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - i
            - float, ndarray
            - :math:`x_i`
        *   - Output
            - 0
            - ndarray
            - :math:`[x_0 \ldots x_{N-1}]`

    This block takes a number of scalar or 1D-array signals and concatenates
    them into a single 1-D array signal.  For example::

        mux = bd.MUX(2)

    :seealso: :class:`Demux` :class:`Dict`
    """

    # TODO could be generalized to creating a list of non numeric data

    nin = -1
    nout = 1

    def __init__(self, nin=1, **blockargs):
        """
        :param nin: Number of input ports, defaults to 1
        :type nin: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(nin=nin, **blockargs)

    def output(self, t, inports, x):
        # TODO, handle inputs that are vectors themselves
        out = []
        for input in inports:
            if isinstance(input, (int, float, bool)):
                out.append(input)
            elif isinstance(input, np.ndarray):
                out.extend(input.flatten().tolist())
        return [np.array(out)]


# ------------------------------------------------------------------------ #
class DeMux(FunctionBlock):
    """
    :blockname:`DEMUX`

    Demultiplex signals.

    :inputs: 1
    :outputs: N
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - 0
            - iterable
            - :math:`x`
        *   - Output
            - i
            - any
            - :math:`x_i`

    This block has a single input port and ``nout`` output ports.  The input signal is
    an iterable whose ``nout`` elements are routed element-wise to individual scalar
    output ports.  If the input is a 1D Numpy array, then each output port is an
    element of that array.

    :seealso: :class:`Mux`
    """

    nin = 1
    nout = -1

    def __init__(self, nout=1, **blockargs):
        """
        :param nout: number of outputs, defaults to 1
        :type nout: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(nout=nout, **blockargs)

    def output(self, t, inports, x):
        input = inports[0]
        # TODO, handle inputs that are vectors themselves
        assert (
            len(input) == self.nout
        ), "Input width not equal to number of output ports"
        return list(input)


# ------------------------------------------------------------------------ #


class Index(FunctionBlock):
    """
    :blockname:`INDEX`

    :inputs: 1
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - i
            - iterable
            - :math:`x`
        *   - Output
            - j
            - iterable
            - :math:`x_i`

    The specified element(s) of the input iterable (list, string, etc.)
    are output.  The index can be an integer, sequence of integers, a Python slice
    object, or a string with Python slice notation, eg. ``"::-1"``.

    :seealso: :class:`Slice1` :class:`Slice2`
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
        """
        super().__init__(**blockargs)

        if isinstance(index, str):
            args = [None if a == "" else int(a) for a in index.split(":")]
            self.index = slice(*args)
        self.index = index

    def output(self, t, inports, x):
        input = inports[0]
        if len(self.index) == 1:
            return [input[self.index[0]]]
        elif isinstance(input, np.ndarray):
            return [np.array([input[i] for i in self.index])]
        else:
            return [[input[i] for i in self.index]]


# ------------------------------------------------------------------------ #


class SubSystem(SubsystemBlock):
    """
    :blockname:`SUBSYSTEM`

    Instantiate a subsystem.

    :inputs: N
    :outputs: M
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - i
            - any
            - :math:`x_i`
        *   - Output
            - j
            - any
            - :math:`y_j`

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

    nin = -1
    nout = -1

    def __init__(self, subsys, nin=1, nout=1, **blockargs):
        """
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

    Input ports for a subsystem.

    :inputs: 0
    :outputs: N
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Output
            - j
            - any
            - :math:`y_j`

    This block connects a subsystem to a parent block diagram.  Inputs to the
    parent-level ``SubSystem`` block appear as the outputs of this block.

    .. note:: Only one ``INPORT`` block can appear in a block diagram but it
        can have multiple ports.  This is different to Simulink(R) which
        would require multiple single-port input blocks.
    """

    nin = 0
    nout = -1

    def __init__(self, nout=1, **blockargs):
        """
        :param nout: Number of output ports, defaults to 1
        :type nout: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(nout=nout, **blockargs)

    def output(self, t, inports, x):
        # signal feed through

        return inports


# ------------------------------------------------------------------------ #


class OutPort(SubsystemBlock):
    """
    :blockname:`OUTPORT`

    Output ports for a subsystem.

    :inputs: N
    :outputs: 0
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - i
            - any
            - :math:`x_i`

    This block connects a subsystem to a parent block diagram.  The
    inputs of this block become the outputs of the parent-level ``SubSystem``
    block.

    .. note:: Only one ``OUTPORT`` block can appear in a block diagram but it
        can have multiple ports.  This is different to Simulink(R) which
        would require multiple single-port output blocks.
    """

    nin = -1
    nout = 0

    def __init__(self, nin=1, **blockargs):
        """
        :param nin: Number of input ports, defaults to 1
        :type nin: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(nin=nin, **blockargs)

    def output(self, t, inports, x):
        # signal feed through
        return inports


if __name__ == "__main__":  # pragma: no cover

    from pathlib import Path

    exec(
        open(
            Path(__file__).parent.parent.parent / "tests" / "test_connections.py"
        ).read()
    )
