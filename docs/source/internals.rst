*******************
Simulation-user API
*******************

This section describes the public API for users of ``bdsim``. This is the API that is
intended to be stable and supported across versions. It includes the classes and methods
that are used to build and simulate block diagrams.

BlockDiagram class
===================

A collection of blocks and wires that can be "executed" by :meth:`BDSim.run`. See the wiki's
`Connecting blocks <https://github.com/petercorke/bdsim/wiki/Connecting-blocks>`_ and `Blocks, wires
and plugs <https://github.com/petercorke/bdsim/wiki/Blocks%2C-Wires-and-Plugs>`_ pages for how this
fits together conceptually.

.. autoclass:: bdsim.BlockDiagram
   :members: compile, connect, report_summary, report_lists, dotfile, showgraph
   :undoc-members:
   :show-inheritance:


BDSim class
-----------

The run-time environment for executing a block diagram. See the wiki's
`Running <https://github.com/petercorke/bdsim/wiki/Running>`_ and `Runtime options
<https://github.com/petercorke/bdsim/wiki/Runtime-options>`_ pages for CLI/code options and how to
invoke it.

.. autoclass:: bdsim.BDSim
   :members: blockdiagram, run, blocks, block_library, report, done
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

BDStruct class
---------------

A struct-like container for storing simulation data, returned by :meth:`BDSim.run`. See the wiki's
`Simulation results <https://github.com/petercorke/bdsim/wiki/Simulation-results>`_ page for the full
layout — continuous vs. discrete/clocked state, watched signals, and the deprecated per-signal
accessors — rather than duplicating that explanation here.

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

BDSim, full listing
=====================

Full member listing for ``BDSim``/``BDStruct`` — see their descriptions and wiki links under
`Simulation-user API`_ above; this section differs only in showing every member, not the curated
public subset.

.. autoclass:: bdsim.BDSim
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :no-index:

.. autoclass:: bdsim.BDStruct
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :no-index:


BlockDiagram, full listing
=============================

Full member listing for ``BlockDiagram`` — see its description and wiki links under
`Simulation-user API`_ above.

.. autoclass:: bdsim.BlockDiagram
   :members: compile, connect, report_summary, report_lists, dotfile, showgraph
   :undoc-members:
   :show-inheritance:
   :no-index:

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

See the wiki's `Time stepping <https://github.com/petercorke/bdsim/wiki/Time-stepping>`_ page for how
``Clock``/``TimeQ`` drive the scheduled-event queue that also carries animation/movie frames.

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




