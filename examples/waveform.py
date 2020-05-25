#!/usr/bin/env python3

import bdsim.simulation as sim

s = sim.Simulation()

wave1 = s.WAVEFORM(wave='triangle', freq=1, phase0=0.25)
wave2 = s.WAVEFORM(wave='square', freq=1, min=0, max=1)
scope1 = s.SCOPE()
scope2 = s.SCOPE()


s.connect(wave1, scope1)
s.connect(wave2, scope2)

s.compile()
s.report()
s.run(4, dt=0.02)