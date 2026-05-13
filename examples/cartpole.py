#!/usr/bin/env python3

"""
Cart-pole dynamic system
Copyright (c) 2021- Peter Corke
"""

import math
import bdsim

sim = bdsim.BDSim(animation=False)  # create simulator

bd = sim.blockdiagram()  # create an empty block diagram

# parameters

M = 1.0  # mass of cart
m = 0.1  # mass of pendulum
l = 0.5  # length of pendulum
g = 9.81  # gravity
I = m * l**2 / 3  # inertia of pendulum about CoG  ????

# define the blocks
F = bd.STEP(T=1, name="disturb-on") - bd.STEP(T=1.2, name="disturb-off")

F_sum = bd.SUM("+-", name="F_sum")
x_ddot = F_sum >> bd.GAIN(1 / M, name="x_ddot")
x_dot = x_ddot >> bd.GAIN(1 / M) >> bd.INTEGRATOR(name="x_dot")
x = x_dot >> bd.INTEGRATOR(name="x")

theta_ddot = bd.GAIN(1 / I, name="theta_ddot")
theta_dot = theta_ddot >> bd.INTEGRATOR(name="theta_dot")
theta = theta_dot >> bd.INTEGRATOR(name="theta")

cos_theta = theta >> bd.FUNCTION(lambda x: math.cos(x[0]), name="cos(theta)")
sin_theta = theta >> bd.FUNCTION(lambda x: math.sin(x[0]), name="sin(theta)")

H = m * (x_ddot + l * sin_theta * theta_dot**2 - l * cos_theta * theta_ddot)
# V = (
#     -(l * m * theta_ddot - m * cos_theta * x_ddot + H * cos_theta - g * m * sin_theta)
#     / sin_theta
# )

# theta_ddot[0] = (H * l * cos_theta + V * l * sin_theta) / I

theta_ddot[0] = (l * m * cos_theta * x_ddot + g * l * m * sin_theta) / (I + l**2 * m)

F_sum[0] = F  # disturbance input
F_sum[1] = H  # horizontal force from pendulum on cart

scope = bd.SCOPE(nin=3, inputs=[F, x, theta], loc="lower right")

bd.report()
bd.dotfile("cartpole.dot")  # write graphviz dot file for visualization
bd.compile()  # check the diagram
bd.report_schedule()
bd.report_summary()

out = sim.run(bd, T=5, watch=[F, x, theta])  # simulate for 5s
print(out)
