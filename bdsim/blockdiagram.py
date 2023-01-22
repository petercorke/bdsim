#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May 18 21:43:18 2020

@author: corkep
"""
import os
from pathlib import Path
import sys
import importlib
import inspect
import traceback
from collections import Counter, namedtuple
from copy import deepcopy
import numpy as np
from colored import fg, attr


from ansitable import ANSITable, Column

from bdsim.components import *


# ------------------------------------------------------------------------- #


class BlockDiagram:
    """
    Block diagram class.  This object is the parent of all blocks and wires in
    the system.

    :ivar wirelist: all wires in the diagram
    :vartype wirelist: list of Wire instances
    :ivar blocklist: all blocks in the diagram
    :vartype blocklist: list of Block subclass instances
    :ivar x: state vector
    :vartype x: np.ndarray
    :ivar compiled: diagram has successfully compiled
    :vartype compiled: bool
    :ivar blockcounter: unique counter for each block type
    :vartype blockcounter: collections.Counter
    :ivar blockdict: index of all blocks by category
    :vartype blockdict: dict of lists
    :ivar name: name of this diagram
    :vartype name: str
    """

    def __init__(self, name="main", **kwargs):

        self.wirelist = []  # list of all wires
        self.blocklist = []  # list of all blocks
        self.clocklist = []  # list of all clock sources
        self.compiled = False  # network has been compiled
        self.blockcounter = Counter()
        self.name = name
        self.nstates = 0
        self.ndstates = 0
        self._issubsystem = False
        self.blocknames = {}
        self.options = None
        self.n_auto_sum = 0
        self.n_auto_prod = 0
        self.n_auto_const = 0
        self.n_auto_gain = 0

    def __getitem__(self, b):
        return self.blocknames[b]

    def __len__(self):
        return len(self.blocklist)

    def __deepcopy__(self, memo):
        # deep copy a block diagram
        # retain references (don't copy) to blocks and the runtime
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if type(v).__name__ == "method":
                # it's a block factory method
                setattr(result, k, v)
            elif k == "runtime":
                # it's a reference to the runtime
                setattr(result, k, v)
            else:
                # otherwise, do a deepcopy
                setattr(result, k, deepcopy(v, memo))
        return result

    @property
    def issubsystem(self):
        return self._issubsystem

    def clock(self, *args, **kwargs):
        clock = Clock(*args, **kwargs)
        clock.bd = self
        self.clocklist.append(clock)
        return clock

    def add_block(self, block):
        if block.name in self.blocknames:
            raise ValueError("block {} already added".format(block.name))
        block.id = len(self.blocklist)
        if block.name is None:
            i = self.blockcounter[block.type]
            self.blockcounter[block.type] += 1
            block.name = "{:s}.{:d}".format(block.type, i)
        block.bd = self
        self.blocklist.append(block)  # add to the list of available blocks
        if block in self.blocknames:
            raise Warning(f"block name {block} is not unique")
        self.blocknames[block.name] = block

    def add_wire(self, wire, name=None):
        wire.id = len(self.wirelist)
        wire.name = name
        # just add wire to the list, gets instantiated at compile time
        # when add_output_wire and add_input_wire are called on the blocks
        return self.wirelist.append(wire)

    def __str__(self):
        return "BlockDiagram: {:s}".format(self.name)

    def __repr__(self):
        return str(self) + " with {:d} blocks and {:d} wires".format(
            len(self.blocklist), len(self.wirelist)
        )
        # for block in self.blocklist:
        #     s += str(block) + "\n"
        # s += "\n"
        # for wire in self.wirelist:
        #     s += str(wire) + "\n"
        # return s.lstrip("\n")

    def ls(self):
        for k, v in self.blockdict.items():
            print("{:12s}: ".format(k), ", ".join(v))

    def connect(self, start, *ends, name=None):

        """
        TODO:
            s.connect(out[3], in1[2], in2[3])  # one to many
            block[1] = SigGen()  # use setitem
            block[1] = SumJunction(block2[3], block3[4]) * Gain(value=2)
        """

        # start.type = 'start'

        for end in ends:

            if isinstance(start, Block):
                if isinstance(end, Block):
                    # connect(X, Y)
                    # wires from all outport to all inports
                    assert (
                        start.nout == end.nin
                    ), "can only connect blocks where number of input and output ports match"
                    for i in range(start.nout):
                        wire = Wire(StartPlug(start, i), EndPlug(end, i), name)
                        self.add_wire(wire)

                elif isinstance(end, Plug) and not end.isslice:
                    # connect(X, Y[i])
                    assert (
                        start.nout == 1
                    ), "can only connect single output block to a port"
                    end.type = "end"
                    wire = Wire(StartPlug(start, 0), end, name)
                    self.add_wire(wire)

                elif isinstance(end, Plug) and end.isslice:
                    # connect(X, Y[m:n])
                    assert (
                        start.nout == end.width
                    ), "can only connect single output block to an input port slice of width 1"
                    end.type = "end"
                    for i in range(start.nout):
                        wire = Wire(StartPlug(start, i), end[i], name)
                        self.add_wire(wire)

                else:
                    raise ValueError("bad end type")

            elif isinstance(start, Plug) and not start.isslice:

                if isinstance(end, Block):
                    # connect(X[i], Y)
                    # wires from all outport to all inports
                    assert (
                        end.nin == 1
                    ), "can only connect a port to a block with single input port"
                    wire = Wire(start, EndPlug(end, 0), name)
                    self.add_wire(wire)

                elif isinstance(end, Plug) and not end.isslice:
                    # connect(X[i], Y[i])
                    end.type = "end"
                    wire = Wire(start, end, name)
                    self.add_wire(wire)

                elif isinstance(end, Plug) and end.isslice:
                    # connect(X[i], Y[m:n])
                    assert (
                        end.width == 1
                    ), "can only connect output port to an input port slice of width 1"
                    end.type = "end"
                    wire = Wire(start, end[0], name)
                    self.add_wire(wire)

                else:
                    raise ValueError("bad end type")

            elif isinstance(start, Plug) and start.isslice:

                if isinstance(end, Block):
                    # connect(X[i:j], Y)
                    assert (
                        start.width == end.nin
                    ), "can only connect output slice to a block with matching number of input ports"
                    for i in range(end.nin):
                        wire = Wire(start[i], EndPlug(end, i), name)
                        self.add_wire(wire)

                elif isinstance(end, Plug) and not end.isslice:
                    # connect(X[i:j], Y[m])
                    assert (
                        start.width == 1
                    ), "can only connect output slice of width 1 to a port"
                    wire = Wire(start[0], end, name)
                    self.add_wire(wire)

                if isinstance(end, Plug) and end.isslice:
                    # connect(X[i:j], Y[m:n])
                    assert (
                        start.width == end.width
                    ), "can only connect port slices of same width"
                    for i in range(start.width):
                        wire = Wire(start[i], end[i], name)
                        self.add_wire(wire)

                else:
                    raise ValueError("bad end type")

            else:
                raise ValueError("bad start type")

    # ---------------------------------------------------------------------- #

    def compile(
        self, subsystem=False, doimport=True, evaluate=True, report=False, verbose=True
    ):
        """
        Compile the block diagram

        :param subsystem: importing a subsystems, defaults to False
        :type subsystem: bool, optional
        :param doimport: import subsystems, defaults to True
        :type doimport: bool, optional
        :raises RuntimeError: various block diagram errors
        :return: Compile status
        :rtype: bool

        Performs a number of operations:

            - Check sanity of block parameters
            - Recursively clone and import subsystems
            - Check for loops without dynamics
            - Check for inputs driven by more than one wire
            - Check for unconnected inputs and outputs
            - Link all output ports to outgoing wires
            - Link all input ports to incoming wires
            - Evaluate all blocks in the network

        """

        # name the elements
        self.nblocks = len(self.blocklist)
        self.nwires = len(self.wirelist)

        error = False

        self.nstates = 0
        self.ndstates = 0
        self.statenames = []
        self.dstatenames = []
        self.blocknames = {}

        if not subsystem and verbose:
            print("\nCompiling:")

        # process all subsystem imports
        # ssblocks = [b for b in self.blocklist if b.type == 'subsystem']
        # for b in ssblocks:
        #     print('  importing subsystem', b.name)
        #     if b.ssvar is not None:
        #         print('-- Wiring in subsystem', b, 'from module local variable ', b.ssvar)
        self.blocklist, self.wirelist = self._subsystem_import(self, None)

        # check that wires all point to valid blocks
        for w in self.wirelist:
            if w.start.block not in self.blocklist:
                raise RuntimeError(
                    f"wire {w} starts at unreferenced block {w.start.block}"
                )
            if w.end.block not in self.blocklist:
                raise RuntimeError(f"wire {w} ends at unreferenced block {w.end.block}")

        # run block specific checks
        for b in self.blocklist:
            try:
                b.check()
            except:
                raise RuntimeError("block failed check " + str(b))

        # build a dictionary of all block names
        for b in self.blocklist:
            self.blocknames[b.name] = b

        # visit all stateful blocks
        for b in self.blocklist:
            if b.blockclass == "transfer":
                self.nstates += b.nstates
                if b._state_names is not None:
                    assert (
                        len(b._state_names) == b.nstates
                    ), "number of state names not consistent with number of states"
                    self.statenames.extend(b._state_names)
                else:
                    # create default state names
                    self.statenames.extend(
                        [b.name + "x" + str(i) for i in range(0, b.nstates)]
                    )
            if b.blockclass == "clocked":
                self.ndstates += b.ndstates
                if b._state_names is not None:
                    assert (
                        len(b._state_names) == b.nstates
                    ), "number of state names not consistent with number of states"
                    self.dstatenames.extend(b._state_names)
                else:
                    # create default state names
                    self.statenames.extend(
                        [b.name + "X" + str(i) for i in range(0, b.nstates)]
                    )

        # initialize lists of input and output ports
        for b in self.blocklist:
            b.output_wires = [[] for i in range(0, b.nout)]
            b.input_wires = [None for i in range(0, b.nin)]
            b.sources = [None for i in range(0, b.nin)]

            # used to build execution plan
            # TODO: might overlap with sources
            b._parents = [None for i in range(0, b.nin)]

        # connect the source and destination blocks to each wire
        for w in self.wirelist:
            try:
                w.start.block.add_output_wire(w)
                w.end.block.add_input_wire(w)
                w.end.block._parents[w.end.port] = w.start.block

            except:
                print(fg("red"))
                print("error connecting wire ", w.fullname + ": ", sys.exc_info()[1])
                print(attr(0))
                error = True

        # check connections every block
        for b in self.blocklist:
            # check all inputs are connected
            for port, connection in enumerate(b.input_wires):
                if connection is None:
                    print(
                        "  ERROR: [{:s}] input {:d} is not connected".format(
                            str(b), port
                        )
                    )
                    error = True

            # check all outputs are connected
            for port, connections in enumerate(b.output_wires):
                if len(connections) == 0:
                    print(
                        "  INFORMATION: [{:s}] output {:d} is not connected".format(
                            str(b), port
                        )
                    )

            if b._inport_names is not None:
                assert (
                    len(b._inport_names) == b.nin
                ), "incorrect number of input names given: " + str(b)
            if b._outport_names is not None:
                assert (
                    len(b._outport_names) == b.nout
                ), "incorrect number of output names given: " + str(b)
            if b._state_names is not None:
                assert (
                    len(b._state_names) == b.nstates
                ), "incorrect number of state names given: " + str(b)

        # check for cycles of function blocks
        def _DFS(path):
            start = path[0]
            tail = path[-1]
            for outgoing in tail.output_wires:
                # for every port on this block
                for w in outgoing:
                    dest = w.end.block
                    if dest == start:
                        print(
                            "  ERROR: cycle found: ",
                            " - ".join([str(x) for x in path + [dest]]),
                        )
                        return True
                    if dest.blockclass == "function":
                        return _DFS(path + [dest])  # recurse
            return False

        for b in self.blocklist:
            if b.blockclass == "function":
                # do depth first search looking for a cycle
                if _DFS([b]):
                    error = True

        if error:
            if not subsystem:
                raise RuntimeError("could not compile system")

        # create the execution plan/schedule
        self.execution_plan()

        ## evaluate the network once to check out wire types
        x = self.getstate0()

        for clock in self.clocklist:
            clock._x = clock.getstate0()

        if report:
            self.report()
            self.plan_print()

        if not subsystem and evaluate:
            # run all the blocks for one step
            try:
                self.evaluate_plan(x, 0.0, sinks=False)
            except RuntimeError as err:
                print("\nFrom compile: unrecoverable error in value propagation:", err)
                traceback.print_exc(file=sys.stderr)
                error = True

        if error:
            # show report if there was an error
            if not report:
                self.report()
            if not subsystem:
                raise RuntimeError("could not compile system")
        else:
            self.compiled = True

        return self.compiled

    def _subsystem_import(self, bd, sspath):

        blocks = []
        wires = bd.wirelist

        for b in bd.blocklist:
            # rename the block to include subsystem path
            if sspath is not None:
                b.name = sspath + "/" + b.name

            if b.type == "subsystem":
                # deal with a subsystem
                #  - recurse to import it
                #  - add its blocks and wires to the set
                ssb, ssw = self._subsystem_import(b.subsystem, b.name)
                blocks.extend(ssb)
                wires.extend(ssw)

                # INPORT/OUTPORT blocks now become simple pass throughs
                # same number of inputs and outputs
                b.inport.nin = b.inport.nout
                b.outport.nout = b.outport.nin

                # modify the wiring, keep the INPORT/OUTPORT blocks but lose
                # the SUBSYSTEM blocks
                for w in bd.wirelist:
                    # for all wires at this level, find those that connect
                    # to the subsystem and tweak them
                    if w.start.block == b:
                        # SS output
                        w.start.block = b.outport
                    if w.end.block == b:
                        # SS input
                        w.end.block = b.inport

            else:
                # not a subsystem, just add the block to the list
                blocks.append(b)

        # systematically renumber all blocks and wires
        for i, b in enumerate(blocks):
            b.id = i
        for i, w in enumerate(wires):
            w.id = i
        return blocks, wires

    # ---------------------------------------------------------------------- #

    def evaluate_plan(self, x, t, checkfinite=True, debuglist=[], sinks=True):
        """
        Evaluate all blocks in the network

        :param x: state :type x: numpy.ndarray :param t: current time :type t:
        float :param checkfinite: check for Inf or Nan values in block outputs
        :type checkfinite: bool :return: state derivative :rtype: numpy.ndarray

        Performs the following steps:

        1. Partition the state vector ``x`` to all stateful blocks
        2. Execute the blocks in the order given by the ``plan``. The block
           outputs are "sent" to their connected inputs.

        Sink blocks are not executed here, but after completion their inputs
        will all be valid.
        """

        # TODO: don't copy outputs to inputs of next block, have inputs
        # pull the value from connected inputs

        try:
            self.state.t = t
        except:
            pass

        self.runtime.DEBUG("state", ">>>>>>>>> t={}, x={} >>>>>>>>>>>>>>>>", t, x)

        # reset all the blocks ready for the evalation
        self.reset()

        # split the state vector to stateful blocks
        for b in self.blocklist:
            if b.blockclass == "transfer":
                x = b.setstate(x)

        # split the discrete state vector to clocked blocks
        for clock in self.clocklist:
            clock.setstate()

        self.runtime.DEBUG("propagate", "t={:.3f}", t)

        for sequence, group in enumerate(self.plan):

            # self.runtime.DEBUG('propagate', '---- sequence = ', sequence)

            for b in group:
                # ask the block for output, check for errors
                try:
                    out = b.output(t)
                except Exception as err:
                    # output method failed, report it
                    print(fg("red"))
                    print(
                        "--Error at t={:f} when computing output of [{:s}::{:s}]".format(
                            t, b.type, str(b)
                        )
                    )
                    print()
                    # print('  {}'.format(err))
                    traceback.print_exc(limit=-1, file=sys.stderr)

                    print()
                    for i, input in enumerate(b.inputs):
                        print(f"Input[{i}] = {input}")

                    if b.nstates > 0:
                        print(f"Block state x = {b._x}")
                    print(attr(0))
                    raise RuntimeError from None

                self.runtime.DEBUG("propagate", "block {:s}: output = {}", b, out)

                # check that output is a list of correct length
                if not isinstance(out, (tuple, list)):
                    raise AssertionError(
                        f"block {b} output {b} must be a list: {type(out)}"
                    )
                if len(out) != b.nout:
                    raise AssertionError(
                        f"block {b} output {b} has incorrect length: {len(out)} instead of {b.nout}"
                    )

                # TODO check output validity once at the startq

                # check it has no nan or inf values
                if (
                    checkfinite
                    and isinstance(out, (int, float, np.ndarray))
                    and not np.isfinite(out).any()
                ):
                    raise RuntimeError(f"block {b} output contains NaN")

                # # send block outputs to all downstream connected blocks
                # for (port, outwires) in enumerate(b.outports): # every port
                #     value = out[port]
                #     for w in outwires:     # every wire

                #         self.DEBUG('propagate', '  [{}] = {} -->  {}[{}]', port, value, w.end.block.name, w.end.port)

                #         # send value to wire
                #         w.send(value)

                #         # TODO send return status no longer needed
                #         # TODO use common error handler in all cases above
                b.output_values = out

        # gather the derivative
        YD = self.deriv()

        self.runtime.DEBUG("deriv", YD)
        return YD

    def execution_plan(self):
        """
        Create execution plan

        The plan is saved in the attribute ``plan`` and is a list
        ``[L0, L1, ... LN]`` where each ``Li`` is a list of blocks.  The blocks
        in the lists are executed sequentially, ie. all the blocks in ``L0``
        then all the blocks in ``L1`` etc.

        The plan ensures that the inputs of all blocks in ``Li`` have been
        previously computed.

        .. note::
            - The plan is essentially a dataflow graph.
            - The blocks in list ``Li`` could potentially be executed in
              parallel.
            - Constant blocks and stateful blocks are all executed in ``L0``
            - The block attribute ``_sequence`` is ``i`` and indicates its
              execution order

        :seealso: :func:`plan_print`, :func:`plan_dotfile`
        """

        plan = []
        group = []
        for b in self.blocklist:
            b._sequence = None
            if b.blockclass in ("source", "transfer", "clocked"):
                b._sequence = 0
                group.append(b)
        plan.append(group)
        sequence = len(plan)

        while True:
            group = []
            for b in self.blocklist:
                if b._sequence is not None:
                    continue  # already has a sequence assigned

                if all(
                    [
                        p._sequence < sequence if p._sequence is not None else False
                        for p in b._parents
                    ]
                ):
                    group.append(b)

            for b in group.copy():
                b._sequence = sequence
                if b.blockclass in ("sink", "graphics"):
                    group.remove(b)
            if len(group) == 0:
                break
            plan.append(group)
            sequence += 1

        self.plan = plan

    def plan_print(self):
        """
        Display execution plan in tabular form

        :seealso: :func:`execution_plan`, :func:`plan_dotfile`
        """
        table = ANSITable(
            Column("Sequence"),
            Column("Blocks", colalign="<", headalign="^"),
            border="thin",
        )

        for sequence, group in enumerate(self.plan):
            table.row(sequence, ", ".join([str(b) for b in group]))

        table.print()

    def plan_dotfile(self, filename):
        """
        Write a GraphViz dot file representing the execution schedule

        :param file: Name of file to write to
        :type file: str

        The file can be processed using neato or dot::

            % dot -Tpng -o out.png dotfile.dot

        Display execution plan as a dataflow graph.

        :seealso: :func:`execution_plan`, :func:`plan_print`
        """

        if isinstance(filename, str):
            file = open(filename, "w")
        else:
            file = filename

        header = r"""digraph G {

    graph [splines=ortho, rankdir=LR, splines=spline]
    node [shape=box]
    
    """
        file.write(header)

        for sequence, group in enumerate(self.plan):
            # for each execution group, place the blocks in a subgraph
            file.write("\tsubgraph step{:d} {{\n".format(sequence))
            file.write("\t\trank=same;\n")

            for b in group:
                file.write('\t\t"{:s}"\n'.format(b.name))

            file.write("\t}\n\n")

        # connect them to their parents, except if a transfer block
        for b in self.blocklist:
            if not b.blockclass == "transfer":
                for p in b._parents:
                    file.write('\t"{:s}" -> "{:s}"\n'.format(p.name, b.name))

        file.write("}\n")

    # ---------------------------------------------------------------------- #

    def _debugger(self, state=None, integrator=None):

        if state.t_stop is not None and state.t < state.t_stop:
            return

        state.t_stop = None
        print("\n")
        while True:
            cmd = input(f"(bdsim, t={state.t:.4f}) ")

            if len(cmd) == 0:
                continue

            if cmd[0] == "p":
                # print variables
                if len(cmd) > 1:
                    id = int(cmd[1:])
                    b = self.blocklist[id]
                    print(b.name, b.output(t=state.t))
                else:
                    for b in self.blocklist:
                        if b.nout > 0:
                            print(b.name, b.output(t=state.t))
            elif cmd[0] == "i":
                print(integrator.status, integrator.step_size, integrator.nfev)
            elif cmd[0] == "s":
                # step
                break
            elif cmd[0] == "c":
                # continue
                self.debug_stop = False
                self.t_stop = None
                break
            elif cmd[0] == "t":
                self.t_stop = float(cmd[1:])
                break
            elif cmd[0] == "q":
                sys.exit(1)
            elif cmd[0] in "h?":
                print("p    print all outputs")
                print("pI   print block id I output")
                print("i    print integrator status")
                print("s    single step")
                print("c    continue")
                print("tT   stop at or after time T")
                print("q    quit")

    # ---------------------------------------------------------------------- #

    def report_summary(self):
        """
        Print a summary of block diagram.

        Print a table with 4 columns:

        1. Block name, sorted in alphabetical order
        2. The input port (if not a source block)
        3. The block driving this port (if not a source block)
        4. The type of value driving this port (if not a source block)

        If the block is an event source, add a ``@`` suffix.
        """
        table = ANSITable(
            Column("block", headalign="^", colalign="<"),
            Column("inport", headalign="^", colalign="<"),
            Column("source", headalign="^", colalign="<"),
            Column("source type", headalign="^", colalign="<"),
            border="thin",
        )

        first = True
        legend = None
        for b in sorted(self.blocklist, key=lambda x: x.name):
            name = str(b)
            if isinstance(b, EventSource):
                name += "@"
                legend = "Note: @ = event source"
            # add a divider before each subsequent row
            if not first:
                table.rule()
            else:
                first = False

            # print the details
            if len(b.sources) > 0:
                # non source block, list all its inputs, one per row
                for (port, source) in enumerate(b.sources):  # every port

                    value = b.input(port)
                    typ = type(value).__name__
                    if isinstance(value, np.ndarray):
                        typ += "{:s}.{:s}".format(str(value.shape), str(value.dtype))

                    table.row(name if port == 0 else "", port, source.block.name, typ)
            else:
                # source block, just list the name
                table.row(name, "", "", "")
        table.print()
        if legend:
            print(legend + "\n")

    def report(self):
        """
        Print a tabular report about the block diagram.

        Print the important lists in pretty format.

        * block list, all blocks
        * wire list, all wires
        * clock list, all discrete time clocks

        """
        # print all the blocks
        print("\nBlocks::\n")
        table = ANSITable(
            Column("id"),
            Column("name"),
            Column("nin"),
            Column("nout"),
            Column("nstate"),
            Column("ndstate"),
            Column("type", headalign="^", colalign="<"),
            border="thin",
        )
        for b in self.blocklist:
            table.row(b.id, str(b), b.nin, b.nout, b.nstates, b.ndstates, b.type)
        table.print()

        # print all the wires
        print("\nWires::\n")
        table = ANSITable(
            Column("id"),
            Column("from", headalign="^"),
            Column("to", headalign="^"),
            Column("description", headalign="^", colalign="<"),
            Column("type", headalign="^", colalign="<"),
            border="thin",
        )
        for w in self.wirelist:
            start = "{:d}[{:d}]".format(w.start.block.id, w.start.port)
            end = "{:d}[{:d}]".format(w.end.block.id, w.end.port)

            try:
                value = w.end.block.inputs[w.end.port]
                typ = type(value).__name__
                if isinstance(value, np.ndarray):
                    typ += "{:s}.{:s}".format(str(value.shape), str(value.dtype))
            except:
                typ = "??"
            table.row(w.id, start, end, w.fullname, typ)
        table.print()

        if len(self.clocklist) > 0:
            # print all the clocked blocks
            print("\nClocked blocks::\n")
            table = ANSITable(
                Column("id"),
                Column("block"),
                Column("clock"),
                Column("period"),
                Column("offset"),
                border="thin",
            )
            for b in self.blocklist:
                if b.blockclass == "clocked":
                    c = b.clock
                    table.row(b.id, str(b), c.name, c.T, c.offset)
            table.print()

        print("\nContinuous state variables: {:d}".format(self.nstates))
        print("Discrete state variables:   {:d}".format(self.ndstates))

        if not self.compiled:
            print("** System has not been compiled, or had a compile time error")

    # ---------------------------------------------------------------------- #

    def _error_handler(self, where, block):
        # called from except clause

        import traceback
        import types

        t, v, tb = sys.exc_info()  # get the exception

        print(fg("red"))  # red text

        # print the traceback
        print(
            f"[{where}]: exception {t.__name__} occurred in {block.type} block {block.name}  "
        )
        print(f"  {v}\n")
        traceback.print_tb(tb)

        # print all block inputs
        print()
        for i in range(block.nin):
            input = block.inputs[i]
            print(
                f"input {i} from {block.sources[i].block.name} [{input.__class__.__name__}]"
            )
            print("  ", input)

        print(attr(0))  # default text

        # traceback = err[2]
        # back_frame = traceback.tb_frame.f_back

        # back_tb = types.TracebackType(tb_next=None,
        #                           tb_frame=back_frame,
        #                           tb_lasti=back_frame.f_lasti,
        #                           tb_lineno=back_frame.f_lineno)
        # raise RuntimeError('Fatal failure').with_traceback(back_tb)
        raise RuntimeError("Fatal failure") from None

    def getstate0(self):
        # get the state from each stateful block
        x0 = np.array([])
        for b in self.blocklist:
            try:
                if b.blockclass == "transfer":
                    x0 = np.r_[x0, b.getstate0()]
                # print('x0', x0)
            except:
                self._error_handler("getstate0", b)
        return x0

    def reset(self):
        """
        Reset conditions within every active block.  Most importantly, all
        inputs are marked as unknown.

        Invokes the `reset` method on all blocks.

        """
        for b in self.blocklist:
            try:
                b.reset()
            except:
                self._error_handler("reset", b)

    def step(self, state=None):
        """
        Step all blocks

        :param state: simulation state, defaults to None
        :type state: SimState, optional
        :param graphics: graphics enabled, defaults to False
        :type graphics: bool, optional

        Tell all blocks to take action on new inputs by invoking their
        ``step`` method and passing the ``state`` object.  Used to save
        results to a figure or file.

        Called at the end of every integration interval.

        .. note::
            - if ``graphics`` is False, Graphics blocks are not called
        """

        # TODO could be done by output method, even if no outputs

        for b in self.blocklist:
            if b.isgraphics and not state.options.graphics:
                continue  # skip graphics blocks
            try:
                b.step(state=state)
            except:
                self._error_handler("step", b)

    def deriv(self):
        """
        Harvest derivatives from all blocks .
        """
        YD = np.array([])
        for b in self.blocklist:
            if b.blockclass == "transfer":
                try:
                    yd = b.deriv().flatten()
                    if not isinstance(yd, np.ndarray):
                        raise AssertionError(f"deriv: block {b} did not return ndarray")
                    if yd.ndim != 1 or yd.shape[0] != b.nstates:
                        raise AssertionError(
                            f"deriv: block {b} returns wrong shape {yd.shape}, should be ({b.nstates},)"
                        )
                    YD = np.r_[YD, yd]
                except:
                    self._error_handler("deriv", b)
        return YD

    def start(self, graphics=False, state=None, **kwargs):
        """
        Start all blocks

        :param state: simulation state, defaults to None
        :type state: SimState, optional
        :param graphics: graphics enabled, defaults to False
        :type graphics: bool, optional

        Inform all blocks that BlockDiagram execution is about to start by
        invoking their ``start`` method and passing the ``state`` object.  Used
        to open files, create figures etc.

        .. note:: if ``graphics`` is False, Graphics blocks are not called

        """

        for c in self.clocklist:
            try:
                c.start(state=state, **kwargs)
            except:
                self._error_handler("start clock", c)

        # safe wrapper for block starting, does error handling
        for b in self.blocklist:
            if b.isgraphics and not graphics:
                continue
            # print('starting block', b)
            try:
                b.start(state=state, **kwargs)
            except:
                self._error_handler("block.start", b)

    def initialstate(self):
        for b in self.blocklist:
            if b.blockclass in ("transfer", "clocked"):
                b._x = b._x0

    def done(self, block=False, graphics=False):
        """
        Finishup all blocks

        :param state: simulation state, defaults to None
        :type state: SimState, optional
        :param graphics: graphics enabled, defaults to False
        :type graphics: bool, optional

        Inform all blocks that BlockDiagram execution is complete by invoking their
        ``done`` method and passing options.  Used
        to close files, display figures etc.

        .. note:: if ``graphics`` is False, Graphics blocks are not called
        """
        for b in self.blocklist:
            if b.isgraphics and not graphics:
                continue
            try:
                b.done(block=block)
            except:
                self._error_handler("block.done", b)

    def dotfile(self, filename):
        """
        Write a GraphViz dot file representing the network.

        :param file: Name of file to write to
        :type file: str

        The file can be processed using neato or dot::

            % dot -Tpng -o out.png dotfile.dot

        """

        if isinstance(filename, str):
            file = open(filename, "w")
        else:
            file = filename

        header = r"""digraph G {

    graph [splines=ortho, rankdir=LR]
    node [shape=box]
    
    """
        file.write(header)
        # add the blocks
        for b in self.blocklist:
            options = []
            if b.blockclass == "source":
                options.append("shape=box3d")
            elif b.blockclass == "sink":
                options.append("shape=folder")
            elif b.blockclass == "function":
                if b.type == "gain":
                    options.append("shape=triangle")
                    options.append("orientation=-90")
                    options.append('label="{:g}"'.format(b.gain))
                elif b.type == "sum":
                    options.append("shape=point")
            elif b.blockclass == "transfer":
                options.append("shape=component")
            if b.pos is not None:
                options.append('pos="{:g},{:g}!"'.format(b.pos[0], b.pos[1]))
            options.append(
                'xlabel=<<BR/><FONT POINT-SIZE="8" COLOR="blue">{:s}</FONT>>'.format(
                    b.type
                )
            )
            file.write('\t"{:s}" [{:s}]\n'.format(b.name, ", ".join(options)))

        # add the wires
        for w in self.wirelist:
            options = []
            # options.append('xlabel="{:s}"'.format(w.name))
            if w.end.block.type == "sum":
                options.append(
                    'headlabel="{:s} "'.format(w.end.block.signs[w.end.port])
                )
            file.write(
                '\t"{:s}" -> "{:s}" [{:s}]\n'.format(
                    w.start.block.name, w.end.block.name, ", ".join(options)
                )
            )

        file.write("}\n")

    def blockvalues(self):
        for b in self.blocklist:
            print("Block {:s}:".format(b.name))
            print("  inputs:  ", b.inputs)
            print("  outputs: ", b.output(t=0))


if __name__ == "__main__":  # pragma: no cover

    import bdsim

    bd = bdsim.BlockDiagram()

    # define the blocks
    demand = bd.STEP(T=1, pos=(0, 0), name="demand")
    sum = bd.SUM("+-", pos=(1, 0))
    gain = bd.GAIN(10, pos=(1.5, 0))
    plant = bd.LTI_SISO(0.5, [2, 1], name="plant", pos=(3, 0))
    # scope = bd.SCOPE(pos=(4,0), styles=[{'color': 'blue'}, {'color': 'red', 'linestyle': '--'})
    scope = bd.SCOPE(nin=2, styles=["k", "r--"], pos=(4, 0))

    # connect the blocks
    bd.connect(demand, sum[0], scope[1])
    bd.connect(plant, sum[1])
    bd.connect(sum, gain)
    bd.connect(gain, plant)
    bd.connect(plant, scope[0])

    bd.compile()  # check the diagram
    bd.report()  # list all blocks and wires
    bd.run(5, debug=True)

    # from pathlib import Path

    # exec(open(Path(__file__).parent.absolute() / "test_blockdiagram.py").read())
