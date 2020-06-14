#!/usr/bin/env python3

# run with command line -a switch to show animation

import bdsim.simulation as sim
import math
import numpy as np

bd = sim.Simulation()

#x0 = [8, 5, math.pi/2]
x0 = [5, 2, 0]
L = [1, -2, 4]

def plot_homline(ax, line, *args, xlim, ylim, **kwargs):
    if abs(line[1]) > abs(line[0]):
        y = (-line[2] - line[0]*xlim) / line[1]
        ax.plot(xlim, y, *args, **kwargs);
    else:
        x = (-line[2] - line[1]*ylim) / line[0]
        ax.plot(x, ylim, *args, **kwargs);


def background_graphics(ax):
    plot_homline(ax, L, "r--", xlim=np.r_[0,10], ylim=np.r_[0,10])
    ax.plot(x0[0], x0[1], 'o')
    

speed = bd.CONSTANT(0.5)
slope = bd.CONSTANT(math.atan2(-L[0], L[1]))
d2line = bd.FUNCTION(lambda u: (u[0]*L[0] + u[1]*L[1] + L[2])/math.sqrt(L[0]**2 + L[1]**2))
heading_error = bd.SUM('+-', angles=True)
steer_sum = bd.SUM('+-')
Kd = bd.GAIN(0.5)
Kh = bd.GAIN(1)
bike = bd.BICYCLE(x0=x0)
vplot = bd.VEHICLE(scale=[0, 10], size=0.7, shape='box', init=background_graphics, movie='rvc4_6.mp4')
hscope = bd.SCOPE(name='heading')
mux = bd.MUX(2)

bd.connect(d2line, Kd)
bd.connect(Kd, steer_sum[1])
bd.connect(steer_sum, bike.gamma)
bd.connect(speed, bike.v)

bd.connect(slope, heading_error[0])
bd.connect(bike[2], heading_error[1])

bd.connect(heading_error, Kh)
bd.connect(Kh, steer_sum[0])

bd.connect(mux, d2line)

bd.connect(bike[0:2], mux)
bd.connect(bike[0:3], vplot[0:3])
bd.connect(bike[2], hscope)

bd.compile()
bd.report()

out = bd.run(20, block=True)

bd.done()
