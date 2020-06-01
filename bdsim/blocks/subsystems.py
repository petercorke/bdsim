from bdsim.components import Sink, Source, Function


# class _SubSystem(Function):
#     pass

# class _InPort(Source):
#     pass

# class _OutPort(Sink):
#     pass

"""
At compile time we remove/disable certain wires.
Block should have the subsystem enable status
"""

from bdsim.components import *


@block
class _Mux(Function):
    def __init__(self, nin=1, **kwargs):

        super().__init__(**kwargs)
        self.nin = nin
        self.nout = 1
        self.type = 'mux'
    
    def output(self, t=None):
        # TODO, handle inputs that are vectors themselves
        return [ np.r_[self.inputs] ]