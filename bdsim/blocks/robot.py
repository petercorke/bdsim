import numpy as np
import math

import matplotlib.pyplot as plt
import time

from bdsim.Block import *



class _Bicycle(Transfer):
    def __init__(self, x0=None, L=1, **kwargs):
        super().__init__(**kwargs)
        self.nin = 2
        self.nout = 3
        self.nstates = 3
        self.L = L
        if x0 is None:
            self.x0 = np.zeros((slef.nstates,))
        else:
            assert len(x0) == self.nstates, "x0 is {:d} long, should be {:d}".format(len(x0), self.nstates)
            self.x0 = x0
        
    def output(self, t):
        return list(self.x)
    
    def deriv(self):
        theta = self.x[2]
        v = self.inputs[0]; gamma = self.inputs[1]
        xd = np.r_[v*math.cos(theta), v*math.sin(theta), v*math.tan(gamma)/self.L ]
        return xd
    
    # unicycle
    # quadrotor
    # quadrotor plot
    # seriallink
    # RNE
    # fkine
    # robot plot