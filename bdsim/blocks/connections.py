
"""
Define subsystem connection blocks for use in block diagrams.  These are blocks that:

- have inputs or outputs
- have no state variables
- are a subclass of ``SubsysttemBlock``


Each class MyClass in this module becomes a method MYCLASS() of the Simulation object.
"""

import importlib.util
import numpy as np
import copy

"""
At compile time we remove/disable certain wires.
Block should have the subsystem enable status
"""
import bdsim
from bdsim.components import SubsystemBlock, SourceBlock, SinkBlock, FunctionBlock, block

@block
class Mux(FunctionBlock):
    def __init__(self, nin=1, **kwargs):

        super().__init__(**kwargs)
        self.nin = nin
        self.nout = 1
        self.type = 'mux'
    
    def output(self, t=None):
        # TODO, handle inputs that are vectors themselves
        return [ np.r_[self.inputs] ]


@block
class DeMux(FunctionBlock):
    def __init__(self, nout=1, **kwargs):

        super().__init__(**kwargs)
        self.nin = 1
        self.nout = nout
        self.type = 'demux'
    
    def output(self, t=None):
        # TODO, handle inputs that are vectors themselves
        assert len(self.inputs[0]) == self.nout, 'Input width not equal to number of output ports'
        return list(self.inputs[0])

@block
class SubSystem(SubsystemBlock):
    
    def __init__(self, subsys, **kwargs):
        super().__init__(**kwargs)
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

@block
class InPort(SubsystemBlock):
    
    def __init__(self, nout=1, **kwargs):
        super().__init__(**kwargs)
        self.nout= nout
        self.type = 'inport'

@block
class OutPort(SubsystemBlock):
    
    def __init__(self, nin=1, **kwargs):
        super().__init__(**kwargs)
        self.nin = nin
        self.type = 'outport'


if __name__ == "__main__":

    import pathlib
    import os.path

    exec(open(os.path.join(pathlib.Path(__file__).parent.absolute(), "test_subsystems.py")).read())