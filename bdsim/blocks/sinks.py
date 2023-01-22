"""
Sink blocks:

- have inputs but no outputs
- have no state variables
- are a subclass of ``SinkBlock`` |rarr| ``Block``
- that perform graphics are a subclass of  ``GraphicsBlock`` |rarr| ``SinkBlock`` |rarr| ``Block``

"""


import numpy as np
from math import pi, sqrt, sin, cos, atan2

import matplotlib.pyplot as plt
from matplotlib.pyplot import Polygon

from bdsim.components import SinkBlock

# ------------------------------------------------------------------------ #


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

    nin = 1
    nout = 0

    def __init__(self, fmt=None, file=None, **blockargs):
        """
        Print signal.

        :param fmt: Format string, defaults to None
        :type fmt: str, optional
        :param file: file to write data to, defaults to None
        :type file: file object, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A PRINT block
        :rtype: Print instance

        Creates a console print block which displays the value of a signal
        at each simulation time step. The display format is like::

            PRINT(print.0 @ t=0.100) [-1.0 0.2]

        and includes the block name, time, and the formatted value.

        The numerical formatting of the signal is controlled by ``fmt``:

        - if not provided, ``str()`` is used to format the signal
        - if provided:
            - a scalar is formatted by the ``fmt.format()``
            - a NumPy array is formatted by ``fmt.format()`` applied to every
              element

        Examples::

            pr = bd.PRINT()     # create PRINT block
            bd.connect(x, inputs=pr)   # its input comes from x

            bd.PRINT(x)         # create PRINT block with input from x

            bd.PRINT(x, name='X')  # block name appears in the printed text

            bd.PRINT(x, fmt="{:.1f}") # print with explicit format

        .. note::
            - By default writes to stdout
            - The output is cleaner if progress bar printing is disabled.

        """
        super().__init__(**blockargs)
        self.format = fmt
        self.file = file

        # TODO format can be a string or function

    def step(self, state=None):
        prefix = "{:12s}".format("PRINT({:s} (t={:.3f})".format(self.name, state.t))
        value = self.inputs[0]
        if self.format is None:
            # no format string
            if hasattr(value, "strline"):
                print(prefix, value.strline(), file=self.file)
            else:
                print(prefix, str(value), file=self.file)
        else:
            # format string provided
            if isinstance(value, (int, float)):
                print(prefix, self.format.format(value), file=self.file)

            elif isinstance(value, np.ndarray):
                with np.printoptions(
                    formatter={"all": lambda x: self.format.format(x)}
                ):
                    print(prefix, value, file=self.file)
            else:
                print(prefix, str(value), file=self.file)


# ------------------------------------------------------------------------ #


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

    nin = 1
    nout = 0

    def __init__(self, func=None, **blockargs):
        """
        Conditional simulation stop.

        :param func: evaluate stop condition, defaults to None
        :type func: callable, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A STOP block
        :rtype: Stop instance

        Conditionally stop the simulation if the input is:

        - bool type and True
        - numeric type and > 0

        If ``func`` is provided, then it is applied to the block input
        and if it returns True the simulation is stopped.
        """
        super().__init__(**blockargs)

        if func is not None and not callable(func):
            raise TypeError("argument must be a callable")
        self.stopfunc = func

    def step(self, state=None):
        value = self.inputs[0]
        if self.stopfunc is not None:
            value = self.stopfunc(value)

        stop = False
        if isinstance(value, bool):
            stop = value
        else:
            try:
                stop = value > 0
            except:
                raise RuntimeError("bad input type to stop block")

        # we signal stop condition by setting state.stop to the block calling
        # the stop
        if stop:
            state.stop = self


# ------------------------------------------------------------------------ #


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

    nin = -1
    nout = 0

    def __init__(self, nin=1, **blockargs):
        """
        Discard signal.

        :param nin: number of input ports, defaults to 1
        :type nin: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A NULL block
        :rtype: Null instance

        Create a sink block with arbitrary number of input ports that discards
        all data.  Useful for testing.

        """
        super().__init__(nin=nin, **blockargs)


# ------------------------------------------------------------------------ #


class Watch(SinkBlock):
    """
    :blockname:`WATCH`

    .. table::
       :align: left

    +--------+---------+---------+
    | inputs | outputs |  states |
    +--------+---------+---------+
    | N      | 0       | 0       |
    +--------+---------+---------+
    | 1      |         |         |
    +--------+---------+---------+
    """

    nin = 1
    nout = 0

    def __init__(self, **blockargs):
        """
        Watch a signal.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A NULL block
        :rtype: Null instance

        Causes the input signal to be logged during the
        simulation run.  Equivalent to adding it as the ``watch=`` argument
        to ``bdsim.run``.

        :seealso: :method:`BDSim.run`
        """
        super().__init__(**blockargs)

    def start(self, state=None):
        # called at start of simulation, add this block to the watchlist
        plug = self.sources[0]  # start plug for input wire

        # append to the watchlist, bdsim.run() will do the rest
        state.watchlist.append(plug)
        state.watchnamelist.append(str(plug))


if __name__ == "__main__":  # pragma: no cover

    from pathlib import Path

    exec(open(Path(__file__).parent.parent.parent / "tests" / "test_sinks.py").read())
