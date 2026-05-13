#!/usr/bin/env python3

"""
Real-time system, waveform generator driving an LED
Copyright (c) 2026- Peter Corke
"""

import bdsim
import platform

rt = bdsim.BDRealTime(
    io_provider="mock" if platform.system() != "Linux" else None,
)  # create real-time framework

bd = rt.blockdiagram()  # create an empty block diagram

# define the blocks
clock = bd.clock(50, "Hz", name="clock")
demand = bd.WAVEFORM(wave="triangle", freq=1, unit="Hz", name="demand")
led = bd.PWMOUT(clock, channel="led", name="LED")  # type: ignore[attr-defined]

# connect the blocks
bd.connect(demand, led)

bd.compile()  # check the diagram
bd.report_summary()

out = rt.run(bd, tf=20)  # simulate for 20s
print(out)
# stats = out.stats
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
