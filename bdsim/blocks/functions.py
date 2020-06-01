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
import scipy.interpolate
import math

from bdsim.components import *


@block
class _Sum(Function):
    def __init__(self, signs, angles=False, **kwargs):
        """
        Create a summing junction.
        
        :param signs: signs associated with input ports
        :type signs: str
        :param angles: the signals are angles, wrap to [-pi,pi)
        :type angles: bool
        :param **kwargs: common Block options
        :return: A SCOPE block
        :rtype: _Sum
        
        The number of input ports is determined by the length of the `signs`
        string.  For example::
            
            SUM('+-+')
            
        is a 3-input summing junction where ports 0 and 2 are added and
        port 1 is subtracted.

        """
        super().__init__(**kwargs)
        assert isinstance(signs, str), 'first argument must be signs string'
        self.nin = len(signs)
        self.nout = 1
        self.type = 'sum'
        self.signs = signs
        self.angles = angles
        
        signdict = {'+': 1, '-': -1}
        self.gain = [signdict[s] for s in signs]
        
    def output(self, t=None):
        sum = 0
        for i,input in enumerate(self.inputs):
            sum += self.gain[i] * input
        
        if self.angles:
            sum = np.mod(sum + math.pi, 2 * math.pi) - math.pi

        return [sum]

# ------------------------------------------------------------------------ #

@block
class _Gain(Function):
    def __init__(self, gain, order='premul', **kwargs):
        """
        Create a gain block.
        
        :param gain: The gain value
        :type gain: float
        :param order: the order of multiplication: 'postmul' [default], 'premul'
        :type order: str, optional
        :param **kwargs: common Block options
        :return: A SCOPE block
        :rtype: _Gain
        
        This block has only one input and one output port. The output is the
        product of the input by the gain.
        
        Either or both the input and gain can be numpy arrays and numpy will
        compute the appropriate product.  If both are numpy arrays then the
        matmult operator `@` is used and by default the input is postmultiplied
        by the gain, but this can be changed using the `order` option.

        """
        super().__init__(**kwargs)
        self.nin = 1
        self.nout = 1
        self.gain  = gain
        self.type = 'gain'
        self.order = order
        
    def output(self, t=None):
        input = self.inputs[0]
        
        if isinstance(input, np.ndarray) and isinstance(self.gain, np.ndarray):
            # array x array case
            if self.order == 'postmul':
                return [input @ self.gain]
            elif self.order == 'premul':
                return [self.gain @ input]
            else:
                raise ValueError('bad value of order')
        else:
            return [self.inputs[0] * self.gain]

# ------------------------------------------------------------------------ #

@block
class _Function(Function):
    def __init__(self, func, nin=1, args=(), kwargs={}, **kwargs_):
        """
        Create a Python function block.
        
        :param func: A function or lambda
        :type func: callable
        :param nin: number of inputs, defaults to 1
        :type nin: int, optional
        :param args: extra positional arguments passed to the function, defaults to ()
        :type args: tuple, optional
        :param kwargs: extra keyword arguments passed to the function, defaults to {}
        :type kwargs: dict, optional
        :param **kwargs: common Block options
        :return: A FUNCTION block
        :rtype: _Function
        
        A function block always has one output.
        
        A block that sums its two inputs is::
            
            FUNCTION(lambda u1, u2: u1+u2, nin=2)
            
        A block with a function that takes additional arguments::
        
            def myfun(u1, u2, param1, param2):
                pass
            
            FUNCTION(myfun, nin=2, args=(p1,p2))
            
            
        A block with a function that takes additional keyword arguments::
        
            def myfun(u1, u2, param1=1, param2=2, param3=3, param4=4):
                pass
            
            FUNCTION(myfun, nin=2, kwargs={'param2':7, 'param3':8}}

        """
        super().__init__(**kwargs_)
        self.nin = nin
        self.nout = 1
        self.type = 'function'
        
        
        if kwargs is None:
            # we can check the number of arguments
            n = len(inspect.signature(func).parameters)
            assert nin + len(args) == n, 'argument count mismatch'
        assert callable(func), 'Function must be a callable'
        self.func  = func
        self.args = args
        self.kwargs = kwargs

    def output(self, t=None):
        return [self.func(*self.inputs, *self.args, **self.kwargs)]
        
@block
class _Interpolate(Function):
    def __init__(self, x=None, y=None, xy=None, time=False, kind='linear', **kwargs):
        """
        
        :param x: x-values of function
        :type x: array_like, shape (N,) optional
        :param y: y-values of function
        :type y: array_like, optional
        :param xy: combined x- and y-values of function
        :type xy: array_like, optional
        :param time: x new is simulation time, defaults to False
        :type time: bool
        :param kind: interpolation method, defaults to 'linear'
        :type kind: str
        :param **kwargs: common Block options
        :return: INTERPOLATE block
        :rtype: _Function
        
        A block that interpolates its input according to a piecewise function.
        
        A simple triangle function with domain [0,10] and range [0,1] can be
        defined by::
            
        INTERPOLATE(x=(0,5,10), y=(0,1,0))
        
        We might also express this as::
            
        INTERPOLATE(xy=[(0,0), (5,1), (10,0)])
        
        The data can also be expressed as numpy arrays.  If that is the case,
        the interpolation function can be vector valued. ``x`` has a shape of
        (N,1) and ``y`` has a shape of (N,M).  Alternatively ``xy`` has a shape
        of (N,M+1) and the first column is the x-data.
        
        The input to the interpolator comes from:
            
        - Input port 0
        - Simulation time, if ``time=True``.  In this case the block has no
          input ports and is a ``Source`` not a ``Function``.

        """
        super().__init__(**kwargs)
        self.nout = 1
        self.time = time
        if time:
            self.nin = 0
            self.blockclass = 'source'
        else:
            self.nin = 1
            
        if xy is None:
            # process separate x and y vectors
            x = np.array(x)
            y = np.array(y)
            assert x.shape[0] == y.shape[0], 'x and y data must be same length'
        else:
            # process mixed xy data
            if isinstance(xy, (list, tuple)):
                x = [_[0] for _ in xy]
                y = [_[1] for _ in xy]
                # x = np.array(x).T
                # y = np.array(y).T
                print(x, y)
            elif isinstance(xy, np.ndarray):
                x = xy[:,0]
                y = xy[:,1:]
        self.f = scipy.interpolate.interp1d(x=x, y=y, kind=kind, axis=0, **kwargs)
        self.x = x
                
    def start(self, **kwargs):
        if self.time:
            assert self.x[0] <= 0, 'interpolation not defined for t=0'
            assert self.x[-1] >= self.T, 'interpolation not defined for t=T'
        
    def output(self, t=None):
        if self.time:
            xnew = t
        else:
            xnew = self.inputs[0]
        return [self.f(xnew)]



# PID
# product
# saturation
# transform 3D points

if __name__ == "__main__":

    import unittest
    import numpy.testing as nt

    class FunctionBlockTest(unittest.TestCase):


        def test_gain(self):

            block = _Gain(2)
            block.setinputs(1)
            out = block.output()
            self.assertIsInstance(out, list)
            self.assertEqual(len(out), 1)
            self.assertEqual(out[0], 2)

            block = _Gain(2)
            block.setinputs(np.r_[1,2,3])
            out = block.output()
            nt.assert_array_almost_equal(out[0], np.r_[2,4,6])

            block = _Gain(np.r_[1,2,3])
            block.setinputs(2)
            out = block.output()
            nt.assert_array_almost_equal(out[0], np.r_[2,4,6])

            block = _Gain(np.array([[1,2],[3,4]]))
            block.setinputs(2)
            out = block.output()
            nt.assert_array_almost_equal(out[0], np.array([[2,4],[6,8]]))

            block = _Gain(np.array([[1,2],[3,4]]))
            block.setinputs(np.r_[1,2])
            out = block.output()
            nt.assert_array_almost_equal(out[0], np.r_[5,11])

            block = _Gain(np.array([[1,2],[3,4]]))
            block.setinputs(np.array([[5,6],[7,8]]))
            out = block.output()
            nt.assert_array_almost_equal(out[0], np.array([[19,22],[43,50]]))

            block = _Gain(np.array([[1,2],[3,4]]), order='postmul')
            block.setinputs(np.array([[5,6],[7,8]]))
            out = block.output()
            nt.assert_array_almost_equal(out[0], np.array([[23,34],[31,46]]))

        def test_sum(self):

            block = _Sum('++')
            block.setinputs(10, 5)
            out = block.output()
            self.assertIsInstance(out, list)
            self.assertEqual(len(out), 1)
            self.assertEqual(out[0], 15)

            block = _Sum('+-')
            block.setinputs(10, 5)
            out = block.output()
            self.assertEqual(out[0], 5)

            block = _Sum('-+')
            block.setinputs(10, 5)
            out = block.output()
            self.assertEqual(out[0], -5)

            block = _Sum('+-', angles=True)
            block.setinputs(math.pi, -6*math.pi)
            out = block.output()
            self.assertEqual(out[0], -math.pi)

            block.setinputs(0, -5*math.pi)
            out = block.output()
            self.assertEqual(out[0], -math.pi)
            
            block.setinputs(math.pi, -math.pi)
            out = block.output()
            self.assertEqual(out[0], 0)

        def test_function(self):

            def test(x, y):
                return x+y
            
            block = _Function(test, nin=2)
            block.setinputs(1, 2)
            out = block.output()
            self.assertIsInstance(out, list)
            self.assertAlmostEqual(len(out), 1)
            self.assertEqual(out[0], 3)

            
            block = _Function(lambda x, y: x+y, nin=2)
            block.setinputs(1, 2)
            out = block.output()
            self.assertEqual(out[0], 3)
            
            block = _Function(lambda x, y, a, b: x+y+a+b, nin=2, args=(3,4))
            block.setinputs(1, 2)
            out = block.output()
            self.assertEqual(out[0], 10)

            block = _Function(lambda x, y, a=0, b=0: x+y+a+b, nin=2, kwargs={'a':3, 'b':4})
            block.setinputs(1, 2)
            out = block.output()
            self.assertEqual(out[0], 10)
            
        def test_interpolate(self):
            block = _Interpolate(x=(0,5,10), y=(0,1,0))
            block.setinputs(0)
            out = block.output()
            self.assertIsInstance(out, list)
            self.assertAlmostEqual(len(out), 1)
            block.setinputs(0); self.assertEqual(block.output()[0], 0)
            block.setinputs(2.5); self.assertEqual(block.output()[0], 0.5)
            block.setinputs(5); self.assertEqual(block.output()[0], 1)
            block.setinputs(7.5); self.assertEqual(block.output()[0], 0.5)
            block.setinputs(10); self.assertEqual(block.output()[0], 0)
            
            block = _Interpolate(x=np.r_[0,5,10], y=np.r_[0,1,0])
            block.setinputs(0); self.assertEqual(block.output()[0], 0)
            block.setinputs(2.5); self.assertEqual(block.output()[0], 0.5)
            block.setinputs(5); self.assertEqual(block.output()[0], 1)
            block.setinputs(7.5); self.assertEqual(block.output()[0], 0.5)
            block.setinputs(10); self.assertEqual(block.output()[0], 0)
            
            block = _Interpolate(x=np.r_[0,5,10], y=np.r_[0,1,0].reshape((3,1)))
            block.setinputs(0); self.assertEqual(block.output()[0], 0)
            block.setinputs(2.5); self.assertEqual(block.output()[0], 0.5)
            block.setinputs(5); self.assertEqual(block.output()[0], 1)
            block.setinputs(7.5); self.assertEqual(block.output()[0], 0.5)
            block.setinputs(10); self.assertEqual(block.output()[0], 0)
            
            block = _Interpolate(xy=[(0,0), (5,1), (10,0)])
            block.setinputs(0); self.assertEqual(block.output()[0], 0)
            block.setinputs(2.5); self.assertEqual(block.output()[0], 0.5)
            block.setinputs(5); self.assertEqual(block.output()[0], 1)
            block.setinputs(7.5); self.assertEqual(block.output()[0], 0.5)
            block.setinputs(10); self.assertEqual(block.output()[0], 0)
            
            # block = _Interpolate(xy=np.array([(0,0), (5,1), (10,0)]).T)
            # block.setinputs(0); self.assertEqual(block.output()[0], 0)
            # block.setinputs(2.5); self.assertEqual(block.output()[0], 0.5)
            # block.setinputs(5); self.assertEqual(block.output()[0], 1)
            # block.setinputs(7.5); self.assertEqual(block.output()[0], 0.5)
            # block.setinputs(10); self.assertEqual(block.output()[0], 0)
            
            
            block = _Interpolate(x=(0,5,10), y=(0,1,0), time=True)
            out = block.output(0)
            self.assertIsInstance(out, list)
            self.assertAlmostEqual(len(out), 1)
            self.assertEqual(block.output(0)[0], 0)
            self.assertEqual(block.output(2.5)[0], 0.5)
            self.assertEqual(block.output(5)[0], 1)
            self.assertEqual(block.output(7.5)[0], 0.5)
            self.assertEqual(block.output(10)[0], 0)
            
            block = _Interpolate(x=np.r_[0,5,10], y=np.r_[0,1,0], time=True)
            out = block.output(0)
            self.assertIsInstance(out, list)
            self.assertAlmostEqual(len(out), 1)
            out = block.output(0)
            self.assertIsInstance(out, list)
            self.assertAlmostEqual(len(out), 1)
            self.assertEqual(block.output(0)[0], 0)
            self.assertEqual(block.output(2.5)[0], 0.5)
            self.assertEqual(block.output(5)[0], 1)
            self.assertEqual(block.output(7.5)[0], 0.5)
            self.assertEqual(block.output(10)[0], 0)
            
            block = _Interpolate(xy=[(0,0), (5,1), (10,0)], time=True)
            out = block.output(0)
            self.assertIsInstance(out, list)
            self.assertAlmostEqual(len(out), 1)
            self.assertEqual(block.output(0)[0], 0)
            self.assertEqual(block.output(2.5)[0], 0.5)
            self.assertEqual(block.output(5)[0], 1)
            self.assertEqual(block.output(7.5)[0], 0.5)
            self.assertEqual(block.output(10)[0], 0)
            
            # block = _Interpolate(xy=np.array([(0,0), (5,1), (10,0)]), time=True)
            # out = block.output(0)
            # self.assertIsInstance(out, list)
            # self.assertAlmostEqual(len(out), 1)
            # self.assertEqual(block.output(0)[0], 0)
            # self.assertEqual(block.output(2.5)[0], 0.5)
            # self.assertEqual(block.output(5)[0], 1)
            # self.assertEqual(block.output(7.5)[0], 0.)
            # self.assertEqual(block.output(10)[0], 0)


    unittest.main()