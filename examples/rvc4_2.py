#!/usr/bin/env python3

import bdsim.bdsim as bd

s = bd.Simulation()
    
steer = s.WAVEFORM(name='siggen', freq=0.5, min=-0.5, max=0.5)
speed = s.CONSTANT(value=0.5)
bike = s.BICYCLE(x0=[0, 0, 0])
scope = s.SCOPEXY()
#cro = s.SCOPE()

s.connect(speed, bike[0])
s.connect(steer, bike[1])
#s.connect(steer, cro)

s.connect(bike[0:2], scope[0:2])

s.compile()

print(s)

out = s.run(graphics=True)

s.done()