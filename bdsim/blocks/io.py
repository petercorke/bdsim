"""
Define real-time i/o blocks for use in block diagrams.  These are blocks that:

- have inputs or outputs
- have no state variables
- are a subclass of ``SourceBlock`` or ``SinkBlock``

Each class MyClass in this module becomes a method MYCLASS() of the Simulation object.
"""

from bdsim.components import SinkBlock, SourceBlock, block

"""
could have if/else chain here to define these classes according to the platform
or define each hardware in its own file, protected by if platform


Need some kind of synchronous update, evaluate the network, then wait for 
sample time then update all analog blocks.  Perhaps a new kachunk method.
"""

# class _AnalogIn(Source):
#     pass

# class _AnalogOut(Sink):
#     pass

# class _PWMOut(Sink):
#     pass

# class _DigitalIn(Source):
#     pass

# class _DigitalOut(Sink):
#     pass

# """
# digital i/o, specify a number a list of bit ports
# """

# class _Screen(Sink):
#     pass