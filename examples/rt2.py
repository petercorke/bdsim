#!/usr/bin/env python3

"""
Real-time system, waveform generator driving an LED
Copyright (c) 2026- Peter Corke
"""

import platform

from bdsim.realtime import BDRealTime


def _select_io_provider() -> str:
    machine = platform.machine().lower()
    if platform.system() == "Linux" and machine in {
        "arm64",
        "armv6l",
        "armv7l",
        "aarch64",
    }:
        return "rpi"
    return "mock"


rt = BDRealTime(
    io_provider=_select_io_provider(),
    toolboxes=False,
)  # create real-time framework

bd = rt.blockdiagram()  # create an empty block diagram

# define the blocks
clock = bd.clock(50, "Hz", name="clock")
reference = bd.WAVEFORM(
    wave="square", freq=0.25, unit="Hz", min=0.25, max=0.75, name="y*"
)

u = bd.PWMOUT(
    clock, channel=18, freq=10_000, name="u"
)  # BCM GPIO 18 (physical pin 12)  # plant input

y = bd.ANALOGIN(clock, channel=1, name="y")  # plant output
yref = bd.ANALOGIN(clock, channel=0, name="yref")  # reference input for telemetry
telemetry = bd.TELEMETRY(
    clock,
    nin=3,
    name="telemetry",
    schema_period=0,
    decimation=1,
)

# connect the blocks
bd.connect(reference, u, telemetry[0])
bd.connect(y, telemetry[1])
bd.connect(yref, telemetry[2])

bd.compile()  # check the diagram
bd.report_summary()
print(f"telemetry destination: {telemetry.host}:{telemetry.port}")


out = rt.run(bd, tf=30)  # simulate for 20s

print(out)
