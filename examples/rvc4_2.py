#!/usr/bin/env python3

# run with command line -a switch to show animation

import bdsim

sim = bdsim.BDSim(animation=True)
bd = sim.blockdiagram()
    
steer = bd.PIECEWISE( (0,0), (3,0.5), (4,0), (5,-0.5), (6,0), name='steering')
speed = bd.CONSTANT(1, name='speed')
bike = bd.BICYCLE(x0=[0, 0, 0], name='bicycle')
q = bd.DEMUX(3)

tscope= bd.SCOPE(name='theta')
vplot = bd.VEHICLEPLOT(scale=[0, 10, -5, 5], size=0.7, shape='box') #, movie='rvc4_2.mp4')

bd.connect(bike, q, vplot)
bd.connect(speed, bike[0])
bd.connect(steer, bike[1])
bd.connect(q[2], tscope)

bd.compile()
bd.report()

out = sim.run(bd, dt=0.05)

#sim.done(bd, block=True)