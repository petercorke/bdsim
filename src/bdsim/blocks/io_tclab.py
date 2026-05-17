"""TCLab device driver for bdsim serial I/O framework.

This module implements support for the Temperature Control Lab (TCLab)
hardware device, a simple educational platform with two heater outputs (Q1, Q2)
and two temperature inputs (T1, T2).

Protocol Summary:
- Commands: "Q1,<0-100>", "Q2,<0-100>", "T1", "T2", "VER", "X" (exit)
- Responses: numeric value + newline
- Default baud: 115200
- Safe state: Q1=0, Q2=0 (heaters off)
"""

from __future__ import annotations

import time
from typing import Any

from bdsim.blocks.io_serial import SerialDeviceSession
from bdsim.config import DeviceConfig, IOConfig


class TCLabSession(SerialDeviceSession):
    """TCLab device session handler."""

    def __init__(
        self, device_config: DeviceConfig, io_config: IOConfig | None = None
    ) -> None:
        super().__init__(device_config, io_config)
        self.firmware_version: str = ""
        self._last_values: dict[str, float] = {
            "t1": 20.0,
            "t2": 20.0,
            "q1": 0.0,
            "q2": 0.0,
        }

    def startup_handshake(self) -> None:
        """Perform TCLab startup handshake: version probe and initial state."""
        if self.port is None:
            raise RuntimeError("Serial port must be opened before handshake")

        timeout_s = self.device_config.startup_timeout_s
        start = time.time()

        # Clear any pending data
        self.port.reset_input_buffer()

        # Request version (VER command)
        try:
            self._write(b"VER\n")
            self._flush()
            response = self._read_until(b"\n", timeout_s=1.0).decode("utf-8").strip()
            if response:
                self.firmware_version = response
        except Exception as e:
            # Non-fatal: continue even if version probe fails
            pass

        # Set heaters to safe state (0%)
        try:
            self._set_heater("Q1", 0.0)
            self._set_heater("Q2", 0.0)
        except Exception as e:
            raise RuntimeError(f"TCLab startup failed to set safe heater state: {e}")

        elapsed = time.time() - start
        if self.device_config.startup_probe and elapsed > timeout_s:
            raise TimeoutError(f"TCLab startup handshake exceeded {timeout_s}s timeout")

    def read_channel(self, channel_name: str) -> float:
        """Read temperature from T1 or T2 channel."""
        ch_lower = channel_name.lower()

        if ch_lower in ("t1", "t2"):
            try:
                # Ask device for current temperature
                cmd = ch_lower.upper()
                self._write(cmd.encode() + b"\n")
                self._flush()
                response = (
                    self._read_until(b"\n", timeout_s=1.0).decode("utf-8").strip()
                )
                value = float(response)

                # Apply scaling from channel config
                ch_config = self.io_config.get_channel(
                    self.device_config.device_id, ch_lower
                )
                if ch_config:
                    value = value * ch_config.scale + ch_config.offset

                self._last_values[ch_lower] = value
                return value
            except Exception:
                # Return last known value on error
                return self._last_values.get(ch_lower, 20.0)
        else:
            raise ValueError(f"Unknown TCLab channel: {channel_name}")

    def write_channel(self, channel_name: str, value: float) -> None:
        """Write heater power to Q1 or Q2 channel."""
        ch_lower = channel_name.lower()

        if ch_lower in ("q1", "q2"):
            # Clamp value and convert to percentage
            ch_config = self.io_config.get_channel(
                self.device_config.device_id, ch_lower
            )
            if ch_config:
                # Reverse the scaling: convert from eng units back to device units
                if ch_config.scale != 0.0:
                    device_value = (value - ch_config.offset) / ch_config.scale
                else:
                    device_value = value

                # Clamp to eng_min/eng_max
                device_value = max(
                    ch_config.eng_min, min(ch_config.eng_max, device_value)
                )
            else:
                device_value = max(0.0, min(100.0, value))

            self._set_heater(ch_lower.upper(), device_value)
            self._last_values[ch_lower] = value
        else:
            raise ValueError(f"Unknown TCLab channel: {channel_name}")

    def _set_heater(self, cmd: str, percent: float) -> None:
        """Send heater command to device.

        Args:
            cmd: "Q1" or "Q2"
            percent: 0-100 percent drive
        """
        if self.port is None:
            raise RuntimeError("Serial port not open")

        percent = max(0.0, min(100.0, float(percent)))
        command = f"{cmd},{percent:.1f}\n".encode()

        try:
            self._write(command)
            self._flush()
            # Read response (typically echoes back the value)
            response = self._read_until(b"\n", timeout_s=1.0)
        except Exception as e:
            raise RuntimeError(f"Failed to set {cmd}: {e}")

    def safe_shutdown(self) -> None:
        """Safely shut down TCLab: set heaters to 0% and close port."""
        if self._is_shutdown:
            return

        self._is_shutdown = True

        if self.port is not None:
            try:
                # Set both heaters to 0% (safe state)
                self._set_heater("Q1", 0.0)
                self._set_heater("Q2", 0.0)
            except Exception:
                pass  # Ignore errors during shutdown

        self.close_port()


# Register TCLab driver with SerialIOProvider
from bdsim.blocks.io_serial import SerialIOProvider

SerialIOProvider.register_device_driver("tclab", TCLabSession)
