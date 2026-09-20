#!/usr/bin/env python3

"""
Motor speed-control loop, expressed once and runnable two ways.

Triangle-wave setpoint -> PID_S -> PWM magnitude + direction outputs.
Toggle CODEGEN_EMBEDDED to switch the whole diagram between a pure
Python simulation (a simulated INTEGRATOR plant closes the loop) and
generating standalone embedded C++ (DEVICEIN/ANALOGOUT/DIGITALOUT read/
drive real hardware instead) -- illustrating how naturally the same
control-law description covers both.

This is a second, illustrative example alongside motor_control.py, not
a replacement for it: the two CODEGEN_EMBEDDED branches here use
different plant topologies (simulated INTEGRATOR vs. real I/O blocks),
so unlike motor_control.py there's no single diagram to both "simulate
for ground truth" and "generate C++ from" -- verify_codegen.py's
numeric cross-check depends on exactly that, so motor_control.py stays
the canonical, test-referenced fixture for it. See
claude-notes/codegen-embedded-plan.md's "motor_control2.py" section.

Copyright (c) 2021- Peter Corke
"""
CODEGEN_EMBEDDED = True

import bdsim

if CODEGEN_EMBEDDED:
    from bdsim.codegen import Codegen


def pwm_and_direction(u):
    # A plain top-level def, not a lambda: bdsim.codegen inlines a
    # FUNCTION block's callable via inspect.getsource(), which can't
    # reliably extract a lambda's own source when it's embedded inline as
    # a call argument (a real Python `inspect` limitation, not specific
    # to bdsim) -- see docs/codegen-transpilation.md.
    return [abs(u), 1.0 if u >= 0 else -1.0]

sim = bdsim.BDSim(animation=False)  # create simulator
bd = sim.blockdiagram()  # create an empty block diagram

clock = bd.clock(100, "Hz")

if CODEGEN_EMBEDDED:
    # actual motor encoder
    encoder = bd.DEVICEIN(name="encoder")
else:
    # simulated motor plant -- placeholder for a real plant model
    motor = bd.INTEGRATOR(x0=0.0, gain=100.0, name="plant")  # placeholder for a real plant model
    encoder = motor[0]  # feedback from the plant

# common blocks
demand = bd.WAVEFORM(wave="triangle", min=0, max=2000, freq=0.5, name="demand")
pid = bd.PID_S(clock, P=0.2, I=0.0, D=0.1, name="pid")
clip = bd.CLIP(-40, 40, name="clip")
pwm_dir = bd.FUNCTION(pwm_and_direction, nin=1, nout=2, name="pwm+dir")

# connect the blocks
pid[0] = encoder  # plant/encoder feedback
pid[1] = demand  # reference
clip[0] = pid  # clip the PID output to avoid saturating the motor
pwm_dir[0] = clip  # pwm magnitude

scope = bd.SCOPE(styles=["k", "r--", "b--"], inputs=[encoder, demand, pid], loc="lower right")

if CODEGEN_EMBEDDED:
    # connect to actual motor
    pwm = bd.ANALOGOUT(channel=0, inputs=[pwm_dir[0]], name="pwm_magnitude")
    dir = bd.DIGITALOUT(channel=1, inputs=[pwm_dir[1]], name="motor_direction")
else:
    # connect to simulated motor plant
    # convert PWM+sign back to a single input for the plant
    motor[0] = bd.PROD("**", inputs=[pwm_dir[0], pwm_dir[1]], name="plant_input")

bd.compile()  # check the diagram
sim.report(bd, depth=0)
# bd.report_schedule()

# generate C++ for the diagram -- writes codegen.cpp in the cwd, and
# compiles/runs standalone -- see claude-notes/codegen-embedded-plan.md
if CODEGEN_EMBEDDED:
    # generate C++ for the diagram -- writes codegen.cpp in the cwd, and
    # compiles/runs standalone -- see claude-notes/codegen-embedded-plan.md
    Codegen().generate(bd)
else:
    # simulate the diagram for 5 seconds -- this is a placeholder for a real plant model
    out = sim.run(bd, T=5)
