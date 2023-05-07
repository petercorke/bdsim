#!/usr/bin/env python3

"""
Example with one ZOH sampling a sine wave
Copyright (c) 2021- Peter Corke
"""

import bdsim
import time

sim = bdsim.BDSim()
bd = sim.blockdiagram()

clock = bd.clock(5, "Hz")

# define the blocks

sine = bd.WAVEFORM("sine", freq=0.2, unit="Hz")
zoh = bd.ZOH(clock)

scope = bd.SCOPE(styles=[dict(color="b"), dict(color="r", drawstyle="steps")])

# connect the blocks
bd.connect(sine, zoh, scope[0])
bd.connect(zoh, scope[1])

bd.compile()  # check the diagram
bd.report()  # list all blocks and wires

print(clock)

out = sim.run(bd, 5)  # simulate for 5s

sim.done(bd, block=True)
