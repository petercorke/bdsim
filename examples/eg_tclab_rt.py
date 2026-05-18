#!/usr/bin/env python3
"""Example: TCLab temperature control with bdsim realtime I/O.

This diagram demonstrates:
- Serial I/O provider for TCLab hardware
- TOML-based device configuration
- Realtime feedback loop with safe shutdown
- Telemetry logging to UDP client

To run this example:
1. Connect a TCLab device via USB serial port
2. Edit bdsim.toml in the repo root — set the correct serial port
   under [devices.tclab0] (e.g. /dev/ttyACM0 on Linux,
   /dev/cu.usbmodem* on macOS)
3. Run: python examples/eg_tclab_rt.py

The telemetry client can visualize the temperatures in real-time:
   telemetry-client --listen 127.0.0.1:5001
"""

import os

from bdsim.realtime import BDRealTime

# bdsim.toml is searched automatically: CWD first, then ~/bdsim.toml.
# Place it in the repo root (or your home directory) and update the port.
rt = BDRealTime(io_provider="serial")

target_temperature = 40.0  # °C  (keep ≥15°C below the 55°C firmware alarm)
Kp = 5.0  # proportional gain
telemetry_endpoint = os.getenv("BDSIM_TELEMETRY", "127.0.0.1:5001")
max_heater = 75.0  # % (TCLab heaters are 0-100% but we limit to 75% for safety)

# Create block diagram
bd = rt.blockdiagram(name="TCLab Temperature Control")

clock = bd.clock(2, "Hz", name="main")  # Clock: sample at 2 Hz

t_ref = bd.CONSTANT(
    target_temperature, name="T_ref"
)  # Input: constant reference temperature

# Analog input: Read T1 temperature from TCLab
t1_block = bd.ANALOGIN(
    clock=clock,
    channel="t1",
    device="tclab0",
    name="T1",
)
# Analog output: Write Q1 command to TCLab
q1_block = bd.ANALOGOUT(
    clock=clock,
    channel="q1",
    device="tclab0",
    name="Q1",
)

# Telemetry: Send temperature and heater signals to UDP client
telemetry = bd.TELEMETRY(
    clock,
    nin=2,
    name="Telemetry",
    endpoint=telemetry_endpoint,
)

# controller components
error = bd.SUM("+-", name="Error")  # Error: reference - measured
gain = bd.GAIN(Kp, name="P")  # Proportional gain block
saturation = bd.CLIP(
    min=0.0, max=max_heater, name="Saturation"
)  # clamp heater command to valid range (0-70% for TCLab)

# Simple proportional controller: error = t_ref - t1
bd.connect(t_ref, error[0])
bd.connect(t1_block, error[1])
bd.connect(error, gain)  # Control signal: proportional gain * error
bd.connect(gain, saturation)
bd.connect(saturation, q1_block)
bd.connect(t1_block, telemetry[0])  # T1 temperature
bd.connect(saturation, telemetry[1])  # Heater command (Q1)

# Compile and run
bd.compile(verbose=True)
bd.report_summary()

print(f"Starting TCLab temperature control loop (10 Hz, 30 second duration)...")
print(f"Target temperature: {target_temperature}°C on T1")

result = rt.run(bd, tf=60.0, watch=["T1[0]", "Saturation[0]"], log_signals=True)
if "y" in result and result["y"].shape[1] >= 2:
    t1_start = result["y"][0, 0]
    t1_end = result["y"][-1, 0]
    print(f"T1: {t1_start:.2f}°C → {t1_end:.2f}°C  (Δ{t1_end - t1_start:+.2f}°C)")
    print(f"Final Q1 command: {result['y'][-1, 1]:.1f}%")
