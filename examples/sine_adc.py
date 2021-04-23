from bdsim import BDSim
sim = BDSim()
bd = sim.blockdiagram()

clock = bd.clock(100, 'Hz')

sine = bd.WAVEFORM('sine', 2)
square = bd.WAVEFORM('square', 3)
signal = bd.SUM('++', sine, square)

sampled = bd.ADC(clock, signal, bit_width=8, v_range=(-5, 5))

scope = bd.SCOPE(nin=2, labels=["OG Signal", "ADC Sampled"],
                 stairs=[False, True])
scope[0] = signal
scope[1] = sampled

bd.compile()

sim.run(bd, T=1)
sim.done(bd, block=True)
