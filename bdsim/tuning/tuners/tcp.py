from socket import socket
from select import poll, POLLIN, POLLOUT
from enum import Enum
import struct
import numpy as np

from bdsim.tuning.parameter import VecParam, HyperParam, NumParam, EnumParam
from .tuner import Tuner


class TcpTuner(Tuner):

    def __init__(self, server_addr=("localhost", 7331), titles="BDSim Tuner"):
        super().__init__(None, titles)

        self.param_map = {}  # id -> param
        self.server_addr = server_addr

        # setup socket
        self.socket = socket()
        self.socket.setblocking(None)  # dont block; throw error instead
        self.socket.connect(server_addr)  # todo: handle failure

        # poll for updates
        self.poll = poll()
        self.poll.register(socket, POLLIN | POLLOUT)

    def setup(self, params, _bd=None):
        self.setup_param_map(params)

    def setup_param_map(self, params):
        for param in params:
            if isinstance(param, HyperParam):
                # recurse through subparameters
                self.setup_param_map(param.params)
            else:
                # only build the param map for primitives
                id = len(params)
                self.param_map[id] = param

    def update(self):
        def retrieve(format):
            return struct.unpack(format, self.socket.recv(struct.calcsize(format)))

        def retrieve_val(param):
            if isinstance(param, VecParam):
                # always a numpy array
                return np.frombuffer(param.val)  # easy peasy

            elif isinstance(param, NumParam):
                # can be either float or int
                return retrieve('q' if type(param.val) is int  # i64
                                else 'd')  # f64

            elif isinstance(param, EnumParam):
                idx = retrieve('B')  # u8
                return param.oneof[idx]

            elif isinstance(param.val, str):
                return val_bytes.decode()

            else:  # assume its a bool
                return retrieve('?')

        # Anything new on the line?
        if self.poll.poll():
            _id = retrieve('H')  # u16
            # any data recieved here is generally from a primitive type
            val_bytes = retrieve('p')  # 1st byte is data_len, followed by data
            param = self.param_map[_id]
            param.val = retrieve_val(param)


class ParamPrimitives(Enum):
    Int = 1
    Vec = 2
    Str = 3
    Bool = 4
    Float = 5
