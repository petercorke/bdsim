

# class _SubSystem(Function):
#     pass

# class _InPort(Source):
#     pass

# class _OutPort(Sink):
#     pass

"""
At compile time we remove/disable certain wires.
Block should have the subsystem enable status
"""

from bdsim.components import SubsystemBlock, block


@block
class Subsystem(SubsystemBlock):
    pass

class InputPort(SubsystemBlock):
    pass


class OutputPort(SubsystemBlock):
    pass



if __name__ == "__main__":

    import pathlib
    import os.path

    exec(open(os.path.join(pathlib.Path(__file__).parent.absolute(), "test_subsystems.py")).read())