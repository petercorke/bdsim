from bdsim import BDSim

PWM_FREQ = 20

sim = BDSim()
bd = sim.blockdiagram()

clock = bd.clock(50, 'Hz')

duty = bd.TIME()  # essentially a ramp input

pwm = bd.PWM(clock, duty, freq=PWM_FREQ, v_range=(0, 1))

scope = bd.SCOPE(nin=2, labels=["Duty Cycle", "PWM Signal"])
scope[0] = duty
scope[1] = pwm

bd.compile()

sim.run(bd, T=1, dt=1 / PWM_FREQ / 10)
sim.done(bd, block=True)
