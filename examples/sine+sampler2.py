#!/usr/bin/env python3

"""
Example with two ZOHs sampling a sine wave
Copyright (c) 2021- Peter Corke
"""

import bdsim
import time

sim = bdsim.BDSim()
bd = sim.blockdiagram()

clock1 = bd.clock(5, "Hz")
clock2 = bd.clock(10, "Hz")

# define the blocks

sine = bd.WAVEFORM("sine", freq=0.2, unit="Hz")
zoh1 = bd.ZOH(clock1)
zoh2 = bd.ZOH(clock2)

scope = bd.SCOPE(styles=[dict(color="k", linestyle="--"), dict(color="r", drawstyle="steps"), dict(color="b", drawstyle="steps")])

# connect the blocks
bd.connect(sine, zoh1, zoh2, scope[0])
bd.connect(zoh1, scope[1])
bd.connect(zoh2, scope[2])

bd.compile()  # check the diagram
bd.report()  # list all blocks and wires

print(clock1)
print(clock2)

out = sim.run(bd, 5)  # simulate for 5s

sim.done(bd, block=True)
