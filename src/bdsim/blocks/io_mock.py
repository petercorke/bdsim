"""Mock realtime I/O provider for development and desktop demos.

The mock provider keeps the block-level API runnable without hardware:

- input blocks return a constant zero sample
- output blocks silently discard their values

It is intended for macOS/desktop testing and for example diagrams that should
exercise the realtime scheduler without touching GPIO or serial hardware.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .io_base import IOBlockSpec, IOProvider


@dataclass
class _MockInputHandle:
    value: Any = 0

    def read(self) -> Any:
        return self.value


@dataclass
class _MockOutputHandle:
    def write(self, value: Any) -> None:
        return None


class MockIOProvider(IOProvider):
    """Provider that simulates I/O without external hardware."""

    name = "mock"

    def __init__(self, input_value: Any = 0) -> None:
        self.input_value = input_value
        self.analog_in_calls: list[IOBlockSpec] = []
        self.analog_out_calls: list[IOBlockSpec] = []
        self.digital_in_calls: list[IOBlockSpec] = []
        self.digital_out_calls: list[IOBlockSpec] = []
        self.discarded_outputs: list[tuple[str, Any]] = []
        self._analog_input_handle = _MockInputHandle(input_value)
        self._digital_input_handle = _MockInputHandle(0)
        self._analog_output_handle = _MockOutputHandle()
        self._digital_output_handle = _MockOutputHandle()

    def open_analog_input(self, spec: IOBlockSpec) -> _MockInputHandle:
        self.analog_in_calls.append(spec)
        return self._analog_input_handle

    def open_analog_output(self, spec: IOBlockSpec) -> _MockOutputHandle:
        self.analog_out_calls.append(spec)
        return self._analog_output_handle

    def open_digital_input(self, spec: IOBlockSpec) -> _MockInputHandle:
        self.digital_in_calls.append(spec)
        return self._digital_input_handle

    def open_digital_output(self, spec: IOBlockSpec) -> _MockOutputHandle:
        self.digital_out_calls.append(spec)
        return self._digital_output_handle

    def close(self) -> None:
        """Nothing to release for the mock provider."""
