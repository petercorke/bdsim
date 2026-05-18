"""Serial I/O provider framework for device drivers like TCLab and Firmata.

This module provides the base provider and device session abstractions for
serial-connected hardware. Concrete drivers (TCLab, Firmata, etc.) subclass
these to implement their specific command protocols.
"""

from __future__ import annotations

import atexit
import signal
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

try:
    import serial
except ImportError:
    # Serial module not available; provide stub for type checking
    serial = None  # type: ignore

from bdsim.blocks.io_base import (
    AnalogInputHandle,
    AnalogOutputHandle,
    DigitalInputHandle,
    DigitalOutputHandle,
    IOBlockSpec,
    IOProvider,
    UnsupportedIOBlockError,
)
from bdsim.config import ChannelConfig, DeviceConfig, IOConfig


def _find_config(explicit: str | None = None) -> str | None:
    """Return the first existing config path from the search order:

    1. The explicit path if given.
    2. ``./bdsim.toml`` (current working directory).
    3. ``~/.bdsim.toml`` (user home directory, dot-file convention).

    Returns *None* if no file is found.
    """
    from pathlib import Path

    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(Path(explicit))
    candidates.append(Path.cwd() / "bdsim.toml")
    candidates.append(Path.home() / ".bdsim.toml")

    for p in candidates:
        if p.exists():
            return str(p)
    return None


@dataclass
class SerialSessionHandle:
    """Wraps a device session and channel config for I/O binding."""

    session: "SerialDeviceSession"
    channel_config: ChannelConfig


class SerialDeviceSession(ABC):
    """Abstract base for a serial-connected device session.

    Concrete implementations (TCLabSession, FirmataSession, etc.) manage:
    - Serial port lifecycle
    - Command/response protocol
    - Channel value scaling and safety
    """

    def __init__(
        self, device_config: DeviceConfig, io_config: IOConfig | None = None
    ) -> None:
        self.device_config = device_config
        self.io_config = io_config or IOConfig()
        self.port: Any = None  # serial.Serial | None
        self._lock = threading.RLock()
        self._is_shutdown = False

    @abstractmethod
    def startup_handshake(self) -> None:
        """Perform initial handshake: version probe, mode setup, param sync.

        Should raise an exception on protocol error or timeout.
        """
        pass

    @abstractmethod
    def read_channel(self, channel_name: str) -> float:
        """Read the current value from a named input channel.

        Should apply scaling/offset from channel config before returning.
        """
        pass

    @abstractmethod
    def write_channel(self, channel_name: str, value: float) -> None:
        """Write a value to a named output channel.

        Should apply clamping based on eng_min/eng_max and scaling before sending.
        """
        pass

    def open_port(self) -> None:
        """Open the serial port with configured baud/timeout settings."""
        if self.port is not None:
            return  # Already open

        if serial is None:
            raise RuntimeError(
                "pyserial module not available; install with: pip install pyserial"
            )

        port_name = self.device_config.port
        baud = self.device_config.baud
        timeout = 1.0  # Block for up to 1s on reads

        try:
            self.port = serial.Serial(port_name, baudrate=baud, timeout=timeout)
            # TCLab/Arduino resets on DTR toggle; must wait ~2 s for boot.
            self.port.dtr = False
            time.sleep(0.1)
            self.port.dtr = True
            time.sleep(2.0)  # match official tclab library boot wait
        except Exception as e:
            raise RuntimeError(
                f"Failed to open serial port {port_name} at {baud} baud: {e}"
            ) from e

    def close_port(self) -> None:
        """Close the serial port."""
        if self.port is not None:
            try:
                self.port.close()
            except Exception:
                pass
            self.port = None

    def safe_shutdown(self) -> None:
        """Set all outputs to safe values and close session.

        Called on normal shutdown, signal interruption, or atexit.
        Subclasses should override to implement device-specific shutdown.
        """
        if self._is_shutdown:
            return

        self._is_shutdown = True

        # Set all outputs to safe values
        if self.device_config.channels:
            for ch_name, ch_config in self.device_config.channels.items():
                if ch_config.direction == "out" and ch_config.safe is not None:
                    try:
                        self.write_channel(ch_name, ch_config.safe)
                    except Exception:
                        pass  # Ignore errors during shutdown

        self.close_port()

    def _read_until(self, end_marker: bytes, timeout_s: float = 1.0) -> bytes:
        """Read from serial port until end_marker or timeout.

        Uses pyserial's read_until() so the OS delivers all bytes in one call
        rather than polling one byte at a time (avoids repeated USB CDC latency
        penalties on macOS).
        """
        if self.port is None:
            raise RuntimeError("Serial port not open")

        self.port.timeout = timeout_s
        result = self.port.read_until(end_marker)
        if not result.endswith(end_marker):
            raise TimeoutError(f"No response from device (waited {timeout_s}s)")
        return result

    def _write(self, data: bytes) -> None:
        """Write bytes to serial port."""
        if self.port is None:
            raise RuntimeError("Serial port not open")
        self.port.write(data)

    def _flush(self) -> None:
        """Flush output buffer."""
        if self.port is not None:
            self.port.flush()


class SerialAnalogInputHandle(AnalogInputHandle):
    """Handle for reading from a serial device analog input channel."""

    def __init__(self, session_handle: SerialSessionHandle) -> None:
        self.session = session_handle.session
        self.channel_config = session_handle.channel_config

    def read(self) -> float:
        return self.session.read_channel(self.channel_config.name)


class SerialAnalogOutputHandle(AnalogOutputHandle):
    """Handle for writing to a serial device analog output channel."""

    def __init__(self, session_handle: SerialSessionHandle) -> None:
        self.session = session_handle.session
        self.channel_config = session_handle.channel_config

    def write(self, value: float) -> None:
        self.session.write_channel(self.channel_config.name, value)


class SerialIOProvider(IOProvider):
    """Base provider for serial-connected devices (TCLab, Firmata, etc.).

    Manages device session lifecycle and provides factory methods for I/O handles.
    Supports safe shutdown on signal or normal process exit.
    """

    name = "serial"
    _device_factories: dict[str, type[SerialDeviceSession]] = {}

    def __init__(
        self, config_path: str | None = None, auto_shutdown: bool = True
    ) -> None:
        resolved = _find_config(config_path)
        self.config_path = resolved
        if resolved:
            self.io_config = IOConfig.from_file(resolved)
        else:
            import warnings
            from pathlib import Path

            searched = [
                str(Path.cwd() / "bdsim.toml"),
                str(Path.home() / ".bdsim.toml"),
            ]
            warnings.warn(
                "SerialIOProvider: no config file found. "
                f"Searched: {searched}. "
                "Create bdsim.toml in your working directory or "
                "~/.bdsim.toml for a personal config.",
                stacklevel=2,
            )
            self.io_config = IOConfig()
        self.sessions: dict[str, SerialDeviceSession] = {}
        self._lock = threading.RLock()

        if auto_shutdown:
            self._register_shutdown_handlers()

    @classmethod
    def register_device_driver(
        cls, driver_name: str, session_class: type[SerialDeviceSession]
    ) -> None:
        """Register a device driver (e.g., 'tclab' -> TCLabSession)."""
        cls._device_factories[driver_name.lower()] = session_class

    def _get_or_create_session(self, spec: IOBlockSpec) -> SerialSessionHandle | None:
        """Get or create a device session for the given device_id."""
        if spec.device is None:
            return None

        device_id = spec.device

        with self._lock:
            if device_id in self.sessions:
                session = self.sessions[device_id]
            else:
                # Create new session
                device_config = self.io_config.get_device(device_id)
                if device_config is None:
                    cfg_hint = (
                        f"loaded from {self.config_path!r}"
                        if self.config_path
                        else "no config file was found"
                    )
                    raise ValueError(
                        f"device {device_id!r} not found in config "
                        f"({cfg_hint}). "
                        "Check that bdsim.toml exists in your working "
                        "directory or in ~/.bdsim.toml and defines a "
                        f"[devices.{device_id}] section."
                    )

                session = self._create_session(device_config)
                self.sessions[device_id] = session

            # Resolve channel config
            channel_config = self.io_config.get_channel(
                device_id, spec.channel
            ) or self.io_config.resolve_channel_ref(device_id, spec.channel)

            if channel_config is None:
                raise ValueError(
                    f"channel {spec.channel!r} not found in device {device_id!r}"
                )

            return SerialSessionHandle(session=session, channel_config=channel_config)

    def _create_session(self, device_config: DeviceConfig) -> SerialDeviceSession:
        """Create a new device session based on driver name."""
        driver_name = device_config.driver.lower()
        factory = self._device_factories.get(driver_name)

        if factory is None:
            known = ", ".join(sorted(self._device_factories))
            raise ValueError(
                f"unknown serial device driver {device_config.driver!r}; "
                f"known drivers: {known}"
            )

        session = factory(device_config, self.io_config)
        session.open_port()
        session.startup_handshake()
        return session

    def open_analog_input(self, spec: IOBlockSpec) -> AnalogInputHandle:
        handle = self._get_or_create_session(spec)
        if handle is None:
            raise UnsupportedIOBlockError(
                "analog input requires device and channel specification"
            )
        return SerialAnalogInputHandle(handle)

    def open_analog_output(self, spec: IOBlockSpec) -> AnalogOutputHandle:
        handle = self._get_or_create_session(spec)
        if handle is None:
            raise UnsupportedIOBlockError(
                "analog output requires device and channel specification"
            )
        return SerialAnalogOutputHandle(handle)

    def open_digital_input(self, spec: IOBlockSpec) -> DigitalInputHandle:
        # For now, serial devices use analog handles for all I/O
        raise UnsupportedIOBlockError(
            "serial provider uses analog I/O for all channels"
        )

    def open_digital_output(self, spec: IOBlockSpec) -> DigitalOutputHandle:
        raise UnsupportedIOBlockError(
            "serial provider uses analog I/O for all channels"
        )

    def safe_shutdown_all(self) -> None:
        """Set all devices to safe state and close sessions."""
        with self._lock:
            for session in self.sessions.values():
                try:
                    session.safe_shutdown()
                except Exception:
                    pass

    def close(self) -> None:
        """Release all provider resources."""
        self.safe_shutdown_all()

    def _register_shutdown_handlers(self) -> None:
        """Register SIGINT/SIGTERM handlers and atexit handler for safe shutdown."""

        def _signal_handler(signum: int, frame: Any) -> None:
            # Request graceful shutdown via safe_shutdown_all
            self.safe_shutdown_all()
            # Re-raise to exit normally
            raise KeyboardInterrupt() if signum == signal.SIGINT else SystemExit(1)

        try:
            signal.signal(signal.SIGINT, _signal_handler)
            signal.signal(signal.SIGTERM, _signal_handler)
        except (ValueError, OSError):
            pass  # Signal handling may not be available in all contexts

        # Also register atexit handler for clean shutdown
        atexit.register(self.safe_shutdown_all)


# Register this provider so it can be discovered
# Import builtin device drivers after all classes are defined so that
# circular-import lookups (e.g. io_tclab -> SerialDeviceSession) succeed.
try:
    import bdsim.blocks.io_tclab  # noqa: F401
except ImportError:
    pass

IOProvider._load_builtin_providers()
