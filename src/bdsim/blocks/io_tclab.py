"""TCLab device driver for bdsim serial I/O framework.

This module implements support for the Temperature Control Lab (TCLab)
hardware device, a simple educational platform with two heater outputs (Q1, Q2)
and two temperature inputs (T1, T2).

Protocol Summary (firmware v2.0.1):
- Commands: "Q1 <0-100>\n", "Q2 <0-100>\n", "T1\n", "T2\n", "VER\n", "X\n"
  Separator is SPACE (sp=' '), terminator is LF (nl='\n').
- Responses: float as decimal string + '\n'
- Default baud: 115200
- LED: dim=heaters off, bright=heaters on, blinking=high-temp alarm
- Safe state: Q1=0, Q2=0 (heaters off)
- Note: heater elements require EXTERNAL power supply (not USB)
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
        """Perform TCLab startup handshake: flush boot message, read version, display diagnostics."""
        if self.port is None:
            raise RuntimeError("Serial port must be opened before handshake")

        # Flush the Arduino boot greeting (one readline, may be empty on
        # some firmware versions — matches official tclab library behaviour).
        try:
            self.port.readline()
        except Exception:
            pass

        # Request firmware version.
        try:
            self._write(b"VER\n")
            self._flush()
            response = self._read_until(b"\n", timeout_s=2.0).decode("utf-8").strip()
            if response:
                self.firmware_version = response
        except Exception:
            self.firmware_version = "(unknown)"

        # Read initial temperatures.
        try:
            t1_init = self._query_temp("T1")
            t2_init = self._query_temp("T2")
        except Exception:
            t1_init = t2_init = float("nan")

        # Heater limits per channel from channel config (eng_max).
        dev = self.device_config.device_id
        q1_ch = self.io_config.get_channel(dev, "q1")
        q2_ch = self.io_config.get_channel(dev, "q2")
        q1_limit = q1_ch.eng_max if q1_ch else 100.0
        q2_limit = q2_ch.eng_max if q2_ch else 100.0

        # Print startup info.
        print(f"  [{dev}] firmware : {self.firmware_version}")
        print(f"  [{dev}] T1={t1_init:.1f}°C  T2={t2_init:.1f}°C")
        print(f"  [{dev}] heater limits: Q1={q1_limit:.0f}%  Q2={q2_limit:.0f}%")

        # Set heaters to safe state (0%).
        try:
            self._set_heater("Q1", 0.0)
            self._set_heater("Q2", 0.0)
        except Exception as e:
            raise RuntimeError(f"TCLab startup failed to set safe heater state: {e}")

    def read_channel(self, channel_name: str) -> float:
        """Read temperature from T1 or T2 channel."""
        if self._is_shutdown:
            return self._last_values.get(channel_name.lower(), 20.0)
        ch_lower = channel_name.lower()

        if ch_lower in ("t1", "t2"):
            try:
                value = self._query_temp(ch_lower.upper())

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

    def _query_temp(self, cmd: str) -> float:
        """Send T1/T2 command and return the float response.

        Flushes the RX buffer first to discard any pending heater echo bytes
        left over from fire-and-forget writes.
        """
        if self.port is not None:
            self.port.reset_input_buffer()
        self._write(cmd.upper().encode() + b"\n")
        self._flush()
        return float(self._read_until(b"\n", timeout_s=1.0).decode("utf-8").strip())

    def write_channel(self, channel_name: str, value: float) -> None:
        """Write heater power to Q1 or Q2 channel."""
        if self._is_shutdown:
            return  # Ignore writes after shutdown has started
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

        TCLab firmware protocol: ``Q1 <value>\r\n`` (space-separated).
        The firmware echoes back the accepted value.

        Args:
            cmd: "Q1" or "Q2"
            percent: 0-100 percent drive
        """
        if self.port is None:
            raise RuntimeError("Serial port not open")

        percent = max(0.0, min(100.0, float(percent)))
        # Space separator, \n terminator — matches firmware: sep=' ', nl='\n'.
        command = f"{cmd} {percent:.1f}\n".encode()

        try:
            self._write(command)
            self._flush()
            # Fire-and-forget: skip echo read to avoid a second USB round-trip.
            # The RX buffer is flushed before the next _query_temp call.
        except Exception as e:
            raise RuntimeError(f"Failed to set {cmd}: {e}")

    def safe_shutdown(self) -> None:
        """Safely shut down TCLab: set heaters to 0% and close port."""
        if self._is_shutdown:
            return

        self._is_shutdown = True

        dev = self.device_config.device_id if self.device_config else "tclab"
        if self.port is not None:
            try:
                self._set_heater("Q1", 0.0)
                self._set_heater("Q2", 0.0)
                print(f"  [{dev}] heaters off (Q1=0%, Q2=0%)")
            except Exception as e:
                print(f"  [{dev}] WARNING: shutdown heater-off command failed: {e}")

        self.close_port()
        print(f"  [{dev}] serial port closed")


# Register TCLab driver with SerialIOProvider
from bdsim.blocks.io_serial import SerialIOProvider

SerialIOProvider.register_device_driver("tclab", TCLabSession)
