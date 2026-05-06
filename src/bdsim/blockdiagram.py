"""Block-diagram container, compilation, and evaluation logic."""

from __future__ import annotations

from collections import defaultdict
import itertools
from copy import deepcopy
import io
import json
import sys
from tempfile import _TemporaryFileWrapper
import traceback
import warnings
from typing import TYPE_CHECKING, Any, NoReturn

if TYPE_CHECKING:
    from typing import Self

import numpy as np
from ansitable import ANSITable, Column  # type: ignore[import-not-found]
from colored import attr, fg

from bdsim.exceptions import BlockRuntimeError

if TYPE_CHECKING:
    from bdsim._blockdiagram_mixin import BlockDiagramMixin
else:
    try:
        from bdsim._blockdiagram_mixin import BlockDiagramMixin
    except (ImportError, SyntaxError, NameError):
        # if the mixin file is missing or has syntax errors, create a dummy one so that the rest of the code can be imported without errors.  The real mixin will be generated at runtime by the @block decorator when the blocks are imported.
        class BlockDiagramMixin:  # type: ignore[no-redef]
            pass


from bdsim.components import *
from bdsim.connect import EndPlug, Plug, Port, StartPlug, Wire

# ------------------------------------------------------------------------- #


# class BlockDiagram(BlockDiagramMixin):
class BlockDiagram(BlockDiagramMixin):
    r"""
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
    :vartype blockcounter: defaultdict of itertools.count
    :ivar blockdict: index of all blocks by category
    :vartype blockdict: dict of lists
    :ivar name: name of this diagram
    :vartype name: str

    This object:

    * holds all the blocks and wires that comprise the system
    * manages continuous- and discrete-time state vector for the whole system, splitting
      it across blocks as required
    * evaluates the entire diagram as a function to compute :meth:`\dot{x} = f(x, t)`
    """

    def __init__(self, name="main", **kwargs) -> None:
        self.wirelist: list[Wire] = []  # list of all wires
        self.blocklist: list[Block] = []  # list of all blocks
        self.clocklist: list[Clock] = []  # list of all clock sources
        self.compiled = False  # network has been compiled
        self.blockcounter: defaultdict = defaultdict(itertools.count)
        self._block_id_counter = itertools.count()
        self._wire_id_counter = itertools.count()
        self.name: str = name
        self.nstates = 0
        self.ndstates = 0
        self._issubsystem = False
        self.blocknames: dict[str, Any] = {}
        self.options = None
        self.runtime: Any = None  # set by BDSim before compilation
        self.n_auto_sum = itertools.count()
        self.n_auto_prod = itertools.count()
        self.n_auto_const = itertools.count()
        self.n_auto_gain = itertools.count()
        self.n_auto_pow = itertools.count()
        self._state_map: dict[Block, np.ndarray | None] = {}
        self.compiled = False

    def __getitem__(self, id):
        print(id)
        if isinstance(id, str):
            return self.blocknames[id]
        else:
            for b in self.blocklist:
                if b.id == id:
                    return b
            raise ValueError(f"block {id} not found")

    def __len__(self) -> int:
        return len(self.blocklist)

    def __deepcopy__(self, memo) -> Self:
        # deep copy a block diagram
        # retain references (don't copy) to blocks and the runtime
        cls: type[Self] = self.__class__
        result: Self = cls.__new__(cls)
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

    def __repr__(self) -> str:
        return f"BlockDiagram(name={self.name}, nblocks={len(self.blocklist)}, nwires={len(self.wirelist)})"

    def ls(self) -> None:
        for k, v in self.blocknames.items():
            print("{:12s}: ".format(k), ", ".join(v))

    @property
    def issubsystem(self) -> bool:
        return self._issubsystem

    def clock(self, *args, **kwargs) -> Clock:
        clock: Clock = Clock(*args, **kwargs)
        clock.bd = self
        self.clocklist.append(clock)
        return clock

    # ---------------------------------------------------------------------- #

    def connect(self, start: Port, *ends: Port, name=None) -> None:
        """Connect blocks

        :param start: The output port that the wire starts from.
        :type start: Block | Plug
        :param ends: The input port(s) that the wire ends at.  Can be one or more.
        :type ends: Block | Plug
        :param name: The name of the wire, defaults to None
        :type name: _type_, optional

        Connect blocks together.  The start block can be connected to one or more end
        blocks.

        Blocks are added to the block diagram's ``blocklist`` if they are not already
        part of it.

        The wires are added to the diagram's ``wirelist``, but the connections are not
        actually made until compile time.  The ``wirelist`` is a list of things that
        will be connected later.
        """

        # start.type = 'start'

        # ensure all blocks are in the blocklist
        for x in [start, *ends]:
            if isinstance(x, Block):
                if x.bd is None:
                    self.add_block(x)
            elif isinstance(x, Plug):
                if x.block.bd is None:
                    self.add_block(x.block)

        for end in ends:
            if isinstance(start, Block):
                if isinstance(end, Block):
                    # connect(X, Y)
                    # wires from all outport to all inports
                    assert start.nout == end.nin, (
                        "can only connect blocks where number of input and output ports"
                        " match"
                    )
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
                    assert start.nout == end.width, (
                        "can only connect single output block to an input port slice of"
                        " width 1"
                    )
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
                    assert start.width == end.nin, (
                        "can only connect output slice to a block with matching number"
                        " of input ports"
                    )
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

    def add_block(self, block) -> None:
        if block.name in self.blocknames:
            raise ValueError("block {} already added".format(block.name))
        block.id = next(self._block_id_counter)
        if block.name is None:
            block.name = "{:s}.{:d}".format(
                block.type, next(self.blockcounter[block.type])
            )
        block._bd = self
        self.blocklist.append(block)  # add to the list of available blocks
        if block in self.blocknames:
            raise Warning(f"block name {block} is not unique")
        self.blocknames[block.name] = block

    def add_wire(self, wire, name=None):
        wire.id = next(self._wire_id_counter)
        wire.name = name
        # just add wire to the list, gets instantiated at compile time
        # when add_output_wire and add_input_wire are called on the blocks
        return self.wirelist.append(wire)

    def delete_block(self, block):
        # check block is in blocklist
        if block not in self.blocklist:
            raise ValueError("block not in block diagram")
        # delete a block and all wires connected to it
        self.blocklist.remove(block)
        self.blocknames.pop(block.name, None)
        for w in self.wirelist[:]:
            if w.start.block == block or w.end.block == block:
                self.wirelist.remove(w)

    # ---------------------------------------------------------------------- #

    def compile(
        self, subsystem=False, doimport=True, evaluate=True, report=False, verbose=True
    ) -> bool:
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
        self.nblocks: int = len(self.blocklist)
        self.nwires: int = len(self.wirelist)

        error = False

        self.nstates = 0
        self.ndstates = 0
        self.statenames = []
        self.dstatenames = []
        self.blocknames = {}

        if not subsystem and verbose:
            if not self.compiled:
                print(f"\nCompiling blockdiagram '{self.name}':")
            else:
                print(f"\nRecompiling blockdiagram '{self.name}':")
        self.compiled = False

        # recursively instantiate all subsystem imports
        self.blocklist, self.wirelist = self._subsystem_import(
            self, None, verbose=verbose
        )

        # get all the blocks in the complete wirelist ready for compilation
        #  - create _input_wires and _output_wires lists
        #  - create _inport_slots and _outport_slots lists
        #  - create PortValueSlot for each output port
        for b in self.blocklist:
            b.compile()

        # check that wires all point to valid blocks
        if verbose:
            print("  ☑ checking wires and connections...")
        for w in self.wirelist:
            if w.start.block not in self.blocklist:
                raise RuntimeError(
                    f"wire {w} starts at unreferenced block {w.start.block}"
                )
            if w.end.block not in self.blocklist:
                raise RuntimeError(f"wire {w} ends at unreferenced block {w.end.block}")

        # run block specific checks
        if verbose:
            print("  ☑ checking block parameters...")
        try:
            for b in self.blocklist:
                b.check_safe()
        except BlockRuntimeError as err:
            self._handle_block_runtime_error(err)

        # build a dictionary of all block names
        self.blocknames = {b.name: b for b in self.blocklist if b.name is not None}

        # visit all stateful blocks
        if verbose:
            print("  ☑ checking all stateful blocks...")
        for b in self.blocklist:
            if b.blockclass == "continuous":
                self.nstates += b.nstates
                if b._state_names is not None:
                    assert (
                        len(b._state_names) == b.nstates
                    ), "number of state names not consistent with number of states"
                    self.statenames.extend(b._state_names)
                else:
                    # create default state names
                    self.statenames.extend(
                        [(b.name or "") + "x" + str(i) for i in range(0, b.nstates)]
                    )
            if b.blockclass == "sampled":
                self.ndstates += b.ndstates
                if b._state_names is not None:
                    assert (
                        len(b._state_names) == b.nstates
                    ), "number of state names not consistent with number of states"
                    self.dstatenames.extend(b._state_names)
                else:
                    # create default state names
                    self.statenames.extend(
                        [(b.name or "") + "X" + str(i) for i in range(0, b.nstates)]
                    )

        # connect the source and destination blocks to each wire
        if verbose:
            print("  ☑ connecting wires to blocks...")
        for w in self.wirelist:
            try:
                w.start.block.add_output_wire(w)
                w.end.block.add_input_wire(w)

            except:
                print(fg("red"))
                print("error connecting wire ", w.fullname + ": ", sys.exc_info()[1])
                print(attr(0))
                error = True

        # check connections every block
        # determine the predecessor/parent blocks, used later to generate the schedule
        if verbose:
            print("  ☑ checking block inputs/outputs are connected...")
        for b in self.blocklist:
            # check all inputs are connected
            for port, w in enumerate(b._input_wires):
                if w is None:
                    print(
                        "  ERROR: [{:s}] input {:d} is not connected".format(
                            str(b), port
                        )
                    )
                    error = True
                # b.add_parent(w.start.block)

            # check all outputs are connected
            for port, ws in enumerate(b._output_wires):
                if len(ws) == 0:
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
        if verbose:
            print("  ☑ checking for algebraic loops...")

        def _DFS(path):
            start = path[0]
            tail = path[-1]
            for outgoing in tail._output_wires:
                # for every port on this block
                for w in outgoing:
                    dest = w.end.block
                    if dest == start:
                        print(
                            "  ERROR: cycle found: ",
                            " - ".join([str(x) for x in path + [dest]]),
                        )
                        return True
                    if dest.blockclass == "function" or (
                        dest.hasstate and dest._feedthrough
                    ):
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
        if verbose:
            print("  ☑ creating execution schedule...")
        self.schedule_generate()

        # bind runtime input slots to source output slots.
        # done here after subsystem flattening, block.compile(), and wire hookup.
        if verbose:
            print("  ☑ create slots to transfer data between blocks...")
        for w in self.wirelist:
            source_slot = w.start.block.outport_slot(w.start.port)
            w.bind_slot(source_slot)
            w.end.block.bind_input_slot(w.end.port, source_slot)

        ## evaluate the network once to check out wire types
        if verbose:
            print(
                "  ☑ evaluating network with initial conditions to determine wire datatype..."
            )
        state_map = self.initial_state_map()

        if report:
            self.report()
            self.report_schedule()

        if not subsystem and evaluate:
            # run all the blocks for one step
            self.evaluate(state_map, 0.0, sinks=False)

        if error:
            # show report if there was an error
            if not report:
                self.report()
            if not subsystem:
                raise RuntimeError("could not compile system")
        else:
            self.compiled = True

        return self.compiled

    def _subsystem_import(
        self, bd: BlockDiagram, sspath: str, verbose: bool = False, depth: int = 0
    ):
        """Recursively import subsystems

        :param bd: the block diagram in which to instantiate subsystems
        :type bd: BlockDiagram
        :param sspath: subsystem name prefix
        :type sspath: str
        :param verbose: print details of subsystem instantiation, defaults to False
        :type verbose: bool, optional
        :param depth: subsystem import recursion depth, defaults to 0
        :type depth: int, optional
        :return: _description_
        :rtype: _type_
        """
        blocks = []  # create an empty block list
        wires = bd.wirelist  # start with wires in the current diagram

        for b in bd.blocklist:
            # rename the block to include subsystem path
            if sspath is not None:
                b.name = sspath + "/" + b.name

            if not isinstance(b, SubsystemBlock):
                # not a Subsystem block, just add the block to the list
                b._depth = depth
                blocks.append(b)
            else:
                # Subsystem block encountered, recurse to find its constituent blocks and wires
                # do not add it to the block list, it was just a container for the subsystem blocks and wires
                if verbose:
                    print(f"{'  '*(depth+1)}instantiating subsystem ", b.name)
                ssb, ssw = self._subsystem_import(
                    b.subsystem,  # reference to the BlockDiagram that describes the subsystem
                    b.name,  # name of the subsystem block, becomes a prefix for all blocks within the subsystem
                    depth=depth + 1,  # increase subsystem nesting depth
                    verbose=verbose,
                )
                #  add its blocks and wires to the current set
                blocks.extend(ssb)
                wires.extend(ssw)

                # INPORT/OUTPORT blocks now become simple pass throughs with equal numbers of input and outport ports
                # INPORT block had nout outputs and 0 inputs
                # OUTPORT block had 0 outputs and nin inputs
                b.inport.nin = b.inport.nout  # num inputs <- num outputs
                b.outport.nout = b.outport.nin  # num outputs <- num inputs

                # modify the wiring, so that wires connecting to the Subsystem block are moved to
                # the INPORT and OUTPORT blocks.
                for w in bd.wirelist:
                    # for all wires at this level, find those that connect
                    # to the Subsystem and tweak them
                    if w.start.block == b:
                        # Subsystem block output
                        w.start.block = (
                            b.outport
                        )  # change to OUTPORT block, leave the port intact
                    if w.end.block == b:
                        # Subsystem block input
                        w.end.block = (
                            b.inport
                        )  # change to INPORT block, leave the port intact

        # systematically renumber all blocks and wires
        for i, b in enumerate(blocks):
            b.id = i
        for i, w in enumerate(wires):
            w.id = i
        return blocks, wires

    # ---------------------------------------------------------------------- #

    def initial_state_map(self) -> dict[Block, np.ndarray | None]:
        """Return a one-shot state map built from each stateful block's x0."""
        state_map: dict[Block, np.ndarray | None] = {}
        for b in self.blocklist:
            if b.hasstate:
                state_map[b] = np.array(b.getstate0_safe(), copy=True)
        return state_map

    def state_map(
        self,
        continuous_state: (
            np.ndarray[tuple[Any, ...], np.dtype[Any]] | Any | None
        ) = None,
        simstate: SimulationState | None = None,
    ) -> dict[Block, np.ndarray | None]:
        """Build a unified block->state map from runtime storage."""
        state_map: dict[Block, np.ndarray | None] = {}

        continuous = np.array([], dtype=float)
        if continuous_state is not None:
            continuous = np.asarray(continuous_state).reshape(-1)

        index = 0
        for b in self.blocklist:
            if b.blockclass != "continuous":
                continue
            width = b.nstates
            state_map[b] = continuous[index : index + width]
            index += width

        for clock in self.clocklist:
            if simstate is None or clock not in simstate.clock_states:
                clock_state = np.array(clock.getstate0(), copy=True)
            else:
                clock_state = simstate.clock_states[clock].state
            offset = 0
            for b in clock.blocklist:
                width = b.ndstates
                state_map[b] = clock_state[offset : offset + width]
                offset += width

        return state_map

    def continuous_state_vector(
        self, state_map: dict[Block, np.ndarray | None]
    ) -> np.ndarray[tuple[Any, ...], np.dtype[Any]]:
        """Flatten the continuous entries of a unified state map."""
        x = np.array([])
        for b in self.blocklist:
            if b.blockclass == "continuous":
                xb = state_map.get(b)
                assert xb is not None
                x = np.r_[x, np.asarray(xb).reshape(-1)]
        return x

    def set_block_state(
        self, state_map: dict[Block, np.ndarray | None], block: Block, value: Any
    ) -> None:
        """Write a block state back through the shared unified state map."""
        xb = state_map.get(block)
        if xb is None:
            raise ValueError(f"block {block} has no state entry")
        xb[:] = np.asarray(value).reshape(xb.shape)

    def evaluate(self, state_map, t, checkfinite=True, sinks=True) -> None:
        """
        Evaluate all blocks in the network using the compiled execution schedule

        :param state_map: block->state map
        :type state_map: dict
        :param t: current time
        :type t: float
        :param checkfinite: check for Inf or Nan values in block outputs
        :type checkfinite: bool
        :param sinks: evaluate sink blocks, defaults to Trye
        :type sinks: bool, optional
        :param simstate: simulation state

        Performs the following steps:

        1. Read state values from the provided runtime state map
        2. Execute the blocks in the order given by the ``plan``. The block
           outputs are "sent" to their connected inputs.

        Sink blocks are not executed here, but after completion their inputs
        will all be valid.
        """

        # TODO: don't copy outputs to inputs of next block, have inputs
        # pull the value from connected inputs

        try:
            self.runtime.DEBUG(
                "state", ">>>>>>>>> t={}, x={} >>>>>>>>>>>>>>>>", t, state_map
            )

            # reset all the blocks ready for the evalation
            self.reset()

            self._state_map = state_map

            self.runtime.DEBUG("propagate", "t={:.3f}", t)

            for sequence, group in enumerate(self.plan):
                for b in group:
                    # inports = None if sequence == 0 else b.inport_values
                    inports = b.inport_values
                    block_state = state_map.get(b)
                    out = b.output_safe(t, inports, block_state)

                    self.runtime.DEBUG("propagate", "block {:s}: output = {}", b, out)

                    if not isinstance(out, (tuple, list)):
                        b._raise_runtime_error(
                            "output",
                            AssertionError(
                                f"block {b} output {b} must be a list: {type(out)}"
                            ),
                            t=t,
                            inputs=inports,
                            state=block_state,
                        )
                    if len(out) != b.nout:
                        b._raise_runtime_error(
                            "output",
                            AssertionError(
                                f"block {b} output {b} has incorrect length: {len(out)} instead of {b.nout}"
                            ),
                            t=t,
                            inputs=inports,
                            state=block_state,
                        )

                    if (
                        checkfinite
                        and isinstance(out, (int, float, np.ndarray))
                        and not np.isfinite(out).any()
                    ):
                        b._raise_runtime_error(
                            "output",
                            RuntimeError(f"block {b} output contains NaN"),
                            t=t,
                            inputs=inports,
                            state=block_state,
                        )

                    b._publish_output_values(out)

            if sinks:
                for b in self.blocklist:
                    if isinstance(b, SinkBlock):
                        b.step_safe(t, b.inport_values)
        except BlockRuntimeError as err:
            self._handle_block_runtime_error(err)

    def schedule_generate(self) -> None:
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

        :seealso: :func:`schedule_report`, :func:`schedule_dotfile`
        """

        plan = []
        group = []
        for b in self.blocklist:
            b._sequence = None
            if b.blockclass == "source" or (b.hasstate and not b._feedthrough):
                b._sequence = 0
                group.append(b)
        plan.append(group)
        sequence: int = len(plan)

        while True:
            group = []
            for b in self.blocklist:
                if b._sequence is not None:
                    continue  # already has a sequence assigned

                if all(
                    [
                        p._sequence < sequence if p._sequence is not None else False
                        for p in b.sources
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

    def schedule_dotfile(self, filename) -> None:
        """
        Write a GraphViz dot file representing the execution schedule

        :param file: Name of file to write to
        :type file: str

        The file can be processed using neato or dot::

            % dot -Tpng -o out.png dotfile.dot

        Display execution plan as a dataflow graph.

        :seealso: :func:`schedule_plan`, :func:`schedule_print`
        """

        if isinstance(filename, str):
            file: io.TextIOWrapper = open(filename, "w")
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

        # connect them to their sources, except if a transfer block
        for b in self.blocklist:
            if not b.blockclass == "continuous":
                for p in b.sources:
                    file.write('\t"{:s}" -> "{:s}"\n'.format(p.name, b.name))

        file.write("}\n")

    # ---------------------------------------------------------------------- #

    def _debugger(self, simstate: SimulationState, integrator=None):
        if simstate.t_stop is not None and simstate.t < simstate.t_stop:
            return

        def print_output(b, t, inports) -> None:
            out = [b.outport_value(i) for i in range(b.nout)]
            if len(out) == 1:
                print(f"{b.name} = {out[0]}")
            else:
                print(f"{b.name}:")
                for i, o in enumerate(out):
                    print(f"  [{i}] = {o}")

        np.set_printoptions(precision=6, linewidth=120)
        simstate.t_stop = None
        if not hasattr(self, "debug_watch"):
            self.debug_watch = None
        print("\n")
        if self.debug_watch is not None:
            t = simstate.t
            for b in self.debug_watch:
                print_output(b, t, b.inport_values)

        while True:
            try:
                t = simstate.t
                cmd: str = input(f"(t={t:10.6f}) bsdsim> ")

                if len(cmd) == 0:
                    continue

                if cmd[0] == "p":
                    # print variables
                    if len(cmd) > 1:
                        id = int(cmd[1:])
                        b = self.blocklist[id]
                        print_output(b, t, b.inport_values)
                    else:
                        for b in self.blocklist:
                            if b.nout > 0:
                                print_output(b, t, b.inport_values)
                elif cmd[0] == "i":
                    if integrator is None:
                        print("no active integrator")
                    else:
                        print(
                            f"status={integrator.status}, dt={integrator.step_size:.4g}, nfev={integrator.nfev}"
                        )
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
                elif cmd[0] == "r":
                    self.report()
                elif cmd[0] == "w":
                    if len(cmd) == 1:
                        # clear the watch list
                        print(self.debug_watch)
                        self.debug_watch = None
                    else:
                        self.debug_watch = [
                            self.blocklist[int(s.strip())] for s in cmd[2:].split(" ")
                        ]
                elif cmd == "pdb":
                    import pdb

                    pdb.runeval('print("type exit to leave Pdb")')
                elif cmd[0] in "h?":
                    print("p    print all outputs")
                    print("pI   print block id I output")
                    print("i    print integrator status")
                    print("s    single step")
                    print("c    continue")
                    print("tT   stop at or after time T")
                    print("r    print block and wires")
                    print("pdb  enter PDB debugger")
                    print("w id watch list, display at every step")
                    print("q    quit")

            except (IndexError, ValueError, TypeError):
                print("??")
                pass

    # ---------------------------------------------------------------------- #

    def report_summary(
        self, sortby: str = "name", depth: int | None = None, **kwargs
    ) -> None:
        """
        Print a summary of block diagram.

        :param sortby: sort rows by specified block attribute: "name" [default] or "type"
        :type sortby: str, optional
        :param depth: only show blocks with subsystem depth less than or equal to this value, defaults to None (show all)
        :type depth: int, optional
        :param style: table style, one of: ansi (default), markdown, latex
        :type style: str

        Print a table with 4 columns:

        1. Block name, sorted in alphabetical order
        2. The input port (if not a source block)
        3. The block driving this port (if not a source block)
        4. The type of value driving this port (if not a source block)

        If the block is an event source, add a ``@`` suffix.
        """

        table = ANSITable(
            Column("block", headalign="^", colalign="<"),
            Column("nc", headalign="^", colalign="^"),
            Column("nd", headalign="^", colalign="^"),
            Column("type", headalign="^", colalign="<"),
            Column("inport", headalign="^", colalign="<"),
            Column("source", headalign="^", colalign="<"),
            Column("source type", headalign="^", colalign="<"),
            border="thin",
        )

        if sortby == "name":
            sortfunc = lambda x: x.name
        elif sortby == "type":
            sortfunc = lambda x: x.type

        first = True
        legend = None
        for b in sorted(self.blocklist, key=sortfunc):
            if depth is not None:
                # show blocks with depth less than or equal to depth
                skip = b._depth > depth
                if b.type == "inport" and (b._depth - depth) == 1:
                    skip = False
                if skip:
                    continue
            name = b.name
            if isinstance(b, EventSource):
                name += "@"
                legend = "Note: @ = event source"
            # add a divider before each subsequent row
            if not first:
                table.rule()
            else:
                first = False

            # print the details
            if b.nin > 0:
                # non source block, list all its inputs, one per row
                for port, source in enumerate(b.inports):
                    value = source.block.outport_value(source.port)
                    typ = type(value).__name__
                    if isinstance(value, np.ndarray):
                        typ += "{:s}.{:s}".format(str(value.shape), str(value.dtype))
                    src_name = source.block.name or ""
                    if source.block.nout > 1:
                        src_name += f"[{source.port}]"
                    if port == 0:
                        # first row for this block
                        table.row(
                            b.name,
                            b.nstates,
                            b.ndstates,
                            b.type,
                            port,
                            src_name,
                            typ,
                        )
                    else:
                        # subsequent rows
                        table.row("", "", "", "", port, src_name, typ)
            else:
                # source block, just list the name
                table.row(name, b.nstates, b.ndstates, b.type, "", "", "")
        table.print(**kwargs)

        if legend:
            print(legend + "\n")

    def report(self, **kwargs) -> None:
        warnings.warn("use reports_lists() method instead", DeprecationWarning)
        self.report_lists(**kwargs)

    def report_lists(self, **kwargs) -> None:
        """
        Print a tabular report about the block diagram.

        :param kwargs: options passed to :meth:`ansitable.ANSITable.print`

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
            table.row(b.id, b.name, b.nin, b.nout, b.nstates, b.ndstates, b.type)
        table.print(**kwargs)

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
        for wire in self.wirelist:
            start: str = "{}[{}]".format(wire.start.block.id, wire.start.port)
            end: str = "{}[{}]".format(wire.end.block.id, wire.end.port)

            try:
                value = wire.end.block.inport_value(wire.end.port)
                typ: str = type(value).__name__
                if isinstance(value, np.ndarray):
                    typ += "{:s}.{:s}".format(str(value.shape), str(value.dtype))
            except:
                typ = "??"
            table.row(wire.id, start, end, wire.fullname, typ)
        table.print(**kwargs)

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
                if b.blockclass == "sampled":
                    c = b._clock
                    assert c is not None
                    table.row(b.id, b.name, c.name, c.T, c.offset)
            table.print(**kwargs)

    def report_schedule(self, **kwargs) -> None:
        """
        Display execution schedule in tabular form

        :param kwargs: options passed to :meth:`ansitable.ANSITable.print`

        :seealso: :func:`schedule_plan`, :func:`schedule_dotfile`
        """
        table = ANSITable(
            Column("Step"),
            Column("Blocks", colalign="<", headalign="^"),
            border="thin",
        )

        for sequence, group in enumerate(self.plan):
            table.row(sequence, ", ".join([b.name for b in group]))

        table.print(**kwargs)

    # ---------------------------------------------------------------------- #

    def _handle_block_runtime_error(self, err: BlockRuntimeError) -> NoReturn:
        if isinstance(err.__cause__, Exception):
            cause: Exception = err.__cause__
        elif isinstance(err.cause, Exception):
            cause = err.cause
        else:
            # Fallback so we always emit useful diagnostics.
            cause = err

        print(fg("red"))
        if err.t is None:
            print(f"[{err.block.type} block: {err.block.name}.{err.operation}]")
        else:
            print(
                f"[{err.block.type} block: {err.block.name}.{err.operation}] at t={err.t:f}"
            )

        if cause.__traceback__ is not None:
            # Show full traceback for the originating exception so callers can
            # identify the offending line, not just the final frame.
            trace = "".join(
                traceback.format_exception(type(cause), cause, cause.__traceback__)
            ).rstrip()
            for line in trace.splitlines():
                print(f"  {line}")
        else:
            print(
                "  "
                + "".join(traceback.format_exception_only(type(cause), cause)).strip()
            )

        if isinstance(err.inputs, (list, tuple)) and len(err.inputs) > 0:
            print()
            for i, value in enumerate(err.inputs):
                print(f"Input[{i}] = {value}")
        elif err.inputs is not None:
            print()
            print(f"Inputs = {err.inputs}")

        if err.state is not None:
            print()
            print(f"State = {err.state}")

        print(attr(0))
        raise RuntimeError("Fatal failure") from cause

    def getstate0(self) -> np.ndarray[tuple[Any, ...], np.dtype[Any]] | Any:
        # get the state from each stateful block
        try:
            x0: np.ndarray[tuple[Any, ...], np.dtype[Any]] = np.array([])
            for b in self.blocklist:
                if b.blockclass == "continuous":
                    x0 = np.r_[x0, b.getstate0_safe()]
            return x0
        except BlockRuntimeError as err:
            self._handle_block_runtime_error(err)

    def reset(self) -> None:
        """
        Reset conditions within every active block.  Most importantly, all
        inputs are marked as unknown.

        Invokes the `reset` method on all blocks.

        """
        try:
            for b in self.blocklist:
                b.reset_safe()
        except BlockRuntimeError as err:
            self._handle_block_runtime_error(err)

    def step(self, t) -> None:
        """
        Step all blocks

        :param t: simulation time, defaults to None
        :type t: float
        :param inports: block input port values
        :type inports: list

        Tell all blocks to take action on new inputs by invoking their
        ``step`` method and passing the ``state`` object.  Used to save
        results to a figure or file.

        Called at the end of every integration interval.

        .. note::
            - if ``graphics`` is False, Graphics blocks are not called
        """

        # TODO could be done by output method, even if no outputs

        try:
            for b in self.blocklist:
                if isinstance(b, SinkBlock):
                    b.step_safe(t, b.inport_values)
        except BlockRuntimeError as err:
            self._handle_block_runtime_error(err)

    def deriv(
        self,
        t,
        state_map: dict[Block, np.ndarray | None] | None = None,
    ) -> np.ndarray[tuple[Any, ...], np.dtype[Any]] | Any:
        """
        Harvest derivatives from all blocks.

        :param t: simulation time, defaults to None
        :type t: float
        :param state_map: optional block->state map, defaults to most recent evaluate
        :type state_map: dict, optional
        """
        try:
            active_state_map = self._state_map if state_map is None else state_map
            YD: np.ndarray[tuple[Any, ...], np.dtype[Any]] = np.array([])
            for b in self.blocklist:
                if b.blockclass == "continuous":
                    block_state = active_state_map.get(b)
                    yd = b.deriv_safe(t, b.inport_values, block_state)
                    if not isinstance(yd, np.ndarray):
                        b._raise_runtime_error(
                            "deriv",
                            AssertionError(f"deriv: block {b} did not return ndarray"),
                            t=t,
                            inputs=b.inport_values,
                            state=block_state,
                        )
                    if yd.ndim != 1 or yd.shape[0] != b.nstates:
                        b._raise_runtime_error(
                            "deriv",
                            AssertionError(
                                f"deriv: block {b} returns wrong shape {yd.shape}, should be ({b.nstates},)"
                            ),
                            t=t,
                            inputs=b.inport_values,
                            state=block_state,
                        )
                    YD = np.r_[YD, yd]
            self.runtime.DEBUG("deriv", YD)
            return YD
        except BlockRuntimeError as err:
            self._handle_block_runtime_error(err)

    def next(
        self,
        t,
        state_map: dict[Block, np.ndarray | None] | None = None,
    ) -> dict[Clock, np.ndarray[tuple[Any, ...], np.dtype[Any]]]:
        """Harvest discrete next-state values grouped by clock."""
        active_state_map = self._state_map if state_map is None else state_map
        clock_next: dict[Clock, np.ndarray[tuple[Any, ...], np.dtype[Any]]] = {}
        for clock in self.clocklist:
            x_next: np.ndarray[tuple[Any, ...], np.dtype[Any]] = np.array([])
            for b in clock.blocklist:
                block_state = active_state_map.get(b)
                xb = b.next_safe(t, b.inport_values, block_state)
                if not isinstance(xb, np.ndarray):
                    b._raise_runtime_error(
                        "next",
                        AssertionError(f"next: block {b} did not return ndarray"),
                        t=t,
                        inputs=b.inport_values,
                        state=block_state,
                    )
                x_next = np.r_[x_next, xb.flatten()]
            clock_next[clock] = x_next
        return clock_next

    def start(self, simstate: SimulationState) -> None:
        """
        Start all blocks

        :param simstate: simulation state
        :type simstate: SimState

        Inform all blocks that BlockDiagram execution is about to start by
        invoking their ``start`` method and passing the ``state`` object.  Used
        to open files, create figures etc.

        .. note:: if ``graphics`` is False, Graphics blocks are not called

        """

        for c in self.clocklist:
            try:
                c.start(simstate)
            except Exception as err:
                print(fg("red"))
                print(f"[clock: {c.name}.start]")
                if err.__traceback__ is not None:
                    frame = traceback.extract_tb(err.__traceback__)[-1]
                    print(
                        f'  File "{frame.filename}", line {frame.lineno}, in {frame.name}'
                    )
                    if frame.line is not None:
                        print(f"    {frame.line.strip()}")
                print(
                    "  "
                    + "".join(traceback.format_exception_only(type(err), err)).strip()
                )
                print(attr(0))
                raise RuntimeError("Fatal failure") from None

        try:
            for b in self.blocklist:
                b.start_safe(simstate)
        except BlockRuntimeError as err:
            self._handle_block_runtime_error(err)

    def initialstate(self) -> None:
        self._state_map = self.initial_state_map()

    def done(self, block=False) -> None:
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
        try:
            for b in self.blocklist:
                b.done_safe(block=block)
        except BlockRuntimeError as err:
            self._handle_block_runtime_error(err)

    def dotfile(self, filename, shapes=None) -> None:
        """
        Write a GraphViz dot file representing the network.

        :param file: Name of file to write to, or file handle
        :type file: str, file handle
        :param shapes: block shapes
        :type shapes: dict

        Create a GraphViz format file for procesing by ``dot``.  The graph is:

        * directed graph, drawn left to right
        * source blocks are in the first column
        * sink and graphics blocks are in the last column
        * ``SUM`` and ``PROD`` blocks have the sign or operation of their input wires
          labeled.

        The file can be processed using ``dot``::

            % dot -Tpng -o out.png dotfile.dot

        .. image:: ../figs/eg1.png
            :width: 600
            :alt: Block diagram represented as a mathematical graph

        .. note:: By default all blocks have the default shape, with source blocks shown
            as a rectangle ("record"), and sink/graphics blocks as a rounded rectangle
            ("Mrecord").  This can be overriden by provide a dictionary ``shapes`` that
            maps block class (sink, source, graphics, function, transfer) to the names
            of GraphViz shapes.

        :seealso: :meth:`showgraph`
        """
        if shapes is None:
            shapes = dict(source="record", sink="Mrecord", graphics="Mrecord")

        if isinstance(filename, str):
            file: io.TextIOWrapper = open(filename, "w")
        else:
            file = filename

        header = r"""digraph G {
    rankdir = "LR"

"""
        file.write(header)
        # add the blocks
        for b in self.blocklist:
            options = []
            if b.blockclass in shapes:
                options.append("shape={:s}".format(shapes[b.blockclass]))
            if b.blockclass == "source":
                options.append('rank="source"')
            if b.blockclass in ("sink", "graphics"):
                options.append('rank="sink"')
            if b.pos is not None:
                options.append('pos="{:g},{:g}!"'.format(b.pos[0], b.pos[1]))
            # options.append(
            #     'xlabel=<<BR/><FONT POINT-SIZE="8" COLOR="blue">{:s}</FONT>>'.format(
            #         b.type
            #     )
            # )
            if len(options) > 0:
                file.write('\t"{:s}" [{:s}]\n'.format(b.name, ", ".join(options)))
        file.write("\n")

        # add the wires
        for w in self.wirelist:
            options = []
            # options.append('xlabel="{:s}"'.format(w.name))
            if w.end.block.type == "sum":
                options.append(
                    'headlabel="{:s} "'.format(w.end.block.signs[w.end.port])
                )
                options.append("labeldistance=1.5")
            if w.end.block.type == "prod":
                options.append('headlabel="{:s} "'.format(w.end.block.ops[w.end.port]))
                options.append("labeldistance=1.5")
            file.write(
                '\t"{:s}" -> "{:s}" [{:s}]\n'.format(
                    w.start.block.name, w.end.block.name, ", ".join(options)
                )
            )

        file.write("}\n")

    def showgraph(self) -> None:
        """
        Display diagram as a graph in browser tab

        :seealso: :meth:`dotfile`
        """

        # Lazy import
        try:
            import tempfile
            import subprocess
            import webbrowser
        except ModuleNotFoundError:
            return

        # create the temporary dotfile
        dotfile: io.TextIOWrapper = tempfile.TemporaryFile(mode="w")
        self.dotfile(dotfile)

        # rewind the dot file, create PDF file in the filesystem, run dot
        dotfile.seek(0)
        pdffile: _TemporaryFileWrapper[bytes] = tempfile.NamedTemporaryFile(
            suffix=".pdf", delete=False
        )
        subprocess.run("dot -Tpdf", shell=True, stdin=dotfile, stdout=pdffile)

        # open the PDF file in browser (hopefully portable), then cleanup
        webbrowser.open(f"file://{pdffile.name}")

    def blockvalues(self, t=None, simstate=None) -> None:
        for b in self.blocklist:
            print("Block {:s}:".format(b.name))
            print("  inputs:  ", b.inport_values)
            if b.nout > 0:
                print("  outputs: ", [b.outport_value(i) for i in range(b.nout)])


# --------------------------------------------------------------------------- #


def bdload(
    bd: "BlockDiagram",
    filename: str,
    globalvars: dict[str, Any] | None = None,
    verbose: bool = False,
    allow_eval: bool | None = None,
    trace_eval: bool = False,
    **kwargs: Any,
) -> "BlockDiagram":
    """
    Load a block diagram model

    :param bd: block diagram to load into
    :type bd: BlockDiagram instance
    :param filename: name of JSON file to load from
    :type filename: str or Path
    :param globalvars: global variables for evaluating expressions, defaults to {}
    :type globalvars: dict, optional
    :param verbose: print parameters of all blocks as they are instantiated, defaults to False
    :type verbose: bool, optional
    :param allow_eval: controls expression evaluation behavior. ``True`` enables
        ``eval`` without warning, ``False`` refuses required ``=...`` expressions,
        ``None`` (default) allows evaluation with a one-time warning.
    :type allow_eval: bool, optional
    :param trace_eval: print each expression before it is evaluated.
    :type trace_eval: bool, optional
    :raises RuntimeError: unable to load the file
    :raises ValueError: unable to load the file
    :return: the loaded block diagram
    :rtype: BlockDiagram instance

    Block diagrams are saved as JSON files.

    A number of errors can arise at this stage:

    * a parameter starting with "=" cannot be evaluated
    * the block throws an error when instantiated, incorrect parameter values
    * unconnected input port

    If the JSON file contains a parameter of the form ``"=expression"`` then
    it is evaluated using ``eval`` with the global name space given by
    ``globalvars``. This means that you can embed lambda expressions that use
    functions/classes defined in your module if ``globalvars`` is set to ``globals()``.

    Since ``eval`` executes code, only load trusted model files. Set
    ``allow_eval=False`` to refuse required ``=...`` expressions.

    """

    # load the JSON file
    with open(filename, "r") as f:
        model = json.load(f)

    output_dict: dict = {}  # block output id -> Plug
    connector_dict: dict = {}  # connector block: input socket -> output socket
    wire_dict: dict = {}  # wire: start socket -> end socket
    block_dict: dict = {}  # block: block id -> Block instance

    if globalvars is None:
        globalvars = {}

    import math

    _eval_ns: dict[str, Any] = {"np": np, "math": math, "pi": math.pi}
    try:
        from spatialmath import SE3, SE2

        _eval_ns.update({"SE3": SE3, "SE2": SE2})
    except ImportError:
        pass
    namespace = {**_eval_ns, **globalvars}

    warned_eval = False

    for block in model["blocks"]:
        if block["block_type"] == "CONNECTOR":
            start = block["inputs"][0]["id"]
            end = block["outputs"][0]["id"]
            connector_dict[end] = start

        elif block["block_type"] == "MAIN":
            continue

        else:
            try:
                block_init = bd.__dict__[block["block_type"]]
            except KeyError:
                print(fg("red"))
                print(f"block [{block['block_type']}] not loaded, check BDSIMPATH")
                print(attr(0))

            params = dict(block["parameters"])

            if verbose:
                print(f"[{block['title']}]:")

            for key, value in params.items():
                if verbose:
                    print(f"    {key}: ", end="")

                newvalue = None
                if isinstance(value, str):
                    if value[0] == "=":
                        expr = value[1:]
                        if allow_eval is False:
                            raise RuntimeError(
                                "bdload: eval disabled by allow_eval=False while "
                                f"resolving parameter {key} for block [{block['title']}]"
                            )
                        if allow_eval is None and not warned_eval:
                            warnings.warn(
                                "bdload is evaluating model expressions using eval(); "
                                "load only trusted .bd files. Use allow_eval=False to "
                                "disable expression evaluation.",
                                UserWarning,
                                stacklevel=2,
                            )
                            warned_eval = True
                        if trace_eval:
                            print(
                                f"[eval] block=[{block['title']}] param={key} expr={expr}"
                            )
                        try:
                            newvalue = eval(expr, namespace)
                        except (ValueError, TypeError, NameError, SyntaxError):
                            print(fg("red"))
                            print(
                                f"bdload: error resolving parameter {key}: {value} for"
                                f" block [{block['title']}]"
                            )
                            traceback.print_exc(limit=-1, file=sys.stderr)
                            print(attr(0))
                            raise RuntimeError(
                                f"cannot instantiate block [{block['title']}] - bad"
                                " parameters?"
                            )
                    else:
                        if allow_eval is not False:
                            if allow_eval is None and not warned_eval:
                                warnings.warn(
                                    "bdload is evaluating model expressions using eval(); "
                                    "load only trusted .bd files. Use allow_eval=False to "
                                    "disable expression evaluation.",
                                    UserWarning,
                                    stacklevel=2,
                                )
                                warned_eval = True
                            if trace_eval:
                                print(
                                    f"[eval] block=[{block['title']}] param={key} expr={value}"
                                )
                            try:
                                newvalue = eval(value, namespace)
                            except (NameError, SyntaxError):
                                pass
                else:
                    newvalue = value

                if newvalue is None:
                    if verbose:
                        print(f" {value} default")
                else:
                    params[key] = newvalue
                    if verbose:
                        print(f" {value} -> {newvalue}")

            try:
                if "blockargs" in params:
                    blockargs = params["blockargs"]
                    del params["blockargs"]
                else:
                    blockargs = {}

                blockargs = blockargs or {}

                newblock = block_init(name=block["title"], **params, **blockargs)

            except (
                ValueError,
                TypeError,
                NameError,
                SyntaxError,
                AssertionError,
                AttributeError,
            ):
                print(fg("red"))
                print(f"bdload: error instantiating block [{block['title']}]")
                args = ", ".join(
                    [f"{arg[0]} = {arg[1]}" for arg in block["parameters"]]
                )
                print(f"  {block['block_type']}({args})")
                print(attr(0))
                raise RuntimeError(
                    f"cannot instantiate block [{block['title']}] - bad parameters?"
                )

            block_dict[block["id"]] = newblock
            for output in block["outputs"]:
                output_dict[output["id"]] = newblock[output["index"]]

    for wire in model["wires"]:
        wire_dict[wire["end_socket"]] = wire["start_socket"]

    for block in model["blocks"]:
        if block["block_type"] == "CONNECTOR":
            continue

        id = block["id"]

        for input in block["inputs"]:
            in_id = input["id"]

            if in_id not in wire_dict:
                raise ValueError(
                    f"bdload: error block [{block['title']}] has unconnected input port"
                )

            start_id = wire_dict[in_id]

            while start_id in connector_dict:
                start_id = wire_dict[connector_dict[start_id]]

            end = block_dict[id][input["index"]]
            start = output_dict[start_id]

            if verbose:
                print(start, " --> ", end)
            bd.connect(start, end)

    return bd


if __name__ == "__main__":  # pragma: no cover
    try:
        from ._selftest import run_module_test
    except ImportError:
        from bdsim._selftest import run_module_test

    raise SystemExit(run_module_test(__file__))
