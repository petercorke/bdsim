"""
Signal signatures.

A wire in a block diagram can carry any Python object, so a signature is first
of all the *type* of the value.  Only for an ``ndarray`` does it also record the
``shape`` and ``dtype``, since for any other type those are not defined (a
``list`` has a length, but the length is not part of its signature).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
