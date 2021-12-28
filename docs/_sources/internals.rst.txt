bdsim internals
===============


BDSim class
-----------

This class describes the run-time environment for executing a block diagram.

.. autoclass:: bdsim.BDSim
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

BlockDiagram class
------------------

This class describes a block diagram, a collection of blocks and wires that
can be "executed".

.. autoclass:: bdsim.blockdiagram
   :members:
   :undoc-members:
   :show-inheritance:

Components
----------

.. inheritance-diagram:: bdsim.components

.. automodule:: bdsim.components
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__, __mul__, __setattr__, __getattr__, __setitem__, __getitem__
