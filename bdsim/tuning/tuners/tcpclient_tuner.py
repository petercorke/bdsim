import socket
from select import poll, POLLIN
from typing import List
import time
from threading import Thread

import flask
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

        self.stream_app = flask.Flask('dirtywebstream2')
        self.ip = _get_local_ip()
        self.stream_port = 7646
        self.video_streams = []
        self.signal_scopes = []
        self.signal_queue = []

        # unpack the data from msgpack into JSON for easy fast deserialization
        # self.unpacker = msgpack.Unpacker(use_list=False, raw=False)
        self.unpacker = msgpack.Unpacker()


    def register_video_stream(self, feed_fn, name):
        # eventually the socket will be used directly for the video stream.
        # until then we'll host the stream using flask here.

        # flask wants each endpoint to have separate '__name__'s...
        named_feed = lambda: feed_fn()
        named_feed.__name__ = name

        self.stream_app.route('/' + name)(named_feed)
        self.video_streams.append("http://%s:%d/%s" % (self.ip, self.stream_port, name))
        print('video_streams', self.video_streams)

    def register_signal_scope(self, name, n_signals, styles=None, labels=None):
        id = len(self.signal_scopes) + 1 # avoid 0 to use truthyness
        self.signal_scopes.append({'name': name, 'n': n_signals, 'styles': styles, 'labels': labels})
        return id

    def queue_signal_update(self, id, t, data):
        self.signal_queue.append([
            id - 1, # convert to index
            t, *data])

    def setup(self, params, _bd=None):
        self.setup_param_map(params)

        # host the flask videostrema app in a separate thread (for now)
        if any(self.video_streams):
            Thread(target=self.stream_app.run,
                args=((self.ip, self.stream_port)),
                daemon=True).start()

        print('video_streams', self.video_streams)

        msgpack.pack({
            'start_time': time.time() * 1000,
            'ip': self.ip,
            'video_streams': self.video_streams,
            'signal_scopes': self.signal_scopes,
            'params': self.get_param_defs(params)
        }, self.stream)
        self.stream.flush()

    def get_param_defs(self, params, subparams=True):
        # recursively produce parameter definitions to be serialized by msgpack
        param_defs = []
        for param in params:
            param_def = {'id': self.id2param.inverse[param]}
            for attr in param.gui_attrs:
                val = getattr(param, attr)
                if val is not None:
                    param_def[attr] = val.tolist() if isinstance(val, np.ndarray) \
                        else list(val) if isinstance(val, set) \
                        else val

            # if it doesn't have a user-set name, use its "used-in" string
            if 'name' not in param_def:
                param_def['name'] = param.full_name()

            if isinstance(param, HyperParam) and subparams:
                # construct {subparam_name: subparam_def}. could be rewritten better
                param_def['params'] = {k: self.get_param_defs(
                    [v])[0] for k, v in param.params.items()}
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
                msgpack.pack(self.get_param_defs([param], subparams=False), self.stream)
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
