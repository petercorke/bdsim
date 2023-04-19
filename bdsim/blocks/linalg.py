"""
Linear algebra blocks:

- have inputs and outputs
- have no state variables
- are a subclass of ``FunctionBlock`` |rarr| ``Block``

"""

# The constructor of each class ``MyClass`` with a ``@block`` decorator becomes a method ``MYCLASS()`` of the BlockDiagram instance.

import numpy as np
import math

from bdsim.components import FunctionBlock


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

    :seealso: `numpy.linalg.inv <https://numpy.org/doc/stable/reference/generated/numpy.linalg.inv.html>`_,
        `numpy.linalg.pinv <https://numpy.org/doc/stable/reference/generated/numpy.linalg.pinv.html>`_,
        `numpy.linalg.cond <https://numpy.org/doc/stable/reference/generated/numpy.linalg.cond.html>`_
    """

    nin = 1
    nout = 2

    onames = ("inv", "cond")

    def __init__(self, pinv=False, **blockargs):
        """
        :param pinv: force pseudo inverse, defaults to False
        :type pinv: bool, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(**blockargs)
        self.type = "inverse"

        self.pinv = pinv

    def output(self, t, inports, x):
        mat = inports[0]
        if isinstance(mat, np.ndarray):
            if mat.shape[0] != mat.shape[1]:
                pinv = True
            else:
                pinv = self.pinv

            if pinv:
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

    :seealso: `numpy.linalg.transpose <https://numpy.org/doc/stable/reference/generated/numpy.linalg.transpose.html>`_
    """

    nin = 1
    nout = 1

    def __init__(self, **blockargs):
        """
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(**blockargs)
        self.type = "transpose"

    def output(self, t, inports, x):
        mat = inports[0]

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

    :seealso: `numpy.linalg.norm <https://numpy.org/doc/stable/reference/generated/numpy.linalg.norm.html>`_
    """

    nin = 1
    nout = 1

    def __init__(self, ord=None, axis=None, **blockargs):
        """
        :param axis: specifies the axis along which to compute the vector norms, defaults to None.
        :type axis: int, optional
        :param ord: Order of the norm, default to None.
        :type ord: int or str
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(**blockargs)
        self.type = "norm"
        self.args = dict(ord=ord, axis=axis)

    def output(self, t, inports, x):
        vec = inports[0]
        out = np.linalg.norm(vec, **self.args)
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

    :seealso: `numpy.flatten <https://numpy.org/doc/stable/reference/generated/numpy.flatten.html>`_
    """

    nin = 1
    nout = 1

    def __init__(self, order="C", **blockargs):
        """
        :param order: flattening order, either "C" or "F", defaults to "C"
        :type order: str
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(**blockargs)
        self.type = "flatten"
        self.order = order

    def output(self, t, inports, x):
        vec = inports[0]
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

    def __init__(self, rows=None, cols=None, **blockargs):
        """
        :param rows: row selection, defaults to None
        :type rows: tuple(3) or list
        :param cols: column selection, defaults to None
        :type cols: tuple(3) or list
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(**blockargs)
        self.type = "slice2"

        if rows is None:
            self.rows = slice(None, None, None)
        elif isinstance(rows, list):
            self.rows = rows
        elif isinstance(rows, tuple) and len(rows) == 3:
            self.rows = slice(*rows)
        else:
            raise ValueError("bad rows specifier")

        if cols is None:
            self.cols = slice(None, None, None)
        elif isinstance(cols, list):
            self.cols = cols
        elif isinstance(cols, tuple) and len(cols) == 3:
            self.cols = slice(*cols)
        else:
            raise ValueError("bad columns specifier")

    def output(self, t, inports, x):
        array = inports[0]
        if array.ndim != 2:
            raise RuntimeError("Slice2 block expecting 2d array")
        return [array[self.rows, self.cols]]


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

    def __init__(self, index, **blockargs):
        """
        :param index: slice, defaults to None
        :type index: tuple(3)
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(**blockargs)
        self.type = "slice1"

        if index is None:
            self.index = slice(None, None, None)
        elif isinstance(index, list):
            self.index = index
        elif isinstance(index, tuple) and len(index) == 3:
            self.index = slice(*index)
        else:
            raise ValueError("bad index specifier")

    def output(self, t, inports, x):
        array = inports[0]
        if array.ndim != 1:
            raise RuntimeError("Slice1 block expecting 1d array")
        return [array[self.index]]


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

    :seealso: `numpy.linalg.det <https://numpy.org/doc/stable/reference/generated/numpy.linalg.det.html>`_
    """

    nin = 1
    nout = 1

    def __init__(self, **blockargs):
        """
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(**blockargs)
        self.type = "det"

    def output(self, t, inports, x):
        mat = inports[0]
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

    :seealso: `numpy.linalg.cond <https://numpy.org/doc/stable/reference/generated/numpy.linalg.cond.html>`_
    """

    nin = 1
    nout = 1

    def __init__(self, **blockargs):
        """
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(**blockargs)
        self.type = "cond"

    def output(self, t, inports, x):
        mat = inports[0]
        out = np.linalg.cond(mat)
        return [out]


if __name__ == "__main__":  # pragma: no cover

    from pathlib import Path

    exec(open(Path(__file__).parent.parent.parent / "tests" / "test_linalg.py").read())
