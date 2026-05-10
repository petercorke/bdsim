.. _Block library:

*************
Block library
*************

.. include:: <isonum.txt>

The block diagrams comprise blocks which belong to one of a number of different categories. These come from
the package ``bdsim.blocks``, ``roboticstoolbox.blocks``, ``machinevisiontoolbox.blocks``.

Icons, if shown to the left of the black header bar, are as used with `bdedit <https://github.com/petercorke/bdsim/tree/master/bdsim/bdedit>`_.

.. inheritance-diagram:: bdsim.components.SourceBlock bdsim.components.SinkBlock bdsim.graphics.GraphicsBlock bdsim.components.FunctionBlock bdsim.components.ContinuousBlock bdsim.components.SampledBlock bdsim.components.SubsystemBlock
   :caption: Block class hierarchy, arrow from parent class to subclass

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

Display blocks
==============

.. automodule:: bdsim.blocks.displays
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done, nin, nout, inlabels, outlabels

Function blocks
===============

Functions
---------

.. automodule:: bdsim.blocks.functions
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done, nin, nout, inlabels, outlabels


Linear algebra
--------------

.. automodule:: bdsim.blocks.linalg
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done, nin, nout, inlabels, outlabels

Spatial math
------------

.. automodule:: bdsim.blocks.spatial
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


Continuous-time dynamics
========================

.. automodule:: bdsim.blocks.continuous
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done, deriv, nin, nout, inlabels, outlabels

Sampled-time dynamics
=====================


.. automodule:: bdsim.blocks.sampled
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :exclude-members: output, reset, step, start, done, deriv, nin, nout, inlabels, outlabels


External Toolbox blocksets
==========================

External toolbox block documentation is maintained in each toolbox project.

- Robotics Toolbox for Python: https://github.com/petercorke/robotics-toolbox-python
- Machine Vision Toolbox for Python: https://github.com/petercorke/machinevision-toolbox-python

