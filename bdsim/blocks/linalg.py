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
    """
    :blockname:`INVERSE`

    .. table::
       :align: left

    +----------+---------+---------+
    | inputs   | outputs |  states |
    +----------+---------+---------+
    | 1        | 2       | 0       |
    +----------+---------+---------+
    | A(M,N)   | A(N,M)  |         |
    |          | float   |         |
    +----------+---------+---------+
    """

    nin = 1
    nout = 2

    onames = ("inv", "cond")

    def __init__(self, pinv=False, **blockargs):
        """
        Matrix inverse.

        :param pinv: force pseudo inverse, defaults to False
        :type pinv: bool, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: An INVERSE block
        :rtype: Inverse instance

        Compute inverse of the 2D-array input signal.  If the matrix is square
        the inverse is computed unless the ``pinv`` flag is True.  For a
        non-square matrix the pseudo-inverse is used.  The condition number is
        output on the second port.

        :seealso: `numpy.linalg.inv <https://numpy.org/doc/stable/reference/generated/numpy.linalg.inv.html>`_,
            `numpy.linalg.pinv <https://numpy.org/doc/stable/reference/generated/numpy.linalg.pinv.html>`_,
            `numpy.linalg.cond <https://numpy.org/doc/stable/reference/generated/numpy.linalg.cond.html>`_
        """
        super().__init__(**blockargs)
        self.type = "inverse"

        self.pinv = pinv

    def output(self, t=None):

        mat = self.inputs[0]
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
    """
    :blockname:`TRANSPOSE`

    .. table::
       :align: left

    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | 1          | 1       | 0       |
    +------------+---------+---------+
    | A(M,N)     | A(N,M)  |         |
    +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, **blockargs):
        """
        Matrix transpose.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A TRANSPOSE block
        :rtype: Transpose instance

        Compute transpose of the 2D-array input signal.

        .. note::
            - An input 1D-array of shape (N,) is turned into a 2D-array column vector
              with shape (N,1).
            - An input 2D-array column vector of shape (N,1) becomes a 2D-array
             row vector with shape (1,N).

        :seealso: `numpy.linalg.transpose <https://numpy.org/doc/stable/reference/generated/numpy.linalg.transpose.html>`_
        """
        super().__init__(**blockargs)
        self.type = "transpose"

    def output(self, t=None):
        mat = self.inputs[0]

        if mat.ndim == 1:
            out = mat.reshape((mat.shape[0], 1))
        else:
            out = mat.T

        return [out]


# ------------------------------------------------------------------------ #


class Norm(FunctionBlock):
    """
    :blockname:`NORM`

    .. table::
       :align: left

    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | 1          | 1       | 0       |
    +------------+---------+---------+
    | A(N,)      | float   |         |
    | A(N,M)     |         |         |
    +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, ord=None, axis=None, **blockargs):
        """
        Array norm.

        :param axis: specifies the axis along which to compute the vector norms, defaults to None.
        :type axis: int, optional
        :param ord: Order of the norm, default to None.
        :type ord: int or str
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A NORM block
        :rtype: Norm instance

        Computes the specified norm for a 1D- or 2D-array.

        :seealso: `numpy.linalg.norm <https://numpy.org/doc/stable/reference/generated/numpy.linalg.norm.html>`_
        """
        super().__init__(**blockargs)
        self.type = "norm"
        self.args = dict(ord=ord, axis=axis)

    def output(self, t=None):
        vec = self.inputs[0]
        out = np.linalg.norm(vec, **self.args)
        return [out]


# ------------------------------------------------------------------------ #


class Flatten(FunctionBlock):
    """
    :blockname:`FLATTEN`

    .. table::
       :align: left

    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | 1          | 1       | 0       |
    +------------+---------+---------+
    | A(N,M )    | A(NM,)  |         |
    +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, order="C", **blockargs):
        """
        Flatten a multi-dimensional array.

        :param order: flattening order, either "C" or "F", defaults to "C"
        :type order: str
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A FLATTEN block
        :rtype: Flatten instance

        Flattens the incoming array in either row major ('C') or column major ('F') order.

        :seealso: `numpy.flatten <https://numpy.org/doc/stable/reference/generated/numpy.flatten.html>`_
        """
        super().__init__(**blockargs)
        self.type = "flatten"
        self.order = order

    def output(self, t=None):
        vec = self.inputs[0]
        out = vec.flatten(self.order)
        return [out]


# ------------------------------------------------------------------------ #


class Slice2(FunctionBlock):
    """
    :blockname:`SLICE2`

    .. table::
       :align: left

    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | 1          | 1       | 0       |
    +------------+---------+---------+
    | A(N,M)     | A(K,L)  |         |
    +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, rows=None, cols=None, **blockargs):
        """
        Slice out subarray of 2D-array.

        :param rows: row selection, defaults to None
        :type rows: tuple(3) or list
        :param cols: column selection, defaults to None
        :type cols: tuple(3) or list
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A SLICE2 block
        :rtype: Slice2 instance

        Compute a 2D slice of input 2D array.

        If ``rows`` or ``cols`` is ``None`` it means all rows or columns
        respectively.

        If ``rows`` or ``cols`` is a list, perform NumPy fancy indexing, returning
        the specified rows or columns

        Example::

            SLICE2(rows=[2,3])  # return rows 2 and 3, all columns
            SLICE2(cols=[4,1])  # return columns 4 and 1, all rows
            SLICE2(rows=[2,3], cols=[4,1]) # return elements [2,4] and [3,1] as a 1D array

        If a single row or column is selected, the result will be a 1D array

        If ``rows`` or ``cols`` is a tuple, it must have three elements.  It
        describes a Python slice ``(start, stop, step)`` where any element can be ``None``

            * ``start=None`` means start at first element
            * ``stop=None`` means finish at last element
            * ``step=None`` means step by one

        ``rows=None`` is equivalent to ``rows=(None, None, None)``.

        Example::

            SLICE2(rows=(None,None,2))  # return every second row
            SLICE2(cols=(None,None,-1)) # reverse the columns

        The list and tuple notation can be mixed, for example, one for rows
        and one for columns.

        :seealso: :class:`Slice1` :class:`Index`
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

    def output(self, t=None):
        array = self.inputs[0]
        if array.ndim != 2:
            raise RuntimeError("Slice2 block expecting 2d array")
        return [array[self.rows, self.cols]]


# ------------------------------------------------------------------------ #


class Slice1(FunctionBlock):
    """
    :blockname:`SLICE1`

    .. table::
       :align: left

    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | 1          | 1       | 0       |
    +------------+---------+---------+
    | A(N)       | A(M)    |         |
    +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, index, **blockargs):
        """
        Slice out subarray of 1D-array.

        :param index: slice, defaults to None
        :type index: tuple(3)
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A SLICE1 block
        :rtype: Slice1 instance

        Compute a 1D slice of input 1D array.

        If ``index`` is ``None`` it means all elements.

        If ``index`` is a list, perform NumPy fancy indexing, returning
        the specified elements

        Example::

            SLICE1(index=[2,3]) # return elements 2 and 3 as a 1D array
            SLICE1(index=[2])   # return element 2 as a 1D array
            SLICE1(index=2)     # return element 2 as a NumPy scalar

        If ``index`` is a tuple, it must have three elements.  It
        describes a Python slice ``(start, stop, step)`` where any element can be ``None``

            * ``start=None`` means start at first element
            * ``stop=None`` means finish at last element
            * ``step=None`` means step by one

        ``rows=None`` is equivalent to ``rows=(None, None, None)``.

        Example::

            SLICE1(index=(None,None,2))  # return every second element
            SLICE1(index=(None,None,-1)) # reverse the elements

        :seealso: :class:`Slice1`
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

    def output(self, t=None):
        array = self.inputs[0]
        if array.ndim != 1:
            raise RuntimeError("Slice1 block expecting 1d array")
        return [array[self.index]]


# ------------------------------------------------------------------------ #
class Det(FunctionBlock):
    """
    :blockname:`DET`

    .. table::
       :align: left

    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | 1          | 1       | 0       |
    +------------+---------+---------+
    | A(N,N)     | float   |         |
    +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, **blockargs):
        """
        Matrix determinant

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A DET block
        :rtype: Det instance

        Compute the matrix determinant.

        :seealso: `numpy.linalg.det <https://numpy.org/doc/stable/reference/generated/numpy.linalg.det.html>`_
        """
        super().__init__(**blockargs)
        self.type = "det"

    def output(self, t=None):
        mat = self.inputs[0]
        out = np.linalg.det(mat)
        return [out]


# ------------------------------------------------------------------------ #
class Cond(FunctionBlock):
    """
    :blockname:`COND`

    .. table::
       :align: left

    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | 1          | 1       | 0       |
    +------------+---------+---------+
    | A(N,M)     | float   |         |
    +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, **blockargs):
        """
        Compute the matrix condition number.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A COND block
        :rtype: Cond instance

        :seealso: `numpy.linalg.cond <https://numpy.org/doc/stable/reference/generated/numpy.linalg.cond.html>`_
        """
        super().__init__(**blockargs)
        self.type = "cond"

    def output(self, t=None):
        mat = self.inputs[0]
        out = np.linalg.cond(mat)
        return [out]


if __name__ == "__main__":  # pragma: no cover

    from pathlib import Path

    exec(open(Path(__file__).parent.parent.parent / "tests" / "test_linalg.py").read())
