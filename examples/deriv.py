#!/usr/bin/env python3

"""
Demonstrate derivative block driven by sine wave
Copyright (c) 2021- Peter Corke
"""
import bdsim

sim = bdsim.BDSim()
bd = sim.blockdiagram()

u = bd.WAVEFORM("sine", freq=1, unit="rad/s")
du = bd.DERIV(0.1, y0=1)
scope = bd.SCOPE(styles=['k','r--'])

# connect

bd.connect(u, scope[0], du)
bd.connect(du, scope[1])

bd.compile()
sim.report(bd)
out = sim.run(bd, 10)
