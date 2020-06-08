#!/usr/bin/env python3

import bdsim.simulation as sim
import math
import numpy as np

s = sim.Simulation()

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


def bg_graphics(ax):
    plot_homline(ax, L, "r--", xlim=np.r_[0,10], ylim=np.r_[0,10])
    ax.plot(x0[0], x0[1], 'o')
    

speed = s.CONSTANT(0.5)
slope = s.CONSTANT(math.atan2(-L[0], L[1]))
d2line = s.FUNCTION(lambda u: (u[0]*L[0] + u[1]*L[1] + L[2])/math.sqrt(L[0]**2 + L[1]**2))
heading_error = s.SUM('+-', angles=True)
steer_sum = s.SUM('+-')
Kd = s.GAIN(0.5)
Kh = s.GAIN(1)
bike = s.BICYCLE(x0=x0)
xyscope = s.SCOPEXY(scale=[0, 10], init=bg_graphics)
hscope = s.SCOPE(name='heading')
mux = s.MUX(2)

s.connect(d2line, Kd)
s.connect(Kd, steer_sum[1])
s.connect(steer_sum, bike.gamma)
s.connect(speed, bike.v)

s.connect(slope, heading_error[0])
s.connect(bike[2], heading_error[1])

s.connect(heading_error, Kh)
s.connect(Kh, steer_sum[0])

s.connect(mux, d2line)

s.connect(bike[0:2], xyscope, mux)
s.connect(bike[2], hscope)

s.compile()
s.report()

out = s.run(20, block=True)

s.done()
