"""Prototype arduIO backend for realtime I/O blocks.

This module models the design discussed in ``REALTIME_IO_DESIGN.md``:

- the Arduino-side server owns the sample clock
- each completed sample frame is a sampled-time boundary
- generic input blocks read from a cached snapshot, not from the transport
- generic output blocks stage values which are flushed in one batch

The implementation here is intentionally a prototype.  It defines the data
structures and provider-facing behavior needed for a future `BDRealTime`
integration without yet wiring in a concrete runtime or serial transport.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Callable, Iterable, Protocol

from .io_base import IOBlockSpec, IOProvider, IOProviderError


class ArduIOProtocolError(IOProviderError):
    """Raised when an arduIO frame or configuration is invalid."""


class ArduIOSampleLossError(IOProviderError):
    """Raised when a gap in the remote sample sequence is detected."""


class ArduIOTransport(Protocol):
    """Minimal transport contract for an arduIO client session."""

    def clear(self) -> None:
        """Clear any remote input/output tables."""

    def input(self, path: str) -> Any:
        """Declare one remote input path and return a transport proxy."""

    def output(self, path: str) -> Any:
        """Declare one remote output path and return a transport proxy."""

    def start(self, period_ms: int) -> None:
        """Start remote periodic sampling."""

    def stop(self) -> None:
        """Stop remote periodic sampling."""

    def send(self) -> None:
        """Flush staged outputs to the remote server."""


@dataclass(frozen=True)
class ArduIOFrame:
    """One completed sample frame from the remote arduIO server."""

    sequence: int
    late_ms: int
    sample_time: float
    inputs: dict[str, Any]
    raw_line: str | None = None


@dataclass
class ArduIOSampledDomain:
    """Runtime state for one arduIO-paced sampled-time domain."""

    name: str
    period_s: float
    input_paths: list[str] = field(default_factory=list)
    output_paths: list[str] = field(default_factory=list)
    last_frame: ArduIOFrame | None = None
    expected_sequence: int | None = None


class _ArduIOInputHandle:
    """Read a value from the most recent coherent sample snapshot."""

    def __init__(self, provider: ArduIOProvider, path: str) -> None:
        self._provider = provider
        self._path = path

    def read(self) -> Any:
        frame = self._provider.latest_frame()
        try:
            return frame.inputs[self._path]
        except KeyError as err:
            raise ArduIOProtocolError(
                f"current arduIO frame does not contain input {self._path}"
            ) from err


class _ArduIOOutputHandle:
    """Stage an output value for batch transmission after evaluation."""

    def __init__(self, provider: ArduIOProvider, path: str) -> None:
        self._provider = provider
        self._path = path

    def write(self, value: Any) -> None:
        self._provider.stage_output(self._path, value)


class ArduIOProvider(IOProvider):
    """Prototype provider for an externally paced arduIO sampled domain.

    This provider differs from simple pin-level providers in one important way:
    reads are driven by completed remote sample frames rather than by host-side
    polling.  Inputs therefore come from a cached snapshot and outputs are
    staged for one batch flush per sample.
    """

    name = "arduio"

    def __init__(
        self,
        transport: ArduIOTransport | None = None,
        *,
        period_s: float,
        domain_name: str = "arduio.0",
    ) -> None:
        self.transport = transport
        self.domain = ArduIOSampledDomain(name=domain_name, period_s=period_s)
        self._input_proxies: dict[str, Any] = {}
        self._output_proxies: dict[str, Any] = {}
        self._staged_outputs: dict[str, Any] = {}
        self._tick_callback: Callable[[ArduIOFrame], None] | None = None
        self._lock = Lock()

    def set_tick_callback(self, callback: Callable[[ArduIOFrame], None]) -> None:
        """Register a callback to be invoked for each completed sample frame."""

        self._tick_callback = callback

    def connect(self) -> None:
        """Connect and configure the transport.

        A future implementation can call the concrete arduIO Python client API
        here, clear remote tables, and register all declared input/output paths.
        """

    def start_sampling(self) -> None:
        """Start periodic remote sampling.

        The sample clock is owned by the remote server.  A future runtime layer
        should call this before entering its worker loop.
        """

        if self.transport is not None:
            self.transport.start(period_ms=round(self.domain.period_s * 1000.0))

    def stop_sampling(self) -> None:
        """Stop periodic remote sampling."""

        if self.transport is not None:
            self.transport.stop()

    def latest_frame(self) -> ArduIOFrame:
        """Return the latest coherent input snapshot."""

        with self._lock:
            frame = self.domain.last_frame
        if frame is None:
            raise ArduIOProtocolError("no arduIO sample frame has been received yet")
        return frame

    def _path_from_spec(self, spec: IOBlockSpec, *, direction: str) -> str:
        """Resolve a generic block spec to an arduIO path string.

        The current prototype accepts either:

        - a full arduIO path string in ``channel`` or ``device``
        - a backend-specific override in ``options['path']``
        """

        if spec.options is not None:
            path = spec.options.get("path")
            if isinstance(path, str):
                return path

        for candidate in (spec.device, spec.channel):
            if isinstance(candidate, str) and candidate.startswith("/"):
                return candidate

        raise ArduIOProtocolError(
            f"{direction} spec {spec!r} does not define an arduIO path"
        )

    def _register_input(self, path: str) -> None:
        if path in self._input_proxies:
            return
        self.domain.input_paths.append(path)
        if self.transport is not None:
            self._input_proxies[path] = self.transport.input(path)

    def _register_output(self, path: str) -> None:
        if path in self._output_proxies:
            return
        self.domain.output_paths.append(path)
        if self.transport is not None:
            self._output_proxies[path] = self.transport.output(path)

    def open_analog_input(self, spec: IOBlockSpec) -> _ArduIOInputHandle:
        path = self._path_from_spec(spec, direction="input")
        self._register_input(path)
        return _ArduIOInputHandle(self, path)

    def open_analog_output(self, spec: IOBlockSpec) -> _ArduIOOutputHandle:
        path = self._path_from_spec(spec, direction="output")
        self._register_output(path)
        return _ArduIOOutputHandle(self, path)

    def open_digital_input(self, spec: IOBlockSpec) -> _ArduIOInputHandle:
        path = self._path_from_spec(spec, direction="input")
        self._register_input(path)
        return _ArduIOInputHandle(self, path)

    def open_digital_output(self, spec: IOBlockSpec) -> _ArduIOOutputHandle:
        path = self._path_from_spec(spec, direction="output")
        self._register_output(path)
        return _ArduIOOutputHandle(self, path)

    def stage_output(self, path: str, value: Any) -> None:
        """Stage one output value for batch transmission."""

        with self._lock:
            self._staged_outputs[path] = value

    def flush_outputs(self) -> dict[str, Any]:
        """Flush all staged outputs as one batch.

        The returned mapping is useful for testing and for future runtime-side
        logging.  A future concrete implementation can also write these values
        through the transport proxies and call ``transport.send()``.
        """

        with self._lock:
            pending = dict(self._staged_outputs)
            self._staged_outputs.clear()

        if self.transport is not None:
            for path, value in pending.items():
                proxy = self._output_proxies.get(path)
                if proxy is not None and hasattr(proxy, "set"):
                    proxy.set(value)
            if pending:
                self.transport.send()

        return pending

    def ingest_frame(
        self,
        *,
        sequence: int,
        late_ms: int,
        values: Iterable[Any],
        raw_line: str | None = None,
    ) -> ArduIOFrame:
        """Convert one completed sample into the coherent current snapshot.

        `values` must be in the same order as ``domain.input_paths``.
        A future serial reader can call this after parsing one line from the
        remote arduIO server.
        """

        paths = list(self.domain.input_paths)
        payload = list(values)
        if len(paths) != len(payload):
            raise ArduIOProtocolError(
                f"sample has {len(payload)} values for {len(paths)} declared inputs"
            )

        expected = self.domain.expected_sequence
        if expected is not None and sequence != expected:
            raise ArduIOSampleLossError(
                f"expected arduIO sample {expected}, received {sequence}"
            )

        frame = ArduIOFrame(
            sequence=sequence,
            late_ms=late_ms,
            sample_time=sequence * self.domain.period_s,
            inputs=dict(zip(paths, payload)),
            raw_line=raw_line,
        )

        with self._lock:
            self.domain.last_frame = frame
            self.domain.expected_sequence = sequence + 1

        if self._tick_callback is not None:
            self._tick_callback(frame)

        return frame

    def close(self) -> None:
        self.stop_sampling()
