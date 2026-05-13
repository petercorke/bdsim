"""Generic realtime I/O blocks.

These blocks expose a hardware-agnostic diagram API.  A concrete backend is
selected by the runtime and supplies the actual read/write handles during
``start()``.
"""

from __future__ import annotations

from typing import Any

from bdsim.components import SinkBlock, SourceBlock

from .io_base import IOBlockSpec, get_runtime_io_provider


class _IOBlockMixin:
    """Shared binding logic for runtime-selected I/O providers."""

    _io_block_type: str = ""

    def __init__(
        self,
        *,
        channel: Any,
        device: str | None = None,
        io_options: dict[str, Any] | None = None,
    ) -> None:
        self.channel = channel
        self.device = device
        self.io_options = {} if io_options is None else dict(io_options)
        self._io_handle: Any = None

    def _spec(self) -> IOBlockSpec:
        return IOBlockSpec(
            block_type=self._io_block_type,
            channel=self.channel,
            device=self.device,
            options=self.io_options,
        )

    def _provider(self):
        runtime = getattr(self.bd, "runtime", None)
        return get_runtime_io_provider(runtime)


class AnalogIn(_IOBlockMixin, SourceBlock):
    """
    :blockname:`ANALOGIN`

    Hardware-agnostic analog input.

    :inputs: 0
    :outputs: 1
    :states: 0

    The concrete backend is selected by the runtime.  The block binds to the
    backend during ``start()``.
    """

    nin = 0
    nout = 1
    _io_block_type = "analog_in"

    def __init__(
        self,
        channel: Any,
        device: str | None = None,
        io_options: dict[str, Any] | None = None,
        **blockargs: Any,
    ) -> None:
        """
        :param channel: logical or physical input channel identifier
        :type channel: any
        :param device: optional device identifier, defaults to None
        :type device: str, optional
        :param io_options: backend-specific options, defaults to None
        :type io_options: dict, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        SourceBlock.__init__(self, **blockargs)
        _IOBlockMixin.__init__(
            self, channel=channel, device=device, io_options=io_options
        )
        self.add_param("channel")
        self.add_param("device")

    def start(self, simstate) -> None:
        self._io_handle = self._provider().open_analog_input(self._spec())

    def output(self, t, inputs, x):
        return [self._io_handle.read()]


class AnalogOut(_IOBlockMixin, SinkBlock):
    """
    :blockname:`ANALOGOUT`

    Hardware-agnostic analog output.

    :inputs: 1
    :outputs: 0
    :states: 0
    """

    nin = 1
    nout = 0
    _io_block_type = "analog_out"

    def __init__(
        self,
        channel: Any,
        device: str | None = None,
        io_options: dict[str, Any] | None = None,
        **blockargs: Any,
    ) -> None:
        """
        :param channel: logical or physical output channel identifier
        :type channel: any
        :param device: optional device identifier, defaults to None
        :type device: str, optional
        :param io_options: backend-specific options, defaults to None
        :type io_options: dict, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        SinkBlock.__init__(self, **blockargs)
        _IOBlockMixin.__init__(
            self, channel=channel, device=device, io_options=io_options
        )
        self.add_param("channel")
        self.add_param("device")

    def start(self, simstate) -> None:
        self._io_handle = self._provider().open_analog_output(self._spec())

    def step(self, t, inputs) -> None:
        self._io_handle.write(inputs[0])


class DigitalIn(_IOBlockMixin, SourceBlock):
    """
    :blockname:`DIGITALIN`

    Hardware-agnostic digital input.

    :inputs: 0
    :outputs: 1
    :states: 0
    """

    nin = 0
    nout = 1
    _io_block_type = "digital_in"

    def __init__(
        self,
        channel: Any,
        device: str | None = None,
        io_options: dict[str, Any] | None = None,
        **blockargs: Any,
    ) -> None:
        """
        :param channel: logical or physical input channel identifier
        :type channel: any
        :param device: optional device identifier, defaults to None
        :type device: str, optional
        :param io_options: backend-specific options, defaults to None
        :type io_options: dict, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        SourceBlock.__init__(self, **blockargs)
        _IOBlockMixin.__init__(
            self, channel=channel, device=device, io_options=io_options
        )
        self.add_param("channel")
        self.add_param("device")

    def start(self, simstate) -> None:
        self._io_handle = self._provider().open_digital_input(self._spec())

    def output(self, t, inputs, x):
        return [self._io_handle.read()]


class DigitalOut(_IOBlockMixin, SinkBlock):
    """
    :blockname:`DIGITALOUT`

    Hardware-agnostic digital output.

    :inputs: 1
    :outputs: 0
    :states: 0
    """

    nin = 1
    nout = 0
    _io_block_type = "digital_out"

    def __init__(
        self,
        channel: Any,
        device: str | None = None,
        io_options: dict[str, Any] | None = None,
        **blockargs: Any,
    ) -> None:
        """
        :param channel: logical or physical output channel identifier
        :type channel: any
        :param device: optional device identifier, defaults to None
        :type device: str, optional
        :param io_options: backend-specific options, defaults to None
        :type io_options: dict, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        SinkBlock.__init__(self, **blockargs)
        _IOBlockMixin.__init__(
            self, channel=channel, device=device, io_options=io_options
        )
        self.add_param("channel")
        self.add_param("device")

    def start(self, simstate) -> None:
        self._io_handle = self._provider().open_digital_output(self._spec())

    def step(self, t, inputs) -> None:
        self._io_handle.write(inputs[0])


class PWMOut(AnalogOut):
    """
    :blockname:`PWMOUT`

    PWM-flavoured analog output.

    This block maps to the analog-output provider capability and is intended
    for backends where analog output is realized via PWM. The ``clock``
    argument is currently advisory and retained for API consistency with
    sampled I/O examples.

    :inputs: 1
    :outputs: 0
    :states: 0
    """

    def __init__(
        self,
        clock: Any | None = None,
        channel: Any = None,
        device: str | None = None,
        io_options: dict[str, Any] | None = None,
        **blockargs: Any,
    ) -> None:
        options = {} if io_options is None else dict(io_options)
        options.setdefault("mode", "pwm")
        self.clock = clock
        super().__init__(
            channel=channel,
            device=device,
            io_options=options,
            **blockargs,
        )
