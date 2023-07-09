#!/usr/bin/env python
'''
Example of PID control system
Copyright (c) 2021- Peter Corke
'''
import bdsim

sim = bdsim.BDSim(animation=True)  # create simulator
bd = sim.blockdiagram()  # create an empty block diagram

# define the blocks
dmd = bd.STEP(T=1, on=1, name="demand")
controller = bd.PID(P=5, D=0, I=-5, I_band=0.3, name="PID")
plant = bd.LTI_SISO(0.5, [2, 1], name="plant")
scope = bd.SCOPE(styles=["k", "r--"])

# connect the blocks

bd.connect(dmd, controller[1], scope[0])
bd.connect(controller, plant)
bd.connect(plant, controller[0], scope[1])

bd.compile()
sim.report(bd)
out = sim.run(bd, 10)
print(out)