
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
from bdsim.components import SubsystemBlock, SourceBlock, SinkBlock, FunctionBlock, block

# ------------------------------------------------------------------------ #
@block
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

    def __init__(self, item, *inputs, **kwargs):
        """
        :param item: name of dictionary item
        :type item: str
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param ``**kwargs``: common Block options
        :return: An ITEM block
        :rtype: Item instance
        
        Create a signal selector block.

        For a dictionary type inut signal select one item as the output signal.
        For example::
            
            ITEM('xd')
            
        selects the ``xd`` item from the dictionary output signal of the MULTIROTOR
        block.
        """

        super().__init__(nin=1, nout=1, **kwargs)
        self.type = 'item'
        self.item = item
    
    def output(self, t=None):
        # TODO, handle inputs that are vectors themselves
        assert isinstance(self.inputs[0], dict), 'Input signal must be a dict'
        assert self.item in self.inputs[0], 'Item is not in signal dict'
        return [self.inputs[0][self.item]]

# ------------------------------------------------------------------------ #
@block
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

    def __init__(self, nin=1, *inputs, **kwargs):
        """
        :param nin: Number of input ports, defaults to 1
        :type nin: int, optional
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param ``**kwargs``: common Block options
        :return: A MUX block
        :rtype: Mux instance

        Create a multiplexer block.

        This block takes a number of scalar or vector signals and concatenates
        them into a single vector signal.  For example::
            
            MUX(2, func1[2], sum3)
            
        multiplexes the outputs of blocks ``func1`` (port 2) and ``sum3`` into
        a single output vector.  If the explicit inputs are omitted they can be wired
        using the ``connect`` function.
        
        """
        super().__init__(nin=nin, nout=1, inputs=inputs, **kwargs)
        self.type = 'mux'
    
    def output(self, t=None):
        # TODO, handle inputs that are vectors themselves
        return [ np.r_[self.inputs] ]


# ------------------------------------------------------------------------ #
@block
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

    def __init__(self, nout=1, *inputs, **kwargs):
        """
        :param nout: DESCRIPTION, defaults to 1
        :type nout: TYPE, optional
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param ``**kwargs``: common Block options
        :return: A DEMUX block
        :rtype: DeMux instance
        
        Create a demultiplexer block.

        This block has a single input port and ``nout`` output ports.  A vector
        input signal (with ``nout`` elements) is routed element-wise to individual
        scalar output port.

        """
        super().__init__(nin=1, nout=nout, inputs=inputs, **kwargs)
        self.type = 'demux'
    
    def output(self, t=None):
        # TODO, handle inputs that are vectors themselves
        assert len(self.inputs[0]) == self.nout, 'Input width not equal to number of output ports'
        return list(self.inputs[0])

# ------------------------------------------------------------------------ #
@block
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

    def __init__(self, subsys, *inputs, **kwargs):
        """
        :param subsys: Subsystem as either a filename or a ``BlockDiagram`` instance
        :type subsys: str or BlockDiagram
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param ``**kwargs``: common Block options
        :raises ImportError: DESCRIPTION
        :raises ValueError: DESCRIPTION
        :return: A SUBSYSTEM block
        :rtype: SubSystem instance
        
        Create a subsystem block.

        This block represents a subsystem in a parent block diagram.  It can be
        specified as either:
            
            - the name of a module which is imported and must contain only
              only ``BlockDiagram`` instance, or
            - a ``BlockDiagram`` instance
        
        The referenced block diagram must contain one or both of:
        
            - one ``InPort`` block, which has outputs but no inputs. These
              outputs are connected to the inputs to the enclosing ``SubSystem`` block.
            - one ``OutPort`` block, which has inputs but no outputs. These
              inputs are connected to the outputs to the enclosing ``SubSystem`` block.
              
        Notes:
            
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
        super().__init__(inputs=inputs, **kwargs)
        self.type = 'subsystem'
        
        if isinstance(subsys, str):
            # attempt to import the file
            try:
                module = importlib.import_module(subsys, package='.')
            except SyntaxError:
                print('-- syntax error in block definiton: ' + subsys)
            except ModuleNotFoundError:
                print('-- module not found ', subsys)
            # get all the bdsim.BlockDiagram instances
            simvars = [name for name, ref in module.__dict__.items() if isinstance(ref, bdsim.BlockDiagram)]
            if len(simvars) == 0:
                raise ImportError('no bdsim.Simulation instances in imported module')
            elif len(simvars) > 1:
                raise ImportError('multiple bdsim.Simulation instances in imported module' + str(simvars))
            subsys = module.__dict__[simvars[0]]
            self.ssvar = simvars[0]
        elif isinstance(subsys, bdsim.BlockDiagram):
            # use an in-memory digram
            self.ssvar = None
        else:
            raise ValueError('argument must be filename or BlockDiagram instance')

        self.subsystem = copy.deepcopy(subsys)
        self.ssname = subsys.name

# ------------------------------------------------------------------------ #
@block
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
    
    def __init__(self, nout=1, **kwargs):
        """
        :param nout: Number of output ports, defaults to 1
        :type nout: int, optional
        :param ``**kwargs``: common Block options
        :return: An INPORT block
        :rtype: InPort instance

        Create an input port block for a subsystem.
        
        This block connects a subsystem to a parent block diagram.  Inputs to the
        parent-level ``SubSystem`` block appear as outputs of this block.
        """
        super().__init__(nout=nout, **kwargs)
        self.type = 'inport'

# ------------------------------------------------------------------------ #
@block
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

    def __init__(self, nin=1, *inputs, **kwargs):
        """
        :param nin: Number of input ports, defaults to 1
        :type nin: int, optional
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param ``**kwargs``: common Block options
        :return: A OUTPORT block
        :rtype: OutPort instance
        
        Create an output port block for a subsystem.

        This block connects a subsystem to a parent block diagram.  Outputs of the
        parent-level ``SubSystem`` block are the inputs of this block.
        """
        super().__init__(nin=nin, inputs=inputs, **kwargs)
        self.type = 'outport'


if __name__ == "__main__":

    import pathlib
    import os.path

    exec(open(os.path.join(pathlib.Path(__file__).parent.absolute(), "test_connections.py")).read())
