#!/usr/bin/env python3

"""
Example of real-time system using Arduino+Firmata
Copyright (c) 2023- Peter Corke
"""

import bdsim
from bdsim.blocks.io import *

sim = bdsim.BDRealTime(
    toolboxes=False, graphics=True, animation=True
)  # create RT model
bd = sim.blockdiagram()  # create an empty block diagram
scope = bd.SCOPE(scale=[0, 1])

# define the blocks
# demand = bd.WAVEFORM(wave="triangle", name="demand")
pot = AnalogIn(pin=0)
# led = AnalogOut(pin=6, scale=0.5, offset=0.5, bd=bd)
led = AnalogOut(pin=6)

# connect the blocks
bd.connect(pot, led, scope)

bd.compile()  # check the diagram
bd.report_summary()  # list all blocks and wires

out = sim.run(bd, T=10, dt=0.2, samples=False, watch=[pot])  # simulate for 5s
print(out)
print(out.y0)
