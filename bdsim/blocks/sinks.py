"""
Sink blocks:

- have inputs but no outputs
- have no state variables
- are a subclass of ``SinkBlock`` |rarr| ``Block``
- that perform graphics are a subclass of  ``GraphicsBlock`` |rarr| ``SinkBlock`` |rarr| ``Block``

"""

# The constructor of each class ``MyClass`` with a ``@block`` decorator becomes a method ``MYCLASS()`` of the BlockDiagram instance.

import numpy as np
from math import pi, sqrt, sin, cos, atan2

import matplotlib.pyplot as plt
from matplotlib.pyplot import Polygon


import spatialmath.base as sm

from bdsim.components import SinkBlock, block



# ------------------------------------------------------------------------ #

@block
class Print(SinkBlock):
    """    
    :blockname:`PRINT`
    
    .. table::
       :align: left
    
    +--------+---------+---------+
    | inputs | outputs |  states |
    +--------+---------+---------+
    | 1      | 0       | 0       |
    +--------+---------+---------+
    | any    |         |         | 
    +--------+---------+---------+
    """

    def __init__(self, input=None, fmt=None, **kwargs):
        """
        :param fmt: Format string, defaults to None
        :type fmt: str, optional
        :param ``input``: Optional incoming connection
        :type ``input``: Block or Plug
        :param ``**kwargs``: common Block options
        :return: A PRINT block
        :rtype: Print instance
        
        Create a console print block which displays the value of a signal to the
        console at each simulation time step. The format is like::

            PRINT(print.0 @ t=0.100) [-1.0 0.2]

        and includes the block name, time, and the formatted value.

        Examples::

            pr = bd.PRINT()     # create PRINT block
            bd.connect(x, pr)   # its input comes from x

            bd.PRINT(x)         # create PRINT block with input from x

            bd.PRINT(x, name='X')  # block name appears in the printed text

            bd.PRINT(x, fmt="{:.1f}") # print with explicit format
        
        The numerical formatting of the signal is controlled by ``fmt``:

        - if not provided, ``str()`` is used to format the signal
        - if provided:
            - a scalar is formatted by the ``fmt.format()``
            - a NumPy array is formatted by ``fmt.format()`` applied to every
              element

        .. note:: The output is cleaner if progress bar printing is disabled.

        """
        if input is not None:
            input = [input]
        super().__init__(nin=1, inputs=input, **kwargs)
        self.format = fmt
        self.type = 'print'
        
        # TODO format can be a string or function

    def step(self):
        prefix = '{:12s}'.format(
            'PRINT({:s} @ t={:.3f})'.format(self.name, self.bd.state.t)
            )
                
        value = self.inputs[0]
        if self.format is None:
            # no format string
            print(prefix, str(value))
        else:
            # format string provided
            if isinstance(value, (int, float)):
                print(prefix, self.format.format(value))
            elif isinstance(value, np.ndarray):
                with np.printoptions(formatter={'all':lambda x: self.format.format(x)}):
                    print(prefix, value)
            else:
                print(prefix, str(value))

# ------------------------------------------------------------------------ #
            

@block
class Stop(SinkBlock):
    """
    :blockname:`STOP`
    
    .. table::
       :align: left
    
    +--------+---------+---------+
    | inputs | outputs |  states |
    +--------+---------+---------+
    | 1      | 0       | 0       |
    +--------+---------+---------+
    | any    |         |         | 
    +--------+---------+---------+
    """

    def __init__(self, stop, *inputs, **kwargs):
        """
        :param stop: Function 
        :type stop: TYPE
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param ``**kwargs``: common Block options
        :return: A STOP block
        :rtype: Stop instance

        Conditionally stop the simulation.
        """
        super().__init__(nin=1, inputs=inputs, **kwargs)
        self.type = 'stop'
                    
        self.stop  = stop

    def step(self):
        if isinstance(self.stop, bool):
            stop = self.inputs[0]
        elif callable(self.stop):
            stop = self.stop(self.inputs[0])
        else:
            raise RuntimeError('input to stop must be boolean or callable')
        if stop:
            self.bd.state.stop = self

# ------------------------------------------------------------------------ #

@block
class Null(SinkBlock):
    """    
    :blockname:`NULL`
    
    .. table::
       :align: left
    
    +--------+---------+---------+
    | inputs | outputs |  states |
    +--------+---------+---------+
    | N      | 0       | 0       |
    +--------+---------+---------+
    | any    |         |         | 
    +--------+---------+---------+
    """

    def __init__(self, nin=1, **kwargs):
        """
        :param nin: number of input ports
        :type nin: int
        :param ``**kwargs``: common Block options
        :return: A NULL block
        :rtype: Null instance
        
        Create a sink block with arbitrary number of input ports that discards
        all data.  Used for testing.

        """
        super().__init__(nin=nin, **kwargs)
        self.type = 'null'
        
        # TODO format can be a string or function

if __name__ == "__main__":

    import pathlib
    import os.path

    exec(open(os.path.join(pathlib.Path(__file__).parent.absolute(), "test_sinks.py")).read())
