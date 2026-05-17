#!/usr/bin/env python3

"""
Example of continuous-time system expressed without factory blocks
Copyright (c) 2021- Peter Corke
"""

import bdsim

sim = bdsim.BDSim(load=False, animation=False)  # create simulator
bd = sim.blockdiagram()  # create an empty block diagram

# define the blocks, using explicit block types and constructor arguments rather than factory methods
from bdsim.blocks import Sum, Gain, Scope, LTI_SISO, Step

demand = Step(T=1, name="demand", bd=bd)
sum = Sum("+-", bd=bd)
gain = Gain(10, bd=bd)
plant = LTI_SISO(0.5, [2, 1], name="plant", bd=bd)
scope = Scope(styles=["k", "r--"], loc="lower right", bd=bd)

# connect the blocks
bd.connect(demand, sum[0], scope[1])
bd.connect(plant, sum[1])
bd.connect(sum, gain)
bd.connect(gain, plant)
bd.connect(plant, scope[0])

bd.compile()  # check the diagram
bd.report()

out = sim.run(bd, T=5, watch=[demand, sum])  # simulate for 5s
print(out)
