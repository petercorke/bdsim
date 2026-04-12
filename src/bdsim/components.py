#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Components of the simulation system, namely blocks, wires and plugs.
"""
from __future__ import annotations
from io import BufferedWriter
import types
import math
import warnings
import unicodedata
import numpy as np
from typing import TYPE_CHECKING, Optional, Literal, Union, Any, Self

from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from bdsim.blockdiagram import BlockDiagram
    from bdsim.run_sim import BDSimState


# decorator for debugging implicit block creation with operator overloading
def oodebug(func):
    def wrapper(*args, **kwargs):
        ret = func(*args, **kwargs)
        # print(f"{func.__qualname__}{args} --> {ret}")
        return ret

    return wrapper


# remove LaTeX characters from names for use in port names, etc.
_latex_remove: dict[int, str] = str.maketrans(
    {"$": "", "\\": "", "{": "", "}": "", "^": ""}
)


def _fixname(s):
    if isinstance(s, (tuple, list)):
        return [_fixname(x) for x in s]
    else:
        s = s.translate(_latex_remove)
        # PEP 3131: Python normalizes all identifiers to NFKC at parse time.
        # Port names used as attributes must round-trip through that normalization
        # or lookups via __setattr__/__getattr__ will silently fail.
        normalized = unicodedata.normalize("NFKC", s)
        if normalized != s:
            warnings.warn(
                f"Port name {s!r} contains Unicode compatibility characters "
                f"(e.g. U+{ord(next(c for c in s if unicodedata.normalize('NFKC', c) != c)):04X}); "
                f"Python identifiers are NFKC-normalized, so attribute access will use {normalized!r} instead.",
                UnicodeWarning,
                stacklevel=3,
            )
        # if not normalized.isidentifier():
        #     warnings.warn(
        #         f"Port name {normalized!r} is not a valid Python identifier "
        #         f"and cannot be used for attribute-style port access.",
        #         UserWarning,
        #         stacklevel=3,
        #     )
        return normalized


class BDStruct:
    """
    A simple data container object that allows items to be added by attribute or by
    index.

    For example::

        >>> d = BDStruct('thing')
        >>> d.foo = 1
        >>> d.foo
        1
        >>> d["foo"]
        ]
        >>> d["bar"] = 2
        >>> d.bar
        >>> d
        bar   = 2 (int)
        foo   = 1 (int)
    """

    def __init__(self, name="BDStruct2", **kwargs) -> None:
        self._name: str = name
        for key, value in kwargs.items():
            # self.__dict__[key] = value
            setattr(self, key, value)

    def add(self, name, value) -> None:
        # self.__dict__[name] = value
        setattr(self, name, value)

    def __repr__(self) -> str:
        return str(self)

    def __len__(self) -> int:
        return len([k for k in self.__dict__.keys() if not k.startswith("_")])

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value) -> None:
        setattr(self, key, value)

    def __str__(self) -> str:
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
        maxwidth: int = max([len(key) for key in self.__dict__.keys()])
        # if self.name is not None:
        #     rows.append(self.name + '::')
        for k, v in sorted(self.__dict__.items(), key=lambda x: x[0]):
            if k.startswith("_"):
                continue
            if isinstance(v, BDStruct):
                rows.append("{:s}.{:s}::".format(k.ljust(maxwidth), v._name))
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

    def dump(self, outfile) -> None:
        import pickle

        with open(outfile, "wb") as f:
            pickle.dump(self, f)


class OptionsBase:
    """A struct like object for option handling

    Maintains an internal dict to keep options and their values.  Some of these
    values, names in the ``_priority`` list are read-only and cannot be changed.

    Values can be read/written as attributes, or the ``set`` method can take
    a sequence of ``option=value`` arguments.
    """

    def __init__(self, readonly={}, args={}) -> None:
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

    def __setattr__(self, name, value) -> None:
        if name.startswith("_"):
            self.__dict__[name] = value
        else:
            dict = self.__dict__["_dict"]
            if name not in self._readonly:
                dict[name] = value
                self.__dict__["_dict"] = self.sanity(dict)

    def set(self, **changes) -> None:
        changes = self.sanity(changes)
        dict = self._dict
        for name, value in changes.items():
            if name not in self._readonly:
                dict[name] = value
            elif dict[name] != value:
                print(
                    f"attempt to programmatically set option {name}={value} is"
                    f" overriden by command line option {name}={dict[name]}, ignored"
                )

        self._dict = dict

    def sanity(self, options):
        return options

    def __str__(self) -> str:
        dict = self._dict
        maxwidth: int = max([len(option) for option in dict.keys()])
        options = sorted(dict.keys())
        return "\n".join(
            [f"{option.ljust(maxwidth)}: {dict[option]}" for option in options]
        )

    def __repr__(self) -> str:
        return str(self)


class Wire:
    """
    Create a wire.

    :param start: Plug at the start of a wire
    :type start: Plug
    :param end: Plug at the end of a wire
    :type end: Plug
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

    def __init__(self, start: Plug, end: Plug, name: Optional[str] = None) -> None:

        self.name = name
        self.id = None
        self.start = start
        self.end = end
        self.value = None
        self.type = None
        self.name = None

    @property
    def info(self) -> None:
        """
        Interactive display of wire properties.

        Displays all attributes of the wire for debugging purposes.

        """
        print("wire:")
        for k, v in self.__dict__.items():
            print("  {:8s}{:s}".format(k + ":", str(v)))

    def __repr__(self) -> str:
        """
        Display wire with name and connection details.

        :return: Long-form wire description
        :rtype: str

        String format::

            wire.5: d2goal[0] --> Kv[0]

        """
        return str(self) + ": " + self.fullname

    @property
    def fullname(self) -> str:
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


class Port:
    """
    A common base class for blocks and plugs, to allow operator overloading for implicit block creation.
    """

    pass


class Plug(Port):
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

    def __init__(self, block, port=0, type: Optional[str] = None) -> None:

        self.block: Block = block
        self.port: int = port
        self.type: str = type or ""  # start or end

    def __str__(self) -> str:
        """
        Display plug details.

        :return: Plug description
        :rtype: str

        String format::

            bicycle.0[1]

        """
        return str(self.block) + "[" + str(self.port) + "]"

    def __repr__(self):
        """
        Display plug details.

        :return: Plug description
        :rtype: str

        String format::

            bicycle.0[1]

        """
        return "Plug/" + self.type + ":" + str(self)

    @property
    def isslice(self) -> bool:
        """
        Test if port number is a slice.

        :return: Whether the port is a slice
        :rtype: bool

        Returns ``True`` if the port is a slice, eg. ``[0:3]``, and ``False``
        for a simple index, eg. ``[2]``.
        """
        return isinstance(self.port, slice)

    @property
    def portlist(self) -> list[int] | range | ValueError:
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
            start: int = self.port.start or 0
            step: int = self.port.step or 1
            if self.port.stop is None:
                if self.type == "start":
                    stop = self.block.nout
                else:
                    stop = self.block.nin
            else:
                stop: int = self.port.stop

            return range(start, stop, step)
        else:
            return ValueError("bad plug index")

    def __getitem__(self, i) -> Self:
        return self.__class__(self.block, self.portlist[i])

    @property
    def width(self) -> int:
        """
        Return number of ports connected.

        :return: Number of ports
        :rtype: int

        If the port is a simple index, eg. ``[2]`` returns 1.

        If the port is a slice, eg. ``[0:3]``, returns 3.
        """
        return len(self.portlist)

    @oodebug
    def __rshift__(left: Plug, right: Plug | Block) -> Plug | Block:
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
        assert (
            s is not None
        ), "left operand of >> operator must be a plug connected to a block diagram"
        # assert isinstance(right, Block), 'arguments to * must be blocks not ports (for now)'
        w = s.connect(left, right)  # add a wire
        # print('plug * ' + str(w))
        return right

    @oodebug
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
        from bdsim.blocks import Constant, Sum

        if isinstance(other, (int, float, np.ndarray)):
            # plug + constant, create a CONSTANT block
            # other = self.block.bd.CONSTANT(other)
            other = Constant(other, bd=self.block.bd)
        return Sum("++", inputs=(self, other), bd=self.block.bd)

    @oodebug
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
        from bdsim.blocks import Constant, Sum

        if isinstance(other, (int, float, np.ndarray)):
            # constant + plug, create a CONSTANT block
            other = Constant(other, bd=self.block.bd)
        return Sum("++", inputs=(other, self), bd=self.block.bd)

    @oodebug
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
        from bdsim.blocks import Constant, Sum

        if isinstance(other, (int, float, np.ndarray)):
            # plug - constant, create a CONSTANT block
            other = Constant(other, bd=self.block.bd)
        return Sum("+-", inputs=(self, other), bd=self.block.bd)

    @oodebug
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
        from bdsim.blocks import Constant, Sum

        # TODO deal with other cases as per above
        if isinstance(other, (int, float, np.ndarray)):
            # constant - plug, create a CONSTANT block
            other = Constant(other, bd=self.block.bd)
        return Sum("+-", inputs=(other, self), bd=self.block.bd)

    @oodebug
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
        from bdsim.blocks import Gain

        return Gain(-1, inputs=[self], bd=self.block.bd)

    @oodebug
    def __pow__(self, p):
        """
        Overloaded unary power operator for implicit block creation.

        :param self: A signal (plug) to be exponentiated
        :type self: Plug
        :return: POW block
        :rtype: Block subclass

        This method is implicitly invoked by the ** operator for unary power when the operand is a ``Block``::

            result = X**3

        where ``X`` is a block.

        Creates a ``POW(3)`` block named ``_pow.N`` whose input is the
        operand.

        :seealso: :meth:`Plug.__pow__`
        """
        from bdsim.blocks import Pow

        return Pow(p, inputs=[self], bd=self.block.bd)

    @oodebug
    def __mul__(self, other: Block | Plug | int | float | np.ndarray):
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
        from bdsim.blocks import Prod

        if isinstance(other, (int, float, np.ndarray)):
            # plug * constant, create a GAIN block
            return self.block._autogain(other, inputs=[self])
        elif isinstance(other, Block):
            bd = other.bd
        elif isinstance(other, Plug):
            bd = self.block.bd
        else:
            raise ValueError("unsupported operand type for *: " + str(type(other)))

        # value * value, create a PROD block
        assert (
            bd is not None
        ), "left operand of * operator must be a plug connected to a block diagram"
        name = "_prod.{:d}".format(bd.n_auto_prod)
        bd.n_auto_prod += 1
        return Prod("**", matrix=True, name=name, inputs=[self, other], bd=bd)

    @oodebug
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
            matrix: bool = isinstance(other, np.ndarray)
            return self.block._autogain(other, premul=matrix, inputs=[self])

    @oodebug
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
        from bdsim.blocks import Prod, Constant

        if isinstance(other, (int, float, np.ndarray)):
            # plug / constant , create a CONSTANT block
            other = Constant(other, bd=self.block.bd)
        return Prod("*/", inputs=(self, other), bd=self.block.bd)

    @oodebug
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
        from bdsim.blocks import Constant, Prod

        if isinstance(other, (int, float, np.ndarray)):
            # constant / plug, create a CONSTANT block
            other = Constant(other, bd=self.block.bd)
        return Prod("*/", inputs=(other, self), bd=self.block.bd)


class StartPlug(Plug):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, type="start", **kwargs)


class EndPlug(Plug):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, type="end", **kwargs)


# ------------------------------------------------------------------------- #

clocklist = []


class Clock:
    def __init__(self, arg, unit="s", offset=0, name=None) -> None:
        global clocklist
        if unit == "s":
            self.T: Any = arg
        elif unit == "ms":
            self.T = arg / 1000
        elif unit == "Hz":
            self.T: float = 1 / arg
        else:
            raise ValueError("unknown clock unit", unit)

        self.offset: int = offset

        self.blocklist = []

        self.x = []  # discrete state vector numpy.ndarray
        self.t = []
        self.tick = 0
        self.timer = None

        if name is None:
            self.name: str = "clock." + str(len(clocklist))
        else:
            self.name = name

        clocklist.append(self)

        # events happen at time t = kT + offset

    def add_block(self, block) -> None:
        self.blocklist.append(block)

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        s: str = f"{self.name}: T={self.T} sec"
        if self.offset != 0:
            s += f", offset={self.offset}"
        s += f", clocking {len(self.blocklist)} blocks"
        return s

    def getstate0(self) -> np.ndarray[tuple[Any, ...], np.dtype[Any]]:
        # get the state from each stateful block on this clock
        x0: np.ndarray[tuple[Any, ...], np.dtype[Any]] = np.array([])
        for b in self.blocklist:
            x0 = np.r_[x0, b.getstate0()]
            # print('x0', x0)
        return x0

    def getstate(self, t) -> np.ndarray[tuple[Any, ...], np.dtype[Any]]:

        x: np.ndarray[tuple[Any, ...], np.dtype[Any]] = np.array([])
        for b in self.blocklist:
            # update dstate
            xb = b.next(t, b.inputs, b._x)
            x = np.r_[x, xb.flatten()]

        return x

    def setstate(self) -> None:
        x = self._x
        for b in self.blocklist:
            x = b.setstate(x)  # send it to blocks

    def start(self, simstate: BDSimState) -> None:
        self.i = 1
        simstate.declare_event(self, self.time(self.i))
        self.i += 1

    def next_event(self, simstate: BDSimState) -> None:
        simstate.declare_event(self, self.time(self.i))
        self.i += 1

    def time(self, i):
        # return (math.floor((t - self.offset) / self.T) + 1) * self.T + self.offset
        # k = int((t - self.offset) / self.T + 0.5)
        return i * self.T + self.offset

    def savestate(self, t) -> None:
        # save clock state at time t
        self.t.append(t)
        self.x.append(self.getstate(t))


# ------------------------------------------------------------------------- #


class Block(ABC, Port):
    """_summary_

    :param ABC: _description_
    :type ABC: _type_
    :return: _description_
    :rtype: _type_

    Block is the superclass of all blocks in the simulation environment.  It defines the common properties of all blocks:

    - ``nin`` the number of input ports
    - ``nout`` the number of output ports
    - ``nstates`` the number of continuous-time state variables
    - ``ndstates`` the number of discrete-time state variables
    - ``name`` the unique name of the block
    - ``blockclass`` a string indicating the block class, eg. 'sink', 'source', 'function', 'transfer', 'subsystem', 'clocked', etc.
    - ``type`` a string indicating the block type, eg. 'gain', 'sum', 'integrator', etc.

    The simulation engine uses these methods:

        - ``getstate0()``: returns the initial state of the block as a NumPy array
        - ``setstate(x)``: sets the state of the block to the given state ``x`` and returns any remaining state for the next block in the clock sequence
        - ``next(t, u, x)``: computes the next state of the block given the current time ``t``, input values ``inputs``, and current state ``x``
        - ``output(t, u, x)``: returns the output value of the block at output port ``i`` given the current state and inputs. The outputs are cached and
          can be accessed by ``block.output_value(i)``
        - ``deriv(t, u, x)``: returns the derivative of the state variables for continuous-time blocks
        - ``reset()``: resets the block to its initial state
        - ``done()``: performs any cleanup at end of the simulation
        - ``info()``: displays information about the block for debugging purposes

    Ports can be accessed by index, eg. ``block.input_value(i)`` or ``block.output_value(i)``, or by name, eg. ``block.inport("in1")`` or ``block.outport("out1")`` if the block has named ports.

        - ``input_value(i)``: returns the value of the input port at index ``i``
        - ``output_value(i)``: returns the value of the output port at index ``i``
        - ``inport_name(i)``: returns the name of the input port at index ``i``
        - ``outport_name(i)``: returns the name of the output port at index ``i``

    """

    nin: int  # number of input ports
    nout: int  # number of output ports
    nstates: int  # number of continuous-time state variables
    ndstates: int  # number of discrete-time state variables

    # block class, eg. 'sink', 'source', 'function', 'transfer', 'subsystem', 'clocked', etc.
    blockclass: str = "?"
    type: str = "?"

    _name: Optional[str]
    _name_tex: Optional[str]

    # graphical hints
    _pos: Optional[tuple[float, float]]  # position on canvas, eg. (x,y)
    _shape: Optional[str]  # passed to graphviz, eg. 'box', 'ellipse', 'diamond'

    _initd: bool = False
    _bd: Optional[BlockDiagram] = None

    _output_values: Optional[list] = None  # access by block.output_value(i)

    _x: Optional[np.ndarray[tuple[Any, ...], np.dtype[Any]]]

    _inport_names: Optional[list[str]]
    _outport_names: Optional[list[str]]
    _state_names: Optional[list[str]]

    _clocked: bool = False
    _clock: Clock

    _graphics: bool = False
    _parameters: dict[str, Any]

    # these lists are used to record the wires connected to the block, set by connect()
    # used to build inter-block references at compile time
    _input_wires: list[Wire]  # incoming wires
    _output_wires: list[list[Wire]]  # outgoing wires

    # used at compile time to determine the order of block execution
    _sequence: Optional[int]
    _parents: list[Block]  # blocks that feed into this block, set at compile time

    __array_ufunc__ = None  # allow block operators with NumPy operands

    # def __new__(cls, *args, bd=None, **kwargs) -> Self:
    #     """
    #     Construct a new Block object.

    #     :param cls: The class to construct
    #     :type cls: class type
    #     :param *args: positional args passed to constructor
    #     :type *args: list
    #     :param **kwargs: keyword args passed to constructor
    #     :type **kwargs: dict
    #     :return: new Block instance
    #     :rtype: Block instance
    #     """
    #     # print('Block __new__', args,bd, kwargs)
    #     block: Self = super(Block, cls).__new__(cls)  # create a new instance

    #     # we overload setattr, so need to know whether it is being passed a port
    #     # name.  Add this attribute now to allow proper operation.
    #     # block.__dict__["_portnames"] = []  # must be first, see __setattr__
    #     # block._portnames = []  # must be first, see __setattr__
    #     return block

    def __init_subclass__(cls, **kwargs) -> None:
        """
        Initialize a subclass of Block.

        :param cls: The subclass being initialized
        :type cls: class type
        :param **kwargs: keyword args passed to subclass definition
        :type **kwargs: dict

        This method is called when a new subclass of Block is defined, not when it is
        instantiated.  It can be used to set class variables such as ``nin``, ``nout``,
        ``inlabels``, ``outlabels``, etc.  For example::

            class MyBlock(Block):
                nin = 1
                nout = 1
                inlabels = ['in']
                outlabels = ['out']

        """
        super().__init_subclass__(**kwargs)
        # print("*** in Block.__init_subclass__ for class", cls.__name__)
        if "nin" in cls.__dict__ and not isinstance(cls.__dict__["nin"], property):
            # Capture the default value defined in the subclass
            cls._nin = cls.nin
            # Delete it so the Base property is visible again
            del cls.nin

        if "nout" in cls.__dict__ and not isinstance(cls.__dict__["nout"], property):
            # Capture the default value defined in the subclass
            cls._nout = cls.nout
            # Delete it so the Base property is visible again
            del cls.nout

        if "inlabels" in cls.__dict__ and not isinstance(
            cls.__dict__["inlabels"], property
        ):
            # Capture the default value defined in the subclass
            cls._inport_names = cls.inlabels
            # Delete it so the Base property is visible again
            del cls.inlabels

        if "outlabels" in cls.__dict__ and not isinstance(
            cls.__dict__["outlabels"], property
        ):
            # Capture the default value defined in the subclass
            cls._outport_names = cls.outlabels
            # Delete it so the Base property is visible again
            del cls.outlabels

    def __init__(
        self,
        name=None,
        nin=None,
        nout=None,
        nstates=0,
        ndstates=0,
        inputs=None,
        inames=None,
        onames=None,
        snames=None,
        clock=None,
        pos=None,
        bd: Optional["BlockDiagram"] = None,
        type=None,
        blockclass=None,
        **kwargs,
    ) -> None:
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
        :param kwargs: Unused arguments
        :type kwargs: dict
        :return: A Block superclass
        :rtype: Block

        A block object is the superclass of all blocks in the simulation environment.

        This is the top-level initializer, and handles most options passed to
        the superclass initializer for each block in the library.

        """

        # print('Block constructor, bd = ', bd)

        # set basic block parameters

        # nin and nout can be set by the constructor, or by class variables in the subclass, or default to 0.
        if nin is not None:
            self.nin = nin

        if nout is not None:
            self.nout = nout

        self.name = name

        # set the block type and block class
        if type is None:
            self.type: str = self.__class__.__name__.lower()

        if blockclass is None:
            for cls in self.__class__.__bases__:
                if cls.__name__.endswith("Block"):
                    self.blockclass = cls.__name__[:-5].lower()
                    break
        assert (
            self.blockclass is not None
        ), f"blockclass must be specified for block {self.name}"

        # key simulation variables
        self._x = None  # state vector
        self._output_values = None  # cached block output values, set by output() method, accessed by outport_value()

        # set by add_block() when block is added to a block diagram
        self._bd: Optional[BlockDiagram] = bd  # owning block diagram
        self.id = None  # index in block diagram's blocklist

        # deprecated options for graphical display
        self._pos = pos
        self._shape = "block"  # for box

        self._initd = True
        self._clocked = False
        self._clock = clock
        self._graphics = False
        self._parameters = {}

        if bd is not None:
            bd.add_block(self)

        # ports can have names as well as indices, for access by name.
        #  names are set by:
        #  - inames and onames options, or by
        #  - inlabels and outlabels class variables, or
        #  - default to None.
        #
        # _portnames is the list of all port names, used for access by name in __setattr__ and __getattr__
        def checknames(names):
            for name in names:
                if name in self.__dict__:
                    raise ValueError(f"port name {name} conflicts with block attribute")

        if inames is None:
            inames = getattr(self, "_inport_names", None)
        if inames is not None:
            if hasattr(self, "_nin") and self._nin is not None:
                assert (
                    len(inames) == self.nin
                ), "number of input port names must match number of inputs"
            else:
                self.nin = len(inames)
            inames = _fixname(inames)
            assert len(set(inames)) == len(inames), "input port names must be unique"
            checknames(inames)
        self._inport_names = inames

        if onames is None:
            onames = getattr(self, "_outport_names", None)
        if onames is not None:
            if hasattr(self, "_nout") and self._nout is not None:
                assert (
                    len(onames) == self.nout
                ), "number of output port names must match number of outputs"
            else:
                self.nout = len(onames)
            onames = _fixname(onames)
            assert len(set(onames)) == len(onames), "output port names must be unique"
            checknames(onames)
        self._outport_names = onames

        if snames is not None:
            if nstates is not None:
                assert (
                    len(snames) == nstates
                ), "number of state names must match number of states"
            else:
                nstates = len(snames)
        self._state_names = snames

        # block inputs can be specified in the constructor for convenience, and are connected here.
        if isinstance(inputs, Block):
            inputs: tuple[Block] = (inputs,)
        if inputs is not None and len(inputs) > 0:
            # assert len(inputs) == self.nin, 'Number of input connections must match number of inputs'
            assert (
                self.bd is not None
            ), "inputs provided but block is not in a block diagram"
            for i, input in enumerate(inputs):
                self.bd.connect(input, Plug(self, port=i))

        self.nstates = nstates
        self.ndstates = ndstates

    def add_param(self, param, handler=None) -> None:
        if handler == None:

            def handler(self, name, newvalue) -> None:
                setattr(self, name, newvalue)

        self.__dict__["_parameters"][param] = handler

    def set_param(self, name, newvalue) -> None:
        print(f"setting parameter {name} of block {self.name} to {newvalue}")
        self._parameters[name](self, name, newvalue)

    @property
    def nin(self) -> int:
        return self._nin

    @nin.setter
    def nin(self, nin) -> None:
        self._nin = nin

        if hasattr(self, "_inport_names") and self._inport_names is not None:
            assert (
                len(self._inport_names) == self.nin
            ), "number of input port names must match number of inputs"

    @property
    def nout(self) -> int:
        return self._nout

    @nout.setter
    def nout(self, nout) -> None:
        self._nout = nout
        # update output wires and port names
        # self._output_wires = [[]] * self.nout
        if hasattr(self, "_outport_names") and self._outport_names is not None:
            assert (
                len(self._outport_names) == self.nout
            ), "number of output port names must match number of outputs"

    @property
    def name(self) -> str | None:
        return self._name

    @property
    def name_tex(self) -> str | None:
        return self._name_tex

    @name.setter
    def name(self, name) -> None:
        if name is not None:
            self._name_tex = name
            self._name = _fixname(name)
        else:
            self._name_tex = None
            self._name = None

    @property
    def info(self) -> None:
        """
        Interactive display of block properties.

        Displays all attributes of the block for debugging purposes.

        """
        print("block: " + type(self).__name__)
        items = sorted(self.__dict__.items())
        for k, v in [i for i in items if i[0].startswith("_")] + [
            i for i in items if not i[0].startswith("_")
        ]:
            print("  {:11s}{:s}".format(k + ":", str(v)))

    def __str__(self):
        if hasattr(self, "name") and self.name is not None:
            return self.name
        else:
            return self.blockclass + ".??"

    def __repr__(self):
        return self.__str__()

    def state_names(self, names) -> None:
        self._state_names = names

    @property
    def fullname(self):
        return self.blockclass + "." + str(self)

    # ---------------------------------------------------------------------- #

    @property
    def isclocked(self) -> bool:
        """
        Test if block is clocked

        :return: True if block is clocked
        :rtype: bool

        True if block is clocked, False if it is continuous time.
        """
        return self._clocked

    @property
    def isgraphics(self) -> bool:
        """
        Test if block does graphics

        :return: True if block does graphics
        :rtype: bool
        """
        return self._graphics

    @property
    def pos(self) -> Optional[tuple[float, float]]:
        return self._pos

    @property
    def shape(self) -> str:
        return self._shape

    @property
    def initd(self) -> bool:
        return self._initd

    @property
    def bd(self) -> BlockDiagram:
        assert self._bd is not None, "block is not in a block diagram"
        return self._bd

    @property
    def bd(self) -> BlockDiagram:
        assert self._bd is not None, "block is not in a block diagram"
        return self._bd

    # ---------------------------------------------------------------------- #
    # inputs to the block

    @property
    def parents(self) -> list[Block]:
        """
        List of blocks feeding into this block.

        :return: List of parent blocks
        :rtype: list of Block, of length ``nin``

        Returns the list of parent blocks, those that feed into this block.

        This is determined at compile time by the connections in the block diagram.  It
        is used to determine the order of block execution.

        :seealso: :meth:`Block.inports` :meth:`Block.inputs`
        """
        return [w.start.block for w in self._input_wires]

    @property
    def inports(self) -> list[Plug]:
        """
        List of output plugs feeding into this block.

        :return: List of source plugs
        :rtype: list of Plug, of length ``nin``

        Returns the list of plugs that describe the outout ports (block and port) that
        feed into this block.

        This is determined at compile time by the connections in the block diagram.  It
        is used to determine the order of block execution.

        :seealso: :meth:`Block.parents` :meth:`Block.inputs`
        """
        return [w.start for w in self._input_wires]

    @property
    def inport_values(self):
        """
        Get inport values as a list

        :return: list of input to block
        :rtype: list of length ``nin``

        Returns a list of values corresponding to the input ports of the block.  The types of the
        elements are dictated by the blocks connected to the input ports.

        .. note:: The value is obtained from the predecessor block's output values
            which are stored in the attribute ``_output_values`` -- a list of length
            ``nout``. These values are set when the predecessor block's ``output``
            method is evaluated.

        :seealso: :meth:`inport_value`
        """
        values = []
        for w in self._input_wires:
            plug = w.start
            # for port in range(self.nin):
            #     plug = self.sources[port]  # get plug for source block output
            values.append(plug.block.outport_value(plug.port))
        return values

    def inport_value(self, i: int) -> Any:
        """
        Get the value applied to specified input port.

        :param i: Input port index
        :type i: int
        :return: Input port value
        :rtype: Any

        Get the value of the signal applied to port ``i``.

        .. note:: The value is obtained from the predecessor block's output values
            which are stored in the attribute ``_output_values`` -- a list of length
            ``nout``. These values are set when the predecessor block's ``output``
            method is evaluated.

        :seealso: :meth:`inport_values`
        """
        source = self._parents[i].start
        return source.block.outport_value(source.port)

    def inport_name(self, i: int) -> str:
        """
        Get the name of an input port.

        :param i: Input port index
        :type i: int

        Get the name of an input port by index.  By default the name is the port number
        in square brackets, but if the block has named ports then the name is taken from
        the list of input port names.

        :seealso: :meth:`outport_name` :meth:`source_name`
        """
        assert i < self.nin, f"block {self.name} input port index {i} out of range"
        if self._inport_names is None:
            return f"[{i}]"
        else:
            return self._inport_names[i]

    def source_name(self, port):
        """
        Get the name of output port driving this input port.

        :param port: Input port
        :type port: int
        :return: Port name
        :rtype: str

        Get the name of the output port that drives the specified input port.  By default
        the name is the port number in square brackets, but if the block has named ports
        then the name is taken from the list of input port names.

        :seealso: :meth:`outport_name` :meth:`inport_name`
        """

        wire = self._input_wires[port]
        if wire.name is not None:
            return wire.name
        b = wire.start.block
        return f"{b.name}{b.outport_name(wire.start.port)}"

    # ---------------------------------------------------------------------- #
    # outputs of a block

    def outport_value(self, i: int) -> Any:
        """
        Get the value of an output port.

        :param i: Output port index
        :type i: int
        :return: Output port value
        :rtype: Any

        Get the value of the signal at output port ``i``.

        .. note:: The value is obtained from the block's output values
            which are stored in the attribute ``_output_values`` -- a list of length
            ``nout``. These values are set when the block's ``output``
            method is evaluated.

        :seealso: :meth:`inport_value`
        """
        assert (
            self._output_values[i] is not None
        ), f"block {self.name} output value {i} not set"
        return self._output_values[i]

    def outport_name(self, i: int) -> str:
        """
        Get the name of an output port.

        :param i: Output port index
        :type i: int

        Get the name of an output port by index.  By default the name is the port number
        in square brackets, but if the block has named ports then the name is taken from
        the list of output port names.

        :seealso: :meth:`inport_name` :meth:`source_name`
        """
        assert i < self.nout, f"block {self.name} output port index {i} out of range"
        if self._outport_names is None:
            return f"[{i}]"
        else:
            return self._outport_names[i]

    # ---------------------------------------------------------------------- #
    # methods used for unit testing

    #  test_MMMMM is a wrapper around the normal block method MMMMM, which checks the inputs and outputs for
    #  consistency with the block definition, and is used for concise unit tests.

    def test_output(self, *inputs, t=0.0, x=None):
        """
        Evaluate a block for unit testing.

        :param *inputs: Input port values
        :param t: Simulation time, defaults to 0.0
        :type t: float, optional
        :param x: state vector
        :type x: ndarray
        :return: Block output port values
        :rtype: list

        The output ports of the block are evaluated for a given simulation time
        and set of input port values. Input ports are assigned to consecutive inputs,
        output port values are a list.

        Mostly used for making concise unit tests.
        """
        # check inputs and assign to attribute
        assert len(inputs) == self.nin, "wrong number of inputs provided"

        # evaluate the block
        out = self.output(t, inputs, x)

        # sanity check the output
        assert isinstance(out, list), "result must be a list"
        assert len(out) == self.nout, "result list is wrong length"
        return out

    def test_deriv(self, *inputs, t=0.0, x=None):
        """
        Evaluate a block for unit testing.

        :param inputs: input port values
        :type inputs: list
        :param t: Simulation time, defaults to 0.0
        :type t: float, optional
        :param x: state vector
        :type x: ndarray
        :return: Block derivative value
        :rtype: ndarray

        The derivative of the block is evaluated for a given set of input port
        values. Input port values are treated as lists.

        Mostly used for making concise unit tests.
        """

        # check inputs and assign to attribute
        assert len(inputs) == self.nin, "wrong number of inputs provided"

        if x is not None:
            assert len(x) == self.nstates, "passed state is wrong length"

        # evaluate the block
        out = self.deriv(t, inputs, x)

        # sanity check the output
        assert isinstance(out, np.ndarray), "result must be an ndarray"
        assert out.shape == (self.nstates,), "result array is wrong length"
        return out

    def test_next(self, *inputs, t=0.0, x=None):
        """
        Evaluate a block for unit testing.

        :param inputs: input port values
        :type inputs: list
        :param t: Simulation time, defaults to 0.0
        :type t: float, optional
        :param x: state vector
        :type x: ndarray
        :return: Block next state value
        :rtype: ndarray

        The next value of a discrete time block is evaluated for a given set of input port
        values. Input port values are treated as lists.

        Mostly used for making concise unit tests.

        """

        # check inputs and assign to attribute
        assert len(inputs) == self.nin, "wrong number of inputs provided"

        if x is not None:
            assert len(x) == self.ndstates, "passed state is wrong length"

        # evaluate the block
        assert hasattr(self, "next"), "block does not have a next method"
        out = self.next(t, inputs, x)

        # sanity check the output
        assert isinstance(out, np.ndarray), "next state must be an ndarray"
        assert out.shape == (self.ndstates,), "next state array is wrong length"
        return out

    def test_step(self, *inputs, t=0.0) -> None:
        """
        Step a block for unit testing.

        :param inputs: input port values
        :type inputs: list
        :param t: Simulation time, defaults to 0.0
        :type t: float, optional

        Step the block for a given set of input port
        values. Input port values are treated as lists.

        Mostly used for making concise unit tests.

        """

        # check inputs and assign to attribute
        assert len(inputs) == self.nin, "wrong number of inputs provided"

        # step the block
        self.step(t, inputs)

    def test_start(self, simstate=None):

        from bdsim.run_sim import BDSimState, Options

        if simstate is None:

            class RunTime:
                def DEBUG(*args) -> None:
                    pass

            class BlockDiagram:
                pass

            self.bd = BlockDiagram()
            self.bd.runtime = RunTime()
            self.bd.runtime.options = Options()
            simstate = BDSimState()
            simstate.options = self.bd.runtime.options
            simstate.t = 0.0

        # step the block
        self.start(simstate)
        return simstate

    # ---------------------------------------------------------------------- #
    #  set/get items and attributes

    def __getitem__(self, port) -> Plug:
        """
        Convert a RHS block slice reference to a Plug.

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

    def __setitem__(self, port, src) -> None:
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
        return self.bd.connect(src, self[port])

    def __getattr__(self, name) -> Plug:
        """
        Convert a RHS block name reference to a Plug.

        :param name: Port name
        :type port: str
        :return: Block or plug for specified block port name
        :rtype: ``Port``

        Used to create a wired connection by assignment, for example::

            c = bd.CONSTANT(1, onames=['v'])

            y = c.v

                +---+               +---+
                | c | -v ---------> | y |
                +---+               +---+

        .. note::  this overloaded method handles all instances of ``setattr`` and
              implements normal functionality as well, only creating a wire
              if ``name`` is a known port name.

        .. warning:: to avoid infinite recursion, this method must use
            ``super().__getattribute__`` to access attributes of the block, and only
            create a Plug if the name is in the list of port names.
        """

        # come here only if the attribute is not found in the normal way, so we know
        # it's not a regular attribute of the block

        # we have to use self.__dict__.get() to avoid infinite recursion, since the port
        # names are stored in attributes of the block

        # on the RHS the ports must be output ports
        outport_names = self.__dict__.get("_outport_names")

        if outport_names is not None and name in outport_names:
            port = outport_names.index(name)
            return Plug(self, port)
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def __setattr__(self, name, value) -> None:
        """
        Convert a LHS block name reference to a wire.

        :param name: Port name
        :type port: str
        :param value: the RHS
        :type value: ``Port``

        Used to create a wired connection by assignment, for example::

            c = bd.CONSTANT(1, inames=['u'])

            c.u = x

        Ths method is invoked to create a wire from ``x`` to port 'u' of
        the constant block ``c``.

                +---+              +---+
                | x | --------> u- | c |
                +---+              +---+

        Notes:

            - this overloaded method handles all instances of ``setattr`` and
              implements normal functionality as well, only creating a wire
              if ``name`` is a known port name.
        """

        # b[port] = src
        # src --> b[port]
        # gets called for regular attribute settings, as well as for wiring

        # on the LHS the ports must be input ports

        inport_names = self.__dict__.get("_inport_names")
        if inport_names is not None and name in (inport_names or []):
            # we're doing wiring
            port = inport_names.index(name)
            self.bd.connect(value, Plug(value, port=0))
        else:
            # regular case, add attribute
            super().__setattr__(name, value)

    # ---------------------------------------------------------------------- #
    # methods used at compile time to build inter-block references

    def compile(self) -> None:
        """
        Compile the block for execution.

        This method is called at compile time to initialize the attributes required for
        compilation.

        :seealso: :meth:`BlockDiagram.compile`
        """
        # initialize lists of input and output ports
        #  these are set when blocks are connected, used to build inter-block references at compile time
        self._output_wires = [[]] * self.nout
        self._input_wires = [None] * self.nin

        # used to build execution plan at compile time, set by compile() method
        self._sequence = None
        self._parents = [None] * self.nin

    def add_output_wire(self, w) -> None:
        port = w.start.port
        assert port < len(self._output_wires), "port number too big"
        self._output_wires[port].append(w)

    def add_input_wire(self, w) -> None:
        port = w.end.port
        assert (
            self._input_wires[port] is None
        ), "attempting to connect second wire to an input"
        self._input_wires[port] = w
        self._parents[port] = w.start

    # ---------------------------------------------------------------------- #
    # operator overloads for implicit wiring

    @oodebug
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
        assert (
            s is not None
        ), "left operand of >> operator must be a block connected to a block diagram"
        # assert isinstance(right, Block), 'arguments to * must be blocks not ports (for now)'
        w = s.connect(left, right)  # add a wire
        # print('block * ' + str(w))
        return right

        # make connection, return a plug

    def _autoconstant(self, value):
        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic constant"

        if isinstance(value, (int, float, str)):
            name = "_const.{:d}({})".format(self.bd.n_auto_const, value)
        else:
            name = "_const.{:d}<{}>".format(self.bd.n_auto_const, type(value).__name__)
        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic constant"
        self.bd.n_auto_const += 1
        return self.bd.CONSTANT(value, name=name)

    def _autogain(self, value, **kwargs):
        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic gain"

        if isinstance(value, (int, float, str)):
            name = "_gain.{:d}({})".format(self.bd.n_auto_gain, value)
        else:
            name = "_gain.{:d}<{}>".format(self.bd.n_auto_gain, type(value).__name__)
        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic gain"
        self.bd.n_auto_gain += 1
        return self.bd.GAIN(value, name=name, **kwargs)

    def _autopow(self, value, **kwargs):
        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic power block"

        name = "_pow.{:d}({})".format(self.bd.n_auto_pow, value)
        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic power block"
        self.bd.n_auto_pow += 1
        return self.bd.POW(value, name=name, **kwargs)

    @oodebug
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
        from bdsim.blocks import Sum

        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic sum block"
        name = "_sum.{:d}".format(self.bd.n_auto_sum)
        self.bd.n_auto_sum += 1
        if isinstance(other, (int, float, np.ndarray)):
            # block + constant, create a CONSTANT block
            other = self._autoconstant(other)
        return Sum("++", inputs=(self, other), name=name, bd=self.bd)

    @oodebug
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
        from bdsim.blocks import Sum

        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic sum block"
        name = "_sum.{:d}".format(self.bd.n_auto_sum)
        self.bd.n_auto_sum += 1
        if isinstance(other, (int, float, np.ndarray)):
            # constant + block, create a CONSTANT block
            other = self._autoconstant(other)
        return Sum("++", inputs=(other, self), name=name, bd=self.bd)

    @oodebug
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
        from bdsim.blocks import Sum

        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic sum block"
        name = "_sum.{:d}".format(self.bd.n_auto_sum)
        self.bd.n_auto_sum += 1
        if isinstance(other, (int, float, np.ndarray)):
            # block - constant, create a CONSTANT block
            other = self._autoconstant(other)
        return Sum("+-", inputs=(self, other), name=name, bd=self.bd)

    @oodebug
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
        from bdsim.blocks import Sum

        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic sum block"

        name = "_sum.{:d}".format(self.bd.n_auto_sum)
        self.bd.n_auto_sum += 1
        if isinstance(other, (int, float, np.ndarray)):
            # constant - block, create a CONSTANT block
            other = self._autoconstant(other)
        return Sum("+-", inputs=(other, self), name=name, bd=self.bd)

    @oodebug
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

    @oodebug
    def __pow__(self, p):
        """
        Overloaded unary power operator for implicit block creation.

        :param self: A signal (block) to be negated
        :type self: Block
        :return: POW block
        :rtype: Block subclass

        This method is implicitly invoked by the ** operator for unary power when the operand is a ``Block``::

            result = X**3

        where ``X`` is a block.

        Creates a ``POW(3)`` block named ``_pow.N`` whose input is the
        operand.

        :seealso: :meth:`Plug.__pow__`
        """
        return self._autopow(p, inputs=[self])

    @oodebug
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
        from bdsim.blocks import Prod

        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic product block"

        matrix = False
        if isinstance(other, (int, float, np.ndarray)):
            # block * constant, create a GAIN block
            matrix: bool = isinstance(other, np.ndarray)
            return self._autogain(other, premul=matrix, matrix=matrix, inputs=[self])
        else:
            # value * value, create a PROD block
            name = "_prod.{:d}".format(self.bd.n_auto_prod)
            self.bd.n_auto_prod += 1
            return Prod(
                "**", inputs=[self, other], matrix=matrix, name=name, bd=self.bd
            )

    @oodebug
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
            matrix: bool = isinstance(other, np.ndarray)
            return self._autogain(other, premul=matrix, inputs=[self])

    @oodebug
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
        from bdsim.blocks import Prod

        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic product block"

        name = "_prod.{:d}".format(self.bd.n_auto_prod)
        self.bd.n_auto_prod += 1
        matrix = False
        if isinstance(other, (int, float, np.ndarray)):
            # block / constant, create a CONSTANT block
            other = self._autoconstant(other)
            matrix: bool = isinstance(other, np.ndarray)
        return Prod("*/", inputs=(self, other), matrix=matrix, name=name, bd=self.bd)

    @oodebug
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
        from bdsim.blocks import Prod

        assert (
            self.bd is not None
        ), "block must be connected to a block diagram to create an automatic product block"

        name = "_prod.{:d}".format(self.bd.n_auto_prod)
        self.bd.n_auto_prod += 1
        matrix = False
        if isinstance(other, (int, float, np.ndarray)):
            # constant / block, create a CONSTANT block
            other = self._autoconstant(other)
            matrix: bool = isinstance(other, np.ndarray)
        return Prod("*/", inputs=(other, self), matrix=matrix, name=name, bd=self.bd)

    # TODO arithmetic with a constant, add a gain block or a constant block

    # ---------------------------------------------------------------------- #

    def reset(self) -> None:
        self._updated = False
        self._output_values = [None] * self.nout

    def start(self, simstate) -> None:  # begin a simulation
        pass

    def check(self) -> None:  # check validity of block parameters at start
        assert hasattr(self, "nin"), f"block {self.name} has no nin specified"
        assert hasattr(self, "nout"), f"block {self.name} has no nout specified"

        assert (
            self.nin > 0 or self.nout > 0
        ), f"block {self.name} no inputs or outputs specified"
        assert (
            hasattr(self, "_initd") and self._initd
        ), "Block superclass not initalized. was super().__init__ called?"

    def done(self, **kwargs) -> None:  # end of simulation
        pass

    def savefig(self, *pos, **kwargs) -> None:
        pass


class SinkBlock(Block):
    """
    A SinkBlock is a subclass of Block that represents a block that has inputs
    but no outputs. Typically used to save data to a variable, file or
    graphics.
    """

    blockclass = "sink"

    def __init__(self, **blockargs) -> None:
        """
        Create a sink block.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: sink block base class
        :rtype: SinkBlock

        This is the parent class of all sink blocks.
        """
        # print('Sink constructor')
        super().__init__(nout=0, nstates=0, ndstates=0, **blockargs)

    @abstractmethod
    def step(self, t: float, inports: list) -> None:  # valid
        pass


class SourceBlock(Block):
    """
    A SourceBlock is a subclass of Block that represents a block that has outputs
    but no inputs.  Its output is a function of parameters and time.
    """

    blockclass = "source"

    def __init__(self, **blockargs) -> None:
        """
        Create a source block.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: source block base class
        :rtype: SourceBlock

        This is the parent class of all source blocks.
        """
        # print('Source constructor')
        super().__init__(nin=0, nstates=0, ndstates=0, **blockargs)

    @abstractmethod
    def output(self, t: float, inports: list, x):
        pass


class TransferBlock(Block):
    """
    A TransferBlock is a subclass of Block that represents a block with inputs
    outputs and states. Typically used to describe a continuous time dynamic
    system, either linear or nonlinear.
    """

    blockclass = "transfer"

    def __init__(self, nstates, **blockargs) -> None:
        """
        Create a transfer function block.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: transfer function block base class
        :rtype: TransferBlock

        This is the parent class of all transfer function blocks.
        """
        # print('Transfer constructor')
        super().__init__(nstates=nstates, ndstates=0, **blockargs)

    def reset(self) -> None:
        super().reset()
        self._x = self._x0
        # return self._x

    def setstate(self, x):
        x = np.array(x)
        self._x = x[: self.nstates]  # take as much state vector as we need
        return x[self.nstates :]  # return the rest

    def getstate0(self):
        return self._x0

    def check(self) -> None:
        super().check()
        assert len(self._x0) == self.nstates, "incorrect length for initial state"
        assert self.nin > 0 or self.nout > 0, "no inputs or outputs specified"

    @abstractmethod
    def deriv(self, t: float, inports: list) -> None:  # valid
        pass

    @abstractmethod
    def output(self, t: float, inports: list, x):
        pass


class FunctionBlock(Block):
    """
    A FunctionBlock is a subclass of Block that represents a block that has inputs
    and outputs but no state variables.  Typically used to describe operations
    such as gain, summation or various mappings.
    """

    blockclass = "function"

    def __init__(self, **blockargs) -> None:
        """
        Create a function block.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: function block base class
        :rtype: FunctionBlock

        This is the parent class of all function blocks.
        """
        # print('Function constructor')
        super().__init__(nstates=0, ndstates=0, **blockargs)

    @abstractmethod
    def output(self, t: float, inports: list, x):
        pass


class SubsystemBlock(Block):
    """
    A SubSystem  s a subclass of Block that represents a block that has inputs
    and outputs but no state variables.  Typically used to describe operations
    such as gain, summation or various mappings.
    """

    blockclass = "subsystem"

    def __init__(self, **blockargs) -> None:
        """
        Create a subsystem block.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: subsystem block base class
        :rtype: SubsystemBlock

        This is the parent class of all subsystem blocks.
        """
        # print('Subsystem constructor')
        super().__init__(nstates=0, ndstates=0, **blockargs)


class ClockedBlock(Block):
    """
    A ClockedBlock is a subclass of Block that represents a block with inputs
    outputs and discrete states. Typically used to describe a discrete time dynamic
    system, either linear or nonlinear.
    """

    blockclass = "clocked"

    def __init__(self, *, ndstates: int, clock: Clock, **blockargs) -> None:
        """
        Create a clocked block.

        :param ndstates: number of discrete-time states
        :type ndstates: int
        :param clock: the clock that governs the block's discrete time updates
        :type clock: Clock
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: clocked block base class
        :rtype: ClockedBlock

        This is the parent class of all clocked blocks.
        """
        # print('Clocked constructor')
        super().__init__(nstates=0, ndstates=ndstates, **blockargs)
        assert clock is not None, "clocked block must have a clock"
        self._clocked = True
        self._clock = clock
        clock.add_block(self)

    def reset(self) -> None:
        super().reset()
        # self._x = self._x0
        # return self._x

    def setstate(self, x):
        self._x = x[: self.ndstates]  # take as much state vector as we need
        # print('** set block state to ', self._x)
        return x[self.ndstates :]  # return the rest

    def getstate0(self):
        return self._x0

    def check(self) -> None:
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
