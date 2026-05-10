*******************
Simulation-user API
*******************

This section describes the public API for users of ``bdsim``. This is the API that is
intended to be stable and supported across versions. It includes the classes and methods
that are used to build and simulate block diagrams.

BlockDiagram class
-------------------

This class describes a block diagram, a collection of blocks and wires that
can be "executed" by :meth:`BDSim.run`.

.. autoclass:: bdsim.BlockDiagram
   :members: compile, connect, report_summary, report_lists, dotfile, showgraph
   :undoc-members:
   :show-inheritance:


BDSim class
-----------

This class describes the run-time environment for executing a block diagram.

.. autoclass:: bdsim.BDSim
   :members: blockdiagram, run, blocks, block_library, report, done
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

BDStruct class
---------------

This class is a struct-like container for storing simulation data.  It is
returned by :meth:`BDSim.run` and contains the time vector, state history, and any watched variables.

.. autoclass:: bdsim.BDStruct
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__, __str__



**************
Developer API
**************

This section describes the internal API for developers of ``bdsim``. This includes
classes and methods that are used internally by the library, and may not be stable or
supported across versions. It is intended for developers who want to understand or
modify the internals of ``bdsim``.

BDSim class
=============

This class describes the run-time environment for executing a block diagram.

.. autoclass:: bdsim.BDSim
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

.. autoclass:: bdsim.BDStruct
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__


BlockDiagram class
====================

This class describes a block diagram, a collection of blocks and wires that
can be "executed".

.. autoclass:: bdsim.BlockDiagram
   :members: compile, connect, report_summary, report_lists, dotfile, showgraph
   :undoc-members:
   :show-inheritance:

Components
===========


Wire
-----

.. autoclass:: bdsim.Wire
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: __dict__, __weakref__, __array_ufunc__, __module__

Plug
-----

.. autoclass:: bdsim.Plug
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members:
   :exclude-members: __dict__, __weakref__, __array_ufunc__, __module__

Blocks
-------

.. autoclass:: bdsim.Block
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: 
   :exclude-members: __dict__, __weakref__, __array_ufunc__, __module__

Source block
^^^^^^^^^^^^^

.. autoclass:: bdsim.SourceBlock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: 

Sink block
^^^^^^^^^^^

.. autoclass:: bdsim.SinkBlock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: 

Function block
^^^^^^^^^^^^^^^

.. autoclass:: bdsim.FunctionBlock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: 

Continuous-time block
^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: bdsim.ContinuousBlock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members:

Discrete-time block
"""""""""""""""""""""

.. autoclass:: bdsim.SampledBlock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

.. autoclass:: bdsim.Clock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

.. autoclass:: bdsim.TimeQ
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

Subsystem block
^^^^^^^^^^^^^^^^

.. autoclass:: bdsim.SubsystemBlock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: 

Graphics block
^^^^^^^^^^^^^^^

.. autoclass:: bdsim.GraphicsBlock
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: 




