#!/usr/bin/env python3

"""
Example of bouncing ball system
Copyright (c) 2021- Peter Corke
"""
import bdsim

# define constants
g = -9.81  # gravity m/s2
e = 0.8  # coefficient of restitution
h0 = 10  # initial height m

sim = bdsim.BDSim()  # create simulator
bd = sim.blockdiagram()  # create an empty block diagram

# define the blocks
velocity = bd.INTEGRATOR(name="velocity", x0=0)  # initial height is initial velocity
position = bd.INTEGRATOR(name="position", x0=h0)
gravity = bd.CONSTANT(g, name="gravity")
scope = bd.SCOPE(styles=["k", "r--"], loc="lower right")


# detect when the ball hits the ground (position=0) and trigger an event
def impact(x):
    velocity.x *= -e  # reverse velocity and apply restitution


# connect the impact function to the event triggered when position crosses zero from above
ground = bd.EVENT("-", impact)

# connect the blocks together
bd.connect(gravity, velocity)
bd.connect(velocity, position)
bd.connect(velocity, scope[0])
bd.connect(position, scope[1])
bd.connect(position, ground)

bd.compile()  # check the diagram
sim.report(bd)

out = sim.run(bd, T=5)  # , watch=[demand, sum])  # simulate for 5s
