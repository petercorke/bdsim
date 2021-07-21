"""
Function blocks:

- have inputs and outputs
- have no state variables
- are a subclass of ``FunctionBlock`` |rarr| ``Block``

"""

# The constructor of each class ``MyClass`` with a ``@block`` decorator becomes a method ``MYCLASS()`` of the BlockDiagram instance.

import numpy as np
import scipy.interpolate
import math
import inspect

from bdsim.components import FunctionBlock


# PID
# product
# saturation
# transform 3D points

        
class Sum(FunctionBlock):
    """
    :blockname:`SUM`
    
    .. table::
       :align: left
    
    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | len(signs) | 1       | 0       |
    +------------+---------+---------+
    | float,     | float,  |         | 
    | A(N,),     | A(N,),  |         |
    | A(N,M)     | A(N,M)  |         | 
    +------------+---------+---------+
    """

    def __init__(self, signs='++', *inputs, angles=False, **kwargs):
        """
        :param signs: signs associated with input ports, accepted characters: + or -, defaults to '++'
        :type signs: str, optional
        :param angles: the signals are angles, wraps to [-pi,pi], defaults to False
        :type angles: bool, optional
        :param kwargs: common Block options
        :return: A SUM block
        :rtype: Sum instance

        
        Create a summing junction.
    
        The number of input ports is determined by the length of the `signs`
        string.  For example::
            
            sum = bd.SUM('+-+')

        If inputs are specified then connections are automatically made::

            sum = bd.SUM('++', block1, block2)

        is equivalent to::

            sum = bd.SUM('++')
            bd.connect(block1, sum[0])
            bd.connect(block2, sum[1])

        The equivalent implicit summation blocks is created by::

            sum = block1 + block2

        which will create a summation block named "autosum.N"

            
        is a 3-input summing junction where ports 0 and 2 are added and
        port 1 is subtracted.
        """
        super().__init__(nin=len(signs), nout=1, inputs=inputs, **kwargs)
        assert isinstance(signs, str), 'first argument must be signs string'
        # self.type = 'sum'
        assert all([x in '+-' for x in signs]), 'invalid sign'
        self.signs = signs
        self.angles = angles
        
        
    def output(self, t=None):
        for i,input in enumerate(self.inputs):
            if self.signs[i] == '-':
                input = -input
            if i == 0:
                sum = input
            else:
                sum = sum + input
        
        if self.angles:
            sum = np.mod(sum + math.pi, 2 * math.pi) - math.pi

        return [sum]

# ------------------------------------------------------------------------ #
class Prod(FunctionBlock):
    """
    :blockname:`PROD`
    
    .. table::
       :align: left
    
    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | len(ops)   | 1       | 0       |
    +------------+---------+---------+
    | float,     | float,  |         | 
    | A(N,),     | A(N,),  |         |
    | A(N,M)     | A(N,M)  |         | 
    +------------+---------+---------+
    """

    def __init__(self, ops='**', *inputs, matrix=False, **kwargs):
        """
        :param ops: operations associated with input ports, accepted characters: * or /, defaults to '**'
        :type ops: str, optional
        :param inputs: Optional incoming connections
        :type inputs: Block or Plug
        :param matrix: Arguments are matrices, defaults to False
        :type matrix: bool, optional
        :param kwargs: common Block options
        :return: A PROD block
        :rtype: Prod instance
        
        Create a product junction.
    
        The number of input ports is determined by the length of the `ops`
        string.  For example::
            
            prod = PROD('*/*')
            
        is a 3-input product junction where ports 0 and 2 are multiplied and
        port 1 is divided.

        If inputs are specified then connections are automatically made::

            prod = bd.PROD('*/', block1, block2)

        is equivalent to::

            prod = bd.PROD('*/')
            bd.connect(block1, prod[0])
            bd.connect(block2, prod[1])

        The inputs can be scalars or NumPy arrays.  By default the ``*``
        and ``/`` operators are used.  The flag ``matrix`` will instead use
        ``@`` and ``@ np.linalg.inv()``.
    
        """
        super().__init__(nin=len(ops), nout=1, inputs=inputs, **kwargs)
        assert isinstance(ops, str), 'first argument must be signs string'
        # self.type = 'prod'
        assert all([x in '*/' for x in ops]), 'invalid op'
        self.ops = ops
        self.matrix = matrix
        
    def output(self, t=None):
        for i, input in enumerate(self.inputs):
            if i == 0:
                if self.ops[i] == '*':
                    prod = input
                else:
                    if self.matrix:
                        prod = numpy.linalg.inv(input)
                    prod = 1.0 / input
            else:
                if self.ops[i] == '*':
                    if self.matrix:
                        prod = prod @ input
                    else:
                        prod *= input
                else:
                    if self.matrix:
                        prod = prod @ numpy.linalg.inv(input)
                    else:
                        prod /= input

        return [prod]

# ------------------------------------------------------------------------ #

class Gain(FunctionBlock):
    """
    :blockname:`GAIN`
    
    .. table::
       :align: left
    
    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | 1          | 1       | 0       |
    +------------+---------+---------+
    | float,     | float,  |         | 
    | A(N,),     | A(N,),  |         |
    | A(N,M)     | A(N,M)  |         | 
    +------------+---------+---------+
    """

    def __init__(self, K=1, *inputs, premul=False, **kwargs):
        """
        :param K: The gain value, defaults to 1
        :type K: array_like
        :param inputs: Optional incoming connection
        :type inputs: Block or Plug
        :param premul: premultiply by constant, default is postmultiply, defaults to False
        :type premul: bool, optional
        :param kwargs: common Block options
        :return: A GAIN block
        :rtype: Gain instance
        
        Create a gain block.
    
        This block has only one input :math:`u` and one output port. The output
        is the product of the input by the gain :math:`u K`.

        If :math:`u` and ``K`` are both NumPy arrays the ``@`` operator is used.
        To premultiply by the gain, to compute :math:`K u` use the
        ``premul`` option.
        
        Either or both the input and gain can be numpy arrays and numpy will
        compute the appropriate product.  If both are numpy arrays then the
        matmult operator `@` is used and by default the input is postmultiplied
        by the gain, but this can be changed using the ``premul`` option.

        For example::

            gain = bd.GAIN(constant)

        If an input is specified then connections are automatically made::

            gain = bd.GAIN(constant, block1)

        is equivalent to::

            gain = bd.GAIN(constant)
            bd.connect(block1, gain)

        """
        super().__init__(nin=1, nout=1, **kwargs)
        self.K  = K
        # self.type = 'gain'
        self.premul = premul
        
    def output(self, t=None):
        input = self.inputs[0]
        
        if isinstance(input, np.ndarray) and isinstance(self.K, np.ndarray):
            # array x array case
            if self.premul:
                # premultiply by gain
                return [self.K @ input]
            else:
                # postmultiply by gain
                return [input @ self.K]
        else:
            return [self.inputs[0] * self.K]
        
# ------------------------------------------------------------------------ #

class Clip(FunctionBlock):
    """
    :blockname:`CLIP`
    
    .. table::
       :align: left
    
    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | 1          | 1       | 0       |
    +------------+---------+---------+
    | float,     | float,  |         | 
    | A(N,)      | A(N,)   |         |
    +------------+---------+---------+

    """
    def __init__(self, min=-math.inf, max=math.inf, **kwargs):
        """
        :param min: Minimum value, defaults to -math.inf
        :type min: float or array_like, optional
        :param max: Maximum value, defaults to math.inf
        :type max: float or array_like, optional
        :param kwargs: common Block options
        :return: A CLIP block
        :rtype: Clip instance

        Create a value clipping block.
        
        Input signals are clipped to the range from ``minimum`` to ``maximum`` inclusive.
        
        The signal can be a vector in which case each element is clipped.  The
        minimum and maximum values can be:
            
            - a scalar, in which case the same value applies to every element of 
              the input vector , or
            - a vector, of the same shape as the input vector that applies elementwise to
              the input vector.

        For example::

            clip = bd.CLIP()

        If an input is specified then a connection is automatically made::

            clip = bd.CLIP(block1, args)

        is equivalent to::

            clip = bd.CLIP()
            bd.connect(block1, clip)
        
        """
        super().__init__(nin=1, nout=1, **kwargs)
        self.min = min
        self.max = max
        # self.type = 'clip'
        
    def output(self, t=None):
        input = self.inputs[0]
        
        if isinstance(input, np.ndarray):
            out = np.clip(input, self.min, self.max)
        else:
            out = min(self.max, max(input, self.min))
        return [ out ]
# ------------------------------------------------------------------------ #

# TODO can have multiple outputs: pass in a tuple of functions, return a tuple
class Function(FunctionBlock):
    """
    :blockname:`FUNCTION`
    
    .. table::
       :align: left
    
    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | nin        | nout    | 0       |
    +------------+---------+---------+
    | any        | any     |         | 
    +------------+---------+---------+
 
    """

    def __init__(self, func=None, nin=1, nout=1, dict=False, pargs=[], dargs={}, **kwargs):
        """
        :param func: A function or lambda, or list thereof, defaults to None
        :type func: callable or sequence of callables, optional
        :param nin: number of inputs, defaults to 1
        :type nin: int, optional
        :param nout: number of outputs, defaults to 1
        :type nout: int, optional
        :param dict: pass in a reference to a dictionary instance, defaults to False
        :type dict: bool, optional
        :param pargs: extra positional arguments passed to the function, defaults to []
        :type pargs: list, optional
        :param dargs: extra keyword arguments passed to the function, defaults to {}
        :type dargs: dict, optional
        :param kwargs: common Block options
        :return: A FUNCTION block
        :rtype: A Function instance
    
        Create a Python function block.
    
        A block with one output port that sums its two input ports is::
            
            FUNCTION(lambda u1, u2: u1+u2, nin=2)
            
        A block with a function that takes two inputs and has two additional arguments::
        
            def myfun(u1, u2, param1, param2):
                pass
            
            FUNCTION(myfun, nin=2, args=(p1,p2))
            
        If we need access to persistent (static) data, to keep some state::
        
            def myfun(u1, u2, param1, param2, dict):
                pass
            
            FUNCTION(myfun, nin=2, args=(p1,p2), dict=True)
            
        where a dictionary is passed in as the last argument which is kept from call to call.
            
        A block with a function that takes two inputs and additional keyword arguments::
        
            def myfun(u1, u2, param1=1, param2=2, param3=3, param4=4):
                pass
            
            FUNCTION(myfun, nin=2, args={'param2':7, 'param3':8})
                     
        A block with two inputs and two outputs, the outputs are defined by two lambda
        functions with the same inputs::
            
            FUNCTION( [ lambda x, y: x_t, lanbda x, y: x* y])
        
        A block with two inputs and two outputs, the outputs are defined by a 
        single function::
            
            def myfun(u1, u2):
                return [ u1+u2, u1*u2 ]
            
            FUNCTION( myfun, nin=2, nout=2)

        For example::

            func = bd.FUNCTION(myfun, args)

        If inputs are specified then connections are automatically made and
        are assigned to sequential input ports::

            func = bd.FUNCTION(myfun, block1, block2, args)

        is equivalent to::

            func = bd.FUNCTION(myfun, args)
            bd.connect(block1, func[0])
            bd.connect(block2, func[1])
        """
        super().__init__(nin=nin, nout=nout, **kwargs)
        # self.nin = nin

        if isinstance(func, (list, tuple)):
            for f in func:
                assert callable(f), 'Function must be a callable'
                if kwargs is None:
                    # we can check the number of arguments
                    n = len(inspect.signature(func).parameters)
                    if dict:
                        n -= 1  # discount dict if used
                    if nin + len(args) != n:
                        raise ValueError(
    f"argument count mismatch: function has {n} args, dict={dict}, nin={nin}"
                                        )
        elif callable(func):
            if len(kwargs) == 0:
                # we can check the number of arguments
                n = len(inspect.signature(func).parameters)
                if dict:
                    n -= 1  # discount dict if used
                if nin + len(args) != n:
                    raise ValueError(
    f"argument count mismatch: function has {n} args, dict={dict}, nin={nin}"
                                    )
            # self.nout = nout
            
        self.func  = func
        if dict:
            self.userdata = {}
            args += (self.userdata,)
        else:
            self.userdata = None
        self.args = pargs
        self.kwargs = dargs

    def start(self, state=None):
        super().start()
        if self.userdata is not None:
            self.userdata.clear()
            print('clearing user data')

    def output(self, t=None):
        if callable(self.func):
            # single function
            try:
                val = self.func(*self.inputs, *self.args, **self.kwargs)
            except TypeError:
                raise RuntimeError('Function invocation failed, check number of arguments') from None
            if isinstance(val, (list, tuple)):
                if len(val) != self.nout:
                    raise RuntimeError('Function returns wrong number of arguments: ' + str(self))
                return val
            else:
                if self.nout != 1:
                    raise RuntimeError('Function returns wrong number of arguments: ' + str(self))
                return [val]
        else:
            # list of functions
            out = []
            for f in self.func:
                try:
                    val = f(*self.inputs, *self.args, **self.kwargs)
                except TypeError:
                    raise RuntimeError('Function invocation failed, check number of arguments') from None
                out.append(val)
            return out
        
class Interpolate(FunctionBlock):
    """
    :blockname:`INTERPOLATE`
    
    .. table::
       :align: left
    
    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | 0 or 1     | 1       | 0       |
    +------------+---------+---------+
    | float      | any     |         | 
    +------------+---------+---------+
    """

    def __init__(self, x=None, y=None, xy=None, time=False, kind='linear', **kwargs):
        """
        :param x: x-values of function, defaults to None
        :type x: array_like, shape (N,) optional
        :param y: y-values of function, defaults to None
        :type y: array_like, optional
        :param xy: combined x- and y-values of function, defaults to None
        :type xy: array_like, optional
        :param time: x new is simulation time, defaults to False
        :type time: bool, optional
        :param kind: interpolation method, defaults to 'linear'
        :type kind: str, optional
        :param kwargs: common Block options
        :return: An INTERPOLATE block
        :rtype: An Interpolate instance
        
        Create an interpolation block.
    
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
        self.time = time
        if time:
            nin = 0
            self.blockclass = 'source'
        else:
            nin = 1
        super().__init__(nin=nin, nout=1, **kwargs)
        # self.type = 'function'

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
        self.f = scipy.interpolate.interp1d(x=x, y=y, kind=kind, axis=0)
        self.x = x
                
    def start(self, **kwargs):
        if self.time:
            assert self.x[0] <= 0, 'interpolation not defined for t=0'
            assert self.x[-1] >= self.bd.T, 'interpolation not defined for t=T'
        
    def output(self, t=None):
        if self.time:
            xnew = t
        else:
            xnew = self.inputs[0]
        return [self.f(xnew)]


if __name__ == "__main__":

    import pathlib
    import os.path

    exec(open(os.path.join(pathlib.Path(__file__).parent.absolute(), "test_functions.py")).read())
