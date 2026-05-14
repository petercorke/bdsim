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
demand = bd.WAVEFORM(wave="triangle", freq=1, unit="Hz", min=0, max=1, name="demand")
led = bd.PWMOUT(
    clock, channel=18, name="LED"
)  # BCM GPIO 18 (physical pin 12)  # type: ignore[attr-defined]

# connect the blocks
bd.connect(demand, led)

bd.compile()  # check the diagram

bd.report_summary()

out = rt.run(bd, tf=20, log_gc=True)  # simulate for 20s
print(out)
stats = out.stats
print(stats)
if "gc" in stats:
    print("gc:", stats["gc"])
# print(
#     f"eval_count={stats.eval_count} "
#     f"overrun_count={stats.overrun_count} "
#     f"queue_depth_max={stats.queue_depth_max}"
# )
# for clock_name, clock_stats in stats.by_clock.items():
#     print(
#         f"{clock_name}: fired={clock_stats['fired']} "
#         f"processed={clock_stats['processed']} "
#         f"dropped={clock_stats['dropped']} "
#         f"lateness_max_ns={clock_stats['lateness_max_ns']}"
#     )
