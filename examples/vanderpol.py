#!/usr/bin/env python3

import bdsim

sim = bdsim.BDSim(animation=True, globs=globals())  # create simulator
bd = sim.blockdiagram()  # create an empty block diagram

λ = 0.3

# define the blocks
x = bd.INTEGRATOR(x0=1)  # integrator block
y = bd.INTEGRATOR(x0=1)  # integrator block
scope = bd.SCOPEXY(scale=[-2, 2, -2, 2])

# we can write this two different ways

## 1. Using a 2-input function block, probably computationally efficient
f = bd.FUNCTION(lambda x, y: -x + λ * (1 - x**2) * y, nin=2)
bd.connect(x, scope[0], f[0])
bd.connect(y, x, scope[1], f[1])
bd.connect(f, y)


## 2. Using implicit block creation
# x[0] = y
# y[0] = -x + λ * (1 - x**2) * y
# scope[0] = x
# scope[1] = y

bd.compile()  # check the diagram
bd.report_summary()  # list all blocks and wires

# probably needs a stiff integrator
out = sim.run(bd, T=20, solver="BDF")  # , watch=[demand, sum])  # simulate for 5s
