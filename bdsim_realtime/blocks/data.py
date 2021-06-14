from typing import  Any, List, Union
from io import IOBase
import msgpack
import numpy as np

from bdsim.components import Block, Clock, Plug, SinkBlock, SourceBlock, block, ClockedBlock


# pivate helpers
_PKT_LEN_SIZE = 4
def _send_msgpack(transport: IOBase, obj: Any):
    data = msgpack.dumps(obj)
    transport.write(len(data).to_bytes(_PKT_LEN_SIZE, 'big') + data)
    transport.flush() # required

def _recv_msgpack(transport: IOBase) -> Any:
    data_len = int.from_bytes(transport.read(_PKT_LEN_SIZE), 'big')
    return msgpack.loads(transport.read(data_len))

@block
class DataSender(SinkBlock, ClockedBlock):

    def __init__(self, receiver: IOBase, *inputs: Union[Block, Plug], nin: int, clock: Clock, **kwargs: Any):
        super().__init__(nin=nin, nout=0, inputs=inputs, clock=clock, **kwargs)
        
        self._x0 = []
        self.receiver = receiver
        self.type = 'datasender'
        self.ready = False

        # SYN -> server(receiver):SYN-ACK -> ACK (copy TCP scheme)
        _send_msgpack(receiver, {
            'version': '0.0.1',
            'role': 'sender'
        })

        syn_ack = _recv_msgpack(receiver)
        assert syn_ack['version'] == '0.0.1'

        _send_msgpack(receiver, {
            'version': '0.0.1',
            'role': 'sender'
        })

    def next(self):
        _send_msgpack(self.receiver, self.inputs)
        return []
    
    def output(self, t: float):
        return []

@block
class DataReceiver(SourceBlock, ClockedBlock):
    # TODO: Should only work with bdsim-realtime

    def __init__(self, sender: IOBase, *, nout: int, clock: Clock, **kwargs: Any):
        super().__init__(nin=0, nout=nout, clock=clock, **kwargs)

        self._x0 = [0] * nout
        self.ndstates = len(self._x0)
        self.sender = sender
        self.type = 'datareceiver'

        syn = _recv_msgpack(sender)
        assert syn['version'] == '0.0.1'

        _send_msgpack(sender, {
            'version': '0.0.1',
            'role': 'receiver'
        })
        
        ack = _recv_msgpack(sender)
        assert ack['version'] == '0.0.1'
    
    def next(self):
        _x = _recv_msgpack(self.sender)
        return _x
    
    def output(self, t: float):
        return list(self._x)



@block
class CSV(SinkBlock):

    def __init__(
        self,
        file: IOBase,
        *inputs: Union[Block, Plug],
        nin: int,
        time: bool = True,
        **kwargs: Any
    ):
        super().__init__(nin=nin, nout=0, inputs=inputs, **kwargs)
        self.file = file
        self.type = "csv"
        self.time = time
    
    def step(self):
        if self.time:
            self.file.write(str(self.bd.state.t))
            the_rest = self.inputs
        else:
            self.file.write(str(self.inputs[0]))
            the_rest = self.inputs[1:]

        for inp in the_rest:
            self.file.write(",{}".format(inp))
        
        self.file.write('\n')
        self.file.flush()
