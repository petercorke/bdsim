Block library
=============

.. include:: <isonum.txt>

The block diagrams comprise blocks which belong to one of a number of different categories. These come from
the package ``bdsim.blocks``.

.. inheritance-diagram:: bdsim.components.SourceBlock bdsim.components.SinkBlock bdsim.graphics.GraphicsBlock bdsim.components.FunctionBlock bdsim.components.TransferBlock bdsim.components.SubsystemBlock


Source blocks
-------------

.. automodule:: bdsim.blocks.sources
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done

Sink blocks
-----------

.. automodule:: bdsim.blocks.sinks
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done


Function blocks
---------------

.. automodule:: bdsim.blocks.functions
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done

Transfer blocks
---------------

.. automodule:: bdsim.blocks.transfers
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done, deriv

Discrete-time blocks
--------------------

.. automodule:: bdsim.blocks.discrete
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done, deriv

Connection blocks
-----------------

.. automodule:: bdsim.blocks.connections
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done

Robot blocks
------------

Arm robots
^^^^^^^^^^

.. automodule:: roboticstoolbox.blocks.arm
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done, deriv

Mobile robots
^^^^^^^^^^^^^

.. automodule:: roboticstoolbox.blocks.mobile
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done, deriv

Multi rotor flying robots
^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: roboticstoolbox.blocks.uav
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done, deriv


io blocks
---------

.. automodule:: bdsim.blocks.io
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: output, reset, step, start, done

Vision blocks
-------------

.. automodule:: bdsim.blocks.vision
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: output, reset, step, start, done

