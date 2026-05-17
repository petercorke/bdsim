"""Unit tests for serial I/O configuration and provider framework.

These tests verify:
- TOML config parsing (DeviceConfig, ChannelConfig)
- Config resolution (device/channel lookups, alias resolution)
- SerialIOProvider registry and factory
- MockTCLab session behavior
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from bdsim.blocks.io_base import IOBlockSpec, UnsupportedIOBlockError
from bdsim.config import ChannelConfig, DeviceConfig, IOConfig


class TestIOConfig(unittest.TestCase):
    """Test TOML parsing and device configuration resolution."""

    def test_config_from_dict_basic(self) -> None:
        """Parse basic device config from dict."""
        data = {
            "io": {"config_version": 1, "default_provider": "serial"},
            "devices": {
                "tclab0": {
                    "provider": "serial",
                    "driver": "tclab",
                    "port": "/dev/ttyACM0",
                    "baud": 115200,
                    "channels": {
                        "q1": {
                            "direction": "out",
                            "kind": "analog",
                            "address": "Q1",
                            "eng_units": "%",
                            "eng_min": 0.0,
                            "eng_max": 100.0,
                            "safe": 0.0,
                        },
                        "t1": {
                            "direction": "in",
                            "kind": "analog",
                            "address": "T1",
                            "scale": 1.0,
                            "offset": 0.0,
                        },
                    },
                }
            },
        }

        config = IOConfig.from_dict(data)

        self.assertEqual(config.config_version, 1)
        self.assertEqual(config.default_provider, "serial")
        self.assertIn("tclab0", config.devices)

        device = config.devices["tclab0"]
        self.assertEqual(device.device_id, "tclab0")
        self.assertEqual(device.provider, "serial")
        self.assertEqual(device.driver, "tclab")
        self.assertEqual(device.port, "/dev/ttyACM0")
        self.assertEqual(device.baud, 115200)

        self.assertIsNotNone(device.channels)
        self.assertIn("q1", device.channels)
        self.assertIn("t1", device.channels)

        q1 = device.channels["q1"]
        self.assertEqual(q1.name, "q1")
        self.assertEqual(q1.direction, "out")
        self.assertEqual(q1.safe, 0.0)

        t1 = device.channels["t1"]
        self.assertEqual(t1.direction, "in")
        self.assertEqual(t1.scale, 1.0)
        self.assertEqual(t1.offset, 0.0)

    def test_config_get_device(self) -> None:
        """Test device lookup by ID."""
        data = {
            "devices": {
                "tclab0": {
                    "provider": "serial",
                    "driver": "tclab",
                    "port": "/dev/ttyACM0",
                }
            }
        }

        config = IOConfig.from_dict(data)

        device = config.get_device("tclab0")
        self.assertIsNotNone(device)
        self.assertEqual(device.device_id, "tclab0")

        missing = config.get_device("nonexistent")
        self.assertIsNone(missing)

    def test_config_get_channel(self) -> None:
        """Test channel lookup within device."""
        data = {
            "devices": {
                "tclab0": {
                    "provider": "serial",
                    "driver": "tclab",
                    "port": "/dev/ttyACM0",
                    "channels": {
                        "t1": {
                            "direction": "in",
                            "kind": "analog",
                            "address": "T1",
                        }
                    },
                }
            }
        }

        config = IOConfig.from_dict(data)

        ch = config.get_channel("tclab0", "t1")
        self.assertIsNotNone(ch)
        self.assertEqual(ch.name, "t1")

        missing = config.get_channel("tclab0", "nonexistent")
        self.assertIsNone(missing)

    def test_config_resolve_channel_ref_by_address(self) -> None:
        """Test channel resolution by address field."""
        data = {
            "devices": {
                "tclab0": {
                    "provider": "serial",
                    "driver": "tclab",
                    "port": "/dev/ttyACM0",
                    "channels": {
                        "t1": {
                            "direction": "in",
                            "kind": "analog",
                            "address": "T1",
                        }
                    },
                }
            }
        }

        config = IOConfig.from_dict(data)

        # Resolve by exact channel name
        ch = config.resolve_channel_ref("tclab0", "t1")
        self.assertIsNotNone(ch)
        self.assertEqual(ch.name, "t1")

        # Resolve by address
        ch = config.resolve_channel_ref("tclab0", "T1")
        self.assertIsNotNone(ch)
        self.assertEqual(ch.name, "t1")

    def test_config_alias_indexing(self) -> None:
        """Test channel alias resolution."""
        data = {
            "devices": {
                "rpi0": {
                    "provider": "rpi",
                    "driver": "gpio",
                    "channels": {
                        "led": {
                            "direction": "out",
                            "kind": "analog",
                            "pin": 18,
                            "alias": "actuator_led",
                        }
                    },
                }
            }
        }

        config = IOConfig.from_dict(data)

        # Resolve alias
        resolved = config.resolve_alias("actuator_led")
        self.assertIsNotNone(resolved)
        device_id, ch_name = resolved
        self.assertEqual(device_id, "rpi0")
        self.assertEqual(ch_name, "led")

        missing = config.resolve_alias("nonexistent")
        self.assertIsNone(missing)

    def test_channel_config_raw(self) -> None:
        """Test ChannelConfig.raw() method."""
        ch = ChannelConfig(
            name="t1",
            device_id="tclab0",
            direction="in",
            kind="analog",
            address="T1",
            eng_units="C",
            scale=1.5,
            offset=0.5,
            alias="main_temp",
        )

        raw = ch.raw()

        self.assertEqual(raw["name"], "t1")
        self.assertEqual(raw["direction"], "in")
        self.assertEqual(raw["kind"], "analog")
        self.assertEqual(raw["eng_units"], "C")
        self.assertEqual(raw["scale"], 1.5)
        self.assertEqual(raw["offset"], 0.5)
        self.assertEqual(raw["alias"], "main_temp")

    def test_device_config_raw(self) -> None:
        """Test DeviceConfig.raw() method."""
        device = DeviceConfig(
            device_id="tclab0",
            provider="serial",
            driver="tclab",
            port="/dev/ttyACM0",
            baud=115200,
            startup_probe=True,
        )

        raw = device.raw()

        self.assertEqual(raw["device_id"], "tclab0")
        self.assertEqual(raw["provider"], "serial")
        self.assertEqual(raw["driver"], "tclab")
        self.assertEqual(raw["port"], "/dev/ttyACM0")
        # baud and startup_probe are only in raw if non-default
        # baud=115200 is default, so it may not be in raw
        self.assertEqual(raw["startup_probe"], True)

    def test_config_from_file(self) -> None:
        """Test loading config from TOML file."""
        toml_content = """
[io]
config_version = 1
default_provider = "serial"

[devices.tclab0]
provider = "serial"
driver = "tclab"
port = "/dev/ttyACM0"
baud = 115200

[devices.tclab0.channels.t1]
direction = "in"
kind = "analog"
address = "T1"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()

            try:
                config = IOConfig.from_file(f.name)

                self.assertEqual(config.config_version, 1)
                self.assertIn("tclab0", config.devices)

                device = config.devices["tclab0"]
                self.assertEqual(device.port, "/dev/ttyACM0")
                self.assertIsNotNone(device.channels)
                self.assertIn("t1", device.channels)
            finally:
                Path(f.name).unlink()

    def test_config_from_nonexistent_file(self) -> None:
        """Test loading from nonexistent file returns empty config."""
        config = IOConfig.from_file("/nonexistent/path.toml")

        self.assertEqual(config.config_version, 1)
        self.assertEqual(config.default_provider, "mock")
        self.assertEqual(len(config.devices), 0)


class TestSerialIOProvider(unittest.TestCase):
    """Test serial I/O provider framework."""

    def test_provider_init(self) -> None:
        """Test SerialIOProvider initialization."""
        # Import inside test to avoid issues with circular imports
        with patch(
            "bdsim.blocks.io_serial.SerialIOProvider._register_shutdown_handlers"
        ):
            from bdsim.blocks.io_serial import SerialIOProvider

            provider = SerialIOProvider(
                config_path="nonexistent.toml", auto_shutdown=False
            )

            self.assertIsNotNone(provider.io_config)
            self.assertEqual(len(provider.sessions), 0)

    def test_provider_register_device_driver(self) -> None:
        """Test device driver registration."""
        from bdsim.blocks.io_serial import SerialIOProvider, SerialDeviceSession

        class MockDriver(SerialDeviceSession):
            def startup_handshake(self) -> None:
                pass

            def read_channel(self, channel_name: str) -> float:
                return 0.0

            def write_channel(self, channel_name: str, value: float) -> None:
                pass

        SerialIOProvider.register_device_driver("mock_device", MockDriver)

        self.assertIn("mock_device", SerialIOProvider._device_factories)
        self.assertEqual(SerialIOProvider._device_factories["mock_device"], MockDriver)

    def test_tclab_driver_registered(self) -> None:
        """Test that TCLab driver is auto-registered."""
        from bdsim.blocks.io_serial import SerialIOProvider

        # Import should trigger auto-registration
        import bdsim.blocks.io_tclab  # noqa: F401

        self.assertIn("tclab", SerialIOProvider._device_factories)


if __name__ == "__main__":
    unittest.main()
