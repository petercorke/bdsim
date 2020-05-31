#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Define fundamental blocks available for use in block diagrams.

Each class _MyClass in this module becomes a method MYCLASS() of the Simulation object.
This is done in Simulation.__init__()

All arguments to MYCLASS() must be named arguments and passed through to the constructor
_MyClass.__init__().

These classses must subclass one of

- Source, output is a constant or function of time
- Sink, input only
- Transfer, output is a function of state self.x (no pass through)
- Function, output is a direct function of input

These classes all subclass Block.

Every class defined here provides several methods:
    
- __init__, mandatory to handle block specific parameter arguments
- reset, 
- output, to compute the output value as a function of self.inputs which is 
  a dict indexed by input number
- deriv, for Transfer subclass only, return the state derivative vector
- check, to validate parameter settings

Created on Thu May 21 06:39:29 2020

@author: Peter Corke
"""
import numpy as np
import math

import matplotlib.pyplot as plt
import inspect

from bdsim.components import *

print('in transfers')
# ------------------------------------------------------------------------ #
#@block
# class _Integrator(Transfer):
#     def __init__(self, N=1, order=1, limit=None, **kwargs):
#         super().__init__(**kwargs)
#         self.N = N
#         self.order = order
#         self.limit = limit
        
#         self.nin = N
#         self.nout = N
#         self.nstates = N*order

# ------------------------------------------------------------------------ #

@block
class _LTI_SISO(Transfer):
    def __init__(self, N=1, D=[1, 1], x0=None, **kwargs):
        """
        Create a SISO LTI block.
        
        :param N: numerator coefficients, defaults to 1
        :type N: array_like, optional
        :param D: denominator coefficients, defaults to [1, 1]
        :type D: array_like, optional
        :param x0: initial states, defaults to zero
        :type x0: array_like, optional
        :param **kwargs: common Block options
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
            
        is the transfer function :math:`\frac{s+2}{2s^2+3s-4}`

        """
        super().__init__(**kwargs)
        if not isinstance(N, list):
            N = [N]
        if not isinstance(D, list):
            D = [D]
        self.N = N
        self.D = N
        n = len(D) - 1
        nn = len(N)
        if x0 is None:
            self.x0 = np.zeros((n,))
        else:
            self.x0 = x0
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
        
        print('A=', self.A)
        print('B=', self.B)
        print('C=', self.C)
        
    def output(self, t=None):
        return list(self.C*self.x)
    
    def deriv(self):
        return self.A@self.x + self.B@np.array(self.inputs)



if __name__ == "__main__":


    import unittest

    class BlockTest(unittest.TestCase):



        def test_LTI_SISO(self):
            pass
