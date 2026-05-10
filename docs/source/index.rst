.. bdsim documentation master file

*******************************************
BDSim: Block Diagram Simulation for Python
*******************************************
.. raw:: html

   <table>
   <tr>
   <td>
   <img width=350 src="https://github.com/petercorke/bdsim/raw/master/figs/bd1-sketch.png">
   </td>
   <td style="padding-left: 20px;">
   <pre style="font-size:10px;">
   # define the blocks
   demand = bd.STEP(T=1, name='demand')
   sum = bd.SUM('+-')
   gain = bd.GAIN(10)
   plant = bd.LTI_SISO(0.5, [2, 1])
   scope = bd.SCOPE(styles=['k', 'r--'])

   # connect the blocks
   bd.connect(demand, sum[0], scope[1])
   bd.connect(plant, sum[1])
   bd.connect(sum, gain)
   bd.connect(gain, plant)
   bd.connect(plant, scope[0])
   </pre>
   </td>
   </tr>
   </table>

Forget the frustration of dragging boxes and managing rigid GUIs. **bdsim** allows you
to harness the full expressiveness of Python to build, simulate, and analyze dynamic
systems. Unlike traditional tools like Simulink® or LabView®, we use a "code-first"
approach where the system is represented through native Python class and method calls. 

This architecture means your "wires" are no longer limited to simple numeric signals. In
``bdsim``, wires can communicate any Python type—including scalars, strings, lists,
dictionaries, NumPy arrays, custom objects, and even functions—enabling a level of
architectural flexibility and complexity that is difficult to achieve in graphical
environments.

.. toctree::
   :maxdepth: 3
   :caption: Code documentation:

   bdsim
   installation
   jupyter-notebooks
   bdsim.blocks
   internals