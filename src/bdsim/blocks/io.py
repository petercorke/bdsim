"""
I/O blocks:

- have either inputs or outputs, matching ordinary Source/Sink blocks
- have no state variables
- are additionally tagged :class:`~bdsim.components.IOBlockMixin`, marking
  them as blocks that read/write real external hardware rather than
  performing pure computation

These blocks' Python ``output()``/``step()`` bodies are deliberately
trivial -- a settable simulated value, just enough for
:meth:`BlockDiagram.compile`'s one-shot ``evaluate()`` to see a
representative value/type for the port. They exist to be recognized (via
``isinstance(block, IOBlockMixin)``) and handled specially by an execution
backend -- :class:`~bdsim.codegen.Codegen` emits a declaration-only C++
function for each of these instead of attempting to transpile the trivial
Python body; see the I/O handling section of
``claude-notes/codegen-embedded-plan.md`` for the full design.

Generic built-ins (``AnalogIn``/``AnalogOut``/``DigitalIn``/``DigitalOut``/
``PWMOut``) map 1:1 onto common microcontroller peripheral calls
(``analogRead``/``analogWrite``/``digitalRead``/``digitalWrite``). For
anything else -- an encoder, an IMU, a stepper driver -- ``DeviceIn``/
``DeviceOut`` are deliberately generic, arbitrary-port-count escape
hatches; the actual meaning lives entirely in hand-written C++ the
generated project leaves for the user to fill in.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from bdsim.components import IOBlockMixin, SinkBlock, SourceBlock


# ------------------------------------------------------------------------ #
class AnalogIn(SourceBlock, IOBlockMixin):
    """
    :blockname:`ANALOGIN`

    Analog input pin.

    :inputs: 0
    :outputs: 1
    :states: 0

    Reads a single analog input channel (e.g. an ADC pin).

    .. note:: ``device`` defaults to ``""``, not ``None`` -- an unset
        optional ``str`` renders as a real, always-usable ``std::string``
        field in generated C++. A Python ``None`` default would map to
        C++'s ``std::nullptr_t``, a legal but permanently-unusable type
        (its only possible value is ``nullptr``), leaving hand-written
        code with no way to ever give it a real value.
    """

    nin = 0
    nout = 1

    def __init__(
        self,
        channel: int,
        device: str = "",
        sim_value: float = 0.0,
        **blockargs: Any,
    ) -> None:
        """
        :param channel: hardware channel/pin identifier
        :type channel: int
        :param device: optional device identifier, for multi-device
            targets, defaults to "" (unspecified)
        :type device: str, optional
        :param sim_value: value this block returns when run in bdsim's own
            Python simulator (not real hardware), defaults to 0.0
        :type sim_value: float, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(**blockargs)
        self.channel = channel
        self.device = device
        self.sim_value = sim_value
        self.add_param("channel")
        self.add_param("device")

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        return [self.sim_value]


# ------------------------------------------------------------------------ #
class AnalogOut(SinkBlock, IOBlockMixin):
    """
    :blockname:`ANALOGOUT`

    Analog output pin.

    :inputs: 1
    :outputs: 0
    :states: 0

    Drives a single analog output channel (e.g. a DAC pin).
    """

    nin = 1
    nout = 0

    def __init__(
        self,
        channel: int,
        device: str = "",
        **blockargs: Any,
    ) -> None:
        """
        :param channel: hardware channel/pin identifier
        :type channel: int
        :param device: optional device identifier, for multi-device
            targets, defaults to "" (unspecified)
        :type device: str, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(**blockargs)
        self.channel = channel
        self.device = device
        self.add_param("channel")
        self.add_param("device")

    def step(self, t: float, inputs: list[Any]) -> None:
        pass


# ------------------------------------------------------------------------ #
class DigitalIn(SourceBlock, IOBlockMixin):
    """
    :blockname:`DIGITALIN`

    Digital input pin.

    :inputs: 0
    :outputs: 1
    :states: 0

    Reads a single digital input channel.
    """

    nin = 0
    nout = 1

    def __init__(
        self,
        channel: int,
        device: str = "",
        sim_value: int = 0,
        **blockargs: Any,
    ) -> None:
        """
        :param channel: hardware channel/pin identifier
        :type channel: int
        :param device: optional device identifier, for multi-device
            targets, defaults to "" (unspecified)
        :type device: str, optional
        :param sim_value: value this block returns when run in bdsim's own
            Python simulator (not real hardware), defaults to 0
        :type sim_value: int, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(**blockargs)
        self.channel = channel
        self.device = device
        self.sim_value = sim_value
        self.add_param("channel")
        self.add_param("device")

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        return [self.sim_value]


# ------------------------------------------------------------------------ #
class DigitalOut(SinkBlock, IOBlockMixin):
    """
    :blockname:`DIGITALOUT`

    Digital output pin.

    :inputs: 1
    :outputs: 0
    :states: 0

    Drives a single digital output channel.
    """

    nin = 1
    nout = 0

    def __init__(
        self,
        channel: int,
        device: str = "",
        **blockargs: Any,
    ) -> None:
        """
        :param channel: hardware channel/pin identifier
        :type channel: int
        :param device: optional device identifier, for multi-device
            targets, defaults to "" (unspecified)
        :type device: str, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(**blockargs)
        self.channel = channel
        self.device = device
        self.add_param("channel")
        self.add_param("device")

    def step(self, t: float, inputs: list[Any]) -> None:
        pass


# ------------------------------------------------------------------------ #
class PWMOut(AnalogOut):
    """
    :blockname:`PWMOUT`

    PWM output pin.

    :inputs: 1
    :outputs: 0
    :states: 0

    An :class:`AnalogOut` realized via PWM on a channel that doesn't have a
    true DAC -- the common case on an 8-bit microcontroller. ``freq`` is
    advisory (a hint for the PWM carrier frequency); a target that doesn't
    support configuring it is free to ignore it.

    .. note:: ``freq`` defaults to ``0.0`` (meaning "unspecified, let the
        hardware/library pick"), not ``None`` -- same reasoning as
        ``device`` on :class:`AnalogIn`: a real, always-usable C++
        ``float`` field, not the unusable ``std::nullptr_t`` a Python
        ``None`` default would map to.
    """

    def __init__(
        self,
        channel: int,
        freq: float = 0.0,
        device: str = "",
        **blockargs: Any,
    ) -> None:
        """
        :param channel: hardware channel/pin identifier
        :type channel: int
        :param freq: PWM carrier frequency in Hz, defaults to 0.0
            (unspecified -- use the target's own default)
        :type freq: float, optional
        :param device: optional device identifier, for multi-device
            targets, defaults to "" (unspecified)
        :type device: str, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        if freq < 0:
            raise ValueError("PWMOut freq must be >= 0 Hz (0 means unspecified)")
        super().__init__(channel=channel, device=device, **blockargs)
        self.freq = freq
        self.add_param("freq")


# ------------------------------------------------------------------------ #
class DeviceIn(SourceBlock, IOBlockMixin):
    """
    :blockname:`DEVICEIN`

    Generic multi-channel device input.

    :inputs: 0
    :outputs: N (configurable via ``nout``)
    :states: 0

    The escape hatch for any input device that isn't a single analog/
    digital pin -- a quadrature encoder (``DeviceIn(nout=1)``), a 6-axis
    IMU (``DeviceIn(nout=6)``), .... bdsim's own Python surface knows
    nothing about the device beyond its port count; the actual meaning
    lives entirely in hand-written C++ supplied elsewhere.
    """

    nin = 0
    nout = -1  # variable, set per-instance -- see bdsim.blocks.functions.Function

    def __init__(
        self,
        nout: int = 1,
        device: str = "",
        sim_values: list[Any] | None = None,
        **blockargs: Any,
    ) -> None:
        """
        :param nout: number of output channels, defaults to 1
        :type nout: int, optional
        :param device: optional device identifier, defaults to "" (unspecified)
        :type device: str, optional
        :param sim_values: values this block returns when run in bdsim's
            own Python simulator (not real hardware), defaults to
            ``[0.0] * nout``
        :type sim_values: list, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(nout=nout, **blockargs)
        self.device = device
        self.sim_values = (
            list(sim_values) if sim_values is not None else [0.0] * nout
        )
        if len(self.sim_values) != nout:
            raise ValueError(
                f"sim_values must have {nout} elements, got {len(self.sim_values)}"
            )
        self.add_param("device")

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        return list(self.sim_values)


# ------------------------------------------------------------------------ #
class DeviceOut(SinkBlock, IOBlockMixin):
    """
    :blockname:`DEVICEOUT`

    Generic multi-channel device output.

    :inputs: N (configurable via ``nin``)
    :outputs: 0
    :states: 0

    The escape hatch for any output device that isn't a single analog/
    digital pin -- a stepper driver (``DeviceOut(nin=2)``: step,
    direction), a servo bank, .... bdsim's own Python surface knows
    nothing about the device beyond its port count; the actual meaning
    lives entirely in hand-written C++ supplied elsewhere.
    """

    nin = -1  # variable, set per-instance -- see bdsim.blocks.functions.Function
    nout = 0

    def __init__(
        self,
        nin: int = 1,
        device: str = "",
        **blockargs: Any,
    ) -> None:
        """
        :param nin: number of input channels, defaults to 1
        :type nin: int, optional
        :param device: optional device identifier, defaults to "" (unspecified)
        :type device: str, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(nin=nin, **blockargs)
        self.device = device
        self.add_param("device")

    def step(self, t: float, inputs: list[Any]) -> None:
        pass
