from bdsim import BDSim
from scipy.signal import cont2discrete, tf2ss

sim = BDSim()
bd = sim.blockdiagram()

clock = bd.clock(50, 'Hz')

step = bd.STEP(T=0)

# convert to ss to avoid "direct passthrough".. ?
plant = tf2ss(1, [1, 2, 4])
A, B, C, _ = plant
continuous = bd.LTI_SS(step, A=A, B=B, C=C)

discretization_methods = ['zoh', 'foh', 'bilinear',
                          'euler', 'backward_diff',
                          ('gbt', 0), ('gbt', 0.3), ('gbt', 0.6), ('gbt', 1)]

discrete_blocks = []
for method in discretization_methods:
    if isinstance(method, tuple):
        method, alpha = method
    else:
        alpha = None
    A, B, C, D, _ = cont2discrete(plant, clock.T, method, alpha)
    discrete_blocks.append(bd.DISCRETE_LTI_SS(
        clock, step, A=A, B=B, C=C))

# add them all to the scope
scope = bd.SCOPE(
    stairs=[False] + [True] * len(discrete_blocks),
    labels=["Continuous", *(
        str(meth) for meth in discretization_methods
    )]
)
scope[0] = continuous
for idx, block in enumerate(discrete_blocks):
    scope[idx + 1] = block

bd.compile()
sim.run(bd, T=5)
sim.done(bd, block=True)
