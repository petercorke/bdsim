"""Device configuration parsing and resolution from TOML.

This module loads and validates I/O device configurations from TOML files,
supporting scaling, channel aliases, and per-device safety parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomllib


@dataclass
class ChannelConfig:
    """Configuration for a single I/O channel."""

    name: str
    device_id: str
    direction: str  # "in" or "out"
    kind: str  # "analog", "digital"
    address: str | int  # Device-side address/pin
    eng_units: str = ""
    eng_min: float = 0.0
    eng_max: float = 1.0
    scale: float = 1.0
    offset: float = 0.0
    safe: float | None = None  # Safe value for outputs on shutdown
    mode: str = ""  # "pwm", "digital", etc.
    alias: str = ""  # User-friendly alias name
    extra: dict[str, Any] | None = None

    def raw(self) -> dict[str, Any]:
        """Return dict of all non-None, non-default fields for passing to provider."""
        result = {
            "name": self.name,
            "device_id": self.device_id,
            "direction": self.direction,
            "kind": self.kind,
            "address": self.address,
        }
        if self.eng_units:
            result["eng_units"] = self.eng_units
        if self.eng_min != 0.0 or self.eng_max != 1.0:
            result["eng_min"] = self.eng_min
            result["eng_max"] = self.eng_max
        if self.scale != 1.0:
            result["scale"] = self.scale
        if self.offset != 0.0:
            result["offset"] = self.offset
        if self.safe is not None:
            result["safe"] = self.safe
        if self.mode:
            result["mode"] = self.mode
        if self.alias:
            result["alias"] = self.alias
        if self.extra:
            result.update(self.extra)
        return result


@dataclass
class DeviceConfig:
    """Configuration for a single I/O device."""

    device_id: str
    provider: str
    driver: str
    port: str = ""
    baud: int = 115200
    startup_probe: bool = False
    startup_timeout_s: float = 2.0
    params: dict[str, Any] | None = None
    channels: dict[str, ChannelConfig] | None = None
    extra: dict[str, Any] | None = None

    def raw(self) -> dict[str, Any]:
        """Return dict of all configuration for passing to provider."""
        result = {
            "device_id": self.device_id,
            "provider": self.provider,
            "driver": self.driver,
        }
        if self.port:
            result["port"] = self.port
        if self.baud != 115200:
            result["baud"] = self.baud
        if self.startup_probe:
            result["startup_probe"] = True
        if self.startup_timeout_s != 2.0:
            result["startup_timeout_s"] = self.startup_timeout_s
        if self.params:
            result["params"] = dict(self.params)
        if self.extra:
            result.update(self.extra)
        return result


class IOConfig:
    """Parsed I/O device configuration from TOML."""

    def __init__(self) -> None:
        self.config_version: int = 1
        self.default_provider: str = "mock"
        self.providers: dict[str, dict[str, Any]] = {}
        self.devices: dict[str, DeviceConfig] = {}
        self._alias_to_device: dict[str, tuple[str, str]] = (
            {}
        )  # alias -> (device_id, channel_name)

    @classmethod
    def from_file(cls, path: str | Path) -> "IOConfig":
        """Load and parse configuration from a TOML file."""
        path = Path(path)
        if not path.exists():
            # Return empty config if file doesn't exist (allows optional config)
            return cls()

        with open(path, "rb") as f:
            data = tomllib.load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IOConfig":
        """Parse configuration from a dict (e.g., from tomllib)."""
        config = cls()

        # Top-level I/O settings
        io_section = data.get("io", {})
        config.config_version = io_section.get("config_version", 1)
        config.default_provider = io_section.get("default_provider", "mock")

        # Provider-level settings (not full provider instances; just metadata)
        providers_section = data.get("providers", {})
        for provider_name, provider_config in providers_section.items():
            config.providers[provider_name] = dict(provider_config)

        # Device configurations
        devices_section = data.get("devices", {})
        for device_id, device_data in devices_section.items():
            device_config = cls._parse_device(device_id, device_data)
            config.devices[device_id] = device_config

            # Index channel aliases
            if device_config.channels:
                for ch_name, ch_config in device_config.channels.items():
                    if ch_config.alias:
                        config._alias_to_device[ch_config.alias] = (device_id, ch_name)

        return config

    @classmethod
    def _parse_device(cls, device_id: str, device_data: dict[str, Any]) -> DeviceConfig:
        """Parse a single device configuration block."""
        provider = device_data.get("provider", "")
        driver = device_data.get("driver", "")
        port = device_data.get("port", "")
        baud = device_data.get("baud", 115200)
        startup_probe = device_data.get("startup_probe", False)
        startup_timeout_s = device_data.get("startup_timeout_s", 2.0)

        params = dict(device_data.get("params", {}))

        # Parse channel configurations
        channels_data = device_data.get("channels", {})
        channels = {}
        for ch_name, ch_data in channels_data.items():
            ch_config = cls._parse_channel(device_id, ch_name, ch_data)
            channels[ch_name] = ch_config

        # Collect any extra fields not explicitly handled
        handled_keys = {
            "provider",
            "driver",
            "port",
            "baud",
            "startup_probe",
            "startup_timeout_s",
            "params",
            "channels",
        }
        extra = {k: v for k, v in device_data.items() if k not in handled_keys}

        return DeviceConfig(
            device_id=device_id,
            provider=provider,
            driver=driver,
            port=port,
            baud=baud,
            startup_probe=startup_probe,
            startup_timeout_s=startup_timeout_s,
            params=params or None,
            channels=channels or None,
            extra=extra or None,
        )

    @classmethod
    def _parse_channel(
        cls, device_id: str, ch_name: str, ch_data: dict[str, Any]
    ) -> ChannelConfig:
        """Parse a single channel configuration block."""
        direction = ch_data.get("direction", "in")
        kind = ch_data.get("kind", "analog")
        address = ch_data.get("address", ch_name)
        eng_units = ch_data.get("eng_units", "")
        eng_min = float(ch_data.get("eng_min", 0.0))
        eng_max = float(ch_data.get("eng_max", 1.0))
        scale = float(ch_data.get("scale", 1.0))
        offset = float(ch_data.get("offset", 0.0))
        safe_val = ch_data.get("safe")
        safe = float(safe_val) if safe_val is not None else None
        mode = ch_data.get("mode", "")
        alias = ch_data.get("alias", "")

        # Collect extra fields (pin, adc, channel, frequency_hz, etc.)
        handled_keys = {
            "direction",
            "kind",
            "address",
            "eng_units",
            "eng_min",
            "eng_max",
            "scale",
            "offset",
            "safe",
            "mode",
            "alias",
        }
        extra = {k: v for k, v in ch_data.items() if k not in handled_keys}

        return ChannelConfig(
            name=ch_name,
            device_id=device_id,
            direction=direction,
            kind=kind,
            address=address,
            eng_units=eng_units,
            eng_min=eng_min,
            eng_max=eng_max,
            scale=scale,
            offset=offset,
            safe=safe,
            mode=mode,
            alias=alias,
            extra=extra or None,
        )

    def get_device(self, device_id: str) -> DeviceConfig | None:
        """Retrieve a device configuration by ID."""
        return self.devices.get(device_id)

    def get_channel(self, device_id: str, channel_name: str) -> ChannelConfig | None:
        """Retrieve a channel configuration within a device."""
        device = self.devices.get(device_id)
        if device is None or device.channels is None:
            return None
        return device.channels.get(channel_name)

    def resolve_alias(self, alias: str) -> tuple[str, str] | None:
        """Resolve a channel alias to (device_id, channel_name), or None if not found."""
        return self._alias_to_device.get(alias)

    def resolve_channel_ref(
        self, device_id: str, channel_ref: str | int
    ) -> ChannelConfig | None:
        """
        Resolve a channel reference (address string or numeric channel) to its config.

        Tries in order:
        1. Exact channel name match
        2. Address field match
        3. Numeric address match (if channel_ref is int)
        """
        device = self.devices.get(device_id)
        if device is None or device.channels is None:
            return None

        # Try exact name
        if channel_ref in device.channels:
            return device.channels[channel_ref]

        # Try address field match
        for ch_config in device.channels.values():
            if str(ch_config.address) == str(channel_ref):
                return ch_config

        return None
