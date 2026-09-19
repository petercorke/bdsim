#!/usr/bin/env python3

"""
Canonical motor speed-control loop -- test diagram for bdsim.codegen.

Triangle-wave setpoint -> PID_S -> PWM magnitude + direction outputs.
Exercises a realistic mix of sampled blocks (WAVEFORM, PID_S -- itself a
flattened subsystem of GAIN/INTEGRATOR_S/DERIV_S/SUM -- and FUNCTION) for
codegen's next()/state pipeline, not just the toy demand/sum/gain/plant
diagram in codegen.py's own __main__.

There is no ABS or SIGN block in bdsim -- both PWM magnitude and motor
direction are derived via FUNCTION.

Encoder feedback is a CONSTANT placeholder, not a real sensor reading --
this diagram exists to exercise codegen against a realistic block
topology, not to close the loop through an actual plant model. Same
pattern already used in test_pid_s.py for "no real plant yet".

Copyright (c) 2021- Peter Corke
"""

import bdsim
from bdsim.codegen import Codegen

sim = bdsim.BDSim(animation=False)  # create simulator
bd = sim.blockdiagram()  # create an empty block diagram

clock = bd.clock(100, "Hz")

# setpoint: triangle wave, 0 to 2000 (e.g. encoder counts or RPM demand)
demand = bd.WAVEFORM(wave="triangle", min=0, max=2000, freq=0.5, name="demand")

# encoder feedback -- placeholder for a real DeviceIn-backed encoder block
# (see claude-notes/codegen-embedded-plan.md's I/O handling section)
encoder = bd.CONSTANT(0.0, name="encoder")

pid = bd.PID_S(clock, P=1.0, I=0.5, D=0.0, name="pid")

def pwm_and_direction(u):
    return [abs(u), 1.0 if u >= 0 else -1.0]


motor_out = bd.FUNCTION(pwm_and_direction, nin=1, nout=2, name="motor_out")

scope = bd.SCOPE(styles=["k", "r--", "b--", "g--"], loc="lower right")

# connect the blocks
bd.connect(encoder, pid[0])  # plant/encoder feedback
bd.connect(demand, pid[1], scope[0])  # reference
bd.connect(pid, motor_out, scope[1])
bd.connect(motor_out[0], scope[2])  # pwm magnitude
bd.connect(motor_out[1], scope[3])  # direction

bd.compile()  # check the diagram
sim.report(bd, depth=0)
bd.report_schedule()

# generate C++ for the diagram -- writes codegen.cpp in the cwd, and
# compiles/runs standalone -- see claude-notes/codegen-embedded-plan.md
Codegen().generate(bd)

out = sim.run(bd, T=5)
