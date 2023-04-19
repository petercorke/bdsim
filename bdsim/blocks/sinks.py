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

    Print signal.

    :inputs: 1
    :outputs: 0
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - 0
            - any
            - :math:`x`

    Creates a console print block which displays the value of the input signal
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

        bd.PRINT(name="X")  # block name appears in the printed text
        bd.PRINT(fmt="{:.1f}") # print with explicit format

    .. note::
        - By default writes to stdout
        - The output is cleaner if progress bar printing is disabled using the
          ``-p`` command line option.
    """

    nin = 1
    nout = 0

    def __init__(self, fmt=None, file=None, **blockargs):
        """
        :param fmt: Format string, defaults to None
        :type fmt: str, optional
        :param file: file to write data to, defaults to None
        :type file: file object, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A PRINT block
        :rtype: Print instance
        """
        super().__init__(**blockargs)
        self.format = fmt
        self.file = file

        # TODO format can be a string or function

    def step(self, t, inports):
        prefix = "{:12s}".format("PRINT({:s} (t={:.3f})".format(self.name, t))
        value = inports[0]
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

    Conditionally stop simulation.

    :inputs: 1
    :outputs: 0
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - 0
            - any
            - :math:`x`

    Conditionally stop the simulation if the input :math:`x` is:

    - bool type and True
    - numeric type and > 0

    If ``func`` is provided, then it is applied to the block input
    and if it returns True the simulation is stopped.
    """

    nin = 1
    nout = 0

    def __init__(self, func=None, **blockargs):
        """
        :param func: evaluate stop condition, defaults to None
        :type func: callable, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(**blockargs)

        if func is not None and not callable(func):
            raise TypeError("argument must be a callable")
        self.stopfunc = func

    def start(self, simstate):
        self._simstate = simstate

    def step(self, t, inports):
        value = inports[0]

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

        # we signal stop condition by setting simstate.stop to the block calling
        # the stop
        if stop:
            self._simstate.stop = self


# ------------------------------------------------------------------------ #


class Null(SinkBlock):
    """
    :blockname:`NULL`

    Discard signal.

    :inputs: N
    :outputs: 0
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - i
            - any
            - :math:`x_i`

    Create a sink block with arbitrary number of input ports that discards
    all data, like ``/dev/null``. Useful for testing.

    .. note:: ``bdsim`` issues a warning for unconnected outputs but execution can continue.
    """

    nin = -1
    nout = 0

    def __init__(self, nin=1, **blockargs):
        """
        :param nin: number of input ports, defaults to 1
        :type nin: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(nin=nin, **blockargs)


# ------------------------------------------------------------------------ #


class Watch(SinkBlock):
    """
    :blockname:`WATCH`

    Watch a signal.

    :inputs: N
    :outputs: 0
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - i
            - any
            - :math:`x_i`

    Causes the output ports connected to this block's input ports :math:`x_i` to be
    logged during the simulation run. Equivalent to adding it as the ``watch=`` argument
    to ``bdsim.run``.

    For example::

        step = bd.STEP(5)
        ramp = bd.RAMP()
        watch = bd.WATCH(2) # watch 2 ports
        watch[0] = step
        watch[1] = ramp

    :seealso: :method:`BDSim.run`
    """

    nin = 1
    nout = 0

    def __init__(self, **blockargs):
        """
        :param nin: number of input ports, defaults to 1
        :type nin: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(**blockargs)

    def start(self, simstate):
        # called at start of simulation, add this block to the watchlist
        plug = self.sources[0]  # start plug for input wire

        # append to the watchlist, bdsim.run() will do the rest
        simstate.watchlist.append(plug)
        simstate.watchnamelist.append(str(plug))


if __name__ == "__main__":  # pragma: no cover

    from pathlib import Path

    exec(open(Path(__file__).parent.parent.parent / "tests" / "test_sinks.py").read())
