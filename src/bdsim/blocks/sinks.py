"""
Sink blocks:

- have inputs but no outputs
- have no state variables
- are a subclass of ``SinkBlock`` |rarr| ``Block``
- that perform graphics are a subclass of  ``GraphicsBlock`` |rarr| ``SinkBlock`` |rarr| ``Block``

"""

from __future__ import annotations

import numpy as np
from typing import Any, Callable, TextIO

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

    def __init__(
        self, fmt: str | None = None, file: TextIO | None = None, **blockargs: Any
    ) -> None:
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

    def step(self, t, inputs) -> None:
        prefix: str = "{:12s}".format("PRINT({:s} (t={:.3f})".format(self.name, t))
        value = inputs[0]
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
                fmt = self.format
                assert fmt is not None
                with np.printoptions(
                    formatter={"all": lambda x: fmt.format(x)}  # type: ignore[arg-type]
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

    def __init__(
        self, func: Callable[[Any], object] | None = None, **blockargs: Any
    ) -> None:
        """
        :param func: evaluate stop condition, defaults to None
        :type func: callable, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(**blockargs)

        if func is not None and not callable(func):
            raise TypeError("argument must be a callable")
        self.stopfunc: None | Callable[..., object] = func
        self._event_detector: Callable[[float, Any], float] | None = None

    @staticmethod
    def _coerce_scalar_metric(metric: Any) -> Any:
        if isinstance(metric, np.ndarray):
            if metric.size != 1:
                raise RuntimeError("bad input type to stop block")
            return metric.item()
        if isinstance(metric, np.generic):
            return metric.item()
        return metric

    @staticmethod
    def _metric_to_stop(metric: Any) -> bool:
        metric = Stop._coerce_scalar_metric(metric)
        if isinstance(metric, bool):
            return metric
        try:
            return bool(metric > 0)
        except Exception as exc:
            raise RuntimeError("bad input type to stop block") from exc

    def _stop_metric(self, value: Any) -> float:
        metric = self.stopfunc(value) if self.stopfunc is not None else value
        metric = self._coerce_scalar_metric(metric)
        if isinstance(metric, bool):
            return 1.0 if metric else -1.0
        try:
            return float(metric)
        except Exception as exc:
            raise RuntimeError("bad input type to stop block") from exc

    def start(self, simstate) -> None:
        self._simstate = simstate

        # If runtime supports crossing detectors (offline solve_ivp), register
        # STOP as a terminal zero-crossing event. For pure discrete/non-ivp
        # modes this method is absent and step() fallback is used.
        if hasattr(simstate, "declare_crossing_event"):

            def event_detector(t: float, y: Any) -> float:
                simstate.t = t
                simstate.count += 1
                # Runtime coordinates one propagation per solve_ivp probe point
                # across all detectors; this callback only reads the metric.
                simstate.ensure_event_probe_evaluated(self.bd, t, y)
                return self._stop_metric(self.inport_values[0])

            event_detector.terminal = True  # type: ignore[attr-defined]
            event_detector.direction = 1.0  # type: ignore[attr-defined]
            self._event_detector = event_detector
            simstate.declare_crossing_event(event_detector, self)

    def event_handler(
        self,
        t_crossing: float,
        y_crossing: Any,
        state_map: Any,
        simstate: Any,
    ) -> None:
        simstate.stop = self

    def step(self, t, inputs) -> None:
        metric = self.stopfunc(inputs[0]) if self.stopfunc is not None else inputs[0]
        stop = self._metric_to_stop(metric)

        # we signal stop condition by setting simstate.stop to the block calling
        # the stop
        if stop:
            self._simstate.stop = self


# ------------------------------------------------------------------------ #


class Event(SinkBlock):
    """
    :blockname:`EVENT`

    Runtime event detector for solve_ivp.

    :inputs: 1
    :outputs: 0
    :states: 0

    The input signal is used as an event function value.  A zero crossing
    triggers an event in ``solve_ivp``.

    Direction can be one of:

    - ``'^'`` or ``'+'``: positive-going crossing (direction = +1)
    - ``'v'`` or ``'-'``: negative-going crossing (direction = -1)

    Event handling callback signature is:

    ``func(block, *fargs, **fkwargs)``

    where ``block`` is this EVENT block instance.
    """

    nin = 1
    nout = 0

    def __init__(
        self,
        direction: str,
        func: Callable[..., Any],
        fargs: list[Any] | tuple[Any, ...] | None = None,
        fkwargs: dict[str, Any] | None = None,
        **blockargs: Any,
    ) -> None:
        """
        :param direction: event crossing direction, one of ``'^'``, ``'v'``, ``'+'``, ``'-'``
        :type direction: str
        :param func: user callback invoked when event is detected
        :type func: callable
        :param fargs: extra positional args passed to callback
        :type fargs: list or tuple, optional
        :param fkwargs: extra keyword args passed to callback
        :type fkwargs: dict, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(**blockargs)

        direction_map = {"^": 1.0, "+": 1.0, "v": -1.0, "-": -1.0}
        if direction not in direction_map:
            raise ValueError("direction must be one of '^', 'v', '+', '-' ")
        if not callable(func):
            raise TypeError("func must be callable")

        self.direction = direction_map[direction]
        self.func = func
        self.args = [] if fargs is None else list(fargs)
        self.kwargs = {} if fkwargs is None else dict(fkwargs)
        self._event_detector: Callable[[float, Any], float] | None = None

    def start(self, simstate) -> None:
        # Build an event function from the current input value. solve_ivp reads
        # .terminal and .direction attributes directly from this callable.
        def event_detector(t: float, y: Any) -> float:
            # print(
            #     "event_detector called at t =",
            #     t,
            #     "u =",
            #     self.inport_values[0][0],
            #     "y =",
            #     y,
            # )

            # print("  ydot called at t =", t, "y =", y)
            simstate.t = t
            simstate.count += 1
            # Runtime coordinates one propagation per solve_ivp probe point
            # across all detectors; this callback only reads the metric.
            simstate.ensure_event_probe_evaluated(self.bd, t, y)

            value = self.inport_values[0]
            if isinstance(value, np.ndarray):
                if value.size != 1:
                    raise RuntimeError(
                        "EVENT input must be a scalar or 1-element array"
                    )
                return float(value.item())
            if isinstance(value, (list, tuple)):
                if len(value) != 1:
                    raise RuntimeError(
                        "EVENT input must be a scalar or 1-element sequence"
                    )
                return float(value[0])
            return float(value)

        event_detector.terminal = True  # type: ignore[attr-defined]
        event_detector.direction = self.direction  # type: ignore[attr-defined]
        self._event_detector = event_detector

        if not hasattr(simstate, "declare_crossing_event"):
            raise RuntimeError(
                "EVENT block requires runtime support for zero-crossing detection"
            )
        simstate.declare_crossing_event(event_detector, self)

    def event_handler(
        self,
        t_crossing: float,
        y_crossing: Any,
        state_map: Any,
        simstate: Any,
    ) -> None:
        try:
            self.func(self, state_map, *self.args, **self.kwargs)
        except TypeError:
            self.func(self, *self.args, **self.kwargs)

    def step(self, t, inputs) -> None:
        pass


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

    nin: int = -1
    nout = 0

    def __init__(self, nin: int = 1, **blockargs: Any) -> None:
        """
        :param nin: number of input ports, defaults to 1
        :type nin: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(nin=nin, **blockargs)

    def step(self, t, inputs) -> None:
        pass  # do nothing


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

    :seealso: :meth:`BDSim.run`
    """

    nin = 1
    nout = 0

    def __init__(self, **blockargs: Any) -> None:
        """
        :param nin: number of input ports, defaults to 1
        :type nin: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(**blockargs)

    def start(self, simstate) -> None:
        # called at start of simulation, add this block to the watchlist
        plug = self.sources[0]  # start plug for input wire

        # append to the watchlist, bdsim.run() will do the rest
        simstate.watchlist.append(plug)
        simstate.watchnamelist.append(str(plug))

    def step(self, t, inputs) -> None:
        pass  # do nothing


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
