"""
NumPy dtype literals for parameters given as text.

A ``.bd`` file is JSON, so a block parameter that is not a JSON type is written as a
string.  The same applies to a value given on the command line with ``--set``.  The
text form of a NumPy scalar or array is the NumPy constructor::

    float32(2)            a numpy.float32 scalar
    float32([1, 2])       a float32 array
    uint16(5)             a numpy.uint16 scalar
    uint16([5, 6])        a uint16 array
    int8([[1, 2], [3, 4]])  a 2-D int8 array
    complex64(1+2j)       a complex64 scalar

The types are ``bool_``, ``int8`` to ``int64``, ``uint8`` to ``uint64``, ``float16``,
``float32``, ``float64``, ``complex64`` and ``complex128``.  A leading ``np.`` or
``numpy.`` is accepted, and so is a leading ``=``, the marker the loader already uses
for an expression.  The default types need no marker: a JSON list of integers or
floats is already an ``int64`` or ``float64`` array for the blocks that convert it.

The text is parsed, never evaluated.  Only a dtype name applied to a number, or to a
nested list or tuple of numbers, is accepted, where a number is an integer, float,
complex or bool literal, optionally signed, or one of ``inf``, ``nan`` and ``pi``.
Anything else is not a literal, and the caller carries on as it would have.  So this
works with ``allow_eval=False``.

An integer out of range for its type, such as ``uint16(70000)`` or ``uint8(-1)``, and a
float that overflows, such as ``float32(1e60)``, are errors, not wrap-around.

:func:`format_literal` is the inverse, for anything that writes such a parameter.
"""

from __future__ import annotations

import ast
import math
import re
from typing import Any

import numpy as np


class _NotALiteral:
    def __repr__(self) -> str:
        return "NOT_A_LITERAL"


NOT_A_LITERAL = _NotALiteral()
"""Returned by :func:`parse_literal` for text that is not a dtype literal."""

DTYPES: dict[str, Any] = {
    name: getattr(np, name)
    for name in (
        "bool_",
        "int8",
        "int16",
        "int32",
        "int64",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "float16",
        "float32",
        "float64",
        "complex64",
        "complex128",
    )
}

_CONSTANTS = {"inf": math.inf, "nan": math.nan, "pi": math.pi}

# cheap test before parsing: the text starts like a call, np.name( or name(
_CANDIDATE = re.compile(r"^\s*=?\s*(?:(?:np|numpy)\.)?[A-Za-z_][A-Za-z0-9_]*\s*\(")


class _Reject(Exception):
    """The text is not a dtype literal."""


def _number(node: ast.expr) -> Any:
    """A number literal: int, float, complex or bool, signed, or inf, nan, pi."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (bool, int, float, complex)):
            return node.value
        raise _Reject
    if isinstance(node, ast.Name):
        if node.id in _CONSTANTS:
            return _CONSTANTS[node.id]
        raise _Reject
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _number(node.operand)
        return -value if isinstance(node.op, ast.USub) else +value
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
        # only to write a complex number: a real part plus or minus an imaginary literal
        right = node.right
        if not (
            isinstance(right, ast.Constant)
            and isinstance(right.value, complex)
            and right.value.real == 0
        ):
            raise _Reject
        left = _number(node.left)
        if isinstance(left, complex):
            raise _Reject
        return (
            left + right.value if isinstance(node.op, ast.Add) else left - right.value
        )
    raise _Reject


def _value(node: ast.expr) -> Any:
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_value(element) for element in node.elts]
    return _number(node)


def _shape(value: Any) -> tuple[int, ...]:
    """Shape of nested lists of numbers, rejecting a ragged one."""
    if not isinstance(value, list):
        return ()
    if len(value) == 0:
        return (0,)
    shapes = {_shape(element) for element in value}
    if len(shapes) != 1:
        raise _Reject
    return (len(value),) + shapes.pop()


def _leaves(value: Any) -> Any:
    if isinstance(value, list):
        for element in value:
            yield from _leaves(element)
    else:
        yield value


def parse_literal(text: Any) -> Any:
    """
    Parse a NumPy dtype literal such as ``float32([1, 2])`` or ``uint16(5)``.

    :param text: the text, or any other object
    :return: a NumPy scalar or ``ndarray`` of the requested dtype, or
        :data:`NOT_A_LITERAL` if ``text`` is not a string of that form
    :raises ValueError: the text is a dtype literal but a value does not fit the
        type, for example ``uint16(70000)``

    The text is parsed with :mod:`ast` and never evaluated, see the module
    documentation for what is accepted.
    """
    if not isinstance(text, str) or not _CANDIDATE.match(text):
        return NOT_A_LITERAL
    source = text.strip()
    if source.startswith("="):
        source = source[1:].strip()
    try:
        tree = ast.parse(source, mode="eval")
        call = tree.body
        if not isinstance(call, ast.Call) or call.keywords or len(call.args) != 1:
            return NOT_A_LITERAL
        func = call.func
        if isinstance(func, ast.Attribute):
            if not (
                isinstance(func.value, ast.Name) and func.value.id in ("np", "numpy")
            ):
                return NOT_A_LITERAL
            name = func.attr
        elif isinstance(func, ast.Name):
            name = func.id
        else:
            return NOT_A_LITERAL
        if name not in DTYPES:
            return NOT_A_LITERAL
        value = _value(call.args[0])
        shape = _shape(value)
    except (_Reject, SyntaxError, ValueError, RecursionError, MemoryError):
        return NOT_A_LITERAL

    try:
        return _convert(name, DTYPES[name], value, shape)
    except (ValueError, OverflowError) as err:
        raise ValueError(f"{text.strip()}: {err}") from err


def _convert(name: str, dtype: Any, value: Any, shape: tuple[int, ...]) -> Any:
    """Make the array or scalar, refusing values that do not fit the type."""
    kind = np.dtype(dtype).kind

    if kind in "iu":
        info = np.iinfo(dtype)
        for leaf in _leaves(value):
            if isinstance(leaf, complex):
                raise ValueError(f"a complex value is not a {name}")
            if isinstance(leaf, float):
                if not math.isfinite(leaf) or not leaf.is_integer():
                    raise ValueError(f"{leaf} is not an integer")
                leaf = int(leaf)
            if not info.min <= int(leaf) <= info.max:
                raise ValueError(f"{int(leaf)} is out of range for {name}")
        array = np.array(_as_ints(value), dtype=dtype)
    elif kind == "b":
        array = np.array(value, dtype=dtype)
    else:  # floating point and complex
        wide = np.complex128 if kind == "c" else np.float64
        if kind == "f" and any(isinstance(leaf, complex) for leaf in _leaves(value)):
            raise ValueError(f"a complex value is not a {name}")
        with np.errstate(over="ignore", invalid="ignore"):
            source = np.array(value, dtype=wide)
            array = np.array(value, dtype=dtype)
        if kind == "c":
            lost = (np.isfinite(source.real) & ~np.isfinite(array.real)) | (
                np.isfinite(source.imag) & ~np.isfinite(array.imag)
            )
        else:
            lost = np.isfinite(source) & ~np.isfinite(array)
        if np.any(lost):
            raise ValueError(f"a value overflows {name}")

    return array[()] if shape == () else array


def _as_ints(value: Any) -> Any:
    if isinstance(value, list):
        return [_as_ints(element) for element in value]
    return int(value)


# ---------------------------------------------------------------------------- #


def _float_str(x: Any) -> str:
    """Shortest text that reads back as the same value in the same float type."""
    if np.isnan(x):
        return "nan"
    if np.isinf(x):
        return "inf" if x > 0 else "-inf"
    magnitude = abs(float(x))
    if magnitude != 0 and (magnitude < 1e-4 or magnitude >= 1e15):
        return str(np.format_float_scientific(x, unique=True, trim="."))
    return str(np.format_float_positional(x, unique=True, trim="."))


def _leaf_str(x: Any, kind: str) -> str:
    if kind == "b":
        return "True" if x else "False"
    if kind in "iu":
        return str(int(x))
    if kind == "f":
        return _float_str(x)
    real, imag = x.real, x.imag
    if not (np.isfinite(real) and np.isfinite(imag)):
        raise ValueError(
            "a complex value that is not finite cannot be written as a literal"
        )
    imag_text = _float_str(imag)
    if not imag_text.startswith("-"):
        imag_text = "+" + imag_text
    return f"{_float_str(real)}{imag_text}j"


def _array_str(a: np.ndarray, kind: str) -> str:
    if a.ndim == 0:
        return _leaf_str(a[()], kind)
    return "[" + ", ".join(_array_str(sub, kind) for sub in a) + "]"


def format_literal(value: Any) -> str:
    """
    Write a NumPy scalar or array as a dtype literal, the inverse of :func:`parse_literal`.

    :param value: a NumPy scalar or ``ndarray`` of a supported dtype
    :return: text such as ``float32([1.5, 2.0])`` or ``uint16(5)``
    :raises ValueError: the dtype is not supported, or the value is not a NumPy scalar
        or array

    Floats are written as the shortest text that gives the same value in the same
    type, so ``parse_literal(format_literal(x))`` equals ``x`` exactly, with the same
    dtype and shape.
    """
    if not isinstance(value, (np.generic, np.ndarray)):
        raise ValueError(f"{type(value).__name__} is not a NumPy scalar or array")
    dtype = value.dtype
    name = "bool_" if dtype == np.dtype(bool) else dtype.name
    if name not in DTYPES or np.dtype(DTYPES[name]) != dtype:
        raise ValueError(f"dtype {dtype} cannot be written as a literal")
    array = np.asarray(value)
    return f"{name}({_array_str(array, dtype.kind)})"
