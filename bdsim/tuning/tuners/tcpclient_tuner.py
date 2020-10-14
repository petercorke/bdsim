from socket import socket
# from select import poll, POLLIN, POLLOUT
import numpy as np
import msgpack

from bdsim.tuning.parameter import HyperParam
from .tuner import Tuner

TIMEOUT = 1e-6


class TcpClientTuner(Tuner):
    "client for a tuning server such as bdsim-webtuner"

    def __init__(self, hostname="localhost", port=31337):
        self.id2param = []  # id -> param

        # setup socket
        self.socket = socket()
        # dont block; throw error instead TODO: review this timeout value
        self.socket.settimeout(TIMEOUT)
        self.socket.connect((hostname, port))  # TODO: handle failure
        # convert to a file-like stream for efficiency & ergonomics
        self.stream = self.socket.makefile(mode='rwb', buffering=0)

        # # poll for updates
        # self.poll = poll()
        # self.poll.register(sock, POLLIN | POLLOUT)

        # unpack the data from msgpack into JSON for easy fast deserialization
        self.unpacker = msgpack.Unpacker(self.stream)

    def setup(self, params, _bd=None):
        self.setup_param_map(params)

        # temporary inverse mapping
        param2id = {param: param_id for param_id, param
                    in enumerate(self.id2param)}

        # transmit the parameter definitions
        # this is almost a one-off so doesn't need to be super efficient - use descriptive key names
        json_param_defs = {}
        for param_id, param in enumerate(self.id2param):
            param_def = json_param_defs[param_id] = {}
            for attr in param.gui_attrs:
                val = getattr(param, attr)
                param_def[attr] = val.tolist() if isinstance(
                    val, np.ndarray) else val

            param_def['val'] = param.val.tolist() \
                if isinstance(param.val, np.ndarray) else param.val

            if isinstance(param, HyperParam):
                param_def['params'] = [param2id[subparam]
                                       for subparam in param.params.vals()]

        print(json_param_defs)
        msgpack.pack(json_param_defs, self.stream)

    def setup_param_map(self, params):
        for param in params:
            if isinstance(param, HyperParam):
                # recurse through subparameters
                self.setup_param_map(param.params.values())
            else:
                # only build the param map for primitives
                self.id2param.append(param)

    def update(self):
        # Anything new on the line?
        # if self.poll.poll():

        # read all available streamed bytes and process any complete param changes
        # all param updates should be a JSON-tuple of [id, val]
        try:
            for param_id, val in self.unpacker:
                self.id2param[param_id].val = val
        except OSError as e:
            # Reset his so unpacker is allowed to call stream.read() again
            self.stream._timeout_occurred = False
