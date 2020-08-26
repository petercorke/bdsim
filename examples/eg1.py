#!/usr/bin/env python3

import bdsim
import time

bd = bdsim.BlockDiagram()

# define the blocks
demand = bd.STEP(T=1, pos=(0,0), name='demand')
sum = bd.SUM('+-', pos=(1,0))
gain = bd.GAIN(10, pos=(1.5,0))
plant = bd.LTI_SISO(0.5, [2, 1], name='plant', pos=(3,0))
#scope = bd.SCOPE(pos=(4,0), styles=[{'color': 'blue'}, {'color': 'red', 'linestyle': '--'})
scope = bd.SCOPE(styles=['k', 'r--'], pos=(4,0))

# connect the blocks
bd.connect(demand, sum[0], scope[1])
bd.connect(plant, sum[1])
bd.connect(sum, gain)
bd.connect(gain, plant)
bd.connect(plant, scope[0])

bd.compile()   # check the diagram
bd.report()    # list all blocks and wires

out = bd.run(5, watch=[plant])  # simulate for 5s

bd.dotfile('bd1.dot')  # output a graphviz dot file
bd.savefig('png')      # save all figures as pdf

time.sleep(10)
#bd.done(block=True)
