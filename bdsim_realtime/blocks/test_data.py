"Script for easily setting up a data-file recording server via command-line"

import os
from bdsim import BDSim
import bdsim_realtime
import socket
import threading

# add realtime blocks to BDSIMPATH so that the blocks are loaded by BDSim.load_blocks()
os.environ['BDSIMPATH'] = os.path.dirname(__file__)

# create blockdiagram with two clocks
bd = BDSim().blockdiagram()

sine = bd.WAVEFORM('sine')
sine_neg_2 = bd.GAIN(-2, sine)
sine3 = bd.GAIN(3, sine)

# create a socket transport pair 
send_socket, recv_socket = socket.socketpair()

# initialize the DATASENDER in another thread because it blocks until the handshake
thread = threading.Thread(
    target=bd.DATASENDER,
    args=(send_socket.makefile('rwb'), sine, sine_neg_2, sine3),
    kwargs=dict(
        nin=3,
        clock=bd.clock(50, 'Hz')
    )
)
thread.start()

# this should wait for the handshake triggered by the previous thread
receiver = bd.DATARECEIVER(
    recv_socket.makefile('rwb'),
    nout=3,
    # offset it by 30ms from sender's clock; so the sender executes at least once and this executes 10ms afterwards
    clock=bd.clock(50, 'Hz', offset=0.03)
)

# the thread should be finished at this point
thread.join(0)

# finally write the results to a CSV
csv_writer = bd.CSV(open('bdsim-dataout.csv', 'w'), receiver[0:3], nin=3)

# lets jam!
bdsim_realtime.run(bd)