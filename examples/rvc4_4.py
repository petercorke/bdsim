#!/usr/bin/env python3

import bdsim.simulation as sim
import math

s = sim.Simulation()

def graphics(ax):
    ax.plot(5, 5, '*')
    ax.plot(5, 2, 'o')
    
goal = s.CONSTANT([5, 5])
error = s.SUM('+-')
d2goal = s.FUNCTION(lambda d: math.sqrt(d[0]**2 + d[1]**2))
h2goal = s.FUNCTION(lambda d: math.atan2(d[1], d[0]))
heading_error = s.SUM('+-', angles=True)
Kv = s.GAIN(0.5)
Kh = s.GAIN(4)
bike = s.BICYCLE(x0=[5, 2, 0])
xyscope = s.SCOPEXY(scale=[0, 10], init=graphics)
vscope = s.SCOPE(name='velocity')
hscope = s.SCOPE(name='heading')
mux = s.MUX(2)

s.connect(goal, error[0])
s.connect(error, d2goal, h2goal)
s.connect(d2goal, Kv)
s.connect(Kv, bike[0], vscope)
s.connect(h2goal, heading_error[0])
s.connect(bike[2], heading_error[1])
s.connect(heading_error, hscope)
s.connect(heading_error, Kh)
s.connect(Kh, bike[1])
s.connect(bike[0:2], mux, xyscope)
s.connect(mux, error[1])

s.compile()
s.report()

out = s.run(block=True)

s.done()
