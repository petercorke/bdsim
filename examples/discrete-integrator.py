#!/usr/bin/env python3

import bdsim
import time

sim = bdsim.BDSim(animation=False)
bd = sim.blockdiagram()

clock = bd.clock(50, 'Hz')

# define the blocks

step = bd.STEP(1)
integ = bd.DINTEGRATOR(x0=0, clock=clock)
scope = bd.SCOPE(stairs=True)

# connect the blocks
bd.connect(step, integ)
bd.connect(integ, scope)

bd.compile()   # check the diagram
bd.report()    # list all blocks and wires

print(clock)

out = sim.run(bd, 5)  # simulate for 5s
print(out)
sim.done(bd, block=True)