#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Components of the simulation system, namely blocks, wires and plugs.
"""
import types
import math
from re import S
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation
from collections import UserDict


class BDStruct(UserDict):
    """
    A dict-like object that allows items to be added by attribute or by key.

    For example::

        >>> d = Struct('thing')
        >>> d.a = 1
        >>> d['b'] = 2
        >>> d.a
        1
        >>> d['a']
        1
        >>> d.b
        2
        >>> str(d)
        "thing {'a': 1, 'b': 2}"
    """

    def __init__(self, name="BDStruct", **kwargs):
        super().__init__()
        self.name = name
        for key, value in kwargs.items():
            self[key] = value

    def __setattr__(self, name, value):
        # invoked by struct[name] = value
        if name in ["data", "name"]:
            super().__setattr__(name, value)
        else:
            self.data[name] = value

    def add(self, name, value):
        self.data[name] = value

    def __getattr__(self, name):
        # return self.data[name]
        # some tricks to make this deepcopy safe
        # https://stackoverflow.com/questions/40583131/python-deepcopy-with-custom-getattr-and-setattr
        # https://stackoverflow.com/questions/25977996/supporting-the-deep-copy-operation-on-a-custom-class
        try:
            return self.data[name]
        except AttributeError:
            raise AttributeError("unknown attribute " + name)

    def __repr__(self):
        return str(self)

    def __str__(self):
        """
        Display struct as a string

        :return: struct in indented string format
        :rtype: str

        The struct is rendered with one line per element, and substructures
        are indented.
        """
        rows = []

        if len(self) == 0:
            return ""
        maxwidth = max([len(key) for key in self.keys()])
        # if self.name is not None:
        #     rows.append(self.name + '::')
        for k, v in sorted(self.items(), key=lambda x: x[0]):
            if isinstance(v, BDStruct):
                rows.append("{:s}.{:s}::".format(k.ljust(maxwidth), v.name))
                rows.append(
                    "\n".join(
                        [" " * (maxwidth + 3) + line for line in str(v).split("\n")]
                    )
                )
            elif isinstance(v, str):
                rows.append(
                    '{:s} = "{:s}" ({:s})'.format(
                        k.ljust(maxwidth), str(v), type(v).__name__
                    )
                )
            elif isinstance(v, np.ndarray):
                rows.append(
                    "{:s} = ndarray:{:s} {:s}".format(
                        k.ljust(maxwidth), v.dtype.type.__name__, str(v.shape)
                    )
                )
            else:
                rows.append(
                    "{:s} = {:s} ({:s})".format(
                        k.ljust(maxwidth), str(v), type(v).__name__
                    )
                )

        return "\n".join(rows)


class OptionsBase:
    """A struct like object for option handling

    Maintains an internal dict to keep options and their values.  Some of these
    values, names in the ``_priority`` list are read-only and cannot be changed.

    Values can be read/written as attributes, or the ``set`` method can take
    a sequence of ``option=value`` arguments.
    """

    def __init__(self, readonly={}, args={}):
        self._readonly = list(readonly)
        self._dict = {**args, **readonly}

    def items(self):
        return self._dict.items()

    def __getattr__(self, name):
        try:
            if name.startswith("_"):
                return self.__dict__[name]
            else:
                return self.__dict__["_dict"][name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            self.__dict__[name] = value
        else:
            dict = self.__dict__["_dict"]
            if name not in self._readonly:
                dict[name] = value
                self.__dict__["_dict"] = self.sanity(dict)

    def set(self, **changes):
        changes = self.sanity(changes)
        dict = self._dict
        for name, value in changes.items():
            if name not in self._readonly:
                dict[name] = value
            elif dict[name] != value:
                print(
                    f"attempt to programmatically set option {name}={value} is overriden by command line option {name}={dict[name]}, ignored"
                )

        self._dict = dict

    def sanity(self, options):
        return options

    def __str__(self):
        dict = self._dict
        maxwidth = max([len(option) for option in dict.keys()])
        options = sorted(dict.keys())
        return "\n".join(
            [f"{option.ljust(maxwidth)}: {dict[option]}" for option in options]
        )

    def __repr__(self):
        return str(self)


class Wire:
    """
    Create a wire.

    :param start: Plug at the start of a wire, defaults to None
    :type start: Plug, optional
    :param end: Plug at the end of a wire, defaults to None
    :type end: Plug, optional
    :param name: Name of wire, defaults to None
    :type name: str, optional
    :return: A wire object
    :rtype: Wire

    A Wire object connects two block ports.  A Wire has a reference to the
    start and end ports.

    A wire records all the connections defined by the user.  At compile time
    wires are used to build inter-block references.

    Between two blocks, a wire can connect one or more ports, ie. it can connect
    a set of output ports on one block to a same sized set of input ports on
    another block.
    """

    def __init__(self, start=None, end=None, name=None):

        self.name = name
        self.id = None
        self.start = start
        self.end = end
        self.value = None
        self.type = None
        self.name = None

    @property
    def info(self):
        """
        Interactive display of wire properties.

        Displays all attributes of the wire for debugging purposes.

        """
        print("wire:")
        for k, v in self.__dict__.items():
            print("  {:8s}{:s}".format(k + ":", str(v)))

    def __repr__(self):
        """
        Display wire with name and connection details.

        :return: Long-form wire description
        :rtype: str

        String format::

            wire.5: d2goal[0] --> Kv[0]

        """
        return str(self) + ": " + self.fullname

    @property
    def fullname(self):
        """
        Display wire connection details.

        :return: Wire name
        :rtype: str

        String format::

            d2goal[0] --> Kv[0]

        """
        return "{:s}[{:d}] --> {:s}[{:d}]".format(
            str(self.start.block), self.start.port, str(self.end.block), self.end.port
        )

    def __str__(self):
        """
        Display wire name.

        :return: Wire name
        :rtype: str

        String format::

            wire.5

        """
        s = "wire."
        if self.name is not None:
            s += self.name
        elif self.id is not None:
            s += str(self.id)
        else:
            s += "??"
        return s


# ------------------------------------------------------------------------- #


class Plug:
    """
    Create a plug.

    :param block: The block being plugged into
    :type block: Block
    :param port: The port on the block, defaults to 0
    :type port: int, optional
    :param type: 'start' or 'end', defaults to None
    :type type: str, optional
    :return: Plug object
    :rtype: Plug

    Plugs are the interface between a wire and block and have information
    about port number and wire end. Plugs are on the end of each wire, and connect a
    Wire to a specific port on a Block.

    The ``type`` argument indicates if the ``Plug`` is at:
        - the start of a wire, ie. the port is an output port
        - the end of a wire, ie. the port is an input port

    A plug can specify a set of ports on a block.

    """

    __array_ufunc__ = None  # allow block operators with NumPy values

    def __init__(self, block, port=0, type=None):

        self.block = block
        self.port = port
        self.type = type  # start

    @property
    def isslice(self):
        """
        Test if port number is a slice.

        :return: Whether the port is a slice
        :rtype: bool

        Returns ``True`` if the port is a slice, eg. ``[0:3]``, and ``False``
        for a simple index, eg. ``[2]``.
        """
        return isinstance(self.port, slice)

    @property
    def portlist(self):
        """
        Return port numbers.

        :return: Port numbers
        :rtype: iterable of int

        If the port is a simple index, eg. ``[2]`` returns [2].

        If the port is a slice, eg. ``[0:3]``, returns [0, 1, 2].
        For the case ``[2:]`` the upper bound is the maximum number of input
        or output ports of the block.
        """
        if isinstance(self.port, int):
            # easy case, this plug is a single wire
            return [self.port]

        elif isinstance(self.port, slice):
            # this plug is a bunch of wires
            start = self.port.start or 0
            step = self.port.step or 1
            if self.port.stop is None:
                if self.type == "start":
                    stop = self.block.nout
                else:
                    stop = self.block.nin
            else:
                stop = self.port.stop

            return range(start, stop, step)
        else:
            return ValueError("bad plug index")

    def __getitem__(self, i):
        return self.__class__(self.block, self.portlist[i])

    @property
    def width(self):
        """
        Return number of ports connected.

        :return: Number of ports
        :rtype: int

        If the port is a simple index, eg. ``[2]`` returns 1.

        If the port is a slice, eg. ``[0:3]``, returns 3.
        """
        return len(self.portlist)

    def __rshift__(left, right):
        """
        Overloaded >> operator for implicit wiring.

        :param left: A plug to be wired from
        :type left: Plug
        :param right: A block or plug to be wired to
        :type right: Block or Plug
        :return: ``right``
        :rtype: Block or Plug

        Implements implicit wiring, where the left-hand operator is a Plug, for example::

            a = bike[2] >> bd.GAIN(3)

        will connect port 2 of ``bike`` to the input of the GAIN block.

        Note that::

           a = bike[2] >> func[1]

        will connect port 2 of ``bike`` to port 1 of ``func``, and port 1 of ``func``
        will be assigned to ``a``.  To specify a different outport port on ``func``
        we need to use parentheses::

            a = (bike[2] >> func[1])[0]

        which will connect port 2 of ``bike`` to port 1 of ``func``, and port 0 of ``func``
        will be assigned to ``a``.

        :seealso: Block.__mul__
        """

        # called for the cases:
        # block * block
        # block * plug
        s = left.block.bd
        # assert isinstance(right, Block), 'arguments to * must be blocks not ports (for now)'
        w = s.connect(left, right)  # add a wire
        # print('plug * ' + str(w))
        return right

    def __add__(self, other):
        """
        Overloaded + operator for implicit block creation.

        :param self: A signal (plug) to be added
        :type self: Plug
        :param other: A signal (block or plug) to be added
        :type other: Block or Plug
        :return: SUM block
        :rtype: Block subclass

        This method is implicitly invoked by the + operator when the left operand is a ``Plug``
        and the right operand is a ``Plug``, ``Block`` or constant::

            result = X[i] + Y
            result = X[i] + Y[j]
            result = X[i] + C

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        Create a ``SUM("++")`` block named ``_sum.N`` whose inputs are the
        left and right operands.  For the third case, a new ``CONSTANT(C)`` block
        named ``_const.N`` is also created.

        :seealso: :meth:`Plug.__radd__` :meth:`Block.__add__`
        """
        if isinstance(other, (int, float, np.ndarray)):
            # plug + constant, create a CONSTANT block
            other = self.block.bd.CONSTANT(other)
        return self.block.bd.SUM("++", inputs=(self, other))

    def __radd__(self, other):
        """
        Overloaded + operator for implicit block creation.

        :param self: A signal (plug) to be added
        :type self: Plug
        :param other: A signal (block or plug) to be added
        :type other: Block or Plug
        :return: SUM block
        :rtype: Block subclass

        This method is implicitly invoked by the + operator when the right operand is a ``Plug``
        and the left operand is a ``Plug``, ``Block`` or constant::

            result = X + Y[j]
            result = X[i] + Y[j]
            result = C + Y[j]

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        Create a ``SUM("++") block named ``_sum.N`` whose inputs are the
        left and right operands.  For the third case, a new ``CONSTANT(C)`` block
        named ``_const.N`` is also created.

        .. note:: The inputs to the summing junction are reversed: right then left operand.

        :seealso: :meth:`Plug.__add__` :meth:`Block.__radd__`
        """
        if isinstance(other, (int, float, np.ndarray)):
            # constant + plug, create a CONSTANT block
            other = self.block.bd.CONSTANT(other)
        return self.block.bd.SUM("++", inputs=(other, self))

    def __sub__(self, other):
        """
        Overloaded - operator for implicit block creation.

        :param self: A signal (plug) to be added (minuend)
        :type self: Plug
        :param other: A signal (block or plug) to be subtracted (subtrahend)
        :type other: Block or Plug
        :return: SUM block
        :rtype: Block subclass

        This method is implicitly invoked by the - operator when the left operand is a ``Plug``
        and the right operand is a ``Plug``, ``Block`` or constant::

            result = X[i] - Y
            result = X[i] - Y[j]
            result = X[i] - C

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        Create a ``SUM("+-")`` block named ``_sum.N`` whose inputs are the
        left and right operands.  For the third case, a new ``CONSTANT(C)`` block
        named ``_const.N`` is also created.

        .. note::
                * The ``mode`` is None, regular addition

        :seealso: :meth:`Plug.__rsub__` :meth:`Block.__sub__`
        """
        if isinstance(other, (int, float, np.ndarray)):
            # plug - constant, create a CONSTANT block
            other = self.block.bd.CONSTANT(other)
        return self.block.bd.SUM("+-", inputs=(self, other))

    def __rsub__(self, other):
        """
        Overloaded - operator for implicit block creation.

        :param self: A signal (plug) to be added (minuend)
        :type self: Plug
        :param other: A signal (block or plug) to be subtracted (subtrahend)
        :type other: Block or Plug
        :return: SUM block
        :rtype: Block subclass

        This method is implicitly invoked by the - operator when the left operand is a ``Plug``
        and the right operand is a ``Plug``, ``Block`` or constant::

            result = X - Y[j]
            result = X[i] - Y[j]
            result = C - Y[j]

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        Create a ``SUM("+-")`` block named ``_sum.N`` whose inputs are the
        left and right operands.  For the third case, a new ``CONSTANT(C)`` block
        named ``_const.N`` is also created.

        .. note:: The inputs to the summing junction are reversed: right then left operand.

        :seealso: :meth:`Plug.__sub__` :meth:`Block.__rsub__`
        """
        # TODO deal with other cases as per above
        if isinstance(other, (int, float, np.ndarray)):
            # constant - plug, create a CONSTANT block
            other = self.block.bd.CONSTANT(other)
        return self.block.bd.SUM("+-", inputs=(other, self))

    def __neg__(self):
        """
        Overloaded unary minus operator for implicit block creation.

        :param self: A signal (plug) to be negated
        :type self: Plug
        :return: GAIN block
        :rtype: Block subclass

        This method is implicitly invoked by the - operator for unary minus when the operand is a ``Plug``::

            result = -X[i]

        where ``X`` is a block.

        Create a ``GAIN(-1)`` block named ``_gain.N`` whose input is the
        operand.

        :seealso: :meth:`Block.__neg__`
        """
        return self.block.bd.GAIN(-1, inputs=[self])

    def __mul__(self, other):
        """
        Overloaded * operator for implicit block creation.

        :param self: A signal (plug) to be multiplied
        :type self: Plug
        :param other: A signal (block or plug) to be multiplied
        :type other: Block or Plug
        :return: PROD or GAIN block
        :rtype: Block subclass

        This method is implicitly invoked by the * operator when the left operand is a ``Plug``
        and the right operand is a ``Plug``, ``Block`` or constant::

            result = X[i] * Y
            result = X[i] * Y[j]
            result = X[i] * C

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        Create a ``PROD("**")`` block named ``_prod.N`` whose inputs are the
        left and right operands.

        For the third case, create a ``GAIN(C)`` block named ``_gain.N``.

        .. note:: Signals are assumed to be scalars, but if ``C`` is a NumPy
            array then the option ``matrix`` is set to True.

        :seealso: :meth:`Plug.__rmul__` :meth:`Block.__mul__`
        """
        if isinstance(other, (int, float, np.ndarray)):
            # plug * constant, create a GAIN block
            return self.block._autogain(other, inputs=[self])
        else:
            # value * value, create a PROD block
            name = "_prod.{:d}".format(self.bd.n_auto_prod)
            self.bd.n_auto_prod += 1
            return self.block.bd.PROD(
                "**", matrix=True, name=name, inputs=[self, other]
            )

    def __rmul__(self, other):
        """
        Overloaded * operator for implicit block creation.

        :param self: A signal (plug) to be multiplied
        :type self: Plug
        :param other: A signal (block or plug) to be multiplied
        :type other: Block or Plug
        :return: PROD or GAIN block
        :rtype: Block subclass

        This method is implicitly invoked by the * operator when the right operand is a ``Plug``
        and the left operand is a ``Plug``, ``Block`` or constant::

            result = X * Y[j]
            result = X[i] * Y[j]
            result = C * Y[j]

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        For the first two cases, a ``PROD("**")`` block named ``_prod.N`` whose inputs are the
        left and right operands.

        For the third case, create a ``GAIN(C)`` block named ``_gain.N``.

        .. note:: Signals are assumed to be scalars, but if ``C`` is a NumPy
            array then the option ``matrix`` is set to True.

        :seealso: :meth:`Plug.__mul__` :meth:`Block.__rmul__`
        """
        if isinstance(other, (int, float, np.ndarray)):
            # constant * plug, create a CONSTANT block
            matrix = isinstance(other, np.ndarray)
            return self.block._autogain(other, premul=matrix, inputs=[self])

    def __truediv__(self, other):
        """
        Overloaded / operator for implicit block creation.

        :param self: A signal (plug) to be multiplied (dividend)
        :type self: Plug
        :param other: A signal (block or plug) to be divided (divisor)
        :type other: Block or Plug
        :return: PROD or GAIN block
        :rtype: Block subclass

        This method is implicitly invoked by the / operator when the left operand is a ``Plug``
        and the right operand is a ``Plug``, ``Block`` or constant::

            result = X[i] / Y
            result = X[i] / Y[j]
            result = X[i] / C

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        Create a ``PROD("**")`` block named ``_prod.N`` whose inputs are the
        left and right operands.

        For the third case, create a ``GAIN(1/C)`` block named ``_gain.N``.

        .. note:: Signals are assumed to be scalars, but if ``C`` is a NumPy
            array then the option ``matrix`` is set to True.

        :seealso: :meth:`Plug.__rtruediv__` :meth:`Block.__truediv__`
        """
        if isinstance(other, (int, float, np.ndarray)):
            # plug / constant , create a CONSTANT block
            other = self.block.bd.CONSTANT(other)
        return self.block.bd.PROD("*/", inputs=(self, other))

    def __rtruediv__(self, other):
        """
        Overloaded / operator for implicit block creation.

        :param self: A signal (plug) to be multiplied (dividend)
        :type self: Plug
        :param other: A signal (block or plug) to be divided (divisor)
        :type other: Block or Plug
        :return: PROD block
        :rtype: Block subclass

        This method is implicitly invoked by the / operator when the right operand is a ``Plug``
        and the left operand is a ``Plug``, ``Block`` or constant::

            result = X / Y[j]
            result = X[i] / Y[j]
            result = C / Y[j]

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        For the first two cases, a ``PROD("*/")`` block named ``_prod.N`` whose inputs are the
        left and right operands.  For the third case, a new CONSTANT block
        named ``_const.N`` is also created.

        .. note:: Signals are assumed to be scalars, but if ``C`` is a NumPy
            array then the option ``matrix`` is set to True.

        :seealso: :meth:`Plug.__truediv__` :meth:`Block.__rtruediv__`
        """
        if isinstance(other, (int, float, np.ndarray)):
            # constant / plug, create a CONSTANT block
            other = self.block.bd.CONSTANT(other)
        return self.block.bd.PROD("*/", inputs=(other, self))

    def __repr__(self):
        """
        Display plug details.

        :return: Plug description
        :rtype: str

        String format::

            bicycle.0[1]

        """
        return str(self.block) + "[" + str(self.port) + "]"


class StartPlug(Plug):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, type="start", **kwargs)


class EndPlug(Plug):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, type="end", **kwargs)


# ------------------------------------------------------------------------- #

clocklist = []


class Clock:
    def __init__(self, arg, unit="s", offset=0, name=None):
        global clocklist
        if unit == "s":
            self.T = arg
        elif unit == "ms":
            self.T = arg / 1000
        elif unit == "Hz":
            self.T = 1 / arg
        else:
            raise ValueError("unknown clock unit", unit)

        self.offset = offset

        self.blocklist = []

        self.x = []  # discrete state vector numpy.ndarray
        self.t = []
        self.tick = 0
        self.timer = None

        if name is None:
            self.name = "clock." + str(len(clocklist))
        else:
            self.name = name

        clocklist.append(self)

        # events happen at time t = kT + offset

    def add_block(self, block):
        self.blocklist.append(block)

    def __repr__(self):
        return str(self)

    def __str__(self):
        s = f"{self.name}: T={self.T} sec"
        if self.offset != 0:
            s += f", offset={self.offset}"
        s += f", clocking {len(self.blocklist)} blocks"
        return s

    def getstate0(self):
        # get the state from each stateful block on this clock
        x0 = np.array([])
        for b in self.blocklist:
            x0 = np.r_[x0, b.getstate0()]
            # print('x0', x0)
        return x0

    def getstate(self):

        x = np.array([])
        for b in self.blocklist:
            # update dstate
            x = np.r_[x, b.next().flatten()]

        return x

    def setstate(self):
        x = self._x
        for b in self.blocklist:
            x = b.setstate(x)  # send it to blocks

    def start(self, state=None):
        self.i = 1
        state.declare_event(self, self.time(self.i))
        self.i += 1

    def next_event(self, state=None):
        state.declare_event(self, self.time(self.i))
        self.i += 1

    def time(self, i):
        # return (math.floor((t - self.offset) / self.T) + 1) * self.T + self.offset
        # k = int((t - self.offset) / self.T + 0.5)
        return i * self.T + self.offset

    def savestate(self, t):
        # save clock state at time t
        self.t.append(t)
        self.x.append(self.getstate())


# ------------------------------------------------------------------------- #


class Block:

    varinputs = False
    varoutputs = False

    __array_ufunc__ = None  # allow block operators with NumPy values

    def __new__(cls, *args, bd=None, **kwargs):
        """
        Construct a new Block object.

        :param cls: The class to construct
        :type cls: class type
        :param *args: positional args passed to constructor
        :type *args: list
        :param **kwargs: keyword args passed to constructor
        :type **kwargs: dict
        :return: new Block instance
        :rtype: Block instance
        """
        # print('Block __new__', args,bd, kwargs)
        block = super(Block, cls).__new__(cls)  # create a new instance

        # we overload setattr, so need to know whether it is being passed a port
        # name.  Add this attribute now to allow proper operation.
        block.__dict__["portnames"] = []  # must be first, see __setattr__

        block.bd = bd
        block.nstates = 0
        block.ndstates = 0
        block._sequence = None

        return block

    _latex_remove = str.maketrans({"$": "", "\\": "", "{": "", "}": "", "^": ""})

    def __init__(
        self,
        name=None,
        nin=None,
        nout=None,
        inputs=None,
        type=None,
        inames=None,
        onames=None,
        snames=None,
        pos=None,
        bd=None,
        blockclass=None,
        verbose=False,
        **kwargs,
    ):

        """
        Construct a new block object.

        :param name: Name of the block, defaults to None
        :type name: str, optional
        :param nin: Number of inputs, defaults to None
        :type nin: int, optional
        :param nout: Number of outputs, defaults to None
        :type nout: int, optional
        :param inputs: Optional incoming connections
        :type inputs: Block, Plug or list of Block or Plug
        :param inames: Names of input ports, defaults to None
        :type inames: list of str, optional
        :param onames: Names of output ports, defaults to None
        :type onames: list of str, optional
        :param snames: Names of states, defaults to None
        :type snames: list of str, optional
        :param pos: Position of block on the canvas, defaults to None
        :type pos: 2-element tuple or list, optional
        :param bd: Parent block diagram, defaults to None
        :type bd: BlockDiagram, optional
        :param verbose: enable diagnostic prints, defaults to False
        :type verbose: bool, optional
        :param kwargs: Unused arguments
        :type kwargs: dict
        :return: A Block superclass
        :rtype: Block

        A block object is the superclass of all blocks in the simulation environment.

        This is the top-level initializer, and handles most options passed to
        the superclass initializer for each block in the library.

        """

        # print('Block constructor, bd = ', bd)
        if name is not None:
            self.name_tex = name
            self.name = self._fixname(name)
        else:
            self.name_tex = None
            self.name = None

        self.bd = bd
        self.pos = pos
        self.id = None
        self.out = []
        self.inputs = None
        self.updated = False
        self.shape = "block"  # for box
        self._inport_names = None
        self._outport_names = None
        self._state_names = None
        self.initd = True
        self._clocked = False
        self._graphics = False
        self._parameters = {}
        self.verbose = verbose

        if nin is not None:
            self.nin = nin
        if nout is not None:
            self.nout = nout
        if blockclass is not None:
            self.blockclass = blockclass

        if type is None:
            self.type = self.__class__.__name__.lower()

        if bd is not None:
            bd.add_block(self)

        if inames is not None:
            self.inport_names(inames)
        if onames is not None:
            self.outport_names(onames)
        if snames is not None:
            self.state_names(snames)

        if isinstance(inputs, Block):
            inputs = (inputs,)
        if inputs is not None and len(inputs) > 0:
            # assert len(inputs) == self.nin, 'Number of input connections must match number of inputs'
            for i, input in enumerate(inputs):
                self.bd.connect(input, Plug(self, port=i))

        if len(kwargs) > 0:
            print("WARNING: unused arguments", kwargs.keys())

    def add_param(self, param, handler=None):
        if handler == None:

            def handler(self, name, newvalue):
                setattr(self, name, newvalue)

        self.__dict__["_parameters"][param] = handler

    def set_param(self, name, newvalue):
        print(f"setting parameter {name} of block {self.name} to {newvalue}")
        self._parameters[name](self, name, newvalue)

    @property
    def info(self):
        """
        Interactive display of block properties.

        Displays all attributes of the block for debugging purposes.

        """
        print("block: " + type(self).__name__)
        for k, v in self.__dict__.items():
            if k != "sim":
                print("  {:11s}{:s}".format(k + ":", str(v)))

    @property
    def isclocked(self):
        """
        Test if block is clocked

        :return: True if block is clocked
        :rtype: bool

        True if block is clocked, False if it is continuous time.
        """
        return self._clocked

    @property
    def isgraphics(self):
        """
        Test if block does graphics

        :return: True if block does graphics
        :rtype: bool
        """
        return self._graphics

    # for use in unit testing

    # TODO: should redo this, eliminate the monkey patch
    # TODO: make T_step(), dummpy out the state object

    def T_output(self, *inputs, t=0.0, x=None):
        """
        Evaluate a block for unit testing.

        :param *inputs: Input port values
        :param t: Simulation time, defaults to 0.0
        :type t: float, optional
        :return: Block output port values
        :rtype: list

        The output ports of the block are evaluated for a given simulation time
        and set of input port values. Input ports are assigned to consecutive inputs,
        output port values are a list.

        Mostly used for making concise unit tests.

        .. warning:: the instance is monkey patched, not useable in a block
            diagram subsequently.

        """
        # check inputs and assign to attribute
        assert len(inputs) == self.nin, "wrong number of inputs provided"
        self._T_inputs = inputs

        if x is not None:
            self._x = x

        # evaluate the block
        out = self.output(t=t)

        # sanity check the output
        assert isinstance(out, list), "result must be a list"
        assert len(out) == self.nout, "result list is wrong length"
        return out

    def T_deriv(self, *inputs, x=None):
        """
        Evaluate a block for unit testing.

        :param inputs: input port values
        :type inputs: list
        :return: Block derivative value
        :rtype: ndarray

        The derivative of the block is evaluated for a given set of input port
        values. Input port values are treated as lists.

        Mostly used for making concise unit tests.

        .. warning:: the instance is monkey patched, not useable in a block
            diagram subsequently.

        """

        # check inputs and assign to attribute
        assert len(inputs) == self.nin, "wrong number of inputs provided"
        self._T_inputs = inputs

        if x is not None:
            assert len(x) == self.nstates, "passed state is wrong length"
            self._x = x

        # evaluate the block
        out = self.deriv()

        # sanity check the output
        assert isinstance(out, np.ndarray), "result must be an ndarray"
        assert out.shape == (self.nstates,), "result array is wrong length"
        return out

    def T_next(self, *inputs, x=None):
        """
        Evaluate a block for unit testing.

        :param inputs: input port values
        :type inputs: list
        :return: Block derivative value
        :rtype: ndarray

        The next value of a discrete time block is evaluated for a given set of input port
        values. Input port values are treated as lists.

        Mostly used for making concise unit tests.

        .. warning:: the instance is monkey patched, not useable in a block
            diagram subsequently.

        """

        # check inputs and assign to attribute
        assert len(inputs) == self.nin, "wrong number of inputs provided"
        self._T_inputs = inputs

        if x is not None:
            assert len(x) == self.ndstates, "passed state is wrong length"
            self._x = x

        # evaluate the block
        out = self.next()

        # sanity check the output
        assert isinstance(out, np.ndarray), "result must be an ndarray"
        assert out.shape == (self.ndstates,), "result array is wrong length"
        return out

    def T_step(self, *inputs, state=None):

        from bdsim.run_sim import BDSimState

        if state is None:
            state = BDSimState()

        # check inputs and assign to attribute
        assert len(inputs) == self.nin, "wrong number of inputs provided"
        self._T_inputs = inputs

        # step the block
        self.step(state=state)

    def T_start(self, state=None):

        from bdsim.run_sim import BDSimState, Options

        if state is None:

            class RunTime:
                def DEBUG(*args):
                    pass

            class BlockDiagram:
                pass

            self.bd = BlockDiagram()
            self.bd.runtime = RunTime()
            self.bd.runtime.options = Options()
            state = BDSimState()
            state.options = self.bd.runtime.options
            state.t = 0.0

        # step the block
        self.start(state=state)
        return state

    def _output(self, *inputs, t=0.0):
        return self.T_output(*inputs, t=t)

    def _step(self, *inputs, state=None, t=None):
        return self.T_step(*inputs, t=t)

    def input(self, port):
        """
        Get input to block on specified port

        :param port: port number
        :type port: int
        :return: value applied to specified input port
        :rtype: any

        Return the value of the input applied to the input port numbered
        ``port``.  The type depends on the source port connected to this input.

        .. note:: For unit testing purposes, it the block is simply an instance
            of the class, then setting its attribute ``test_inputs`` to a list
            provides the input values to the block.

        :seealso: :meth:`inputs`
        """
        try:
            p = self.sources[port]  # get plug for source block output
            return p.block.output_values[p.port]
        except:
            # for unit testing a block may not have its input ports connected,
            # take the value from this list instead
            return self._T_inputs[port]

    @property
    def inputs(self):
        """
        Get block inputs as a list

        :return: list of block inputs
        :rtype: list

        Returns a list of values corresponding to the input ports of the block.

        :seealso: :meth:`input`
        """
        return [self.input(i) for i in range(self.nin)]

    def __getitem__(self, port):
        """
        Convert a block slice reference to a plug.

        :param port: Port number
        :type port: int
        :return: A port plug
        :rtype: Plug

        Invoked whenever a block is referenced as a slice, for example::

            c = bd.CONSTANT(1)

            bd.connect(x, c[0])
            bd.connect(c[0], x)

        In both cases ``c[0]`` is converted to a ``Plug`` by this method.
        """
        # block[i] is a plug object
        # print('getitem called', self, port)
        return Plug(self, port)

    def __setitem__(self, port, src):
        """
        Convert a LHS block slice reference to a wire.

        :param port: Port number
        :type port: int
        :param src: the RHS
        :type src: Block or Plug

        Used to create a wired connection by assignment, for example::

            X[0] = Y

        where ``X`` and ``Y`` are blocks. This method is implicitly invoked and
        creates a wire from ``Y`` to input port 0 of ``X``.

        .. note:: The square brackets on the left-hand-side is critical, and
            ``X = Y`` will simply overwrite the reference to ``X``.
        """
        # b[port] = src
        # src --> b[port]
        # print('connecting', src, self, port)
        self.bd.connect(src, self[port])

    def __setattr__(self, name, value):
        """
        Convert a LHS block name reference to a wire.

        :param name: Port name
        :type port: str
        :param value: the RHS
        :type value: Block or Plug

        Used to create a wired connection by assignment, for example::

            c = bd.CONSTANT(1, inames=['u'])

            c.u = x

        Ths method is invoked to create a wire from ``x`` to port 'u' of
        the constant block ``c``.

        Notes:

            - this overloaded method handles all instances of ``setattr`` and
              implements normal functionality as well, only creating a wire
              if ``name`` is a known port name.
        """

        # b[port] = src
        # src --> b[port]
        # gets called for regular attribute settings, as well as for wiring

        if name in self.portnames:
            # we're doing wiring
            # print('in __setattr___', self, name, value)
            self.bd.connect(value, getattr(self, name))
        else:
            # regular case, add attribute to the instance's dictionary
            self.__dict__[name] = value

    def __rshift__(left, right):
        """
        Operator for implicit wiring.

        :param left: A block to be wired from
        :type left: Block
        :param right: A block or plugto be wired to
        :type right: Block or Plug
        :return: ``right``
        :rtype: Block or Plug

        Implements implicit wiring, for example::

            a = bd.CONSTANT(1) >> bd.GAIN(2)

        will connect the output of the CONSTANT block to the input of the
        GAIN block.  The result will be GAIN block, whose output in this case
        will be assigned to ``a``.

        Note that::

           a = bd.CONSTANT(1) >> func[1]

        will connect port 0 of CONSTANT to port 1 of ``func``, and port 1 of ``func``
        will be assigned to ``a``.  To specify a different outport port on ``func``
        we need to use parentheses::

            a = (bd.CONSTANT(1) >> func[1])[0]

        which will connect port 0 of CONSTANT ` to port 1 of ``func``, and port 0 of ``func``
        will be assigned to ``a``.

        :seealso: Plug.__rshift__

        """
        # called for the cases:
        # block * block
        # block * plug
        s = left.bd
        # assert isinstance(right, Block), 'arguments to * must be blocks not ports (for now)'
        w = s.connect(left, right)  # add a wire
        # print('block * ' + str(w))
        return right

        # make connection, return a plug

    def _autoconstant(self, value):
        if isinstance(value, (int, float, str)):
            name = "_const.{:d}({})".format(self.bd.n_auto_const, value)
        else:
            name = "_const.{:d}<{}>".format(self.bd.n_auto_const, type(value).__name__)
        self.bd.n_auto_const += 1
        return self.bd.CONSTANT(value, name=name)

    def _autogain(self, value, **kwargs):
        if isinstance(value, (int, float, str)):
            name = "_gain.{:d}({})".format(self.bd.n_auto_gain, value)
        else:
            name = "_gain.{:d}<{}>".format(self.bd.n_auto_gain, type(value).__name__)
        self.bd.n_auto_gain += 1
        return self.bd.GAIN(value, name=name, **kwargs)

    def __add__(self, other):
        """
        Overloaded + operator for implicit block creation.

        :param self: A signal (block) to be added
        :type self: Block
        :param other: A signal (block or plug) to be added
        :type other: Block or Plug
        :return: SUM block
        :rtype: Block subclass

        This method is implicitly invoked by the + operator
        when the right operand is a ``Block``
        and the left operand is a ``Plug``, ``Block`` or constant::

            result = X + Y
            result = X + Y[j]
            result = X + C

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        Creates a ``SUM("++") block named ``_sum.N`` whose inputs are the
        left and right operands.  For the third case, a new ``CONSTANT(C)`` block
        named ``_const.N`` is also created.

        .. note::
            * The inputs to the summing junction are reversed: right then left operand.
            * The ``mode`` is None, regular addition

        :seealso: :meth:`Block.__radd__` :meth:`Plug.__add__`
        """
        # value + value, create a SUM block
        name = "_sum.{:d}".format(self.bd.n_auto_sum)
        self.bd.n_auto_sum += 1
        if isinstance(other, (int, float, np.ndarray)):
            # block + constant, create a CONSTANT block
            other = self._autoconstant(other)
        return self.bd.SUM("++", inputs=(self, other), name=name)

    def __radd__(self, other):
        """
        Overloaded + operator for implicit block creation.

        :param self: A signal (block) to be added
        :type self: Block
        :param other: A signal (block or plug) to be added
        :type other: Block or Plug
        :return: SUM block
        :rtype: Block subclass

        This method is implicitly invoked by the + operator
        when the right operand is a ``Block``
        and the left operand is a ``Plug``, ``Block`` or constant::

            result = X + Y[j]
            result = X[i] + Y[j]
            result = C + Y[j]

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        Creates a ``SUM("++") block named ``_sum.N`` whose inputs are the
        left and right operands.  For the third case, a new ``CONSTANT(C)`` block
        named ``_const.N`` is also created.

        .. note::
            * The inputs to the summing junction are reversed: right then left operand.
            * The ``mode`` is None, regular addition

        :seealso: :meth:`Block.__add__` :meth:`Plug.__radd__`
        """
        # value + value, create a SUM block
        name = "_sum.{:d}".format(self.bd.n_auto_sum)
        self.bd.n_auto_sum += 1
        if isinstance(other, (int, float, np.ndarray)):
            # constant + block, create a CONSTANT block
            other = self._autoconstant(other)
        return self.bd.SUM("++", inputs=(other, self), name=name)

    def __sub__(self, other):
        """
        Overloaded - operator for implicit block creation.

        :param self: A signal (block) to be added (minuend)
        :type self: Block
        :param other: A signal (block or plug) to be subtracted (subtrahend)
        :type other: Block or Plug
        :return: SUM block
        :rtype: Block subclass

        This method is implicitly invoked by the - operator when the left operand is a ``Block``
        and the right operand is a ``Plug``, ``Block`` or constant::

            result = X - Y
            result = X - Y[j]
            result = X - C

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        Creates a ``SUM("+-")`` block named ``_sum.N`` whose inputs are the
        left and right operands.  For the third case, a new ``CONSTANT(C)`` block
        named ``_const.N`` is also created.

        :seealso: :meth:`Block.__rsub__` :meth:`Plug.__sub__`
        """
        # value - value, create a SUM block
        name = "_sum.{:d}".format(self.bd.n_auto_sum)
        self.bd.n_auto_sum += 1
        if isinstance(other, (int, float, np.ndarray)):
            # block - constant, create a CONSTANT block
            other = self._autoconstant(other)
        return self.bd.SUM("+-", inputs=(self, other), name=name)

    def __rsub__(self, other):
        """
        Overloaded - operator for implicit block creation.

        :param self: A signal (block) to be added (minuend)
        :type self: Block
        :param other: A signal (block or plug) to be subtracted (subtrahend)
        :type other: Block or Plug
        :return: SUM block
        :rtype: Block subclass

        This method is implicitly invoked by the - operator when the left operand is a ``Block``
        and the right operand is a ``Plug``, ``Block`` or constant::

            result = X - Y
            result = X[i] - Y
            result = C - Y

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        Creates a ``SUM("+-")`` block named ``_sum.N`` whose inputs are the
        left and right operands.  For the third case, a new ``CONSTANT(C)`` block
        named ``_const.N`` is also created.

        .. note::
            * The inputs to the summing junction are reversed: right then left operand.
            * The ``mode`` is None, regular addition

        :seealso: :meth:`Block.__sub__` :meth:`Plug.__rsub__`
        """
        # value - value, create a SUM block
        name = "_sum.{:d}".format(self.bd.n_auto_sum)
        self.bd.n_auto_sum += 1
        if isinstance(other, (int, float, np.ndarray)):
            # constant - block, create a CONSTANT block
            other = self._autoconstant(other)
        return self.bd.SUM("+-", inputs=(other, self), name=name)

    def __neg__(self):
        """
        Overloaded unary minus operator for implicit block creation.

        :param self: A signal (block) to be negated
        :type self: Block
        :return: GAIN block
        :rtype: Block subclass

        This method is implicitly invoked by the - operator for unary minus when the operand is a ``Block``::

            result = -X

        where ``X`` is a block.

        Creates a ``GAIN(-1)`` block named ``_gain.N`` whose input is the
        operand.

        :seealso: :meth:`Plug.__neg__`
        """
        return self._autogain(-1.0, inputs=[self])

    def __mul__(self, other):
        """
        Overloaded * operator for implicit block creation.

        :param self: A signal (block) to be multiplied
        :type self: Block
        :param other: A signal (block or plug) to be multiplied
        :type other: Block or Plug
        :return: PROD or GAIN block
        :rtype: Block subclass

        This method is implicitly invoked by the * operator when the left operand is a ``Block``
        and the right operand is a ``Plug``, ``Block`` or constant::

            result = X * Y
            result = X * Y[j]
            result = X * C

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        Create a ``PROD("**")`` block named ``_prod.N`` whose inputs are the
        left and right operands.

        For the third case, create a ``GAIN(C)`` block named ``_gain.N``.

        .. note:: Signals are assumed to be scalars, but if ``C`` is a NumPy
            array then the option ``matrix`` is set to True.

        :seealso: :meth:`Block.__rmul__` :meth:`Plug.__mul__`
        """
        matrix = False
        if isinstance(other, (int, float, np.ndarray)):
            # block * constant, create a GAIN block
            matrix = isinstance(other, np.ndarray)
            return self._autogain(other, premul=matrix, matrix=matrix, inputs=[self])
        else:
            # value * value, create a PROD block
            name = "_prod.{:d}".format(self.bd.n_auto_prod)
            self.bd.n_auto_prod += 1
            return self.bd.PROD("**", inputs=[self, other], matrix=matrix, name=name)

    def __rmul__(self, other):
        """
        Overloaded * operator for implicit block creation.

        :param self: A signal (block) to be multiplied
        :type self: Block
        :param other: A signal (block or plug) to be multiplied
        :type other: Block or Plug
        :return: PROD or GAIN block
        :rtype: Block subclass

        This method is implicitly invoked by the * operator when the right operand is a ``Block``
        and the left operand is a ``Plug``, ``Block`` or constant::

            result = X * Y
            result = X[i] * Y
            result = C * Y

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        For the first two cases, a ``PROD("**")`` block named ``_prod.N`` whose inputs are the
        left and right operands.

        For the third case, create a ``GAIN(C)`` block named ``_gain.N``.

        .. note:: Signals are assumed to be scalars, but if ``C`` is a NumPy
            array then the option ``matrix`` is set to True.

        :seealso: :meth:`Block.__mul__` :meth:`Plug.__rmul__`
        """
        matrix = False
        if isinstance(other, (int, float, np.ndarray)):
            # constant * block, create a GAIN block
            matrix = isinstance(other, np.ndarray)
            return self._autogain(other, premul=matrix, inputs=[self])

    def __truediv__(self, other):
        """
        Overloaded / operator for implicit block creation.

        :param self: A signal (block) to be multiplied (dividend)
        :type self: Block
        :param other: A signal (block or plug) to be divided (divisor)
        :type other: Block or Plug
        :return: PROD or GAIN block
        :rtype: Block subclass

        This method is implicitly invoked by the / operator when the left operand is a ``Block``
        and the right operand is a ``Plug``, ``Block`` or constant::

            result = X / Y
            result = X / Y[j]
            result = X / C

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        Create a ``PROD("**")`` block named ``_prod.N`` whose inputs are the
        left and right operands.

        For the third case, create a ``GAIN(1/C)`` block named ``_gain.N``.

        .. note:: Signals are assumed to be scalars, but if ``C`` is a NumPy
            array then the option ``matrix`` is set to True.

        :seealso: :meth:`Block.__rtruediv__` :meth:`Plug.__truediv__`
        """
        # value / value, create a PROD block
        name = "_prod.{:d}".format(self.bd.n_auto_prod)
        self.bd.n_auto_prod += 1
        matrix = False
        if isinstance(other, (int, float, np.ndarray)):
            # block / constant, create a CONSTANT block
            other = self._autoconstant(other)
            matrix = isinstance(other, np.ndarray)
        return self.bd.PROD("*/", inputs=(self, other), matrix=matrix, name=name)

    def __rtruediv__(self, other):
        """
        Overloaded / operator for implicit block creation.

        :param self: A signal (block) to be multiplied (dividend)
        :type self: Block
        :param other: A signal (block or plug) to be divided (divisor)
        :type other: Block or Plug
        :return: PROD block
        :rtype: Block subclass

        This method is implicitly invoked by the / operator when the right operand is a ``Block``
        and the left operand is a ``Plug``, ``Block`` or constant::

            result = X / Y
            result = X[i] / Y
            result = C / Y

        where ``X`` and ``Y`` are blocks and ``C`` is a Python or NumPy constant.

        For the first two cases, a ``PROD("*/")`` block named ``_prod.N`` whose inputs are the
        left and right operands.  For the third case, a new CONSTANT block
        named ``_const.N`` is also created.

        .. note:: Signals are assumed to be scalars, but if ``C`` is a NumPy
            array then the option ``matrix`` is set to True.

        :seealso: :meth:`Block.__truediv__` :meth:`Plug.__rtruediv__`
        """
        # value / value, create a PROD block
        name = "_prod.{:d}".format(self.bd.n_auto_prod)
        self.bd.n_auto_prod += 1
        matrix = False
        if isinstance(other, (int, float, np.ndarray)):
            # constant / block, create a CONSTANT block
            other = self._autoconstant(other)
            matrix = isinstance(other, np.ndarray)
        return self.bd.PROD("*/", inputs=(other, self), matrix=matrix, name=name)

    # TODO arithmetic with a constant, add a gain block or a constant block

    def __str__(self):
        if hasattr(self, "name") and self.name is not None:
            return self.name
        else:
            return self.blockclass + ".??"

    def __repr__(self):
        return self.__str__()

    def _fixname(self, s):
        return s.translate(self._latex_remove)

    def inport_names(self, names):
        """
        Set the names of block input ports.

        :param names: List of port names
        :type names: list of str

        Invoked by the ``inames`` argument to the Block constructor.

        The names can include LaTeX math markup.  The LaTeX version is used
        where appropriate, but the port names are a de-LaTeXd version of the
        given string with backslash, caret, braces and dollar signs
        removed.
        """
        self._inport_names = names

        for port, name in enumerate(names):
            fn = self._fixname(name)
            setattr(self, fn, self[port])
            self.portnames.append(fn)

    def outport_names(self, names):
        """
        Set the names of block output ports.

        :param names: List of port names
        :type names: list of str

        Invoked by the ``onames`` argument to the Block constructor.

        The names can include LaTeX math markup.  The LaTeX version is used
        where appropriate, but the port names are a de-LaTeXd version of the
        given string with backslash, caret, braces and dollar signs
        removed.

        """
        self._outport_names = names
        for port, name in enumerate(names):
            fn = self._fixname(name)
            setattr(self, fn, self[port])
            self.portnames.append(fn)

    def state_names(self, names):
        self._state_names = names

    def sourcename(self, port):
        """
        Get the name of output port driving this input port.

        :param port: Input port
        :type port: int
        :return: Port name
        :rtype: str

        Return the name of the output port that drives the specified input
        port. The name can be:

            - a LaTeX string if provided
            - block name with port number given in square brackets.  The block
              name will the one optionally assigned by the user using the ``name``
              keyword, otherwise a systematic default name.

        :seealso: outport_names

        """

        w = self.inports[port]
        if w.name is not None:
            return w.name
        src = w.start.block
        srcp = w.start.port
        if src._outport_names is not None:
            return src._outport_names[srcp]
        return str(w.start)

    # @property
    # def fullname(self):
    #     return self.blockclass + "." + str(self)

    def reset(self):
        if self.nin > 0:
            self.inputs = [None] * self.nin
        self.updated = False

    def add_output_wire(self, w):
        port = w.start.port
        assert port < len(self.output_wires), "port number too big"
        self.output_wires[port].append(w)

    def add_input_wire(self, w):
        port = w.end.port
        assert (
            self.input_wires[port] is None
        ), "attempting to connect second wire to an input"
        self.input_wires[port] = w
        self.sources[port] = w.start

    # def setinput(self, port, value):
    #     """
    #     Receive input from a wire

    #     :param self: Block to be updated
    #     :type wire: Block
    #     :param port: Input port to be updated
    #     :type port: int
    #     :param value: Input value
    #     :type val: any
    #     """
    #     # stash it away
    #     self.inputs[port] = value

    # def setinputs(self, *pos):
    #     assert len(pos) == self.nin, 'mismatch in number of inputs'
    #     self.reset()
    #     for i, val in enumerate(pos):
    #         self.inputs[i] = val

    def start(self, **kwargs):  # begin of a simulation
        pass

    def check(self):  # check validity of block parameters at start
        assert hasattr(self, "nin"), f"block {self.name} has no nin specified"
        assert hasattr(self, "nout"), f"block {self.name} has no nout specified"

        assert (
            self.nin > 0 or self.nout > 0
        ), f"block {self.name} no inputs or outputs specified"
        assert (
            hasattr(self, "initd") and self.initd
        ), "Block superclass not initalized. was super().__init__ called?"

    def done(self, **kwargs):  # end of simulation
        pass

    def step(self, **kwargs):  # valid
        pass

    def savefig(self, *pos, **kwargs):
        pass


class SinkBlock(Block):
    """
    A SinkBlock is a subclass of Block that represents a block that has inputs
    but no outputs. Typically used to save data to a variable, file or
    graphics.
    """

    blockclass = "sink"

    def __init__(self, **blockargs):
        """
        Create a sink block.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: sink block base class
        :rtype: SinkBlock

        This is the parent class of all sink blocks.
        """
        # print('Sink constructor')
        super().__init__(**blockargs)
        self.nout = 0
        self.nstates = 0


class SourceBlock(Block):
    """
    A SourceBlock is a subclass of Block that represents a block that has outputs
    but no inputs.  Its output is a function of parameters and time.
    """

    blockclass = "source"

    def __init__(self, **blockargs):
        """
        Create a source block.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: source block base class
        :rtype: SourceBlock

        This is the parent class of all source blocks.
        """
        # print('Source constructor')
        super().__init__(**blockargs)
        self.nin = 0
        self.nstates = 0


class TransferBlock(Block):
    """
    A TransferBlock is a subclass of Block that represents a block with inputs
    outputs and states. Typically used to describe a continuous time dynamic
    system, either linear or nonlinear.
    """

    blockclass = "transfer"

    def __init__(self, nstates=1, **blockargs):
        """
        Create a transfer function block.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: transfer function block base class
        :rtype: TransferBlock

        This is the parent class of all transfer function blocks.
        """
        # print('Transfer constructor')
        self.nstates = nstates
        super().__init__(**blockargs)

    def reset(self):
        super().reset()
        self._x = self._x0
        # return self._x

    def setstate(self, x):
        x = np.array(x)
        self._x = x[: self.nstates]  # take as much state vector as we need
        return x[self.nstates :]  # return the rest

    def getstate0(self):
        return self._x0

    def check(self):
        assert len(self._x0) == self.nstates, "incorrect length for initial state"
        assert self.nin > 0 or self.nout > 0, "no inputs or outputs specified"


class FunctionBlock(Block):
    """
    A FunctionBlock is a subclass of Block that represents a block that has inputs
    and outputs but no state variables.  Typically used to describe operations
    such as gain, summation or various mappings.
    """

    blockclass = "function"

    def __init__(self, **blockargs):
        """
        Create a function block.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: function block base class
        :rtype: FunctionBlock

        This is the parent class of all function blocks.
        """
        # print('Function constructor')
        super().__init__(**blockargs)
        self.nstates = 0


class SubsystemBlock(Block):
    """
    A SubSystem  s a subclass of Block that represents a block that has inputs
    and outputs but no state variables.  Typically used to describe operations
    such as gain, summation or various mappings.
    """

    blockclass = "subsystem"

    def __init__(self, **blockargs):
        """
        Create a subsystem block.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: subsystem block base class
        :rtype: SubsystemBlock

        This is the parent class of all subsystem blocks.
        """
        # print('Subsystem constructor')
        super().__init__(**blockargs)
        self.nstates = 0


class ClockedBlock(Block):
    """
    A ClockedBlock is a subclass of Block that represents a block with inputs
    outputs and discrete states. Typically used to describe a discrete time dynamic
    system, either linear or nonlinear.
    """

    blockclass = "clocked"

    def __init__(self, clock=None, **blockargs):
        """
        Create a clocked block.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: clocked block base class
        :rtype: ClockedBlock

        This is the parent class of all clocked blocks.
        """
        # print('Clocked constructor')
        super().__init__(**blockargs)
        assert clock is not None, "clocked block must have a clock"
        self._clocked = True
        self.clock = clock
        clock.add_block(self)

    def reset(self):
        super().reset()
        # self._x = self._x0
        # return self._x

    def setstate(self, x):
        self._x = x[: self.ndstates]  # take as much state vector as we need
        # print('** set block state to ', self._x)
        return x[self.ndstates :]  # return the rest

    def getstate0(self):
        return self._x0

    def check(self):
        assert len(self._x0) == self.ndstates, "incorrect length for initial state"

        assert self.nin > 0 or self.nout > 0, "no inputs or outputs specified"
        self._x = self._x0


class EventSource:
    pass


# c = Clock(5)
# c1 = Clock(5, 2)

# print(c, c1)
# print(c.next(0), c1.next(0))

if __name__ == "__main__":
    # opt = OptionsBase(dict(foo=1, bar='hello'))
    # print(opt.foo)
    # print(opt.bar)
    # opt.set(foo=3)
    # print(opt.foo)

    # from bdsim.blocks.functions import Sum
    # print(Sum.parameters())

    import bdsim

    sim = bdsim.BDSim()  # create simulator

    print(sim.moduledicts)
