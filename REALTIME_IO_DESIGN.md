# Realtime I/O Design

This note records the current design direction for realtime input/output blocks.
It is intended as a stable reference for future implementation work.

## Goal

Support realtime I/O blocks whose concrete behavior depends on the operating
system, transport, and hardware backend, while preserving a stable block-diagram
API.

Examples of backend differences include:

- serial vs USB vs SPI vs GPIO
- macOS/Linux/Windows runtime differences
- Firmata vs LabJack vs Raspberry Pi GPIO vs custom DAQ devices

The design should avoid pushing those differences into user diagrams.

## Chosen Direction

Use a two-layer model:

1. Generic public I/O blocks in the normal block namespace.
2. Backend-specific provider implementations selected by the realtime runtime.

That means diagrams use stable logical block names such as:

- `ANALOGIN`
- `ANALOGOUT`
- `DIGITALIN`
- `DIGITALOUT`

while the runtime chooses the hardware-specific implementation.

## Why Not One Giant Switch?

A single block class with a large switch over every backend would:

- couple core blocks to many optional dependencies
- import hardware-specific code on machines that cannot support it
- make the block classes hard to test and maintain
- force all backend configuration into block constructors

This is the wrong abstraction boundary.

## Why Not Only Hardware-Specific Block Names?

Using only backend-branded block names such as `FIRMATA_ANALOGIN` or
`LABJACK_ANALOGIN` would leak hardware selection into the diagram itself.

That would make diagrams less portable and would turn the diagram API into a
catalog of devices rather than a model of signal flow.

## Filesystem Layout

The current preferred layout is flat files in `src/bdsim/blocks/`, not nested
folders for each I/O backend.

Recommended layout:

- `src/bdsim/blocks/io.py`
  Generic public I/O block classes.
- `src/bdsim/blocks/io_base.py`
  Shared provider interfaces, exceptions, and helper types.
- `src/bdsim/blocks/io_firmata.py`
  Firmata provider implementation.
- `src/bdsim/blocks/io_labjack.py`
  LabJack provider implementation.
- `src/bdsim/blocks/io_rpi_gpio.py`
  Raspberry Pi GPIO provider implementation.

### Why Flat Files?

The current block loader in `src/bdsim/run_sim.py` scans `*.py` files directly
inside a package's `blocks` directory. It does not recursively scan nested
subdirectories such as `blocks/io/firmata.py`.

A flat layout therefore:

- works with the existing loader
- avoids adding recursive discovery logic
- keeps backend variants easy to discover by filename

If recursive discovery is ever added later, this decision can be revisited, but
flat files are the simplest fit for the current codebase.

## Public API Layer

The public API lives in `src/bdsim/blocks/io.py`.

These classes should remain generic and hardware-agnostic. Their job is to:

- expose stable block names to users
- capture logical configuration such as channel and optional device name
- bind to a runtime-selected provider during `start()`
- delegate reads and writes to provider-supplied handles

They should not know about pyFirmata, GPIO libraries, USB device enumeration,
or OS-specific transport details.

## Provider Layer

The provider interface lives in `src/bdsim/blocks/io_base.py`.

Provider responsibilities:

- own hardware/OS-specific setup and teardown
- map logical block requests onto backend-specific channels or pins
- return lightweight read/write handles to blocks
- raise clear errors when a requested primitive is unsupported

The current base concepts are:

- `IOProvider`
- `IOBlockSpec`
- handle protocols for analog and digital input/output
- `MissingIOProviderError`
- `UnsupportedIOBlockError`

## Runtime Integration

The realtime runtime is expected to choose and expose the active provider.

The generic blocks currently look for one of these runtime hooks:

- `runtime.get_io_provider()`
- `runtime.io_provider`

This keeps block classes stable while the runtime API is finalized.

The long-term model is:

1. `BDRealTime` is created with an I/O backend choice and configuration.
2. `BDRealTime` constructs or receives a provider object.
3. Generic blocks bind to that provider during `start()`.
4. Reads and writes go through backend handles.

Implemented direction:

```python
rt = BDRealTime(io_provider="firmata", io_provider_kwargs={"port": "/dev/ttyUSB0"})
bd = rt.blockdiagram()
u = bd.ANALOGIN(channel=0)
y = bd.DIGITALOUT(channel=13)
```

The diagram stays generic. The runtime owns backend selection.

## Provider Registration and Lookup (Implemented)

Provider resolution is now string-based and class-based:

- each provider subclass sets a `name` (and optional `aliases`)
- `IOProvider.__init_subclass__` auto-registers subclasses into a registry
- `IOProvider.create("name", **kwargs)` resolves and constructs providers

This allows concise runtime creation such as:

```python
rt = BDRealTime(io_provider="mock")
```

without hardwiring provider class imports at each call site.

Built-in provider modules are imported lazily by the lookup path so provider
class registration occurs before name resolution.

## Mock Provider Semantics (Implemented)

The desktop/mock provider behavior is intentionally quiet and deterministic:

- input handles return `0`
- output handles silently discard values

This supports development and scheduler testing on non-hardware hosts.

## Runtime Stats Output (Implemented)

`BDRealTime.run()` emits end-of-run realtime stats to stdout when runtime
options are not quiet. The output includes:

- evaluation count and timing summary
- overrun count and max queue depth
- per-clock fired/processed/dropped/lateness summary

## Host-Paced vs Externally Paced Clocks

The current realtime runner assumes that the host owns time. Each logical clock
in the block diagram is mapped to a host-side periodic timer callback, and each
timer callback enqueues a tick event for the worker thread.

That model is appropriate for ordinary host-paced realtime execution, but it is
not the right ownership model for systems such as `arduIO` where the remote I/O
server performs the sampling on its own schedule and then transmits a completed
sample frame back to the host.

For that class of backend, the completion of a read is not just I/O. It is the
sample boundary.

This implies two distinct clock modes:

- host-paced clock: the host timer causes inputs to be read
- externally paced clock: a completed remote sample frame causes the clock tick

The logical `Clock` object should remain in the model in both cases.

### Why Keep the `Clock` Object?

Even for externally paced I/O, the logical clock still has useful semantic
meaning:

- it defines a sampled-time domain
- it owns the set of clocked blocks
- it declares the nominal sample period `T`
- it remains the natural place for stats and logging

What changes is not the existence of the clock, but who schedules it.

For externally paced backends, the clock should delegate scheduling to the
backend rather than to the host timer backend.

## `arduIO`-Style Sampled I/O Domains

`arduIO` is not just a collection of pin-level reads and writes. It combines:

- a sampling clock on the remote device
- a transport channel
- a coherent batch of sampled inputs
- a batched output update path
- timing metadata such as sequence number and lateness

This has important consequences for the provider design.

Simple per-port I/O handles are not enough on their own. A backend like
`arduIO` needs a higher-level sampled-stream capability.

### Recommended Model

Treat `arduIO` as a clocked I/O domain.

In this model:

1. The runtime configures the remote input and output tables.
2. The remote device runs periodic sampling on its own schedule.
3. A host reader receives one complete sample frame.
4. That completed frame becomes the trigger for one logical clock tick.
5. The worker thread evaluates the diagram once for that sample.
6. Output values are collected and sent back as one batched update.

This inverts the normal host-paced relationship:

- host-paced: the clock tick causes input acquisition
- `arduIO`-paced: input acquisition completion causes the clock tick

That inversion is desirable because it preserves the timing integrity provided
by the remote sampler.

## Snapshot Semantics for Generic Input Blocks

For an externally paced sampled domain, generic input blocks must not perform
their own transport reads.

Instead, all generic input blocks in that domain should read from a cached input
snapshot associated with the current sample frame.

This ensures that:

- all inputs correspond to the same sample instant
- there is no host-side skew between different input blocks
- one sample frame leads to exactly one model evaluation

Similarly, generic output blocks should not immediately write to the transport on
every block `step()`. They should stage output values into the provider, and the
provider should flush the full output set once per completed evaluation.

This preserves coherent batched I/O semantics.

## Event Structure for Externally Paced Domains

The current realtime runner uses a timer-oriented tick event carrying host timer
metadata. That is sufficient for host timers, but not for backends such as
`arduIO`.

An externally paced tick event should carry richer information, including:

- clock or domain identifier
- sequence number
- nominal sample time
- timing diagnostics such as remote lateness
- coherent input snapshot for that sample

For `arduIO`, the sequence number is important for detecting missed samples.

## Time Base for `arduIO`

For an externally paced backend, simulation time should not be derived from the
host receipt time of the incoming frame.

Instead, the preferred model time is the nominal sample time implied by the
remote sequence number and sample period:

$$
t_k = kT
$$

where:

- `k` is the remote sample sequence number
- `T` is the configured remote sample period

Timing diagnostics such as `late` are still valuable, but they should be kept
as metadata and statistics rather than redefining model time.

## Implications for Provider Types

The existing `IOProvider` abstraction is still useful for ordinary per-port
I/O backends.

For externally paced systems, an additional capability is needed on top of the
basic provider model. Conceptually this is a sampled-stream provider, responsible
for:

- starting and stopping remote sampling
- receiving and parsing completed sample frames
- storing the latest coherent input snapshot
- detecting missed samples
- staging and flushing batched outputs
- generating tick events for the logical sampled-time domain

This capability may be expressed either as:

- a subclass of `IOProvider`, or
- a sibling abstraction used only by `BDRealTime`

Either choice is acceptable so long as the block-level API remains generic.

## Integration Direction for `BDRealTime`

`BDRealTime` should evolve from assuming every clock is driven by a host timer
to supporting a more general tick source concept.

Useful categories of tick source are:

- host periodic timer backend
- external sampled-stream source

Both should ultimately enqueue the same logical kind of work item to the worker
thread: one completed sample event for one sampled-time domain.

This allows most of the worker-side evaluation logic to remain shared.

Current implementation note:

- host-paced clocks are discovered from `bd.clocklist` in `BDRealTime.run()`
- one periodic timer is started per clock
- each timer firing enqueues a tick event processed by a single worker thread

For multi-clock scaling, compile-time schedule generation and runtime execution
should evolve toward per-clock-domain sample/compute/commit phases.

## Practical Interpretation for `arduIO`

The recommended interpretation is:

- keep a logical `CLOCK` in the model
- allow that clock to be marked as externally paced
- let the `arduIO` backend delegate scheduling for that clock
- let incoming sample completion trigger the tick

That preserves the conceptual role of the clock while allowing the backend to
own the actual timing.

## Current Skeleton Files

The following files now exist as a starting point:

- `src/bdsim/blocks/io.py`
- `src/bdsim/blocks/io_base.py`
- `src/bdsim/blocks/io_firmata.py`

Current status:

- generic block names exist
- a provider base class exists
- a Firmata provider skeleton exists
- `src/bdsim/blocks/__init__.py` exports the generic I/O blocks

Not yet implemented:

- `BDRealTime` wiring for provider selection and lifetime management
- actual Firmata session setup
- pin/channel mapping rules
- tests for provider binding and block behavior
- externally paced sampled-domain support for backends such as `arduIO`

## Discovery and Caching Notes

An important architectural detail is that block discovery already supports
external block packages through package names and `BDSIMPATH`, but the current
block library is cached globally in `BDSim._blocklibrary`.

That matters if future realtime configurations want different block sets or
backend-specific packages loaded per runtime instance.

If runtime-selected I/O packages become part of the supported design, the block
library cache may need to become:

- keyed by discovery inputs, or
- refreshable on demand

so that block availability is not accidentally frozen by the first created
runtime.

## Naming Guidance

Keep names boring and explicit.

Recommended conventions:

- generic blocks: `AnalogIn`, `AnalogOut`, `DigitalIn`, `DigitalOut`
- provider base: `IOProvider`
- backend providers: `FirmataProvider`, `LabJackProvider`, `RPiGPIOProvider`
- backend modules: `io_firmata.py`, `io_labjack.py`, `io_rpi_gpio.py`

Avoid backend-specific public block names unless there is a strong reason to
expose a capability that cannot be expressed generically.

## Next Implementation Steps

1. Extend `BDRealTime` to accept and expose an I/O provider.
2. Generalize the realtime runner so a sampled-time domain can be driven by a
  host timer or by an external sample stream.
3. Implement one concrete provider end-to-end, most likely Firmata.
4. Add a sampled-stream backend design for `arduIO`, including snapshot-based
  inputs and batched outputs.
5. Add focused tests that verify generic I/O blocks bind through the provider
  interface and that an externally paced sample frame triggers one logical
  clock tick.
6. Decide whether backend-specific packages should be loaded through the normal
  block loader, through runtime registration, or both.

## Summary

The intended architecture is:

- generic block names in diagrams
- one flat Python file per backend implementation
- backend selection owned by the realtime runtime
- hardware-specific details isolated behind provider objects
- support for both host-paced and externally paced sampled-time domains

This keeps the diagram API stable, matches the current loader constraints, and
leaves room for multiple realtime I/O backends without turning core blocks into
backend-specific switch statements.

---

## Current Status (as of 2026-05-02)

### Files Created

| File | Purpose |
|------|---------|
| `src/bdsim/blocks/io_base.py` | `IOProvider` base class, handle Protocols, `IOBlockSpec`, `get_runtime_io_provider()`, error types |
| `src/bdsim/blocks/io.py` | Four public generic block classes: `AnalogIn`, `AnalogOut`, `DigitalIn`, `DigitalOut` |
| `src/bdsim/blocks/io_firmata.py` | Firmata provider skeleton (pin mapping not yet implemented) |
| `src/bdsim/blocks/io_arduio.py` | arduIO provider prototype (frame-driven sampled I/O, no serial reader yet) |
| `src/bdsim/blocks/__init__.py` | Extended with `from .io import *` |

### `io_arduio.py` Module Structure

Key classes in the arduIO prototype:

- `ArduIOTransport` — Protocol: `clear`, `input`, `output`, `start`, `stop`, `send`.
  Works with a real serial client or a test double.
- `ArduIOFrame` — frozen dataclass: `sequence`, `late_ms`, `sample_time` (= sequence × period),
  `inputs` dict mapping path → float, `raw_line`.
- `ArduIOSampledDomain` — dataclass per logical domain: `period_s`, `input_paths`,
  `output_paths`, `last_frame`, `expected_sequence`.
- `_ArduIOInputHandle.read()` — reads from the latest frame snapshot, not from the transport.
- `_ArduIOOutputHandle.write()` — stages value into a pending dict; does not write to transport.
- `ArduIOProvider(IOProvider)` — central class:
  - `ingest_frame(sequence, late_ms, values)` — validates sequence, builds `ArduIOFrame`,
    stores snapshot, fires tick callback.
  - `flush_outputs()` — batches all staged outputs and calls `transport.send()` once.
  - `set_tick_callback(cb)` — hook for `BDRealTime` to register a function called on each frame.
  - `open_analog_input/output` and `open_digital_input/output` — map to arduIO path resolution.

### Pending Work

1. **`BDRealTime` wiring** — Add `io_provider` attribute to `BDRealTime`.  Call
   `provider.set_tick_callback(lambda frame: tick_queue.put(…))` before starting sampling.
   Call `provider.flush_outputs()` after each diagram evaluation in the worker loop.

2. **Serial reader thread** — Background thread reads lines from the arduIO serial port,
   parses the frame format (`*seq,late|v1|v2|...\n`), and calls
   `provider.ingest_frame(sequence, late_ms, values)`.

3. **Firmata concrete implementation** — Fill in `FirmataProvider.connect()` with
   `Arduino(port)` + `Iterator` setup, and `_pin()` with pyFirmata `board.get_pin()` mapping.

4. **Tick-source generalisation** — Extend `BDRealTime` so a sampled-time domain can be
   driven by an `IOProvider`'s external frame callback rather than a host periodic timer.

5. **Tests** — Unit tests that exercise `ArduIOProvider.ingest_frame()`, snapshot reads via
   `_ArduIOInputHandle`, and `flush_outputs()` without real hardware (mock transport).
   Integration test confirming generic I/O blocks bind through the provider interface.