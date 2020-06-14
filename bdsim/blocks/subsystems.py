
"""
Define subsystem connection blocks for use in block diagrams.  These are blocks that:

- have inputs or outputs
- have no state variables
- are a subclass of ``SubsysttemBlock``


Each class MyClass in this module becomes a method MYCLASS() of the Simulation object.
"""

import importlib.util


"""
At compile time we remove/disable certain wires.
Block should have the subsystem enable status
"""
import bdsim
from bdsim.components import SubsystemBlock, SourceBlock, SinkBlock, block


@block
class SubSystem(SubsystemBlock):
    
    def __init__(self, fname, **kwargs):
        super().__init__(**kwargs)
        self.type = 'subsystem'
        
        # attempt to import the file
        try:
            module = importlib.import_module(fname, package='.')
        except SyntaxError:
            print('-- syntax error in block definiton: ' + file)
        except ModuleNotFoundError:
            print('-- module not found ', fname)

        # get all the bdsim.Simulation instances
        simvars = [name for name, ref in module.__dict__.items() if isinstance(ref, bdsim.Simulation)]
        if len(simvars) == 0:
            raise ImportError('no bdsim.Simulation instances in imported module')
        elif len(simvars) > 1:
            raise ImportError('multiple bdsim.Simulation instances in imported module' + str(simvars))
            
        self.subsystem = module.__dict__[simvars[0]]
        self.ssvar = simvars[0]

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