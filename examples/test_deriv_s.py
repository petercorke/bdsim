#!/usr/bin/env python3

"""
Test continuous-time integrator
Copyright (c) 2026- Peter Corke
"""
import bdsim

sim = bdsim.BDSim(animation=True)  # create simulator
bd = sim.blockdiagram()  # create an empty block diagram

# define the blocks
clock = bd.clock(10, "Hz")
demand = bd.RAMP(T=1, name="demand")
deriv = bd.DERIV_S(clock, gain=2, x0=0)
scope = bd.SCOPE(styles=["k", "r--"], loc="lower right")  # , movie='eg1.mp4')

# connect the blocks
bd.connect(demand, deriv, scope[0])
bd.connect(deriv, scope[1])


bd.compile()  # check the diagram
bd.report_summary(depth=0)  # print block report lists

out = sim.run(bd, T=5)
