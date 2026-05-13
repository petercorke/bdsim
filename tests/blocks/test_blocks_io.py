import os
import platform
import unittest

import bdsim
from bdsim.blocks.io import AnalogIn, AnalogOut, DigitalIn, DigitalOut
from bdsim.blocks.io_mock import MockIOProvider
from bdsim.blocks.io_base import (
    IOBlockSpec,
    IOProvider,
    IOProviderError,
    MissingIOProviderError,
    UnsupportedIOBlockError,
    get_runtime_io_provider,
)


class _FakeInputHandle:
    def __init__(self, value):
        self.value = value

    def read(self):
        return self.value


class _FakeOutputHandle:
    def __init__(self):
        self.writes = []

    def write(self, value):
        self.writes.append(value)


class _FakeProvider(IOProvider):
    name = "fake"

    def __init__(self):
        self.analog_in_calls = []
        self.analog_out_calls = []
        self.digital_in_calls = []
        self.digital_out_calls = []
        self.analog_in_handle = _FakeInputHandle(1.25)
        self.digital_in_handle = _FakeInputHandle(True)
        self.analog_out_handle = _FakeOutputHandle()
        self.digital_out_handle = _FakeOutputHandle()

    def open_analog_input(self, spec: IOBlockSpec):
        self.analog_in_calls.append(spec)
        return self.analog_in_handle

    def open_analog_output(self, spec: IOBlockSpec):
        self.analog_out_calls.append(spec)
        return self.analog_out_handle

    def open_digital_input(self, spec: IOBlockSpec):
        self.digital_in_calls.append(spec)
        return self.digital_in_handle

    def open_digital_output(self, spec: IOBlockSpec):
        self.digital_out_calls.append(spec)
        return self.digital_out_handle


class _RegisteredProvider(IOProvider):
    name = "registered-test"
    aliases = ("registered-alias",)


class _AttributeRuntime:
    def __init__(self, provider):
        self.io_provider = provider


class _GetterRuntime:
    def __init__(self, provider):
        self._provider = provider

    def get_io_provider(self):
        return self._provider


class IOMacSafeTest(unittest.TestCase):
    def setUp(self):
        self.bd = bdsim.BlockDiagram(name="io-test")
        self.simstate = bdsim.BDRealTimeState()

    def test_provider_lookup_from_attribute(self):
        provider = _FakeProvider()
        runtime = _AttributeRuntime(provider)
        self.assertIs(get_runtime_io_provider(runtime), provider)

    def test_provider_lookup_from_getter(self):
        provider = _FakeProvider()
        runtime = _GetterRuntime(provider)
        self.assertIs(get_runtime_io_provider(runtime), provider)

    def test_missing_provider_raises(self):
        with self.assertRaises(MissingIOProviderError):
            get_runtime_io_provider(None)

    def test_unsupported_provider_raises(self):
        runtime = object()
        with self.assertRaises(MissingIOProviderError):
            get_runtime_io_provider(runtime)

    def test_analog_in_reads_from_provider(self):
        provider = _FakeProvider()
        self.bd.runtime = _AttributeRuntime(provider)
        block = AnalogIn(channel=3, device="adc0", io_options={"gain": 2}, bd=self.bd)

        block.start(self.simstate)

        self.assertEqual(block.output(0.0, [], []), [1.25])
        self.assertEqual(len(provider.analog_in_calls), 1)
        self.assertEqual(provider.analog_in_calls[0].block_type, "analog_in")
        self.assertEqual(provider.analog_in_calls[0].channel, 3)
        self.assertEqual(provider.analog_in_calls[0].device, "adc0")
        self.assertEqual(provider.analog_in_calls[0].options, {"gain": 2})

    def test_analog_out_writes_to_provider(self):
        provider = _FakeProvider()
        self.bd.runtime = _AttributeRuntime(provider)
        block = AnalogOut(
            channel=4, device="pwm0", io_options={"freq": 200}, bd=self.bd
        )

        block.start(self.simstate)
        block.step(0.0, [0.75])

        self.assertEqual(provider.analog_out_handle.writes, [0.75])
        self.assertEqual(len(provider.analog_out_calls), 1)
        self.assertEqual(provider.analog_out_calls[0].block_type, "analog_out")
        self.assertEqual(provider.analog_out_calls[0].channel, 4)
        self.assertEqual(provider.analog_out_calls[0].device, "pwm0")
        self.assertEqual(provider.analog_out_calls[0].options, {"freq": 200})

    def test_digital_in_and_out(self):
        provider = _FakeProvider()
        self.bd.runtime = _AttributeRuntime(provider)
        din = DigitalIn(channel=17, bd=self.bd)
        dout = DigitalOut(channel=18, bd=self.bd)

        din.start(self.simstate)
        dout.start(self.simstate)

        self.assertEqual(din.output(0.0, [], []), [True])
        dout.step(0.0, [False])

        self.assertEqual(provider.digital_out_handle.writes, [False])
        self.assertEqual(len(provider.digital_in_calls), 1)
        self.assertEqual(len(provider.digital_out_calls), 1)

    def test_mock_provider_zeros_and_discards(self):
        provider = MockIOProvider()
        self.bd.runtime = _AttributeRuntime(provider)

        ain = AnalogIn(channel=0, bd=self.bd)
        aout = AnalogOut(channel=1, bd=self.bd)
        din = DigitalIn(channel=2, bd=self.bd)
        dout = DigitalOut(channel=3, bd=self.bd)

        ain.start(self.simstate)
        aout.start(self.simstate)
        din.start(self.simstate)
        dout.start(self.simstate)

        self.assertEqual(ain.output(0.0, [], []), [0])
        self.assertEqual(din.output(0.0, [], []), [0])

        aout.step(0.0, [0.75])
        dout.step(0.0, [1])

        self.assertEqual(len(provider.analog_in_calls), 1)
        self.assertEqual(len(provider.analog_out_calls), 1)
        self.assertEqual(len(provider.digital_in_calls), 1)
        self.assertEqual(len(provider.digital_out_calls), 1)

    def test_provider_create_by_name(self):
        provider = IOProvider.create("mock")
        self.assertIsInstance(provider, MockIOProvider)

    def test_provider_create_by_alias(self):
        provider = IOProvider.create("registered-alias")
        self.assertIsInstance(provider, _RegisteredProvider)

    def test_provider_create_unknown_raises(self):
        with self.assertRaises(IOProviderError):
            IOProvider.create("definitely-unknown-provider")

    @unittest.skipUnless(platform.system() == "Linux", "Pi hardware tests run on Linux")
    def test_pi_hardware_placeholder(self):
        self.skipTest("hardware-in-the-loop Pi backend test belongs on the target Pi")


if __name__ == "__main__":
    unittest.main()
