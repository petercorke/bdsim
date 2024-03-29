#!/usr/bin/env python3

import bdsim

sim = bdsim.BDSim(animation=True)  # create simulator
bd = sim.blockdiagram()  # create an empty block diagram

# define the clocks
clock1 = bd.clock(10, "Hz")

# define the blocks
demand = bd.STEP(T=1, name="demand")
sum = bd.SUM("+-")
gain = bd.GAIN(10)
plant = bd.LTI_SISO(0.5, [2, 1], name="plant")
scope = bd.SCOPE(styles=["k", "r--"])
zoh = bd.ZOH(clock=clock1)

# connect the blocks
bd.connect(demand, sum[0], scope[1])
bd.connect(plant, sum[1])
bd.connect(sum, gain)
# bd.connect(gain, plant)
bd.connect(gain, zoh)
bd.connect(zoh, plant)
bd.connect(plant, scope[0])


bd.compile()  # check the diagram
bd.report()
bd.report_summary()  # list all blocks and wires

out = sim.run(bd, watch=[demand, sum])  # simulate for 5s
# out = sim.run(bd, 5 watch=[plant,demand])  # simulate for 5s
print(out)

# sim.savefig(scope, 'scope0') # save scope figure as scope0.pdf
