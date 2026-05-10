#!/usr/bin/env python3

"""
Test discrete-time integrator with step input
Copyright (c) 2026- Peter Corke
"""
import bdsim

sim = bdsim.BDSim(animation=True)  # create simulator
bd = sim.blockdiagram()  # create an empty block diagram

# define the blocks
clock = bd.clock(10, "Hz")
demand = bd.STEP(T=1, name="demand")
integrator = bd.INTEGRATOR_S(clock, gain=2, x0=0)
scope = bd.SCOPE(styles=["k", "r--"], loc="lower right")

# connect the blocks
bd.connect(demand, integrator, scope[0])
bd.connect(integrator, scope[1])

bd.compile()  # check the diagram

out = sim.run(bd, T=5)
