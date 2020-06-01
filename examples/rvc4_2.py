#!/usr/bin/env python3

import bdsim.simulation as sim

s = sim.Simulation()
    
steer = s.PIECEWISE( (0,0), (3,0.5), (4,0), (5,-0.5), (6,0), name='steering')
speed = s.CONSTANT(1, name='speed')
bike = s.BICYCLE(x0=[0, 0, 0], name='bicycle')

tscope= s.SCOPE(name='theta')
scope = s.SCOPEXY(scale=[0, 10, 0, 1.2])

s.connect(speed, bike[0])
s.connect(steer, bike[1])

s.connect(bike[0:2], scope)
s.connect(bike[2], tscope)

s.compile()

out = s.run(dt=0.05, block=False)

s.done()
