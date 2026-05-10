#!/usr/bin/env python3

"""
Test continuous-time system
Franklin, Powell, Workman, 2nd edition, 1990, Sec 5.3
Copyright (c) 2026- Peter Corke
"""
import bdsim

sim = bdsim.BDSim(animation=True)  # create simulator
bd = sim.blockdiagram()  # create an empty block diagram

# define the blocks
demand = bd.STEP(T=1, name="demand")
sum = bd.SUM("+-")
scope = bd.SCOPE(styles=["k", "r--", "b:"], loc="lower right")

# discrete-time transfer values from page 160, 175
G = bd.LTI_SISO(1, [10, 1, 0], name="G")  # antenna drive system
D = bd.LTI_SISO([10, 1], [1, 1], name="D")  # compensator


# connect the blocks
bd.connect(demand, sum[0], scope[0])
bd.connect(sum, D)
bd.connect(D, G, scope[2])
bd.connect(G, sum[1], scope[1])

bd.compile()  # check the diagram

out = sim.run(bd, T=5)
