#!/usr/bin/env python
"""
System of eg1.py with PI controller
Copyright (c) 2021- Peter Corke
"""

import bdsim

sim = bdsim.BDSim(animation=True)  # create simulator
bd = sim.blockdiagram()  # create an empty block diagram

# define the blocks
demand = bd.STEP(T=1, name="demand")
plant = bd.LTI_SISO(0.5, [2, 1], name="plant")
controller = bd.PID(P=10, D=0, I=3, name="PID")  # inputs are: plant, reference
scope = bd.SCOPE(styles=["k", "r--"], loc="lower right")

# connect the blocks
bd.connect(demand, controller[1], scope[0])
bd.connect(controller, plant)
bd.connect(plant, controller[0], scope[1])

bd.compile()
out = sim.run(bd, 10)
print(out)
