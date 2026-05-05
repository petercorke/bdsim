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
deriv = bd.DERIV2(wn=5, zeta=0.7071)
scope = bd.SCOPE(styles=["k", "r--"], loc="lower right")

# connect the blocks
bd.connect(demand, deriv, scope[0])
bd.connect(deriv, scope[1])

bd.report_lists()  # print block report lists

bd.compile()  # check the diagram

out = sim.run(bd, T=5)
