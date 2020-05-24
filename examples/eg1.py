#!/usr/bin/env python3

import bdsim.bdsim as bd

s = bd.Simulation()

plant = s.LTI_SISO(0.5, [1, 2], name='plant')
demand = s.WAVEFORM(wave='square', freq='2')
sum = s.SUM('+-')
scope = s.SCOPE()
gain = s.GAIN(2)

s.connect(demand, sum[0])
s.connect(plant, sum[1])
s.connect(sum, gain)
s.connect(gain, plant)
s.connect(plant, scope)

s.compile()

s.dotfile('bd1.dot')