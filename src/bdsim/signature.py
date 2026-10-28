"""
Signal signatures.

A wire in a block diagram can carry any Python object, so a signature is first
of all the *type* of the value.  Only for an ``ndarray`` does it also record the
``shape`` and ``dtype``, since for any other type those are not defined (a
``list`` has a length, but the length is not part of its signature).
"""

from __future__ import annotations

import numbers
import operator
from dataclasses import dataclass
from functools import reduce
from typing import Any, Sequence

import numpy as np


@dataclass(frozen=True, slots=True)
class Signature:
    """
    The type of the signal on a wire.

    :param type: Python type of the value
    :param shape: shape, only if ``type`` is ``ndarray``, otherwise ``None``
    :param dtype: element type, only if ``type`` is ``ndarray``, otherwise ``None``

    Create one from a value with :meth:`of`.  Signatures are immutable and
    compare by value.

    A Python or NumPy scalar has no shape: its signature is just its type, for
    example ``int``, ``float`` or ``numpy.float64``.  A 1-D array of size 1 is
    presented by bdsim as a scalar, so it does not appear as a signature.

    :seealso: :meth:`of`
    """

    type: type
    shape: tuple[int, ...] | None = None
    dtype: np.dtype | None = None

    @classmethod
    def of(cls, value: Any) -> Signature:
        """
        Signature of a value.

        :param value: any Python object
        :return: its signature
        """
        if isinstance(value, np.ndarray):
            return cls(np.ndarray, value.shape, value.dtype)
        return cls(type(value))

    def __str__(self) -> str:
        if self.type is np.ndarray:
            return f"ndarray{self.shape} {self.dtype}"
        return self.type.__name__


def unify(*values: Any, names: Sequence[str] | None = None) -> tuple[Any, ...]:
    """
    Make the values a source block emits all of one type, or raise.

    :param values: the values, for example the ``off`` and ``on`` of a step
    :param names: names of the parameters, used in error messages
    :raises TypeError: the values are of different types
    :raises ValueError: the values are arrays with different shape or dtype
    :return: the values, with numbers promoted to a common type

    A source whose output is one of several values must emit the same type
    every time, otherwise the signal on its wire changes type during a run.
    The rules, in order:

    1. all ``ndarray``: shape and dtype must match, otherwise ``ValueError``.
       There is no promotion between arrays.
    2. an ``ndarray`` with anything else: ``TypeError``.
    3. all ``bool`` (or ``numpy.bool_``): accepted.  A bool with a non-bool is
       ``TypeError``, since ``True`` is also the integer 1 and the intent is
       ambiguous.
    4. all numbers (``numbers.Number``, including NumPy scalars): promoted to a
       common type by Python's own numeric tower, the type of their sum, so
       ``(0, 1.0)`` becomes ``(0.0, 1.0)`` and ``(0, 1)`` is unchanged.
    5. anything else: all must be exactly the same type, so ``[0]`` and ``[1]``
       are fine and so are two strings or two ``SE3``.  A list is not turned
       into an array.

    The values are returned in order.  Values that need no change are returned
    as the same objects.
    """
    if len(values) == 0:
        return ()
    if names is None:
        names = [f"value {i}" for i in range(len(values))]
    if len(names) != len(values):
        raise ValueError("names and values must be the same length")

    def describe() -> str:
        return ", ".join(f"{n} is {Signature.of(v)}" for n, v in zip(names, values))

    first = values[0]

    # 1. and 2. arrays
    if any(isinstance(v, np.ndarray) for v in values):
        if not all(isinstance(v, np.ndarray) for v in values):
            raise TypeError(f"an array cannot be mixed with another type: {describe()}")
        for n, v in zip(names, values):
            if v.shape != first.shape or v.dtype != first.dtype:
                raise ValueError(
                    f"arrays must have the same shape and dtype: {describe()}"
                )
        return tuple(values)

    # 3. bool is a subclass of int, so it must be recognised first
    is_bool = [isinstance(v, (bool, np.bool_)) for v in values]
    if any(is_bool):
        if not all(is_bool) or len({type(v) for v in values}) != 1:
            raise TypeError(f"a bool cannot be mixed with another type: {describe()}")
        return tuple(values)

    # 4. numbers
    if all(isinstance(v, numbers.Number) for v in values):
        try:
            common = type(reduce(operator.add, values))
            return tuple(v if type(v) is common else common(v) for v in values)
        except (TypeError, OverflowError) as err:
            raise TypeError(f"cannot promote to a common type: {describe()}") from err

    # 5. everything else
    if len({type(v) for v in values}) != 1:
        raise TypeError(f"must all be the same type: {describe()}")
    return tuple(values)


def _is_numeric(value: Any) -> bool:
    """Is ``value`` a number, a bool, a numeric ndarray, or a list or tuple of those?"""
    if isinstance(value, (bool, np.bool_, numbers.Number)):
        return True
    if isinstance(value, np.ndarray):
        return value.dtype.kind in "biufc"
    if isinstance(value, (list, tuple)):
        return all(_is_numeric(v) for v in value)
    return False


def maybe_asarray(value: Any, asarray: bool = True) -> Any:
    """
    Turn a list or tuple of numbers into an ``ndarray``, for blocks that emit a value.

    :param value: the value a block is to emit
    :param asarray: if false, return ``value`` unchanged
    :return: an ``ndarray`` if ``value`` is a non-empty list or tuple of numbers,
        otherwise ``value`` itself

    **By default a list or tuple of numbers is converted to an ``ndarray`` with
    the dtype NumPy chooses: ``int64`` if all the elements are integers,
    ``float64`` if any is a float, ``bool`` for bools and ``complex128`` for
    complex numbers.**  (On Windows with NumPy 1.x the integer default is
    ``int32``.)  Nested lists give a 2-D array, and elements that already have
    a dtype, such as ``np.float32(1)``, keep it.  To get a different dtype, pass
    an array: ``np.array([1, 2], dtype=np.float32)``.

    A user who writes ``CONSTANT([1, 2, 3])`` wants a vector, and arithmetic on
    a ``list`` is not vector arithmetic (``[1, 2] * 2`` is ``[1, 2, 1, 2]``).
    Only a sequence whose elements are all numbers, bools, or lists and arrays
    of them is converted.  A list of strings, of objects (including ``SE3``,
    which NumPy would otherwise stack into an array of matrices), a ragged
    list, an empty list and every other type are returned as given.
    """
    if asarray and isinstance(value, (list, tuple)) and _is_numeric(value):
        try:
            array = np.asarray(value)
        except ValueError:  # ragged
            return value
        if array.size > 0:
            return array
    return value
