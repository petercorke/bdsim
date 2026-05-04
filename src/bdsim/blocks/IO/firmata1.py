from __future__ import annotations
from pyfirmata import Arduino, util
import time

board = Arduino("/dev/cu.usbmodem1441401")
print("connected to Arduino/firmata node")

# x = board.send_sysex(0x61, b"\x00\x00\x00\x01")
# while True:
#     x = board.send_sysex(0x61, b"\x01\x00")
#     print(x)
#     time.sleep(1)

# ain = board.get_pin("a:0:i")
# aio = board.get_pin("d:6:p")
# # it = util.Iterator(board)
# # it.start()
# while True:
#     board.iterate()
#     print(x := ain.read())
#     aio.write(x)
#     time.sleep(0.5)

# aio = board.get_pin("d:6:p")
# out = 0.0
# while True:
#     aio.write(out)
#     out += 0.05
#     if out > 1:
#         out = 0
#     time.sleep(0.05)

dio = board.get_pin("d:6:o")
while True:
    dio.write(True)
    time.sleep(0.5)
    dio.write(False)
    time.sleep(0.5)


# standard firmata does digital and analog output, no encoder
# config firmata does digital and analog output, no encoder support
