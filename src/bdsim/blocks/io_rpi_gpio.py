"""Raspberry Pi GPIO provider for realtime I/O blocks.

This provider is intentionally small and hardware-focused. It supports the
Pi use case needed by the realtime LED example:

- analog output via PWM
- digital input/output via GPIO pins

The provider tries ``RPi.GPIO`` first and falls back to ``gpiozero`` if it is
available. Importing this module does not require either library; the backend is
selected when the provider is instantiated.
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
        self._gpio = None
        self._gpiozero = None
        self._gpiozero_devices: list[Any] = []
        self._pwm_devices: list[Any] = []
        self._mode = self._configure_backend()

    def _configure_backend(self) -> str:
        try:
            from gpiozero import DigitalInputDevice, DigitalOutputDevice, PWMOutputDevice  # type: ignore[import-not-found]
            from gpiozero.pins.lgpio import LGPIOFactory  # type: ignore[import-not-found]

            # Set up lgpio as the pin factory (prefers lgpio > native > RPi.GPIO)
            import gpiozero

            gpiozero.Device.pin_factory = LGPIOFactory()

            self._gpiozero = {
                "DigitalInputDevice": DigitalInputDevice,
                "DigitalOutputDevice": DigitalOutputDevice,
                "PWMOutputDevice": PWMOutputDevice,
            }
            return "gpiozero"
        except Exception:
            pass

        try:
            import RPi.GPIO as gpio  # type: ignore[import-not-found]

            gpio.setwarnings(False)
            gpio.setmode(gpio.BCM)
            self._gpio = gpio
            return "rpi_gpio"
        except Exception as err:
            raise IOProviderError(
                "RpiGPIOProvider requires either gpiozero or RPi.GPIO to be installed"
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

        if self._gpio is not None:
            gpio = self._gpio
            gpio.setup(pin, gpio.OUT)
            pwm = gpio.PWM(pin, frequency)
            pwm.start(0.0)
            self._pwm_devices.append(pwm)

            def write(value: Any) -> None:
                pwm.ChangeDutyCycle(_clamp01(value) * 100.0)

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

        if self._gpio is not None:
            gpio = self._gpio
            gpio.setup(
                pin, gpio.IN, pull_up_down=gpio.PUD_UP if pull_up else gpio.PUD_DOWN
            )
            return _CallableInputHandle(lambda: gpio.input(pin))

        assert self._gpiozero is not None
        input_device = self._gpiozero["DigitalInputDevice"](pin, pull_up=pull_up)
        self._gpiozero_devices.append(input_device)
        return _CallableInputHandle(lambda: input_device.value)

    def open_digital_output(self, spec: IOBlockSpec):
        pin = self._spec_pin(spec)
        options = spec.options or {}
        active_high = bool(options.get("active_high", True))

        if self._gpio is not None:
            gpio = self._gpio
            gpio.setup(pin, gpio.OUT)
            return _CallableOutputHandle(
                lambda value: gpio.output(pin, 1 if value else 0)
            )

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
        if self._gpio is not None:
            self._gpio.cleanup()
        for device in self._gpiozero_devices:
            close = getattr(device, "close", None)
            if callable(close):
                close()
        for pwm in self._pwm_devices:
            stop = getattr(pwm, "stop", None)
            if callable(stop):
                stop()
