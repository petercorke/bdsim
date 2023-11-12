"""
Define real-time i/o blocks for use in block diagrams.  These are blocks that:

- have inputs or outputs
- have no state variables
- are a subclass of ``SourceBlock`` or ``SinkBlock``

"""
# The constructor of each class ``MyClass`` with a ``@block`` decorator becomes a method ``MYCLASS()`` of the BlockDiagram instance.

from bdsim.components import SinkBlock, SourceBlock
import time
import sys


class FirmataIO:
    board = None
    port = "/dev/cu.usbmodem1441401"

    def __init__(self):
        from pyfirmata import Arduino, util

        if FirmataIO.board is None:
            print(f"connecting to Arduino/firmata node on {self.port}...", end="")
            sys.stdout.flush()
            FirmataIO.board = Arduino(self.port)
            print(" done")

            # start a background thread to read inputs
            iterator = util.Iterator(FirmataIO.board)
            iterator.start()
            time.sleep(0.25)  # allow time for the iterator thread to start

    def pin(self, name):
        return FirmataIO.board.get_pin(name)


class AnalogIn(SourceBlock):
    nin = 0
    nout = 1

    def __init__(self, pin=None, scale=1.0, offset=0.0, **blockargs):
        super().__init__(**blockargs)
        self.board = FirmataIO()
        self.pin = self.board.pin(f"a:{pin}:i")
        self.scale = scale
        self.offset = offset

        # deal with random None values at startup
        while self.pin.read() == None:
            time.sleep(0.1)

    def output(self, t, inports, x):
        return [self.scale * self.pin.read() + self.offset]


class AnalogOut(SinkBlock):
    nin = 1
    nout = 0

    def __init__(self, pin=None, scale=1.0, offset=0.0, **blockargs):
        super().__init__(**blockargs)
        self.board = FirmataIO()
        self.pin = self.board.pin(f"d:{pin}:p")  # PWM output
        self.scale = scale
        self.offset = offset

    def step(self, t, inports):
        self.pin.write(self.scale * inports[0] + self.offset)


class DigitalIn(FirmataIO, SourceBlock):
    nin = 0
    nout = 1

    def __init__(self, pin=None, bool=False, **blockargs):
        super().__init__(**blockargs)
        self.pin = self.board.get_pin(f"d:{pin}:i")

    def output(self, t, inports, x):
        if self.bool:
            return [self.pin.read()]
        else:
            return [self.pin.read() > 0]


class DigitalOut(FirmataIO, SinkBlock):
    nin = 1
    nout = 0

    def __init__(self, pin=None, **blockargs):
        super().__init__(**blockargs)
        self.pin = self.board.get_pin(f"d:{pin}:o")

    def step(self, t, inports):
        self.pin.write(inports[0] > 0)
