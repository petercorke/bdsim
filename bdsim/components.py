#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Components of the simulation system, namely blocks, wires and plugs.
"""

import numpy as np


                
class Wire:
    """
    A Wire object connects two block ports.  A Wire has a reference to the
    start and end ports.
    """
                
                
    def __init__(self, start=None, end=None, name=None):
        self.name = name
        self.id = None
        self.start = start
        self.end = end
        self.value = None
        self.type = None
        self.name = None

    @property
    def info(self):
        print("block:")
        for k,v in self.__dict__.items():
            print("  {:8s}{:s}".format(k+":", str(v)))
            
    def send(self, value):
        # dest is a Wire
        return self.end.block.setinput(self.end.port, value)
        
    def __repr__(self):
        return str(self) + ": " + self.fullname
    
    @property
    def fullname(self):
        return "{:s}[{:d}] --> {:s}[{:d}]".format(str(self.start.block), self.start.port, str(self.end.block), self.end.port)
    
    def __str__(self):
        s = "wire."
        if self.name is not None:
            s += self.name
        elif self.id is not None:
            s += str(self.id)
        else:
            s += '??'
        return s

# ------------------------------------------------------------------------- # 

class Plug:
    """
    Plugs are on the end of each wire, and connect a Wire to a specific port on
    a Block.
    """
    def __init__(self, block, port=0, type=None):
        self.block = block
        self.port = port
        self.type = type  # start
        
    
    @property
    def isslice(self):
        return isinstance(self.port, slice)
    
    @property
    def portlist(self):
        if self.isslice:
            if self.type == 'start':
                seq = range(0, self.block.nout)
                return seq[self.port]
            elif self.type == 'end':
                seq = range(0, self.block.nin)
                return seq[self.port]
            else:
                return None
        else:
            return [0]
        
    
    @property
    def width(self):
        return len(self.portlist)
            
        
    def __mul__(left, right):
        # called for the cases:
        # block * block
        # block * plug
        s = left.block.sim
        #assert isinstance(right, Block), 'arguments to * must be blocks not ports (for now)'
        w = s.connect(left, right)  # add a wire
        print('plug * ' + str(w))
        return right
        
    def __repr__(self):
        return str(self.block) + "[" + str(self.port) + "]"
    
# ------------------------------------------------------------------------- # 

blocklist = []

def block(cls):
    """
    Decorator for blocks
    
    :param cls: A block to be registered for the simulator
    :type cls: subclass of Block
    :return: the class
    :rtype: subclass of Block
    
    @block
    class MyBlock

    """
    
    if issubclass(cls, Block):
        blocklist.append(cls)  # append class to a global list
    else:
        raise ValueError('@block used on non Block subclass')
    return cls

# ------------------------------------------------------------------------- #

class Block:
    """
    A block object is the superclass of all blocks in the simulation environment.
    """
    
    _latex_remove = str.maketrans({'$':'', '\\':'', '{':'', '}':'', '^':'', '_':''})
    
    def __init__(self, blockclass=None, name=None, inp_names=None, outp_names=None, state_names=None, pos=None, **kwargs):
        #print('Block constructor'
        if name is not None:
            self.name_tex = name
            self.name = self._fixname(name)
        else:
            self.name = None
        self.pos = pos
        self.id = None
        self.out = []
        self.inputs = None
        self.updated = False
        self.shape = 'block' # for box
        self.blockclass = blockclass
        self._inport_names = None
        self._outport_names = None
        self._state_names = None
        
        self._inport_names = None
        self._outport_names = None
        self._state_names = None
        
        if inp_names is not None:
            self.inport_names(inp_names)
        if outp_names is not None:
            self.outport_names(outp_names)
        if state_names is not None:
            self.state_names(state_names)

        if len(kwargs) > 0:
            print('WARNING: unused arguments', kwargs.keys())
        
        # self.passthru
        

    @property
    def info(self):
        print("block: " + type(self).__name__)
        for k,v in self.__dict__.items():
            if k != 'sim':
                print("  {:11s}{:s}".format(k+":", str(v)))

        
    def __getitem__(self, port):
        # block[i] is a plug object
        return Plug(self, port)
    
    def __setitem__(self, i, port):
        pass
    
    def __mul__(left, right):
        # called for the cases:
        # block * block
        # block * plug
        s = left.sim
        assert isinstance(right, Block), 'arguments to * must be blocks not ports (for now)'
        s.connect(left, right)  # add a wire
        return right
        
        # make connection, return a plug
        
    def __str__(self):
        s = self.type + '.'
        if self.name is not None:
            s += self.name
        elif self.id is not None:
            s += 'block' + str(self.id)
        else:
            s += '??'
        return s
    
    def __repr__(self):
        return self.fullname
    

    def _fixname(self, s):
        return s.translate(self._latex_remove)

    def inport_names(self, names):
        self._inport_names = names
        
        for port,name in enumerate(names):
            setattr(self, self._fixname(name), self[port])
        
        
    def outport_names(self, names):
        self._outport_names = names
        for port,name in enumerate(names):
            setattr(self, self._fixname(name), self[port])

    def state_names(self, names):
        self._state_names = names
        
    def sourcename(self, port):

        w = self.inports[port]
        print(self, port, w)
        if w.name is not None:
            return w.name
        src = w.start.block
        srcp = w.start.port
        if src._outport_names is not None:
            return src._outport_names[srcp]
        return str(w.start)
    
    @property
    def fullname(self):
        return self.blockclass + "." + str(self)
    
    def reset(self):
        if self.nin > 0:
            self.inputs = [None] * self.nin
        self.updated = False
        
    def add_outport(self, w):
        port = w.start.port
        assert port < len(self.outports), 'port number too big'
        self.outports[port].append(w)
        
    def add_inport(self, w):
        port = w.end.port
        assert self.inports[port] is None, 'attempting to connect second wire to an input'
        self.inports[port] = w
        
    def setinput(self, port, value):
        """
        Receive input from a wire
        
        :param self: Block to be updated
        :type wire: Block
        :param port: Inut port to be updated
        :type port: int
        :param value: Input value
        :type val: any
        :return: If all inputs have been received
        :rtype: bool

        """
        
        # stash it away
        self.inputs[port] = value

        # check if all inputs have been assigned
        if all([x is not None for x in self.inputs]):
            self.updated = True
            #self.update()
        return self.updated
    
    def setinputs(self, *pos):
        assert len(pos) == self.nin, 'mismatch in number of inputs'
        self.reset()
        for i,val in enumerate(pos):
            self.inputs[i] = val
    
    def start(self, **kwargs):  # begin of a simulation
        pass
    

    def check(self):  # check validity of block parameters at start
        pass
    
    def done(self, **kwargs):  # end of simulation
        pass
    
    def step(self):  # valid
        pass
        
class Sink(Block):
    """
    A Sink is a subclass of Block that represents a block that has inputs
    but no outputs. Typically used to save data to a variable, file or 
    graphics.
    """
    
    blockclass = "sink"
    
    def __init__(self, movie=None, **kwargs):
        #print('Sink constructor')
        super().__init__(blockclass='sink', **kwargs)
        self.nin = 1
        self.nout = 0
        self.nstates = 0
        self.movie = movie

    def start(self):
        if self.movie is not None:
            self.writer = animation.FFMpegWriter(fps=10, extra_args=['-vcodec', 'libx264'])
            self.writer.setup(fig=self.fig, outfile=self.movie)
                
    def step(self):
        if self.movie is not None:
            self.writer.grab_frame()
                
                
    def done(self):
        if self.movie is not None:
            self.writer.finish()
            self.cleanup()
            

class Source(Block):
    """
    A Source is a subclass of Block that represents a block that has outputs
    but no inputs.  Its output is a function of parameters and time.
    """
    blockclass = "source"
    
    def __init__(self, **kwargs):
        #print('Source constructor')
        super().__init__(blockclass='source', **kwargs)
        self.nin = 0
        self.nout = 1
        self.nstates = 0
        
class Transfer(Block):
    """
    A Transfer is a subclass of Block that represents a block with inputs
    outputs and states. Typically used to describe a continuous time dynamic
    system, either linear or nonlinear.
    """
    blockclass = "transfer"
    
    def __init__(self, **kwargs):
        #print('Transfer constructor')
        super().__init__(blockclass='transfer', **kwargs)
        
    def reset(self):
        super().reset()
        self._x = self._x0
        return self._x
    
    def setstate(self, x):
        self._x = x[:self.nstates] # take as much state vector as we need
        return x[self.nstates:]   # return the rest
    
    def getstate(self):
        return self._x0
    
    def check(self):
        assert len(self._x0) == self.nstates, 'incorrect length for initial state'
                
    

class Function(Block):
    """
    A Function is a subclass of Block that represents a block that has inputs
    and outputs but no state variables.  Typically used to describe operations
    such as gain, summation or various mappings.
    """
    blockclass = "function"
    
    def __init__(self, **kwargs):
        super().__init__(blockclass='function', **kwargs)
        self.nstates = 0