"""Example Firmata provider skeleton for realtime I/O blocks.

This file intentionally contains provider code only, not block classes.  The
public diagram API stays in ``bdsim.blocks.io`` while the runtime chooses this
provider when Firmata-backed hardware is requested.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .io_base import IOBlockSpec, IOProvider


@dataclass
class _FirmataInputHandle:
    pin: Any

    def read(self) -> Any:
        return self.pin.read()


@dataclass
class _FirmataOutputHandle:
    pin: Any

    def write(self, value: Any) -> None:
        self.pin.write(value)


class FirmataProvider(IOProvider):
    """Firmata-backed provider skeleton.

    The concrete pyFirmata session setup is intentionally deferred.  This file
    is a placeholder for the eventual runtime-selected implementation.
    """

    name = "firmata"

    def __init__(
        self,
        port: str,
        baudrate: int = 57600,
        board_factory: Any | None = None,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.board_factory = board_factory
        self._board: Any = None

    def connect(self) -> None:
        """Establish the underlying Firmata session.

        A later implementation can instantiate pyFirmata here and start any
        iterator thread required for background input updates.
        """

    def _pin(self, spec: IOBlockSpec, mode: str) -> Any:
        raise NotImplementedError(
            "FirmataProvider pin mapping is not implemented yet"
        )

    def open_analog_input(self, spec: IOBlockSpec) -> _FirmataInputHandle:
        self.connect()
        return _FirmataInputHandle(self._pin(spec, "analog_in"))

    def open_analog_output(self, spec: IOBlockSpec) -> _FirmataOutputHandle:
        self.connect()
        return _FirmataOutputHandle(self._pin(spec, "analog_out"))

    def open_digital_input(self, spec: IOBlockSpec) -> _FirmataInputHandle:
        self.connect()
        return _FirmataInputHandle(self._pin(spec, "digital_in"))

    def open_digital_output(self, spec: IOBlockSpec) -> _FirmataOutputHandle:
        self.connect()
        return _FirmataOutputHandle(self._pin(spec, "digital_out"))