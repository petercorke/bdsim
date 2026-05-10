#!/usr/bin/env python3

import bdsim

sim = bdsim.BDSim(graphics=False)  # create simulator
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
bd.connect(plant, scope[0])

# remove the direct connection from gain to plant and insert a ZOH in between
# bd.connect(gain, plant)
bd.connect(gain, zoh)
bd.connect(zoh, plant)

bd.compile()  # check the diagram
bd.report()
bd.report_summary()  # list all blocks and wires

out = sim.run(bd, 5, watch=[demand, sum, zoh])  # simulate for 5s
print(out)

