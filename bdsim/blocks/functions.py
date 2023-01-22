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
import spatialmath.base as smb
from typing import Any, Union, Callable

ArrayLike = Union[np.ndarray, int, float, list, tuple]

from bdsim.components import FunctionBlock


# PID
# product
# transform 3D points


class Sum(FunctionBlock):
    """Summing junction.
    :blockname:`SUM`

    :inputs: N [float, ndarray(N), ndarray(N,M)]

    :outputs: 1 [float, ndarray(N), ndarray(N,M)]

    :states: 0

    :param signs: signs associated with input ports, accepted characters: + or -, defaults to '++'
    :type signs: str, optional
    :param mode: controls angle wrapping per element, accepted characters r or c or C or L, defaults to None
    :type mode: str, optional
    :param inputs: Optional incoming connections
    :type inputs: Block or Plug
    :param blockargs: |BlockOptions|
    :type blockargs: dict
    :return: A SUM block
    :rtype: Sum instance

    Add or subtract input signals according to the `signs` string.  The
    number of input ports is the length of this string.

    For example::

        sum = bd.SUM('+-+')

    is a 3-input summing junction which computes port0 - port1 + port2.

    If some elements of the inputs are angles then ``mode`` controls, per element, how
    they are wrapped.  The elements of the string can be

    | character  | purpose                           |
    | :--------- | :-------------------------------- |
    | r          | real number, don't wrap (default) |
    | c          | angle on circle, wrap to [-π, π)  |
    | C          | angle on circle, wrap to [0, 2π)  |
    | L          | latitude angle, wrap to [0, π]    |

    For example if ``mode="rc"`` then a 2-element array would have its
    second element wrapped to the range [-π, π).

    :note: The signals must be compatible, all scalars, or all arrays
        of the same shape.
    """

    nin = -1
    nout = 1

    _modefuncs = {
        "r": lambda x: x,
        "c": smb.wrap_mpi_pi,
        "C": smb.wrap_0_2pi,
        "L": smb.wrap_0_pi,
        "l": smb.wrap_0_pi,
    }

    def __init__(self, signs: str = "++", mode: str = None, **blockargs):
        super().__init__(nin=len(signs), **blockargs)
        assert isinstance(signs, str), "first argument must be signs string"
        assert all([x in "+-" for x in signs]), "invalid sign"
        self.signs = signs
        self.mode = mode

    def output(self, t=None):
        for i, input in enumerate(self.inputs):
            # code makes no assumption about types of inputs
            # NOTE: use sum = sum =/- input rather than sum +/-= input since
            #       these are references
            if self.signs[i] == "-":
                if i == 0:
                    sum = -input
                else:
                    sum = sum - input
            else:
                if i == 0:
                    sum = input
                else:
                    sum = sum + input

        if self.mode is not None:
            if isinstance(sum, np.ndarray):
                # sum is an array
                if sum.ndim == 1:
                    if len(self.mode) != len(sum):
                        raise ValueError("length of mode string doesn't match")
                    sum = np.array(
                        [self._modefuncs[m](x) for (m, x) in zip(self.mode, sum)]
                    )
                elif sum.ndim == 2:
                    if len(self.mode) != sum.shape[0]:
                        raise ValueError(
                            "length of mode string doesn't match number of rows"
                        )
                    out = []
                    for col in sum.T:
                        out.append(
                            [self._modefuncs[m](x) for (m, x) in zip(self.mode, col)]
                        )
                    sum = np.array(out).T

                else:
                    raise ValueError("expecting 1D or 2D array")
            else:
                # sum is a scalar
                sum = self._modefuncs[self.mode[0]](sum)

        return [sum]


# ------------------------------------------------------------------------ #
class Prod(FunctionBlock):
    """Product junction.

    :blockname:`PROD`

    :inputs: N [float, ndarray(N), ndarray(N,M)]

    :outputs: 1 [float, ndarray(N), ndarray(N,M)]

    :states: 0

    :param ops: operations associated with input ports, accepted characters: * or /, defaults to '**'
    :type ops: str, optional
    :param inputs: Optional incoming connections
    :type inputs: Block or Plug
    :param matrix: Arguments are matrices, defaults to False
    :type matrix: bool, optional
    :param blockargs: |BlockOptions|
    :type blockargs: dict
    :return: A PROD block
    :rtype: Prod instance

    Multiply or divide input signals according to the `ops` string.  The
    number of input ports is the length of this string.

    For example::

        prod = PROD('*/*')

    is a 3-input product junction which computes port0 / port 1 * port2.

    :note: The inputs can be scalars or NumPy arrays.

    :note: By default the ``*`` and ``/`` operators are used which perform element-wise
        operations.

    :note: The option ``matrix`` will instead use ``@`` and ``@ np.linalg.inv()``. The
        shapes of matrices must conform.  A matrix on a ``/`` input must be square and
        non-singular.
    """

    nin = -1
    nout = 1

    def __init__(self, ops: str = "**", matrix: bool = False, **blockargs):
        super().__init__(nin=len(ops), **blockargs)
        assert isinstance(ops, str), "first argument must be signs string"
        assert all([x in "*/" for x in ops]), "invalid op"
        self.ops = ops
        self.matrix = matrix

    def output(self, t=None):
        for i, input in enumerate(self.inputs):
            if i == 0:
                if self.ops[i] == "*":
                    prod = input
                else:
                    if self.matrix:
                        prod = np.linalg.inv(input)
                    prod = 1.0 / input
            else:
                if self.ops[i] == "*":
                    if self.matrix:
                        prod = prod @ input
                    else:
                        prod = prod * input
                else:
                    if self.matrix:
                        prod = prod @ np.linalg.inv(input)
                    else:
                        prod = prod / input

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

    nin = 1
    nout = 1

    def __init__(
        self, K: Union[int, float, np.ndarray] = 1, premul: bool = False, **blockargs
    ):
        """
        Gain block.

        :param K: The gain value, defaults to 1
        :type K: array_like
        :param premul: premultiply by constant, default is postmultiply, defaults to False
        :type premul: bool, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A GAIN block
        :rtype: Gain instance

        Scale the input signal. If the input is :math:`u` the output is :math:`u K`.

        Either or both the input and gain can be Numpy arrays and Numpy will
        compute the appropriate product :math:`u K`.

        If :math:`u` and ``K`` are both NumPy arrays the ``@`` operator is used
        and :math:`u` is postmultiplied by the gain. To premultiply by the gain,
        to compute :math:`K u` use the ``premul`` option.

        For example::

            gain = bd.GAIN(constant)
        """
        super().__init__(**blockargs)
        self.K = K
        self.premul = premul

        self.add_param("K")

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

    nin = 1
    nout = 1

    def __init__(
        self, min: ArrayLike = -math.inf, max: ArrayLike = math.inf, **blockargs
    ):
        """
        Signal clipping.

        :param min: Minimum value, defaults to -math.inf
        :type min: float or array_like, optional
        :param max: Maximum value, defaults to math.inf
        :type max: float or array_like, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A CLIP block
        :rtype: Clip instance

        The input signal is clipped to the range from ``minimum`` to ``maximum`` inclusive.

        The signal can be a 1D-array in which case each element is clipped.  The
        minimum and maximum values can be:

            - a scalar, in which case the same value applies to every element of
              the input vector , or
            - a 1D-array, of the same shape as the input vector that applies elementwise to
              the input vector.

        For example::

            clip = bd.CLIP()

        """
        super().__init__(**blockargs)
        self.min = min
        self.max = max

    def output(self, t=None):
        input = self.inputs[0]

        if isinstance(input, np.ndarray):
            out = np.clip(input, self.min, self.max)
        else:
            out = min(self.max, max(input, self.min))
        return [out]


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

    nin = -1
    nout = -1

    def __init__(
        self,
        func: Callable = None,
        nin: int = 1,
        nout: int = 1,
        persistent: bool = False,
        fargs: list = None,
        fkwargs: dict = None,
        **blockargs,
    ):

        """
        Python function.

        :param func: A function or lambda, or list thereof, defaults to None
        :type func: callable or sequence of callables, optional
        :param nin: number of inputs, defaults to 1
        :type nin: int, optional
        :param nout: number of outputs, defaults to 1
        :type nout: int, optional
        :param persistent: pass in a reference to a dictionary instance to hold persistent state, defaults to False
        :type persistent: bool, optional
        :param fargs: extra positional arguments passed to the function, defaults to []
        :type fargs: list, optional
        :param fkwargs: extra keyword arguments passed to the function, defaults to {}
        :type fkwargs: dict, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict, optional
        :return: A FUNCTION block
        :rtype: A Function instance

        Inputs to the block are passed as separate arguments to the function.
        Programmatic ositional or keyword arguments can also be passed to the function.

        A block with one output port that sums its two input ports is::

            FUNCTION(lambda u1, u2: u1+u2, nin=2)

        A block with a function that takes two inputs and has two additional arguments::

            def myfun(u1, u2, param1, param2):
                pass

            FUNCTION(myfun, nin=2, args=(p1,p2))

        If we need access to persistent (static) data, to keep some state::

            def myfun(u1, u2, param1, param2, state):
                pass

            FUNCTION(myfun, nin=2, args=(p1,p2), persistent=True)

        where a dictionary is passed in as the last argument and which is kept from call to call.

        A block with a function that takes two inputs and additional keyword arguments::

            def myfun(u1, u2, param1=1, param2=2, param3=3, param4=4):
                pass

            FUNCTION(myfun, nin=2, kwargs=dict(param2=7, param3=8))

        A block with two inputs and two outputs, the outputs are defined by two lambda
        functions with the same inputs::

            FUNCTION( [ lambda x, y: x_t, lambda x, y: x* y])

        A block with two inputs and two outputs, the outputs are defined by a
        single function which returns a list::

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
        if func is None:
            raise ValueError("function is not defined")

        super().__init__(nin=nin, nout=nout, **blockargs)

        if fargs is None:
            fargs = list()
        if fkwargs is None:
            fkwargs = dict()

        # TODO, don't know why this happens
        if len(fargs) > 0 and fargs[0] == {}:
            fargs = []

        if isinstance(func, (list, tuple)):
            for f in func:
                assert callable(f), "Function must be a callable"
                if fkwargs is None:
                    # we can check the number of arguments
                    n = len(inspect.signature(func).parameters)
                    if persistent:
                        n -= 1  # discount dict if used
                    if nin + len(fargs) != n:
                        raise ValueError(
                            f"argument count mismatch: function has {n} args, dict={dict}, nin={nin}"
                        )
        elif callable(func):
            if len(fkwargs) == 0:
                # we can check the number of arguments
                n = len(inspect.signature(func).parameters)
                if persistent:
                    n -= 1  # discount dict if used
                if nin + len(fargs) != n:
                    raise ValueError(
                        f"argument count mismatch: function has {n} args, dict={dict}, nin={nin}"
                    )
            # self.nout = nout

        self.func = func
        if persistent:
            self.userdata = dict()
            fargs += (self.userdata,)
        else:
            self.userdata = None
        self.args = fargs
        self.kwargs = fkwargs

    def start(self, state=None):
        super().start()
        if self.userdata is not None:
            self.userdata.clear()
            print("clearing user data")

    def output(self, t=None):
        if callable(self.func):
            # single function
            try:
                val = self.func(*self.inputs, *self.args, **self.kwargs)
            except TypeError:
                raise RuntimeError(
                    "Function invocation failed, check number of arguments"
                ) from None
            if isinstance(val, (list, tuple)):
                if len(val) != self.nout:
                    raise RuntimeError(
                        "Function returns wrong number of arguments: " + str(self)
                    )
                return val
            else:
                if self.nout != 1:
                    raise RuntimeError(
                        "Function returns wrong number of arguments: " + str(self)
                    )
                return [val]
        else:
            # list of functions
            out = []
            for f in self.func:
                try:
                    val = f(*self.inputs, *self.args, **self.kwargs)
                except TypeError:
                    raise RuntimeError(
                        "Function invocation failed, check number of arguments"
                    ) from None
                out.append(val)
            return out


# ------------------------------------------------------------------------ #


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

    nin = -1
    nout = 1

    def __init__(
        self,
        x: Union[list, tuple, np.ndarray] = None,
        y: Union[list, tuple, np.ndarray] = None,
        xy: np.ndarray = None,
        time: bool = False,
        kind: str = "linear",
        **blockargs,
    ):
        """
        Interpolate signal.

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
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: An INTERPOLATE block
        :rtype: An Interpolate instance

        Interpolate the input signal using to a piecewise function.

        A simple triangle function with domain [0,10] and range [0,1] can be
        defined by::

            INTERPOLATE(x=(0,5,10), y=(0,1,0))

        We might also express this as a list of 2D-coordinats::

            INTERPOLATE(xy=[(0,0), (5,1), (10,0)])

        The data can also be expressed as Numpy arrays.  If that is the case,
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
            self.blockclass = "source"
        else:
            nin = 1
        super().__init__(nin=nin, **blockargs)

        if xy is None:
            # process separate x and y vectors
            x = np.array(x)
            y = np.array(y)
            assert x.shape[0] == y.shape[0], "x and y data must be same length"
        else:
            # process mixed xy data
            if isinstance(xy, (list, tuple)):
                x = [_[0] for _ in xy]
                y = [_[1] for _ in xy]
                # x = np.array(x).T
                # y = np.array(y).T
                print(x, y)
            elif isinstance(xy, np.ndarray):
                x = xy[:, 0]
                y = xy[:, 1:]
        self.f = scipy.interpolate.interp1d(x=x, y=y, kind=kind, axis=0)
        self.x = x

    def start(self, state, **blockargs):
        if self.time:
            assert self.x[0] >= 0, "interpolation not defined for t<0"
            if self.x[-1] is np.inf:
                self.x[-1] = state.T
            assert self.x[-1] >= state.T, "interpolation not defined for t>T"

    def output(self, t=None):
        if self.time:
            xnew = t
        else:
            xnew = self.inputs[0]
        return [self.f(xnew)]


if __name__ == "__main__":  # pragma: no cover

    from pathlib import Path

    exec(
        open(Path(__file__).parent.parent.parent / "tests" / "test_functions.py").read()
    )
