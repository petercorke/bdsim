from socket import socket
from select import poll, POLLIN
import numpy as np
import msgpack
from bidict import bidict
from typing import List

from bdsim.tuning.parameter import HyperParam, VecParam, Param
from .tuner import Tuner

# TODO: review this timeout value
TIMEOUT = 1e-6


class TcpClientTuner(Tuner):
    "client for a tuning server such as bdsim-webtuner"

    def __init__(self, hostname="localhost", port=31337):
        self.id2param = bidict({})  # id <-> param

        # setup socket
        self.sock = sock = socket()
        # dont block; throw error instead
        sock.settimeout(TIMEOUT)
        sock.connect((hostname, port))  # TODO: handle failure
        # turn sock into file-like stream for efficiency (according to micropython docs)
        self.stream = sock.makefile('rwb')

        # implement update poll to prevent the socket from timing out when reading data
        self.poll = poll()
        self.poll.register(sock, POLLIN)

        # unpack the data from msgpack into JSON for easy fast deserialization
        # self.unpacker = msgpack.Unpacker(use_list=False, raw=False)
        self.unpacker = msgpack.Unpacker()

    def setup(self, params, _bd=None):
        self.setup_param_map(params)

        msgpack.pack(self.get_param_defs(params), self.stream)
        self.stream.flush()

    def get_param_defs(self, params):
        # recursively produce parameter definitions to be serialized by msgpack

        # transmit the parameter definitions
        param_defs = []
        for param in params:
            param_def = {'id': self.id2param.inverse[param]}
            for attr in param.gui_attrs:
                val = getattr(param, attr)
                if val is not None:
                    param_def[attr] = val.tolist() if isinstance(val, np.ndarray) \
                        else val

            # if it doesn't have a user-set name, use its "used-in" string
            if 'name' not in param_def:
                param_def['name'] = param.full_name()

            if isinstance(param, HyperParam):
                # construct {subparam_name: subparam_def}. could be rewritten better
                param_def['params'] = {k: self.get_param_defs(
                    [v])[0] for k, v in param.params.items()}
                param_def['hidden'] = list(param.hidden)
            else:
                param_def['val'] = param.val.tolist() \
                    if isinstance(param.val, np.ndarray) else param.val

            param_defs.append(param_def)

        return param_defs

    def setup_param_map(self, params: List[Param]):
        for param in params:
            id = len(self.id2param)
            self.id2param[id] = param

            def gui_reconstructor(param):
                msgpack.pack(self.get_param_defs([param]), self.stream)
                self.stream.flush()

            param.register_gui_reconstructor(gui_reconstructor)
            if isinstance(param, HyperParam):
                # recurse through sub-parameters
                self.setup_param_map(param.params.values())

    def update(self):
        # Anything new on the line?
        if self.poll.poll(TIMEOUT):
            # read all available streamed bytes and process any complete param changes
            # all param updates should be a JSON-like tuple of [id, val]

            # TODO: review this buffer size
            self.unpacker.feed(self.sock.recv(2048))

            for param_id, val in self.unpacker:
                param = self.id2param[param_id]

                # decode vectors into np arrays
                param.val = np.array(val) if isinstance(
                    param, VecParam) else val
        # try:
        #     # self.unpacker.feed(self.socket.recv(2**16))
        # except OSError as e:
        #     # Reset his so unpacker is allowed to call stream.read() again
        #     # self.stream._timeout_occurred = False
        #     pass
