#!/usr/bin/env python3

"""
Cart-pole dynamic system
Copyright (c) 2021- Peter Corke
"""

import math
import bdsim

sim = bdsim.BDSim(animation=True)  # create simulator

bd = sim.blockdiagram()  # create an empty block diagram

import matplotlib.patches as patches
import matplotlib.transforms as transforms

# animation functions written by gemini
# Prompt: I want to write a simple matplotlib
# animation of the cart pole system. A rectangle for the cart, a horizontal line for it
# to move across, and the pendulum which pivots about the middle top of the cart. Use
# MPL patches and their transformations. For the purpose of the prototype, the cart
# position and pole angle can increase linearly with time.


def cartpole_init(self, fig, ax):
    # 1. Setup the figure and axis
    ax.set_xlim(-5, 5)
    ax.set_ylim(-2, 4)
    ax.set_aspect("equal")
    ax.grid(True, linestyle="--")

    # Draw the horizontal track
    self.ax.axhline(0, color="black", lw=1.5)

    # 2. Define geometry constraints
    cart_w, cart_h = 1.0, 0.6
    pole_w, pole_h = 0.1, 2.0

    # Pivot point relative to the cart: top-middle
    pivot_x_rel = cart_w / 2.0
    pivot_y_rel = cart_h

    # 3. Create the patches at the origin (0,0)
    # Cart anchor is bottom-left, so we center it horizontally at X=0
    cart = patches.Rectangle(
        (-cart_w / 2, 0),
        cart_w,
        cart_h,
        linewidth=1.5,
        edgecolor="blue",
        facecolor="lightblue",
    )

    # Pole anchor is bottom-left. Center it horizontally at X=0, resting at Y=0
    pole = patches.Rectangle(
        (-pole_w / 2, 0),
        pole_w,
        pole_h,
        linewidth=1.5,
        edgecolor="red",
        facecolor="salmon",
    )

    ax.add_patch(cart)
    ax.add_patch(pole)

    self.cart = cart
    self.pole = pole

    self.pivot_y_rel = pivot_y_rel


def cartpole_update(self, t, u):
    cart_x = u[0]
    pole_angle = u[1]
    ax = self.ax

    # --- Cart Transformation ---
    # 1. Shift the cart horizontally by cart_x
    # 2. Transform from model to display coordinates (+ ax.transData)
    cart_trans = transforms.Affine2D().translate(cart_x, 0) + ax.transData
    self.cart.set_transform(cart_trans)

    # --- Pole Transformation ---
    # 1. Rotate the pole around its own bottom-center (0,0 in its local space)
    # 2. Translate it to match the cart's current absolute pivot position
    # 3. Transform from model to display coordinates (+ ax.transData)
    pivot_x_abs = cart_x
    pivot_y_abs = self.pivot_y_rel

    pole_trans = (
        transforms.Affine2D().rotate(-pole_angle).translate(pivot_x_abs, pivot_y_abs)
    ) + ax.transData

    self.pole.set_transform(pole_trans)


# Model as per: Underactuated Robotics, Chapter 3, Russ Tedrake, MIT.

# parameters

M = 1.0  # mass of cart
m = 0.1  # mass of pendulum
l = 0.5  # length of pendulum
g = -9.81  # gravity
I = m * l**2 / 3  # inertia of pendulum about CoG  ????
b = 10  # cart friction

# -------------------- define the blocks -------------------- #

# force pulse at t=1s for 0.2s
F = bd.STEP(1, name="disturb-on") - bd.STEP(1.2, name="disturb-off")

# chain of integrators for cart horizontal position
x_dot = bd.INTEGRATOR(name="x_dot")
x = x_dot >> bd.INTEGRATOR(name="x")

# chain of integrators for pendulum angle
theta_dot = bd.INTEGRATOR(name="theta_dot")
theta = theta_dot >> bd.INTEGRATOR(name="theta")

cos_theta = theta >> bd.FUNCTION(lambda x: math.cos(x), name="cos(theta)")
sin_theta = theta >> bd.FUNCTION(lambda x: math.sin(x), name="sin(theta)")

D = M + m * sin_theta**2  # determinant of the mass matrix
f = F - b * x_dot  # nett force on the cart (input minus friction)

# equations of motion (rearranged to isolate the second derivatives)
x_dot[0] = (
    f + m * sin_theta * (l * theta_dot**2 + g * cos_theta)
) / D  # cart acceleration
theta_dot[0] = (
    -f * cos_theta
    - m * l * theta_dot**2 * cos_theta * sin_theta
    - (M + m) * g * sin_theta
) / (
    l * D
)  # pendulum angular acceleration

# total energy of the system (for monitoring)
T = (
    1 / 2 * (M + m) * x_dot**2
    + 1 / 2 * m * l**2 * theta_dot**2
    + m * l * x_dot * theta_dot * cos_theta
)  # kinetic energy (note coupling term from cart-pole interaction)
U = -m * g * l * cos_theta  # potential energy (zero at vertical down)
E = T + U

# display the system state evolution on a scope and animation
scope = bd.SCOPE(
    nin=4,
    inputs=[F, x, theta, E],
    labels=("F", "x", r"$\theta$", "E"),
    loc="lower right",
)
anim = bd.ANIMATION(
    init=cartpole_init, update=cartpole_update, nin=2, inputs=[x, theta]
)

bd.report()
bd.graph("mermaid", "cartpole.md")  # write mermaid file for visualization
bd.compile()  # check the diagram
bd.report_schedule()
bd.report_summary()

out = sim.run(bd, T=20, watch=[F, x, theta])  # simulate for 5s
print(out)
