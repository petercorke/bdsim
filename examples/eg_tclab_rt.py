#!/usr/bin/env python3
"""Example: TCLab temperature control with bdsim realtime I/O.

This diagram demonstrates:
- Serial I/O provider for TCLab hardware
- TOML-based device configuration
- Realtime feedback loop with safe shutdown
- Telemetry logging to UDP client

To run this example:
1. Connect a TCLab device via USB serial port
2. Update bdsim.toml with your serial port (e.g., /dev/ttyACM0)
3. Run: python examples/eg_tclab_rt.py

The telemetry client can visualize the temperatures in real-time:
   telemetry-client --listen 0.0.0.0:5001
"""

import os

from bdsim.realtime import BDRealTime

# Create realtime runner with serial I/O provider
# Load device config from bdsim.toml (or environment)
rt = BDRealTime(
    io_provider="serial",
    io_provider_kwargs={"config_path": "bdsim.toml"},
)

# Create block diagram
bd = rt.blockdiagram(name="TCLab Temperature Control")

# Input: constant reference temperature (set to 35°C for T1)
t_ref = bd.CONSTANT(value=35.0, name="T_ref")

# Clock: sample at 10 Hz
clock = bd.CLOCK(name="main", T=0.1)

# Analog input: Read T1 temperature from TCLab
t1_block = bd.ANALOGIN(
    clock=clock,
    channel="t1",
    device="tclab0",
    name="T1",
)

# Simple proportional controller: error = t_ref - t1
error = bd.SUM("+-", name="Error")
bd.connect(t_ref[0], error[0])
bd.connect(t1_block[0], error[1])

# Proportional gain (Kp = 0.5)
gain = bd.GAIN(value=0.5, name="Kp")
bd.connect(error[0], gain[0])

# Clamp output to valid heater range (0-100%)
saturation = bd.SATURATION(lower=0.0, upper=100.0, name="Saturation")
bd.connect(gain[0], saturation[0])

# Analog output: Write Q1 command to TCLab
q1_block = bd.ANALOGOUT(
    clock=clock,
    channel="q1",
    device="tclab0",
    name="Q1",
)
bd.connect(saturation[0], q1_block[0])

# Telemetry: Send temperature and heater signals to UDP client
# (Requires TELEMETRY block; optional)
try:
    telemetry_endpoint = os.getenv("BDSIM_TELEMETRY", "127.0.0.1:5001")
    telemetry = bd.TELEMETRY(
        clock,
        [t1_block[0], q1_block[0]],
        name="Telemetry",
        endpoint=telemetry_endpoint,
    )
except Exception:
    pass  # TELEMETRY optional if not available

# Compile and run
bd.compile()
print(f"Starting TCLab temperature control loop (10 Hz, 30 second duration)...")
print(f"Target temperature: 35°C on T1")
print(
    f"Serial port: {rt.io_config.get_device('tclab0').port if hasattr(rt, 'io_config') else '/dev/ttyACM0'}"
)
print()

try:
    result = rt.run(bd, tf=30.0, watch=["T1[0]", "Q1[0]"], log_signals=True)
    print("\n<<< Simulation completed successfully")
    print(f"Final T1 value: {result['y0'][-1]:.2f}°C")
    print(f"Final Q1 value: {result['y1'][-1]:.1f}%")
except KeyboardInterrupt:
    print("\n<<< Interrupted by user")
except Exception as e:
    print(f"\n<<< Error: {e}")
    raise
