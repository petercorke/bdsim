from bdsim import BDSim
sim = BDSim()
bd = sim.blockdiagram()

clock = bd.clock(100, 'Hz')

sine = bd.WAVEFORM('sine', 2)
square = bd.WAVEFORM('square', 3)
signal = bd.SUM('++', sine, square)

bit_widths = [4, 8, 12]
sampled = [
    bd.ADC(clock, signal, bit_width=w, v_range=(-2, 2))
    for w in bit_widths
]

scope = bd.SCOPE(labels=["Signal"] + [f"{w}bit ADC" for w in bit_widths],
                 stairs=[False] + [True] * len(bit_widths))
scope[0] = signal
for idx, block in enumerate(sampled):
    scope[idx + 1] = block

bd.compile()

sim.run(bd, T=1)
sim.done(bd, block=True)
