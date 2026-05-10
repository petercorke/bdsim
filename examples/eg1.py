#!/usr/bin/env python3

"""
Example of continuous-time system
Copyright (c) 2021- Peter Corke
"""

import bdsim

sim = bdsim.BDSim(animation=False)  # create simulator

bd = sim.blockdiagram()  # create an empty block diagram

# define the blocks
demand = bd.STEP(T=1, name="demand")
sum = bd.SUM("+-")
gain = bd.GAIN(10)
plant = bd.LTI_SISO(0.5, [2, 1], name="plant")
scope = bd.SCOPE(styles=["k", "r--"], loc="lower right")

# connect the blocks
bd.connect(demand, sum[0], scope[1])
bd.connect(plant, sum[1])
bd.connect(sum, gain)
bd.connect(gain, plant)
bd.connect(plant, scope[0])

bd.compile()  # check the diagram
bd.report_summary()

out = sim.run(bd, T=5, watch=[demand, sum])  # simulate for 5s
print(out)
