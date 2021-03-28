#!/usr/bin/env python3

import bdsim
import time

sim = bdsim.BDSim()
bd = sim.blockdiagram()

clock = bd.clock(2, 'Hz')

# define the blocks

sine = bd.WAVEFORM('sine', freq=0.2, unit='Hz')
zoh = bd.ZOH(clock)

scope = bd.SCOPE()

# connect the blocks
bd.connect(sine, zoh)
bd.connect(zoh, scope)

bd.compile()   # check the diagram
bd.report()    # list all blocks and wires

print(clock)

out = sim.run(bd, 5)  # simulate for 5s

sim.done(bd, block=True)
