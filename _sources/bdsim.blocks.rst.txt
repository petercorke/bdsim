.. _Block library:

*************
Block library
*************

.. include:: <isonum.txt>

The block diagrams comprise blocks which belong to one of a number of different categories. These come from
the package ``bdsim.blocks``, ``roboticstoolbox.blocks``, ``machinevisiontoolbox.blocks``.

Icons, if shown to the left of the black header bar, are as used with `bdedit <https://github.com/petercorke/bdsim/tree/master/bdsim/bdedit>`_.

.. inheritance-diagram:: bdsim.components.SourceBlock bdsim.components.SinkBlock bdsim.graphics.GraphicsBlock bdsim.components.FunctionBlock bdsim.components.TransferBlock bdsim.components.SubsystemBlock


Source blocks
=============

.. automodule:: bdsim.blocks.sources
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done, nin, nout, inlabels, outlabels

Sink blocks
===========

.. automodule:: bdsim.blocks.sinks
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done, nin, nout, inlabels, outlabels


Function blocks
===============

.. automodule:: bdsim.blocks.functions
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done, nin, nout, inlabels, outlabels

Transfer blocks
===============

.. automodule:: bdsim.blocks.transfers
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done, deriv, nin, nout, inlabels, outlabels

Discrete-time blocks
====================

.. automodule:: bdsim.blocks.discrete
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done, deriv, nin, nout, inlabels, outlabels
   
Linear algebra blocks
=====================

.. automodule:: bdsim.blocks.linalg
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done, nin, nout, inlabels, outlabels
  
Connection blocks
=================

.. automodule:: bdsim.blocks.connections
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done, nin, nout, inlabels, outlabels


External Toolbox blocksets
==========================

These blocks are defined within external Toolboxes or packages.


Robot blocks
------------

These blocks are defined within the Robotics Toolbox for Python.

Arm robots
^^^^^^^^^^

.. automodule:: roboticstoolbox.blocks.arm
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done, deriv, nin, nout, inlabels, outlabels

Mobile robots
^^^^^^^^^^^^^

.. automodule:: roboticstoolbox.blocks.mobile
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done, deriv, nin, nout, inlabels, outlabels

Multi rotor flying robots
^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: roboticstoolbox.blocks.uav
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done, deriv, nin, nout, inlabels, outlabels

Vision blocks
-------------

These blocks are defined within the Machine Vision Toolbox for Python.

.. automodule:: machinevisiontoolbox.blocks
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: output, reset, step, start, done, nin, nout, inlabels, outlabels

