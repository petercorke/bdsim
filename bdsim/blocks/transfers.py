"""
Define transfer blocks for use in block diagrams.  These are blocks that:

- have inputs and outputs
- have state variables
- are a subclass of ``TransferBlock``

Each class MyClass in this module becomes a method MYCLASS() of the Simulation object.
"""

import numpy as np
import math

import matplotlib.pyplot as plt
import inspect

from bdsim.components import TransferBlock, block

# ------------------------------------------------------------------------ #
@block
class Integrator(TransferBlock):
    def __init__(self, x0=0, min=None, max=None, **kwargs):
        super().__init__(**kwargs)
        
        self.nin = 1
        self.nout = 1
        if isinstance(x0, np.ndarray):
            assert len(x0.shape) == 1, 'state must be a vector'
            self.nstates = x0.shape[0]
            if min is None:
                min = [-math.inf] * self.nstates
            else:
                assert len(min) == self.nstates, 'minimum bound length must match x0'
                
            if max is None:
                max = [math.inf] * self.nstates
            else:
                assert len(max) == self.nstates, 'mmaximum bound length must match x0'
        elif isinstance(x0, (int, float)):
            self.nstates = 1
            if min is None:
                min = -math.inf
            if max is None:
                max = math.inf
        self._x0 = np.r_[x0]
        self.min = np.r_[min]
        self.max = np.r_[max]
        
    def output(self, t=None):
        return list(self._x)
    
    def deriv(self):
        xd = np.array(self.inputs)
        for i in range(0, self.nstates):
            if self._x[i] < self.min[i] or self._x[i] > self.max[i]:
                xd[i] = 0
        return xd

# ------------------------------------------------------------------------ #

@block
class LTI_SS(TransferBlock):
    def __init__(self, A=None, B=None, C=None, x0=None, verbose=False, **kwargs):
        r"""
        Create a state-space LTI block.
        
        :param N: numerator coefficients, defaults to 1
        :type N: array_like, optional
        :param D: denominator coefficients, defaults to [1, 1]
        :type D: array_like, optional
        :param x0: initial states, defaults to zero
        :type x0: array_like, optional
        :param ``**kwargs``: common Block options
        :return: A SCOPE block
        :rtype: _LTI_SISO
        
        Describes the dynamics of a single-input single-output (SISO) linear
        time invariant (LTI) system described by numerator and denominator
        polynomial coefficients.

        Coefficients are given in the order from highest order to zeroth 
        order, ie. :math:`2s^2 - 4s +3` is ``[2, -4, 3]``.
        
        Only proper transfer functions, where order of numerator is less
        than denominator are allowed.
        
        The order of the states in ``x0`` is consistent with controller canonical
        form.
        
        Examples::
            
            LTI_SISO(N=[1,2], D=[2, 3, -4])
            
        is the transfer function :math:`\frac{s+2}{2s^2+3s-4}`.
        """
        print('in SS constructor')

        super().__init__(**kwargs)

        self.type = 'LTI SS'

        assert A.shape[0] == A.shape[1], 'A must be square'
        n = A.shape[0]
        if len(B.shape) == 1:
            self.nin = 1
            B = B.reshape((n, 1))
        else:
            self.nin = B.shape[1]
        assert B.shape[0] == n, 'B must have same number of rows as A'
        
        if len(C.shape) == 1:
            self.nout = 1
            assert C.shape[0] == n, 'C must have same number of columns as A'
            C = C.reshape((1,n))
        else:
            self.nout = C.shape[0]
            assert C.shape[1] == n, 'C must have same number of columns as A'
        
        self.A = A
        self.B = B
        self.C = C
        
        self.nstates = A.shape[0]
        
        if x0 is None:
            self._x0 = np.zeros((self.nstates,))
        else:
            self._x0 = x0
        
    def output(self, t=None):
        return list(self.C@self._x)
    
    def deriv(self):
        return self.A@self._x + self.B@np.array(self.inputs)
# ------------------------------------------------------------------------ #

@block
class LTI_SISO(LTI_SS):
    def __init__(self, N=1, D=[1, 1], x0=None, verbose=False, **kwargs):
        r"""
        Create a SISO LTI block.
        
        :param N: numerator coefficients, defaults to 1
        :type N: array_like, optional
        :param D: denominator coefficients, defaults to [1, 1]
        :type D: array_like, optional
        :param x0: initial states, defaults to zero
        :type x0: array_like, optional
        :param ``**kwargs``: common Block options
        :return: A SCOPE block
        :rtype: _LTI_SISO
        
        Describes the dynamics of a single-input single-output (SISO) linear
        time invariant (LTI) system described by numerator and denominator
        polynomial coefficients.

        Coefficients are given in the order from highest order to zeroth 
        order, ie. :math:`2s^2 - 4s +3` is ``[2, -4, 3]``.
        
        Only proper transfer functions, where order of numerator is less
        than denominator are allowed.
        
        The order of the states in ``x0`` is consistent with controller canonical
        form.
        
        Examples::
            
            LTI_SISO(N=[1, 2], D=[2, 3, -4])
            
        is the transfer function :math:`\frac{s+2}{2s^2+3s-4}`.
        """
        super(LTI_SS, self).__init__(**kwargs)
        if not isinstance(N, list):
            N = [N]
        if not isinstance(D, list):
            D = [D]
        self.N = N
        self.D = N
        n = len(D) - 1
        nn = len(N)
        if x0 is None:
            self._x0 = np.zeros((n,))
        else:
            self._x0 = x0
        assert nn <= n, 'direct pass through is not supported'
        self.type = 'LTI'
        
        self.nin = 1
        self.nout = 1
        self.nstates = n
        
        # convert to numpy arrays
        N = np.r_[np.zeros((len(D)-len(N),)), np.array(N)]
        D = np.array(D)
        
        # normalize the coefficients to obtain
        #
        #   b_0 s^n + b_1 s^(n-1) + ... + b_n
        #   ---------------------------------
        #   a_0 s^n + a_1 s^(n-1) + ....+ a_n
        

        # normalize so leading coefficient of denominator is one
        D0 = D[0]
        D = D / D0
        N = N / D0
        
        self.A = np.eye(len(D)-1, k=1)  # control canonic (companion matrix) form
        self.A[-1,:] = -D[1:]
        
        self.B = np.zeros((n,1))
        self.B[-1] = 1
        
        self.C = (N[1:] - N[0] * D[1:]).reshape((1,n))
        
        if verbose:
            print('A=', self.A)
            print('B=', self.B)
            print('C=', self.C)


if __name__ == "__main__":

    import pathlib
    import os.path

    exec(open(os.path.join(pathlib.Path(__file__).parent.absolute(), "test_transfers.py")).read())
