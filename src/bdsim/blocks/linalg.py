"""
Linear algebra blocks:

- have inputs and outputs
- have no state variables
- are a subclass of ``FunctionBlock`` |rarr| ``Block``

"""

from __future__ import annotations

import numpy as np
from typing import Any

from bdsim.components import FunctionBlock

IndexSpec = slice | list[Any]


def _index_spec(value: Any, what: str) -> IndexSpec:
    """
    A slice or list given as a block parameter, in the form NumPy indexes with.

    :param value: ``None`` for everything, a list for fancy indexing, or a 3-tuple
        ``(start, stop, step)`` for a slice
    :param what: the name of the parameter, for the error message
    :raises ValueError: the value is none of these
    """
    if value is None:
        return slice(None, None, None)
    if isinstance(value, (slice, list)):
        return value
    if isinstance(value, tuple) and len(value) == 3:
        return slice(*value)
    raise ValueError(f"bad {what} specifier")


class Inverse(FunctionBlock):
    r"""
    :blockname:`INVERSE`

    Matrix inverse.

    :inputs: 1
    :outputs: 2
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - 0
            - ndarray
            - :math:`\mathbf{A}`
        *   - Output
            - 0
            - ndarray
            - :math:`\mathbf{A}^{-1}`
        *   - Output
            - 1
            - float
            - :math:`\mbox{cond}(\mathbf{A})`

    Compute inverse of the 2D-array input signal.  If the matrix is square
    the inverse is computed unless the ``pinv`` flag is True.  For a
    non-square matrix the pseudo-inverse is used.  The condition number is
    output on the second port.

    :seealso: :func:`numpy.linalg.inv` :func:`numpy.linalg.pinv` :func:`numpy.linalg.cond`
    """

    nin = 1
    nout = 2

    onames = ("inv", "cond")

    def __init__(self, pinv: bool = False, **blockargs: Any) -> None:
        """
        :param pinv: force pseudo inverse, defaults to False
        :type pinv: bool, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(**blockargs)

        self.pinv: bool = pinv
        self.add_param("pinv")

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        mat = inputs[0]
        if isinstance(mat, np.ndarray):
            _pinv: bool
            if mat.shape[0] != mat.shape[1]:
                _pinv = True
            else:
                _pinv = self.pinv

            out: np.ndarray[tuple[Any, ...], np.dtype[np.float64]]
            if _pinv:
                out = np.linalg.pinv(mat)
            else:
                try:
                    out = np.linalg.inv(mat)
                except np.linalg.LinAlgError:
                    raise RuntimeError("matrix is singular")
            return [out, np.linalg.cond(mat)]

        elif hasattr(mat, "inv"):
            # ask the object to invert itself
            return [mat.inv(), None]
        else:
            raise RuntimeError("object cannot be inverted")


# ------------------------------------------------------------------------ #
class Transpose(FunctionBlock):
    r"""
    :blockname:`TRANSPOSE`

    Matrix transpose.

    :inputs: 1
    :outputs: 2
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - 0
            - ndarray
            - :math:`\mathbf{A}`
        *   - Output
            - 0
            - ndarray
            - :math:`\mathbf{A}^{\top}`

    Compute transpose of the 2D-array input signal.

    .. note::
        - An input 1D-array of shape (N,) is turned into a 2D-array column vector
          with shape (N,1).
        - An input 2D-array column vector of shape (N,1) becomes a 2D-array
          row vector with shape (1,N).

    :seealso: :func:`numpy.linalg.transpose`
    """

    nin = 1
    nout = 1

    def __init__(self, **blockargs: Any) -> None:
        """
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(**blockargs)

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        mat = inputs[0]

        if mat.ndim == 1:
            out = mat.reshape((mat.shape[0], 1))
        else:
            out = mat.T

        return [out]


# ------------------------------------------------------------------------ #


class Norm(FunctionBlock):
    r"""
    :blockname:`NORM`

    Array norm.

    :inputs: 1
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - 0
            - ndarray
            - :math:`\mathbf{A}`
        *   - Output
            - 0
            - ndarray
            - :math:`\|\mathbf{A}\|`

    Computes the specified norm for a 1D- or 2D-array.

    :seealso: :func:`numpy.linalg.norm`
    """

    nin = 1
    nout = 1

    def __init__(self, ord: Any = None, axis: Any = None, **blockargs: Any) -> None:
        """
        :param axis: specifies the axis along which to compute the vector norms, defaults to None.
        :type axis: int, optional
        :param ord: Order of the norm, default to None.
        :type ord: int or str
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(**blockargs)
        self.ord = ord
        self.axis = axis
        self.add_param("ord", coerce=False)
        self.add_param("axis", coerce=False)

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        vec = inputs[0]
        out = np.linalg.norm(vec, ord=self.ord, axis=self.axis)
        return [out]


# ------------------------------------------------------------------------ #


class Flatten(FunctionBlock):
    r"""
    :blockname:`FLATTEN`

    Flatten a multi-dimensional array.

    :inputs: 1
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - 0
            - ndarray
            - :math:`\mathbf{A}`
        *   - Output
            - 0
            - ndarray
            - :math:`\mbox{vec}(\mathbf{A})`

    Flattens the incoming array in either row major ('C') or column major ('F') order.

    :seealso: :meth:`numpy.ndarray.flatten`
    """

    nin = 1
    nout = 1

    def __init__(self, order: str = "C", **blockargs: Any) -> None:
        """
        :param order: flattening order, either "C" or "F", defaults to "C"
        :type order: str
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(**blockargs)
        self.order: str = order
        self.add_param("order")

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        vec = inputs[0]
        out = vec.flatten(self.order)
        return [out]


# ------------------------------------------------------------------------ #


class Slice2(FunctionBlock):
    r"""
    :blockname:`SLICE2`

    Slice out subarray of 2D-array.

    :inputs: 1
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - 0
            - ndarray
            - :math:`\mathbf{A}`
        *   - Output
            - 0
            - ndarray
            - :math:`\mathbf{A}_{i\ldots j, m\ldots n}`

    Compute a 2D slice of input 2D array.

    If ``rows`` or ``cols`` is ``None`` it means all rows or columns
    respectively.

    If ``rows`` or ``cols`` is a list, perform NumPy fancy indexing, returning
    the specified rows or columns

    Example::

        slice = bd.SLICE2(rows=[2,3])  # return rows 2 and 3, all columns
        slice = bd.SLICE2(cols=[4,1])  # return columns 4 and 1, all rows
        slice = bd.SLICE2(rows=[2,3], cols=[4,1]) # return elements [2,4] and [3,1] as a 1D array

    If a single row or column is selected, the result will be a 1D array

    If ``rows`` or ``cols`` is a tuple, it must have three elements.  It
    describes a Python slice ``(start, stop, step)`` where any element can be ``None``

        * ``start=None`` means start at first element
        * ``stop=None`` means finish at last element
        * ``step=None`` means step by one

    ``rows=None`` is equivalent to ``rows=(None, None, None)``.

    Example::

        slice = bd.SLICE2(rows=(None,None,2))  # return every second row
        slice = bd.SLICE2(cols=(None,None,-1)) # reverse the columns

    The list and tuple notation can be mixed, for example, one for rows
    and one for columns.

    :seealso: :class:`Slice1` :class:`Index`
    """

    nin = 1
    nout = 1

    def __init__(self, rows: Any = None, cols: Any = None, **blockargs: Any) -> None:
        """
        :param rows: row selection, defaults to None
        :type rows: tuple(3) or list
        :param cols: column selection, defaults to None
        :type cols: tuple(3) or list
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(**blockargs)

        self.rows = rows
        self.cols = cols
        self.add_param("rows", coerce=False)
        self.add_param("cols", coerce=False)

    @property
    def rows(self) -> IndexSpec:
        """Rows to select, a slice or a list of row numbers."""
        return self._rows

    @rows.setter
    def rows(self, value: Any) -> None:
        self._rows = _index_spec(value, "rows")

    @property
    def cols(self) -> IndexSpec:
        """Columns to select, a slice or a list of column numbers."""
        return self._cols

    @cols.setter
    def cols(self, value: Any) -> None:
        self._cols = _index_spec(value, "columns")

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        array = inputs[0]
        if array.ndim != 2:
            raise RuntimeError("Slice2 block expecting 2d array")
        return [array[self._rows, self._cols]]


# ------------------------------------------------------------------------ #


class Slice1(FunctionBlock):
    r"""
    :blockname:`SLICE1`

    Slice out subarray of 1D-array.

    :inputs: 1
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - 0
            - ndarray
            - :math:`v`
        *   - Output
            - 0
            - ndarray
            - :math:`v_{i\dots j}`

    Compute a 1D slice of input 1D array.

    If ``index`` is ``None`` it means all elements.

    If ``index`` is a list, perform NumPy fancy indexing, returning
    the specified elements

    Example::

        slice = bd.SLICE1(index=[2,3]) # return elements 2 and 3 as a 1D array
        slice = bd.SLICE1(index=[2])   # return element 2 as a 1D array
        slice = bd.SLICE1(index=2)     # return element 2 as a NumPy scalar

    If ``index`` is a tuple, it must have three elements.  It
    describes a Python slice ``(start, stop, step)`` where any element can be ``None``

        * ``start=None`` means start at first element
        * ``stop=None`` means finish at last element
        * ``step=None`` means step by one

    ``rows=None`` is equivalent to ``rows=(None, None, None)``.

    Example::

        slice = bd.SLICE1(index=(None,None,2))  # return every second element
        slice = bd.SLICE1(index=(None,None,-1)) # reverse the elements

    :seealso: :class:`Slice1`
    """

    nin = 1
    nout = 1

    def __init__(self, index: Any, **blockargs: Any) -> None:
        """
        :param index: slice, defaults to None
        :type index: tuple(3)
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(**blockargs)

        self.index = index
        self.add_param("index", coerce=False)

    @property
    def index(self) -> IndexSpec:
        """Elements to select, a slice or a list of element numbers."""
        return self._index

    @index.setter
    def index(self, value: Any) -> None:
        self._index = _index_spec(value, "index")

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        array = inputs[0]
        if array.ndim != 1:
            raise RuntimeError("Slice1 block expecting 1d array")
        return [array[self._index]]


# ------------------------------------------------------------------------ #
class Det(FunctionBlock):
    r"""
    :blockname:`DET`

    Matrix determinant.

    :inputs: 1
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - 0
            - ndarray
            - :math:`\mathbf{A}`
        *   - Output
            - 0
            - ndarray
            - :math:`\mbox{det}(\mathbf{A})`

    Compute the matrix determinant.

    :seealso: :func:`numpy.linalg.det`
    """

    nin = 1
    nout = 1

    def __init__(self, **blockargs: Any) -> None:
        """
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(**blockargs)

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        mat = inputs[0]
        out = np.linalg.det(mat)
        return [out]


# ------------------------------------------------------------------------ #
class Cond(FunctionBlock):
    r"""
    :blockname:`COND`

    Matrix condition number.

    :inputs: 1
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - 0
            - ndarray
            - :math:`\mathbf{A}`
        *   - Output
            - 0
            - ndarray
            - :math:`\mbox{cond}(\mathbf{A})`

    :seealso: :func:`numpy.linalg.cond`
    """

    nin = 1
    nout = 1

    def __init__(self, **blockargs: Any) -> None:
        """
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(**blockargs)

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        mat = inputs[0]
        out = np.linalg.cond(mat)
        return [out]


if __name__ == "__main__":  # pragma: no cover
    from pathlib import Path
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[3]
    test_file = (
        root / "tests" / "blocks" / f"test_blocks_{Path(__file__).stem.lower()}.py"
    )

    if not test_file.exists():
        print(f"No module unit tests found for {Path(__file__).name}: {test_file}")
        raise SystemExit(0)

    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", str(test_file)]))
