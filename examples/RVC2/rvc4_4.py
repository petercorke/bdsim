#!/usr/bin/env python3

# run with command line -a switch to show animation

import bdsim
import math

sim = bdsim.BDSim(animation=True)
bd = sim.blockdiagram()

def background_graphics(ax):
    ax.plot(5, 5, '*')
    ax.plot(5, 2, 'o')
    
goal = bd.CONSTANT([5, 5])
error = bd.SUM('+-', name='error')
d2goal = bd.FUNCTION(lambda d: math.sqrt(d[0]**2 + d[1]**2))
h2goal = bd.FUNCTION(lambda d: math.atan2(d[1], d[0]))
heading_error = bd.SUM('+-', angles=True)
Kv = bd.GAIN(0.5)
Kh = bd.GAIN(4)
bike = bd.BICYCLE(x0=[5, 2, 0])
vplot = bd.VEHICLEPLOT(scale=[0, 10], size=0.7, shape='box', init=background_graphics, movie='rvc4_4.mp4')
vscope = bd.SCOPE(name='velocity')
hscope = bd.SCOPE(name='heading')
xy = bd.SLICE1([0, 1])
theta = bd.SLICE1([2])

bd.connect(bike, xy, theta, vplot)
bd.connect(goal, error[0])
bd.connect(xy, error[1])
bd.connect(error, d2goal, h2goal)
bd.connect(d2goal, Kv)
bd.connect(Kv, bike[0], vscope)
bd.connect(h2goal, heading_error[0])
bd.connect(theta, heading_error[1])
bd.connect(heading_error, hscope)
bd.connect(heading_error, Kh)
bd.connect(Kh, bike[1])


bd.compile()
bd.report()

out = sim.run(bd)

#sim.done(bd, block=True)
