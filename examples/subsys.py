#!/usr/bin/env python3

"""
Example showing subsystems
Copyright (c) 2021- Peter Corke
"""

import bdsim
sim = bdsim.BDSim(tiles="tall")

# -- create simple subsystem as a blockdiagram -- #
#
#   IN[0] ---> x^2 ---> SUM --> OUT[0]
#                        ^
#                        |
#   IN[1] ---------------+
ss = sim.blockdiagram(name="subsystem1")

squarer = ss.FUNCTION(lambda x: x**2)
sum = ss.SUM("++")
inp = ss.INPORT(2)
outp = ss.OUTPORT(1)

ss.connect(inp[0], squarer)
ss.connect(squarer, sum[0])
ss.connect(inp[1], sum[1])
ss.connect(sum, outp)

# -- create main system as a blockdiagram -- #
main = sim.blockdiagram()

x = main.WAVEFORM("sine", 1, "Hz")
const = main.CONSTANT(1)
scope1 = main.SCOPE(nin=1)
scope2 = main.SCOPE(nin=1)
subsys1 = main.SUBSYSTEM(ss)  # instantiate the subsystem
subsys2 = main.SUBSYSTEM(ss)  # instantiate the subsystem

main.connect(x, subsys1[0], subsys2[0])
main.connect(const, subsys1[1], subsys2[1])
main.connect(subsys1, scope1)
main.connect(subsys2, scope2)

main.compile(verbose=False)
main.report_summary()

sim.report(main)
sim.run(main, T=5)
