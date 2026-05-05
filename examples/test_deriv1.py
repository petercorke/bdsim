#!/usr/bin/env python3

"""
Test continuous-time integrator
Copyright (c) 2026- Peter Corke
"""
import bdsim

sim = bdsim.BDSim(animation=True)  # create simulator
bd = sim.blockdiagram()  # create an empty block diagram

# define the blocks
demand = bd.RAMP(T=1, name="demand")
deriv = bd.DERIV(alpha=5, x0=0)
scope = bd.SCOPE(styles=["k", "r--"], loc="lower right")

# connect the blocks
bd.connect(demand, deriv, scope[0])
bd.connect(deriv, scope[1])


bd.compile()  # check the diagram
bd.report_summary(depth=0)  # print block report lists

out = sim.run(bd, T=5)
