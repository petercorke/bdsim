#!/usr/bin/env python3

import bdsim.simulation as sim
import math

s = sim.Simulation()


# parameters
xg = [5, 5, math.pi/2]
Krho = s.GAIN(1)
Kalpha = s.GAIN(5)
Kbeta = s.GAIN(-2)
xg = [5, 5, math.pi/2]
x0 = [5, 2, 0]

# annotate the graphics
def graphics(ax):
    ax.plot(*xg[0:2], '*')
    ax.plot(*x0[0:2], 'o')

# convert x,y,theta state to polar form
def polar(x, dict):
    rho = math.sqrt(x[0]**2 + x[1]**2)

    if not 'direction' in dict:
        # direction not yet set, set it
        beta = -math.atan2(-x[1], -x[0])
        alpha = -x[2] - beta
        dict['direction'] = -1 if -math.pi/2 <= alpha < math.pi/2 else 1
        print('set direction to ', dict['direction'])

    
    if dict['direction'] == -1:
        beta = -math.atan2(x[1], x[0]);
    else:
        beta = -math.atan2(-x[1], -x[0])
    alpha = -x[2] - beta

    # clip alpha
    if alpha > math.pi/2:
        alpha = math.pi/2
    elif alpha < -math.pi/2:
        alpha = -math.pi/2  

    return [rho, alpha, beta, dict['direction']]

# constants
goal0 = s.CONSTANT([xg[0], xg[1], 0])
goalh = s.CONSTANT(xg[2])

# stateful blocks
bike = s.BICYCLE(x0=x0, name='bike')

# functions
fabs = s.FUNCTION(lambda x: abs(x), name='abs')
polar = s.FUNCTION(polar, nout=4, dict=True, name='polar', inp_names=('x',),
    outp_names=(r'$\rho$', r'$\alpha$', r'$\beta', 'direction'))
stop = s.STOP(lambda x: x < 0.01, name='close enough')
steer_rate = s.FUNCTION(lambda u: math.atan(u), name='atan')

# arithmetic
vprod = s.PROD('**', name='vprod')
aprod = s.PROD('**/', name='aprod')
xerror = s.SUM('+-')
heading_sum = s.SUM('++', angles=True)
gsum = s.SUM('++')

# displays
xyscope = s.VEHICLE(scale=[0, 10], size=0.7, shape='box', init=graphics)
ascope = s.SCOPE(name=r'$\alpha$')
bscope = s.SCOPE(name=r'$\beta$')

# connections

mux = s.MUX(3)

s.connect(bike[0:3], mux[0:3], xyscope[0:3])
s.connect(mux, xerror[0])
s.connect(goal0, xerror[1])

s.connect(xerror, polar)
s.connect(polar[0], Krho, stop) # rho
s.connect(Krho, vprod[1])
s.connect(polar[1], Kalpha, ascope) # alpha
s.connect(Kalpha, gsum[0])
s.connect(polar[2], heading_sum[0]) # beta
s.connect(goalh, heading_sum[1])
s.connect(heading_sum, Kbeta, bscope)

s.connect(polar[3], vprod[0], aprod[1])
s.connect(vprod, fabs, bike.v)
s.connect(fabs, aprod[2])
s.connect(aprod, steer_rate)
s.connect(steer_rate, bike.gamma)

s.connect(Kbeta, gsum[1])
s.connect(gsum, aprod[0])

s.compile()
s.report()
s.dotfile('rvc4_11.dot')

out = s.run(block=True)

s.done()
