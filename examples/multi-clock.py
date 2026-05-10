#!/usr/bin/env python3

"""
Discrete-time system with two clocks: sine wave driving two ZOH blocks
Copyright (c) 2021- Peter Corke
"""

import bdsim
import time

sim = bdsim.BDSim()
bd = sim.blockdiagram()

clock1 = bd.clock(2, "Hz")
clock2 = bd.clock(3, "Hz")

# define the blocks

sine = bd.WAVEFORM("sine", freq=0.2, unit="Hz")
zoh1 = bd.ZOH(clock1)
zoh2 = bd.ZOH(clock2)

y = 0.5 * (zoh1 + zoh2)

scope = bd.SCOPE(styles=[dict(color="b"), dict(color="r", drawstyle="steps")])

# connect the blocks
bd.connect(sine, zoh1, zoh2, scope[0])
bd.connect(y, scope[1])

bd.compile()  # check the diagram
bd.report()  # list all blocks and wires
bd.report_schedule()  # list all blocks and wires in execution order

print(clock1)
print(clock2)
out = sim.run(bd, 5, block=True)  # simulate for 5s and hold graphics

print(out)
