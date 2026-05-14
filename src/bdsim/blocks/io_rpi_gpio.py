"""Raspberry Pi GPIO provider for realtime I/O blocks.

This provider is intentionally small and hardware-focused. It supports the
Pi use case needed by the realtime LED example:

- analog output via PWM
- digital input/output via GPIO pins

The provider uses ``gpiozero`` for digital I/O and MCP3008 ADC access. For
PWM output it prefers ``pigpio`` hardware PWM on supported pins and falls back
to ``gpiozero.PWMOutputDevice`` if pigpio is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .io_base import IOBlockSpec, IOProvider, IOProviderError


def _coerce_pin(spec: IOBlockSpec) -> int:
    for candidate in (spec.channel, spec.device):
        if isinstance(candidate, int):
            return candidate
        if isinstance(candidate, str):
            text = candidate.strip().lower()
            if text.isdigit():
                return int(text)
            if text.startswith("gpio") and text[4:].isdigit():
                return int(text[4:])
            if text.startswith("bcm") and text[3:].isdigit():
                return int(text[3:])

    raise IOProviderError(
        f"rpi provider requires a numeric GPIO pin for {spec.block_type}: {spec!r}"
    )


def _clamp01(value: Any) -> float:
    numeric = float(value)
    if numeric < 0.0:
        return 0.0
    if numeric > 1.0:
        return 1.0
    return numeric


@dataclass
class _CallableInputHandle:
    reader: Callable[[], Any]

    def read(self) -> Any:
        return self.reader()


@dataclass
class _CallableOutputHandle:
    writer: Callable[[Any], None]

    def write(self, value: Any) -> None:
        self.writer(value)


class RpiGPIOProvider(IOProvider):
    """Raspberry Pi GPIO provider."""

    name = "rpi"
    aliases = ("rpi_gpio", "gpio", "gpiozero")

    def __init__(self, *, pwm_frequency: float = 1000.0) -> None:
        self.pwm_frequency = pwm_frequency
        self._gpiozero = None
        self._pigpio = None
        self._gpiozero_devices: list[Any] = []
        self._hw_pwm_pins: set[int] = set()
        self._mode = self._configure_backend()

    @staticmethod
    def _supports_hardware_pwm(pin: int) -> bool:
        # Raspberry Pi hardware PWM-capable GPIO pins.
        return pin in {12, 13, 18, 19}

    def _get_pigpio(self):
        if self._pigpio is not None:
            return self._pigpio

        try:
            import pigpio  # type: ignore[import-not-found]

            pi = pigpio.pi()
            if not pi.connected:
                return None
            self._pigpio = pi
            return pi
        except Exception:
            return None

    def _configure_backend(self) -> str:
        try:
            from gpiozero import DigitalInputDevice, DigitalOutputDevice, PWMOutputDevice  # type: ignore[import-not-found]

            # Use lgpio backend when available; otherwise retain gpiozero default.
            import gpiozero

            try:
                from gpiozero.pins.lgpio import LGPIOFactory  # type: ignore[import-not-found]

                gpiozero.Device.pin_factory = LGPIOFactory()
            except Exception:
                pass

            self._gpiozero = {
                "DigitalInputDevice": DigitalInputDevice,
                "DigitalOutputDevice": DigitalOutputDevice,
                "PWMOutputDevice": PWMOutputDevice,
            }
            return "gpiozero"
        except Exception as err:
            raise IOProviderError(
                "RpiGPIOProvider requires gpiozero to be installed"
            ) from err

    def _spec_pin(self, spec: IOBlockSpec) -> int:
        return _coerce_pin(spec)

    def open_analog_input(self, spec: IOBlockSpec):
        pin = self._coerce_adc_pin(spec)
        options = spec.options or {}
        adc_type = str(options.get("adc_type", "mcp3008")).lower()

        if adc_type == "mcp3008":
            return self._open_mcp3008_input(pin, options)
        else:
            raise IOProviderError(
                f"RpiGPIOProvider does not support ADC type {adc_type}; "
                f"try adc_type='mcp3008'"
            )

    def _coerce_adc_pin(self, spec: IOBlockSpec) -> int:
        """Coerce channel to an ADC pin (0-7 for MCP3008)."""
        for candidate in (spec.channel, spec.device):
            if isinstance(candidate, int):
                if 0 <= candidate <= 7:
                    return candidate
            if isinstance(candidate, str):
                text = candidate.strip().lower()
                if text.isdigit() and 0 <= int(text) <= 7:
                    return int(text)

        raise IOProviderError(f"rpi provider ADC pin must be 0-7 for MCP3008: {spec!r}")

    def _open_mcp3008_input(self, channel: int, options: dict) -> object:
        """Open an MCP3008 ADC channel via gpiozero."""
        try:
            from gpiozero import MCP3008
        except ImportError as err:
            raise IOProviderError(
                "MCP3008 support requires gpiozero. "
                "Install with: pip install gpiozero"
            ) from err

        try:
            adc = MCP3008(channel=channel)
            return _CallableInputHandle(lambda: adc.value)
        except Exception as err:
            raise IOProviderError(
                f"failed to open MCP3008 channel {channel}: {err}"
            ) from err

    def open_analog_output(self, spec: IOBlockSpec):
        pin = self._spec_pin(spec)
        options = spec.options or {}
        frequency = float(options.get("frequency", self.pwm_frequency))
        active_high = bool(options.get("active_high", True))

        # Prefer hardware PWM where available for accurate/high carrier rates.
        hw_pwm_requested = bool(options.get("hardware_pwm", True))
        if hw_pwm_requested and self._supports_hardware_pwm(pin):
            pi = self._get_pigpio()
            if pi is not None:
                freq_hz = max(1, int(round(frequency)))

                def write(value: Any) -> None:
                    duty = int(round(_clamp01(value) * 1_000_000.0))
                    pi.hardware_PWM(pin, freq_hz, duty)

                # Initialize at 0% duty and track pin for close().
                pi.hardware_PWM(pin, freq_hz, 0)
                self._hw_pwm_pins.add(pin)
                return _CallableOutputHandle(write)

        assert self._gpiozero is not None
        pwm_output_device = self._gpiozero["PWMOutputDevice"](
            pin,
            frequency=frequency,
            active_high=active_high,
            initial_value=0.0,
        )
        self._gpiozero_devices.append(pwm_output_device)
        return _CallableOutputHandle(
            lambda value: setattr(pwm_output_device, "value", _clamp01(value))
        )

    def open_digital_input(self, spec: IOBlockSpec):
        pin = self._spec_pin(spec)
        options = spec.options or {}
        pull_up = bool(options.get("pull_up", False))

        assert self._gpiozero is not None
        input_device = self._gpiozero["DigitalInputDevice"](pin, pull_up=pull_up)
        self._gpiozero_devices.append(input_device)
        return _CallableInputHandle(lambda: input_device.value)

    def open_digital_output(self, spec: IOBlockSpec):
        pin = self._spec_pin(spec)
        options = spec.options or {}
        active_high = bool(options.get("active_high", True))

        assert self._gpiozero is not None
        output_device = self._gpiozero["DigitalOutputDevice"](
            pin,
            active_high=active_high,
            initial_value=False,
        )
        self._gpiozero_devices.append(output_device)
        return _CallableOutputHandle(
            lambda value: setattr(output_device, "value", 1 if value else 0)
        )

    def close(self) -> None:
        if self._pigpio is not None:
            for pin in self._hw_pwm_pins:
                try:
                    self._pigpio.hardware_PWM(pin, 0, 0)
                except Exception:
                    pass
            self._hw_pwm_pins.clear()
            try:
                self._pigpio.stop()
            except Exception:
                pass
            self._pigpio = None

        for device in self._gpiozero_devices:
            close = getattr(device, "close", None)
            if callable(close):
                close()
