"Script for easily setting up a data-file recording server via command-line"

import os
from bdsim import BDSim
import bdsim_realtime
from serial import Serial


bd = BDSim().blockdiagram()

fileno = 0
while True:
    filepath = "bdsim-dataout-%d.csv" % fileno
    if not os.path.exists(filepath):
        break
    fileno += 1

recv = bd.DATARECEIVER(Serial("/dev/ttyUSB0", 115200), nout=3)

bd.CSV(open(filepath, 'w'), recv[:])

bdsim_realtime.run(bd)