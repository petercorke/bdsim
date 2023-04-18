#!/usr/bin/env python3

import bdsim

sim = bdsim.BDSim()

# create simple subsystem as a blockdiagram
ss = sim.blockdiagram(name="subsystem1")

squarer = ss.FUNCTION(lambda x: x**2)
sum = ss.SUM("++")
inp = ss.INPORT(2)
outp = ss.OUTPORT(1)

ss.connect(inp[0], squarer)
ss.connect(squarer, sum[0])
ss.connect(inp[1], sum[1])
ss.connect(sum, outp)

# create main system as a blockdiagram
main = sim.blockdiagram()

x = main.WAVEFORM("sine", 1, "Hz")
const = main.CONSTANT(1)
scope = main.SCOPE()
subsys = main.SUBSYSTEM(ss)  # instantiate the subsystem

main.connect(x, subsys[0])
main.connect(const, subsys[1])
main.connect(subsys, scope)

main.compile(verbose=False)

sim.report(main)
sim.run(main, T=5)
