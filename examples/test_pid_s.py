#!/usr/bin/env python3

"""
Test discrete-time PID with 3 different structures
Copyright (c) 2026- Peter Corke
"""
import math
import bdsim

sim = bdsim.BDSim(animation=False)  # create simulator
bd = sim.blockdiagram()  # create an empty block diagram
clock = bd.clock(10, "Hz")

# define the blocks
demand = bd.RAMP(T=1, name="demand")
P, I, D = 5, 3, 2
pid1 = bd.PID_S(clock, P=P, I=I, D=D)
pid2 = bd.PID_S(clock, P=P, I=I / P, D=I / P, structure="ideal")
Ps = (P + math.sqrt(P**2 - 4 * I * D)) / 2.0  # solve quadratic for P_s
pid3 = bd.PID_S(clock, P=Ps, I=I / Ps, D=D / Ps, structure="series")
scope = bd.SCOPE(styles=["k", "r--", "b--", "g--"], loc="lower right")
zero = bd.CONSTANT(0.0, name="zero")

# connect the blocks
bd.connect(demand, pid1[1], pid2[1], pid3[1], scope[0])  # reference
bd.connect(zero, pid1[0], pid2[0], pid3[0])  # plant output
bd.connect(pid1, scope[1])
bd.connect(pid2, scope[2])
bd.connect(pid3, scope[3])

bd.compile()  # check the diagram

bd.report_summary(depth=0)

out = sim.run(bd, T=5)
