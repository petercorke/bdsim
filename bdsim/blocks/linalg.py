"""
Function blocks:

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
    
    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | 1          | 1       | 0       |
    +------------+---------+---------+
    | ndarray   | ndarray  |         | 
    +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, *inputs, pinv=False, **kwargs):
        """
        :param pinv: force pseudo inverse
        :type pinv: bool
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param ``**kwargs``: common Block options
        :return: A SUM block
        :rtype: Inverse instance
        
        Create a matrix inverse.
        """
        super().__init__(inputs=inputs, **kwargs)

        self.pinv = pinv
        
    def output(self, t=None):

        mat = self.inputs[0]
        if mat.shape[0] != mat.shape[1]:
            pinv = True
        else:
            pinv = self.pinv

        if pinv:
            out = np.linalg.pinv()
        else:
            out = np.linalg.inv(mat)

        return [out]

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
    | ndarray    | ndarray |         | 
    +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, *inputs, **kwargs):
        """
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param ``**kwargs``: common Block options
        :return: A TRANSPOSE block
        :rtype: Transpose instance
        
        Create a matrix transpose block.
    
        .. note::
            - A 1D array is turned into a 2D column vector.
            - A column vector becomes a 2D row vector
    
        """
        super().__init__(inputs=inputs, **kwargs)

    def output(self, t=None):
        mat = self.inputs[0]

        if ndim == 1:
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
    | ndarray    | float   |         | 
    +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, *inputs, **kwargs):
        """
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param ``**kwargs``: common Block options
        :return: A NORM block
        :rtype: Norm instance
        
        Create a vector norm block.
        """
        super().__init__(inputs=inputs, **kwargs)

    def output(self, t=None):
        vec = self.inputs[0]
        out = np.linalg.norm(vec)
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
    | ndarray    | ndarray |         | 
    +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, order='C', **kwargs):
        """
        :param ``**kwargs``: common Block options
        :return: A FLATTEN block
        :rtype: Flatten instance

        Create an array flattening block.  Flattens the incoming array in either
        row major ('C') or column major ('F') order.
        
        """
        super().__init__(**kwargs)
        self.type = 'flatten'
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
    | ndarray    | ndarray |         | 
    +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, rows=None, cols=None, **kwargs):
        """
        :param rows: row selection, defaults to None
        :type rows: tuple(3) or list
        :param cols: column selection, defaults to None
        :type cols: tuple(3) or list
        :param ``**kwargs``: common Block options
        :return: A SLICE2 block
        :rtype: Slice2 instance
        
        Create an 2D array slicing block.

        If ``rows`` or ``cols`` is ``None`` it means all rows and columns
        respectively.

        If ``rows`` or ``cols`` is a list, perform NumPy fancy indexing, returning
        the specified row or column

        Example::

            SLICE2(rows=[2,3])  # return rows 2 and 3, all columns
            SLICE2(cols=[4,1])   # return columns 4 and 1, all rows
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
    
        """
        super().__init__(**kwargs)
        self.type = 'slice2'

        if rows is None:
            self.rows = slice()
        elif isinstance(rows, list):
            self.rows =  rows
        elif isinstance(rows, tuple) and len(rows) == 3:
            self.rows = slice(*rows)
        else:
            raise ValueError('bad rows specifier')
            
        if cols is None:
            self.cols = slice()
        elif isinstance(cols, list):
            self.rows =  cols
        elif isinstance(cols, tuple) and len(cols) == 3:
            self.cols = slice(*cols)
        else:
            raise ValueError('bad rows specifier')

    def output(self, t=None):
        array = self.inputs[0]
        if array.ndim != 2:
            raise RuntimeError('flatten2 block expecting 2d array')
        return [out[rows, cols]]

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
    | ndarray    | ndarray |         | 
    +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, index, **kwargs):
        """
        :param index: slice, defaults to None
        :type index: tuple(3)
        :param ``**kwargs``: common Block options
        :return: A SLICE1 block
        :rtype: Slice1 instance
        
        Create an 1D array slicing block.

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
    
        """
        super().__init__(**kwargs)
        self.type = 'slice1'

        if index is None:
            self.index = slice()
        elif isinstance(index, list):
            self.rows =  index
        elif isinstance(index, tuple) and len(index) == 3:
            self.rows = slice(*index)
        else:
            raise ValueError('bad index specifier')

    def output(self, t=None):
        array = self.inputs[0]
        if array.ndim != 1:
            raise RuntimeError('flatten1 block expecting 1d array')
        return [out[index]]

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
    | ndarray    | float   |         | 
    +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, *inputs, **kwargs):
        """
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param ``**kwargs``: common Block options
        :return: A DET block
        :rtype: Det instance
        
        Create a matrix determinant block

        """
        super().__init__(inputs=inputs, **kwargs)

    def output(self, t=None):
        mat = self.inputs[0]
        out = np.linalg.det(mat)
        return [mat]
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
    | ndarray    | float   |         | 
    +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, **kwargs):
        """
        :param ``kwargs``: common Block options
        :return: A COND block
        :rtype: Cond instance
        
        Create a matrix condition number block

        """
        super().__init__(**kwargs)

    def output(self, t=None):
        mat = self.inputs[0]
        out = np.linalg.cond(mat)
        return [mat]

if __name__ == "__main__":

    import pathlib
    import os.path

    exec(open(os.path.join(pathlib.Path(__file__).parent.absolute(), "test_functions.py")).read())
