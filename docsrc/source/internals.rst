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

.. autoclass:: bdsim.Struct
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

.. autoclass:: bdsim.BDSimState
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

.. autoclass:: bdsim.Wire
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__, __mul__, __setattr__, __getattr__, __setitem__, __getitem__

.. autoclass:: bdsim.Plug
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__, __mul__, __setattr__, __getattr__, __setitem__, __getitem__


.. autoclass:: bdsim.Block
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__, __mul__, __setattr__, __getattr__, __setitem__, __getitem__


.. autoclass:: bdsim.SourceBlock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__, __mul__, __setattr__, __getattr__, __setitem__, __getitem__

.. autoclass:: bdsim.SinkBlock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__, __mul__, __setattr__, __getattr__, __setitem__, __getitem__

.. autoclass:: bdsim.FunctionBlock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__, __mul__, __setattr__, __getattr__, __setitem__, __getitem__

.. autoclass:: bdsim.TransferBlock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__, __mul__, __setattr__, __getattr__, __setitem__, __getitem__

.. autoclass:: bdsim.SubsystemBlock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__, __mul__, __setattr__, __getattr__, __setitem__, __getitem__

.. autoclass:: bdsim.GraphicsBlock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__, __mul__, __setattr__, __getattr__, __setitem__, __getitem__


Discrete-time systems
---------------------

.. autoclass:: bdsim.ClockedBlock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

.. autoclass:: bdsim.Clock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

.. autoclass:: bdsim.PriorityQ
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

