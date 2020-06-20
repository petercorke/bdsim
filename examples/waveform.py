#!/usr/bin/env python3

import bdsim

bd = bdsim.BlockDiagram()

wave1 = bd.WAVEFORM(wave='triangle', freq=1, phase=0.25)
wave2 = bd.WAVEFORM(wave='square', freq=1, min=0, max=1)
scope1 = bd.SCOPE()
scope2 = bd.SCOPE()


bd.connect(wave1, scope1)
bd.connect(wave2, scope2)

bd.compile()
bd.report()
bd.run(4, dt=0.02, block=True)

bd.done()
