"""
Function blocks:

- have inputs and outputs
- have no state variables
- are a subclass of ``FunctionBlock`` |rarr| ``Block``

"""

# The constructor of each class ``MyClass`` with a ``@block`` decorator becomes a method ``MYCLASS()`` of the BlockDiagram instance.

import numpy as np
import math

from bdsim.components import FunctionBlock, block


        
@block
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
        super().__init__(nin=1, nout=1, inputs=inputs, **kwargs)
        self.type = 'inverse'

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
@block
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
        super().__init__(nin=1,nout=1, inputs=inputs, **kwargs)
        self.type = 'transpose'

    def output(self, t=None):
        mat = self.inputs[0]

        if ndim == 1:
            out = mat.reshape((mat.shape[0], 1))
        else:
            out = mat.T

        return [out]

# ------------------------------------------------------------------------ #
@block
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

    def __init__(self, *inputs, **kwargs):
        """
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param ``**kwargs``: common Block options
        :return: A NORM block
        :rtype: Norm instance
        
        Create a vector norm block.
        """
        super().__init__(nin=1,nout=1, inputs=inputs, **kwargs)
        self.type = 'norm'

    def output(self, t=None):
        vec = self.inputs[0]
        out = np.linalg.norm(vec)
        return [out]

# ------------------------------------------------------------------------ #
@block
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

    def __init__(self, *inputs, **kwargs):
        """
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param ``**kwargs``: common Block options
        :return: A DET block
        :rtype: Det instance
        
        Create a matrix determinant block

        """
        super().__init__(nin=1,nout=1, inputs=inputs, **kwargs)
        self.type = 'det'

    def output(self, t=None):
        mat = self.inputs[0]
        out = np.linalg.det(mat)
        return [mat]
# ------------------------------------------------------------------------ #


if __name__ == "__main__":

    import pathlib
    import os.path

    exec(open(os.path.join(pathlib.Path(__file__).parent.absolute(), "test_functions.py")).read())
