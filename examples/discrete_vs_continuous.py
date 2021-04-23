from bdsim import BDSim
# from scipy.signal import cont2discrete, tf2ss

sim = BDSim()
bd = sim.blockdiagram()

# clock = bd.clock(50, 'Hz')

step = bd.STEP(T=0)

# s_domain = 1, [1, 2, 4]
continuous = bd.LTI_SISO(1, [1, 2, 4], step)


# discretization_methods = []  # ['zoh']  # ['zoh', 'foh', 'bilinear',
# #   'euler', 'backward_diff']
# #   ('gbt', 0), ('gbt', 0.3), ('gbt', 0.6), ('gbt', 1)]

# discrete_blocks = []
# # because direct-passthrough is not supported and ss2tf returns a lot of numerators
# s_domain_statespace = tf2ss(*s_domain)
# for method in discretization_methods:
#     if isinstance(method, tuple):
#         method, alpha = method
#     else:
#         alpha = None
#     A, B, C, D, _ = cont2discrete(s_domain_statespace, clock.T, method, alpha)
#     discrete_blocks.append(bd.DISCRETE_LTI_SS(
#         clock, step, A=A, B=B, C=C, D=D))

# add them all to the scope
# scope = bd.SCOPE(nin=``, labels=["Continuous", *[
#     (meth if isinstance(meth, str) else meth[0])
#     for meth in discretization_methods
# ]])
scope = bd.SCOPE()
scope[0] = continuous
# for idx, block in enumerate(discrete_blocks):
#     scope[idx + 1] = block

bd.compile()
sim.run(bd, T=5)
sim.done(bd, block=True)
