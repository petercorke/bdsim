import socket
from select import poll, POLLIN
from typing import List

import numpy as np
import msgpack
from bidict import bidict

from bdsim.tuning.parameter import HyperParam, VecParam, Param
from bdsim.tuning.tuners.tuner import Tuner

# TODO: review this timeout value
TIMEOUT = 1e-6

def _get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        host = s.getsockname()[0]
        s.close()
        return host
    except OSError: # if not on any network
        return "localhost"

class TcpClientTuner(Tuner):
    "client for a tuning server such as bdsim-webtuner"

    def __init__(self, hostname="localhost", port=31337):
        super().__init__()
        self.id2param = bidict({})  # id <-> param

        # setup socket
        self.sock = sock = socket.socket()
        # dont block; throw error instead
        sock.settimeout(TIMEOUT)
        sock.connect((hostname, port))  # TODO: handle failure
        # turn sock into file-like stream for efficiency (according to micropython docs)
        self.stream = sock.makefile('rwb')

        # implement update poll to prevent the socket from timing out when reading data
        self.poll = poll()
        self.poll.register(sock, POLLIN)

        self.video_streams = []
        self.signal_scopes = []
        self.signal_queue = []
        self.host = _get_local_ip()

        # unpack the data from msgpack into JSON for easy fast deserialization
        # self.unpacker = msgpack.Unpacker(use_list=False, raw=False)
        self.unpacker = msgpack.Unpacker()


    def register_video_stream(self):
        # eventually the socket will be used directly for the video stream.
        # until then we'll let DISPLAY blocks themselves host the stream
        # through a flask server which is hosted on an address we choose.

        def is_port_in_use(port):
            # taken from https://stackoverflow.com/questions/2470971/fast-way-to-test-if-a-port-is-in-use-using-python
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex((self.host, port)) == 0

        # find a free address to host on
        port = 7645 + 1
        while True:
            if not is_port_in_use(port):
                self.video_streams.append('http://' + self.host + ':' + str(port))
                return self.host, port

    def register_signal_scope(self, name, n_signals, styles=None, labels=None):
        id = len(self.signal_scopes) + 1 # avoid 0 to use truthyness
        self.signal_scopes.append({'name': name, 'n': n_signals, 'styles': styles, 'labels': labels})
        return id

    def queue_signal_update(self, id, t, data):
        self.signal_queue.append([id, t, *data])

    def setup(self, params, _bd=None):
        self.setup_param_map(params)

        msgpack.pack({
            'url': self.host,
            'video_streams': self.video_streams,
            'signal_scopes': self.signal_scopes,
            'params': self.get_param_defs(params)
        }, self.stream)
        self.stream.flush()

    def get_param_defs(self, params):
        # recursively produce parameter definitions to be serialized by msgpack
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
        super().update()

        # Anything new on the line?
        if self.poll.poll(TIMEOUT):
            # read all available streamed bytes and process any complete param val changes.
            # all param updates should be a JSON-like tuple of [id, val]

            # TODO: review this buffer size
            self.unpacker.feed(self.sock.recv(2048))

            for param_id, val in self.unpacker:
                param = self.id2param[param_id]

                # decode vectors into np arrays
                param.val = np.array(val) if isinstance(param, VecParam) else val

        # submit any queued signal updates
        for update in self.signal_queue:
            msgpack.pack(update, self.stream)
        self.stream.flush()
        self.signal_queue = []
