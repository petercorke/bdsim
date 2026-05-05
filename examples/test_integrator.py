#!/usr/bin/env python3

"""
Test continuous-time integrator
Copyright (c) 2026- Peter Corke
"""
import bdsim

sim = bdsim.BDSim(animation=True)  # create simulator
bd = sim.blockdiagram()  # create an empty block diagram

# define the blocks
demand = bd.STEP(T=1, name="demand")
integrator = bd.INTEGRATOR(name="integrator")
scope = bd.SCOPE(styles=["k", "r--"], loc="lower right")  # , movie='eg1.mp4')

# connect the blocks
bd.connect(demand, integrator, scope[0])
bd.connect(integrator, scope[1])

bd.compile()  # check the diagram

out = sim.run(bd, T=5)
