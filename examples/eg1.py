#!/usr/bin/env python3

import bdsim.bdsim as bd

s = bd.Simulation()

demand = s.STEP(T=1, pos=(0,0))
sum = s.SUM('+-', pos=(1,0))
gain = s.GAIN(10, pos=(1.5,0))
plant = s.LTI_SISO(0.5, [1, 2], name='plant', pos=(3,0))
scope = s.SCOPE(pos=(4,0))

s.connect(demand, sum[0])
s.connect(plant, sum[1])
s.connect(sum, gain)
s.connect(gain, plant)
s.connect(plant, scope)

s.compile()

#s.dotfile('bd1.dot')

s.run(5)