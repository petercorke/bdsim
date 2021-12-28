#!/usr/bin/env python3

import bdsim

sim = bdsim.BDSim()  # create simulator
bd = sim.blockdiagram()  # create an empty block diagram

sim.blocks()

# define the blocks
demand = bd.STEP(T=1, name='demand')
sum = bd.SUM('+-')
gain = bd.GAIN(10)
plant = bd.LTI_SISO(0.5, [2, 1], name='plant')
scope = bd.SCOPE(styles=['k', 'r--'], movie='eg1.mp4')

# connect the blocks
bd.connect(demand, sum[0], scope[1])
bd.connect(plant, sum[1])
bd.connect(sum, gain)
bd.connect(gain, plant)
bd.connect(plant, scope[0])

bd.compile()   # check the diagram
bd.report()    # list all blocks and wires

out = sim.run(bd, 5)  # simulate for 5s
# out = sim.run(bd, 5 watch=[plant,demand])  # simulate for 5s
print(out)

# sim.savefig(scope, 'scope0') # save scope figure as scope0.pdf
sim.done(bd, block=True)  # keep figures open on screen
