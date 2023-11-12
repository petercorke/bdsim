Supporting classes
******************


.. inheritance-diagram:: bdsim.components


BDSim class
===========

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
==================

This class describes a block diagram, a collection of blocks and wires that
can be "executed".

.. autoclass:: bdsim.BlockDiagram
   :members:
   :undoc-members:
   :show-inheritance:

Components
==========


Wire
----

.. autoclass:: bdsim.Wire
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: __dict__, __weakref__, __array_ufunc__, __module__

Plug
----

.. autoclass:: bdsim.Plug
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members:
   :exclude-members: __dict__, __weakref__, __array_ufunc__, __module__

Blocks
------

.. autoclass:: bdsim.Block
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: 
   :exclude-members: __dict__, __weakref__, __array_ufunc__, __module__

Source block
^^^^^^^^^^^^

.. autoclass:: bdsim.SourceBlock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: 

Sink block
^^^^^^^^^^

.. autoclass:: bdsim.SinkBlock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: 

Function block
^^^^^^^^^^^^^^

.. autoclass:: bdsim.FunctionBlock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: 

Transfer function block
^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: bdsim.TransferBlock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: 

Subsystem block
^^^^^^^^^^^^^^^

.. autoclass:: bdsim.SubsystemBlock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: 

Graphics block
^^^^^^^^^^^^^^

.. autoclass:: bdsim.GraphicsBlock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: 


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

