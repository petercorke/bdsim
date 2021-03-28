#!/usr/bin/env python3

import bdsim

sim = bdsim.BDSim(animation=True)  # create simulator
print(sim)
bd = sim.blockdiagram()  # create an empty block diagram

# define the blocks
demand = bd.STEP(T=1, pos=(0,0), name='demand')
sum = bd.SUM('+-', pos=(1,0))
gain = bd.GAIN(10, pos=(1.5,0))
plant = bd.LTI_SISO(0.5, [2, 1], name='plant', pos=(3,0))
scope = bd.SCOPE(styles=['k', 'r--'], pos=(4,0))

# connect the blocks
bd.connect(demand, sum[0], scope[1])
bd.connect(plant, sum[1])
bd.connect(sum, gain)
bd.connect(gain, plant)
bd.connect(plant, scope[0])

bd.compile()   # check the diagram
bd.report()    # list all blocks and wires

out = sim.run(bd, 5, watch=[plant,demand])  # simulate for 5s

sim.savefig(scope, 'scope0')
sim.done(bd, block=True)

print(out)
