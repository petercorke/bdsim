import numpy as np
import math

import matplotlib.pyplot as plt
import time

from bdsim.components import *


@block
class _Bicycle(Transfer):
    def __init__(self, x0=None, L=1, vlim=1, slim=1, **kwargs):
        """
        
        :param x0: DESCRIPTION, defaults to None
        :type x0: TYPE, optional
        :param L: DESCRIPTION, defaults to 1
        :type L: TYPE, optional
        :param **kwargs: DESCRIPTION
        :type **kwargs: TYPE
        :return: DESCRIPTION
        :rtype: TYPE

        """
        self._names_in=['v', '$\gamma$']
        self._names_out=['x', 'y', '$\theta$']
        self._names_state = ['x', 'y', '$\theta$']
        super().__init__(**kwargs)
        self.nin = 2
        self.nout = 3
        self.nstates = 3
        self.vlim = vlim
        self.slim = slim
        self.type = 'bicycle'

        
        self.L = L
        if x0 is None:
            self._x0 = np.zeros((self.nstates,))
        else:
            assert len(x0) == self.nstates, "x0 is {:d} long, should be {:d}".format(len(x0), self.nstates)
            self._x0 = x0
        
    def output(self, t):
        return list(self._x)
    
    def deriv(self):
        theta = self._x[2]
        
        # get inputs and clip them
        v = self.inputs[0]
        v = min(self.vlim, max(v, -self.vlim))
        gamma = self.inputs[1]
        gamma = min(self.slim, max(gamma, -self.slim))
        
        xd = np.r_[v*math.cos(theta), v*math.sin(theta), v*math.tan(gamma)/self.L ]
        return xd
    
@block
class _Unicycle(Transfer):
    def __init__(self, x0=None, **kwargs):
        super().__init__(**kwargs)
        self.nin = 2
        self.nout = 3
        self.nstates = 3
        self.type = 'unicycle'
        
        if x0 is None:
            self._x0 = np.zeros((slef.nstates,))
        else:
            assert len(x0) == self.nstates, "x0 is {:d} long, should be {:d}".format(len(x0), self.nstates)
            self._x0 = x0
        
    def output(self, t):
        return list(self._x)
    
    def deriv(self):
        theta = self._x[2]
        v = self.inputs[0]; omega = self.inputs[1]
        xd = np.r_[v*math.cos(theta), v*math.sin(theta), omega]
        return xd
    
    # diffsteer
    # quadrotor
    # quadrotor plot
    # seriallink
    # RNE
    # fkine
    # robot plot