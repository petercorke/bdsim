.. Spatial Maths package documentation master file, created by
   sphinx-quickstart on Sun Apr 12 15:50:23 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Block diagrams for Python
=========================

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

This Python package enables modelling and simulation of dynamic systems
conceptualized in block diagram form, but represented in terms of Python class
and method calls.

Unlike Simulink® or LabView®, we write Python code rather than drawing boxes and
wires.  Wires can communicate any Python type such as scalars, strings, lists,
dictionaries, numpy arrays, other objects, and even functions.

    
.. toctree::
   :maxdepth: 2
   :caption: Code documentation:

   bdsim
   bdsim.blocks
   internals

