"""Generic realtime I/O blocks.

These blocks expose a hardware-agnostic diagram API.  A concrete backend is
selected by the runtime and supplies the actual read/write handles during
``start()``.
"""

from __future__ import annotations

import json
import os
import socket
import time
from typing import Any

import numpy as np

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

    def _try_bind(self, opener_name: str) -> bool:
        if self._io_handle is not None:
            return True

        runtime = getattr(self.bd, "runtime", None)
        if runtime is None:
            # Compile-time/type-propagation path: no runtime/provider yet.
            return False

        provider = get_runtime_io_provider(runtime)
        opener = getattr(provider, opener_name)
        self._io_handle = opener(self._spec())
        return self._io_handle is not None


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
        clock: Any | None = None,
        channel: Any = None,
        device: str | None = None,
        io_options: dict[str, Any] | None = None,
        **blockargs: Any,
    ) -> None:
        """
        :param channel: logical or physical input channel identifier
        :type channel: any
        :param clock: optional sample clock (advisory), defaults to None
        :type clock: Clock, optional
        :param device: optional device identifier, defaults to None
        :type device: str, optional
        :param io_options: backend-specific options, defaults to None
        :type io_options: dict, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        if channel is None and clock is not None:
            # Backward-compatible positional form: ANALOGIN(channel, ...).
            channel, clock = clock, None

        SourceBlock.__init__(self, **blockargs)
        self.clock = clock
        _IOBlockMixin.__init__(
            self, channel=channel, device=device, io_options=io_options
        )
        self.add_param("channel")
        self.add_param("device")

    def start(self, simstate) -> None:
        self._io_handle = self._provider().open_analog_input(self._spec())

    def output(self, t, inputs, x):
        if not self._try_bind("open_analog_input"):
            # No runtime/provider yet (eg compile-time probing): provide a
            # stable scalar fallback so type/shape propagation can continue.
            return [0.0]
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
        clock: Any | None = None,
        channel: Any = None,
        device: str | None = None,
        io_options: dict[str, Any] | None = None,
        **blockargs: Any,
    ) -> None:
        """
        :param channel: logical or physical output channel identifier
        :type channel: any
        :param clock: optional sample clock (advisory), defaults to None
        :type clock: Clock, optional
        :param device: optional device identifier, defaults to None
        :type device: str, optional
        :param io_options: backend-specific options, defaults to None
        :type io_options: dict, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        if channel is None and clock is not None:
            # Backward-compatible positional form: ANALOGOUT(channel, ...).
            channel, clock = clock, None

        SinkBlock.__init__(self, **blockargs)
        self.clock = clock
        _IOBlockMixin.__init__(
            self, channel=channel, device=device, io_options=io_options
        )
        self.add_param("channel")
        self.add_param("device")

    def start(self, simstate) -> None:
        self._io_handle = self._provider().open_analog_output(self._spec())

    def step(self, t, inputs) -> None:
        if not self._try_bind("open_analog_output"):
            # No runtime/provider yet (eg compile-time probing).
            return
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
        clock: Any | None = None,
        channel: Any = None,
        device: str | None = None,
        io_options: dict[str, Any] | None = None,
        **blockargs: Any,
    ) -> None:
        """
        :param channel: logical or physical input channel identifier
        :type channel: any
        :param clock: optional sample clock (advisory), defaults to None
        :type clock: Clock, optional
        :param device: optional device identifier, defaults to None
        :type device: str, optional
        :param io_options: backend-specific options, defaults to None
        :type io_options: dict, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        if channel is None and clock is not None:
            # Backward-compatible positional form: DIGITALIN(channel, ...).
            channel, clock = clock, None

        SourceBlock.__init__(self, **blockargs)
        self.clock = clock
        _IOBlockMixin.__init__(
            self, channel=channel, device=device, io_options=io_options
        )
        self.add_param("channel")
        self.add_param("device")

    def start(self, simstate) -> None:
        self._io_handle = self._provider().open_digital_input(self._spec())

    def output(self, t, inputs, x):
        if not self._try_bind("open_digital_input"):
            # No runtime/provider yet (eg compile-time probing): use 0 as a
            # deterministic digital fallback.
            return [0]
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
        clock: Any | None = None,
        channel: Any = None,
        device: str | None = None,
        io_options: dict[str, Any] | None = None,
        **blockargs: Any,
    ) -> None:
        """
        :param channel: logical or physical output channel identifier
        :type channel: any
        :param clock: optional sample clock (advisory), defaults to None
        :type clock: Clock, optional
        :param device: optional device identifier, defaults to None
        :type device: str, optional
        :param io_options: backend-specific options, defaults to None
        :type io_options: dict, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        if channel is None and clock is not None:
            # Backward-compatible positional form: DIGITALOUT(channel, ...).
            channel, clock = clock, None

        SinkBlock.__init__(self, **blockargs)
        self.clock = clock
        _IOBlockMixin.__init__(
            self, channel=channel, device=device, io_options=io_options
        )
        self.add_param("channel")
        self.add_param("device")

    def start(self, simstate) -> None:
        self._io_handle = self._provider().open_digital_output(self._spec())

    def step(self, t, inputs) -> None:
        if not self._try_bind("open_digital_output"):
            # No runtime/provider yet (eg compile-time probing).
            return
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
        freq: float | None = None,
        device: str | None = None,
        io_options: dict[str, Any] | None = None,
        **blockargs: Any,
    ) -> None:
        """
        :param clock: optional sample clock (advisory), defaults to None
        :type clock: Clock, optional
        :param channel: logical or physical PWM output channel identifier
        :type channel: any
        :param freq: PWM carrier frequency in Hz, defaults to provider default
        :type freq: float, optional
        :param device: optional device identifier, defaults to None
        :type device: str, optional
        :param io_options: backend-specific options, defaults to None
        :type io_options: dict, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        options = {} if io_options is None else dict(io_options)
        options.setdefault("mode", "pwm")
        if freq is not None:
            if float(freq) <= 0:
                raise ValueError("PWMOut freq must be > 0 Hz")
            options["frequency"] = float(freq)
        self.clock = clock
        self.freq = None if freq is None else float(freq)
        super().__init__(
            channel=channel,
            device=device,
            io_options=options,
            **blockargs,
        )
        self.add_param("freq")


class Telemetry(SinkBlock):
    """
    :blockname:`TELEMETRY`

    Stream sink inputs as UDP telemetry packets.

    :inputs: N
    :outputs: 0
    :states: 0

    The block emits compact data packets for each sample and periodic schema
    packets that contain signal names. This keeps per-sample overhead low while
    still allowing connectionless clients to discover metadata after startup.
    """

    nin = -1
    nout = 0

    def __init__(
        self,
        clock: Any,
        port: int = 5001,
        *,
        host: str = "127.0.0.1",
        endpoint: str | None = None,
        nin: int = 1,
        signal_names: list[str] | tuple[str, ...] | None = None,
        schema_period: float = 1.0,
        decimation: int = 1,
        **blockargs: Any,
    ) -> None:
        """
        :param clock: sample clock (kept for API consistency with sampled I/O)
        :type clock: Clock
        :param port: UDP destination port, defaults to 5001
        :type port: int
        :param host: UDP destination host, defaults to 127.0.0.1
        :type host: str, optional
        :param endpoint: optional UDP destination as host:port; if omitted,
            ``BDSIM_TELEMETRY`` is used when set
        :type endpoint: str, optional
        :param nin: number of input ports, defaults to 1
        :type nin: int, optional
        :param signal_names: optional per-input names, defaults to None
        :type signal_names: list[str] | tuple[str, ...], optional
        :param schema_period: seconds between schema packets, defaults to 1.0
        :type schema_period: float, optional
        :param decimation: send every N-th sample only, defaults to 1 (send all)
        :type decimation: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(nin=nin, **blockargs)
        self.clock = clock
        endpoint_text = endpoint
        if endpoint_text is None:
            endpoint_text = os.getenv("BDSIM_TELEMETRY", "").strip() or None

        if endpoint_text is not None:
            host_text, sep, port_text = endpoint_text.strip().rpartition(":")
            if not sep or not host_text or not port_text.isdigit():
                raise ValueError(
                    "TELEMETRY endpoint must be in 'host:port' format, "
                    "for example '192.168.100.1:5001'"
                )
            self.host = host_text
            self.port = int(port_text)
        else:
            self.host = host
            self.port = int(port)
        self.endpoint = endpoint_text
        self.signal_names = None if signal_names is None else list(signal_names)
        self.schema_period = float(schema_period)
        self.decimation = max(1, int(decimation))

        self._sock: socket.socket | None = None
        self._seq = 0
        self._step_count = 0
        self._last_schema_sent_t: float = -1e9
        self._resolved_signal_names: list[str] = []

        self.add_param("host")
        self.add_param("port")
        self.add_param("endpoint")

    def _resolve_signal_names(self) -> list[str]:
        if self.signal_names is not None:
            if len(self.signal_names) != self.nin:
                raise ValueError(
                    f"TELEMETRY signal_names length ({len(self.signal_names)}) "
                    f"must match nin ({self.nin})"
                )
            return list(self.signal_names)

        names: list[str] = []
        for i in range(self.nin):
            try:
                names.append(self.source_name(i))
            except Exception:
                names.append(f"u{i}")
        return names

    def _encode_value(self, value: Any) -> Any:
        # Scalars stay compact; arrays include shape + flat payload so clients
        # can reconstruct either vector traces or matrix element traces.
        if isinstance(value, np.ndarray):
            arr = value
        elif isinstance(value, (list, tuple)):
            arr = np.asarray(value)
            if arr.ndim == 0:
                return arr.item()
            return {
                "kind": "ndarray",
                "shape": list(arr.shape),
                "data": arr.reshape(-1).tolist(),
            }
        elif isinstance(value, np.generic):
            return value.item()
        else:
            return value

        if arr.ndim == 0:
            return arr.item()
        return {
            "kind": "ndarray",
            "shape": list(arr.shape),
            "data": arr.reshape(-1).tolist(),
        }

    def _send_json(self, payload: dict[str, Any]) -> None:
        if self._sock is None:
            return
        packet = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self._sock.sendto(packet, (self.host, self.port))

    def _send_schema(self, t: float) -> None:
        payload = {
            "type": "schema",
            "version": 1,
            "block": self.name,
            "signals": [
                {"index": i, "name": name}
                for i, name in enumerate(self._resolved_signal_names)
            ],
        }
        self._send_json(payload)
        self._last_schema_sent_t = t

    def start(self, simstate: Any) -> None:
        del simstate
        self._seq = 0
        self._step_count = 0
        if self._sock is None:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._resolved_signal_names = self._resolve_signal_names()
        self._send_schema(0.0)

    def step(self, t: float, inputs: list[Any]) -> None:
        if self._sock is None:
            return

        self._step_count += 1
        if self._step_count % self.decimation != 0:
            return

        if (
            self.schema_period > 0
            and (t - self._last_schema_sent_t) >= self.schema_period
        ):
            self._send_schema(t)

        payload = {
            "type": "sample",
            "version": 1,
            "seq": self._seq,
            "t": float(t),
            # Monotonic sender timestamp supports sync-free link jitter analysis
            # in receivers by comparing delta(sender_mono_ns) vs delta(arrival).
            "sender_mono_ns": time.monotonic_ns(),
            "values": [self._encode_value(v) for v in inputs],
        }
        self._send_json(payload)
        self._seq += 1

    def done(self, simstate: Any) -> None:
        del simstate
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None
