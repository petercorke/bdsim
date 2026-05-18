#!/usr/bin/env python3

"""
Real-time system, waveform generator driving a second-order filter
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
    clock, channel=18, freq=20_000, name="u"
)  # BCM GPIO 18 (physical pin 12)  # plant input

y = bd.ANALOGIN(clock, channel=1, name="y")  # plant output
yref = bd.ANALOGIN(clock, channel=0, name="yref")  # reference input for telemetry
clipper = bd.CLIP(min=0, max=1, name="u_clipped")
telemetry = bd.TELEMETRY(
    clock,
    nin=4,
    name="telemetry",
    schema_period=0,
    decimation=1,
)

control = bd.PID_S(clock, P=5, D=0.1, I=2, alpha=0.2, structure="parallel", name="PID")

# connect the blocks
bd.connect(reference, control[1], telemetry[0])
bd.connect(y, control[0], telemetry[1])
bd.connect(control, clipper)
bd.connect(clipper, u)
bd.connect(clipper, telemetry[2])
bd.connect(
    "PID/I", telemetry[3]
)  # utilize late binding to monitor output of integrator term
# bd.connect(control.subsystem.blocknames["I"], telemetry[2])  # connect the I term to telemetry

bd.compile(verbose=True)  # check the diagram
bd.report_summary()
print(f"telemetry destination: {telemetry.host}:{telemetry.port}")


out = rt.run(bd, tf=40, watch=[y, yref, control, "PID/I[0]"], log_signals=True, log_clock_state=True)  # simulate

print(out)
