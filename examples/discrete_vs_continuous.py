from bdsim import BDSim
from scipy.signal import cont2discrete, tf2ss

sim = BDSim()
bd = sim.blockdiagram()

clock = bd.clock(50, 'Hz')

step = bd.STEP(T=1)

s_domain = [1], [1, 2, 3]
continuous = bd.LTI_SISO(*s_domain)


discretization_methods = ['zoh', 'foh', 'gbt',
                          'bilinear', 'euler', 'backward_diff', 'impulse']

discrete_blocks = []
# because direct-passthrough is not supported and ss2tf returns a lot of numerators
s_domain_statespace = tf2ss(*s_domain)
for method in discretization_methods:
    A, B, C, D, _ = cont2discrete(s_domain_statespace, clock.T, method=method)
    discrete_blocks.append(bd.DISCRETE_LTI_SS(
        clock, step, A=A, B=B, C=C, D=D))

# add them all to the scope
scope = bd.SCOPE(nin=2, labels=["Continuous", *discretization_methods])
scope[0] = continuous
for idx, block in enumerate(discrete_blocks):
    scope[idx + 1] = block

bd.compile()
sim.run(bd, T=2)
sim.done(bd, block=True)
