#!/usr/bin/env python3

"""
Test discrete-time system
Franklin, Powell, Workman, 2nd edition, 1990, Sec 5.3
Copyright (c) 2026- Peter Corke
"""
import bdsim

sim = bdsim.BDSim(animation=True)  # create simulator
bd = sim.blockdiagram()  # create an empty block diagram

# define the blocks
clock = bd.clock(5, "Hz")
demand = bd.STEP(T=1, name="demand")
sum = bd.SUM("+-")
scope = bd.SCOPE(styles=["k", "r--", "b:"], loc="lower right")

# discrete-time transfer values from page 177, 179
G = bd.LTI_SISO_S(
    clock, [0.00199, (1, 0.9934)], [(1, -1), (1, -0.9802)], name="G"
)  # antenna drive system
D = bd.LTI_SISO_S(clock, [9.15, (1, -0.9802)], [1, -0.8187], name="D")  # compensator


# connect the blocks
bd.connect(demand, sum[0], scope[0])
bd.connect(sum, D)
bd.connect(D, G, scope[2])
bd.connect(G, sum[1], scope[1])

bd.compile()  # check the diagram

out = sim.run(bd, T=5)
