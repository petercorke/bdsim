#!/usr/bin/env python3

"""
System with no dynamics: waveform driving a scope.
The run loop auto-enables live scope updates for stateless, clockless diagrams.
Copyright (c) 2021- Peter Corke
"""

import bdsim

sim = bdsim.BDSim()  # create simulator
bd = sim.blockdiagram()  # create an empty block diagram

# define the blocks
demand = bd.WAVEFORM(name="demand")
scope = bd.SCOPE(styles=["k"])

# connect the blocks
bd.connect(demand, scope)

bd.compile()  # check the diagram
sim.report(bd)  # , format="latex")
sim.report(bd, "schedule")

out = sim.run(bd, T=5)
print(out)
