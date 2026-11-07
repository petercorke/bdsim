"""Block-diagram container, compilation, and evaluation logic."""

from __future__ import annotations

from collections import defaultdict
import inspect
from copy import deepcopy
import json
import os
import sys
import traceback
import warnings
from typing import TYPE_CHECKING, Any, NoReturn

if TYPE_CHECKING:
    from typing import Self

import math
import numpy as np
from colored import attr, fg

from bdsim._graph import GraphMixin
from bdsim._reports import ReportMixin
from bdsim.analysis import AnalysisMixin
from bdsim.exceptions import BlockRuntimeError
from bdsim.signature import Signature
from bdsim.literals import NOT_A_LITERAL, parse_literal

# Typing-only stubs for the block factory methods: bdsim's own, then generated
# snapshots of the toolboxes' (see bin/stubgen.py).  Blocks are bound per instance
# by BDSim.blockdiagram(), so a missing or broken stub file costs only editor help.
if TYPE_CHECKING:
    from bdsim._blockfactory_stubs import BlockFactoryStubs
    from bdsim._stubs_mvtb import MVTBStubs
    from bdsim._stubs_rtb import RTBStubs
else:
    try:
        from bdsim._blockfactory_stubs import BlockFactoryStubs
    except (ImportError, SyntaxError, NameError):

        class BlockFactoryStubs:
            pass

    try:
        from bdsim._stubs_rtb import RTBStubs
    except (ImportError, SyntaxError, NameError):

        class RTBStubs:
            pass

    try:
        from bdsim._stubs_mvtb import MVTBStubs
    except (ImportError, SyntaxError, NameError):

        class MVTBStubs:
            pass


from bdsim.components import (
    Block,
    Clock,
    Counter,
    SimulationState,
    SinkBlock,
    SubsystemBlock,
)
from bdsim.connect import EndPlug, Plug, Port, StartPlug, Wire

# ------------------------------------------------------------------------- #


def _is_finite(value: Any) -> bool:
    """False for a float or complex value, or an array of them, containing NaN or Inf.

    Integers, booleans and any other object are finite as far as this is
    concerned, and are not examined.
    """
    if type(value) is float:
        return math.isfinite(value)
    if isinstance(value, np.ndarray):
        return value.dtype.kind not in "fc" or bool(np.isfinite(value).all())
    if isinstance(value, (float, complex, np.floating, np.complexfloating)):
        return bool(np.isfinite(value))
    return True


def _state_labels(block: Block, count: int, letter: str) -> list[str]:
    """
    The names of the states of a block, for ``bd.statenames`` and the clocks'.

    :param block: a block with ``count`` states, continuous or discrete
    :param count: its number of states
    :param letter: ``"x"`` for continuous states and ``"X"`` for discrete, used in
        the default names
    :return: the names the block gave its states, with ``snames``, and otherwise
        ``name:x_0``, ``name:x_1``, ...
    :raises ValueError: the block gave the wrong number of names
    """
    given = block._state_names
    if given is None:
        return [f"{block.name or ''}:{letter}_{i}" for i in range(count)]
    if len(given) != count:
        raise ValueError(
            f"block {block.name}: {len(given)} state names for {count} states"
        )
    return list(given)


class BlockDiagram(
    AnalysisMixin, GraphMixin, ReportMixin, BlockFactoryStubs, RTBStubs, MVTBStubs
):
    r"""
    Block diagram class.  This object is the parent of all blocks and wires in
    the system.

    :ivar wirelist: all wires in the diagram
    :vartype wirelist: list[Wire]
    :ivar blocklist: all blocks in the diagram
    :vartype blocklist: list[Block]
    :ivar x: state vector
    :vartype x: numpy.ndarray
    :ivar compiled: diagram has successfully compiled
    :vartype compiled: bool
    :ivar blockcounter: unique counter for each block type
    :vartype blockcounter: collections.defaultdict
    :ivar blockdict: index of all blocks by category
    :vartype blockdict: dict
    :ivar name: name of this diagram, ``None`` until given one.  A main diagram
        is named ``main`` when first compiled; a subsystem diagram's name is the stem of its
        instances' names, see :meth:`BDSim.blockdiagram`
    :vartype name: str or None

    This object:

    * holds all the blocks and wires that comprise the system
    * manages continuous- and discrete-time state vector for the whole system, splitting
      it across blocks as required
    * evaluates the entire diagram as a function to compute :math:`\dot{x} = f(x, t)`
    """

    def __init__(self, name: str | None = None, **kwargs: Any) -> None:
        self.wirelist: list[Wire] = []  # list of all wires
        self.blocklist: list[Block] = []  # list of all blocks
        self.clocklist: list[Clock] = []  # list of all clock sources
        self.compiled = False  # network has been compiled
        self.blockcounter: defaultdict = defaultdict(Counter)
        self._block_id_counter = Counter()
        self._wire_id_counter = Counter()
        self.name: str | None = name
        self.check: bool = True  # run-time checks on, see evaluate()
        self.nstates = 0
        self.ndstates = 0
        self._issubsystem = False
        self.blocknames: dict[str, Any] = {}
        self.subsystems: dict[str, Any] = {}
        self.options = None
        self.runtime: Any = None  # set by BDSim before compilation
        self.n_auto_sum = Counter()
        self.n_auto_prod = Counter()
        self.n_auto_const = Counter()
        self.n_auto_gain = Counter()
        self.n_auto_pow = Counter()
        self._state_map: dict[Block, np.ndarray | None] = {}
        self._started = False  # start() has run since the last compile
        self.compiled = False

    def __getitem__(self, id: int | str) -> Block:
        if isinstance(id, str):
            if id in self.blocknames:
                return self.blocknames[id]
            # a subsystem block is not in the compiled diagram, its blocks replaced it
            return self.subsystems[id]  # type: ignore[no-any-return]
        else:
            for b in self.blocklist:
                if b.id == id:
                    return b
            raise ValueError(f"block {id} not found")

    def __len__(self) -> int:
        return len(self.blocklist)

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
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
        name = f"name={self.name}, " if self.name is not None else ""
        return f"BlockDiagram({name}nblocks={len(self.blocklist)}, nwires={len(self.wirelist)})"

    @property
    def issubsystem(self) -> bool:
        return self._issubsystem

    def clock(self, *args: Any, **kwargs: Any) -> Clock:
        clock: Clock = Clock(*args, **kwargs)
        clock.bd = self
        self.clocklist.append(clock)
        return clock

    # ---------------------------------------------------------------------- #

    def connect(self, start: Port, *ends: Port, name: str | None = None) -> None:
        """Connect blocks

        :param start: The output port that the wire starts from.
        :type start: Block | Plug
        :param ends: The input port(s) that the wire ends at.  Can be one or more.
        :type ends: Block | Plug
        :param name: The name of the wire, defaults to None
        :type name: str, optional

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
                if x._bd is None:
                    self.add_block(x)
            elif isinstance(x, Plug):
                if x.block._bd is None:
                    self.add_block(x.block)

        for end in ends:
            if isinstance(start, Block):
                # connect(X, Y) or connect(X, Y[i]) or connect(X, Y[m:n])

                if isinstance(end, Block):
                    # connect(X, Y)
                    # wires from all outport to all inports
                    if start.nout != end.nin:
                        raise ValueError(
                            "can only connect blocks where number of input and output"
                            " ports match"
                        )
                    for i in range(start.nout):
                        wire = Wire(StartPlug(start, i), EndPlug(end, i), name)
                        self.add_wire(wire)

                elif isinstance(end, Plug) and not end.isslice:
                    # connect(X, Y[i])
                    if start.nout != 1:
                        raise ValueError(
                            "can only connect single output block to a port"
                        )
                    end.type = "end"
                    wire = Wire(StartPlug(start, 0), end, name)
                    self.add_wire(wire)

                elif isinstance(end, Plug) and end.isslice:
                    # connect(X, Y[m:n])
                    if start.nout != end.width:
                        raise ValueError(
                            "can only connect single output block to an input port"
                            " slice of width 1"
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
                    if end.nin != 1:
                        raise ValueError(
                            "can only connect a port to a block with single input port"
                        )
                    wire = Wire(start, EndPlug(end, 0), name)
                    self.add_wire(wire)

                elif isinstance(end, Plug) and not end.isslice:
                    # connect(X[i], Y[i])
                    end.type = "end"
                    wire = Wire(start, end, name)
                    self.add_wire(wire)

                elif isinstance(end, Plug) and end.isslice:
                    # connect(X[i], Y[m:n])
                    if end.width != 1:
                        raise ValueError(
                            "can only connect output port to an input port slice of"
                            " width 1"
                        )
                    end.type = "end"
                    wire = Wire(start, end[0], name)
                    self.add_wire(wire)

                else:
                    raise ValueError("bad end type")

            elif isinstance(start, Plug) and start.isslice:
                if isinstance(end, Block):
                    # connect(X[i:j], Y)
                    if start.width != end.nin:
                        raise ValueError(
                            "can only connect output slice to a block with matching"
                            " number of input ports"
                        )
                    for i in range(end.nin):
                        wire = Wire(start[i], EndPlug(end, i), name)
                        self.add_wire(wire)

                elif isinstance(end, Plug) and not end.isslice:
                    # connect(X[i:j], Y[m])
                    if start.width != 1:
                        raise ValueError(
                            "can only connect output slice of width 1 to a port"
                        )
                    wire = Wire(start[0], end, name)
                    self.add_wire(wire)

                if isinstance(end, Plug) and end.isslice:
                    # connect(X[i:j], Y[m:n])
                    if start.width != end.width:
                        raise ValueError("can only connect port slices of same width")
                    for i in range(start.width):
                        wire = Wire(start[i], end[i], name)
                        self.add_wire(wire)

                else:
                    raise ValueError("bad end type")

            else:
                raise ValueError("bad start type")

    def add_block(self, block: Block) -> None:
        if block.name is not None and block.name in self.blocknames:
            existing = self.blocknames[block.name]
            raise ValueError(
                f"block name '{block.name}' is already used in this diagram "
                f"by a {existing.type} block; block names must be unique. "
                "Pass a different name=, or omit it to get a default name."
            )
        block.id = next(self._block_id_counter)
        if block.name is None:
            # default name is <stem>.<n>; skip any name already taken, for
            # example one the user chose that matches the next count
            stem = block._default_name_stem()
            while True:
                name = f"{stem}.{next(self.blockcounter[stem])}"
                if name not in self.blocknames:
                    break
            block.name = name
        block._bd = self
        self.blocklist.append(block)  # add to the list of available blocks
        self.blocknames[block.name] = block

    _this_file = os.path.abspath(__file__)

    @staticmethod
    def _wire_loc(wire: Wire) -> str:
        """Return 'filename:lineno' for the callsite stored on *wire*."""
        cs = getattr(wire, "callsite", None)
        if cs is None:
            return wire.fullname
        return f"{os.path.basename(cs[0])}:{cs[1]}"

    def add_wire(self, wire: Wire, name: str | None = None) -> None:
        wire.id = next(self._wire_id_counter)  # type: ignore[assignment]
        wire.name = name
        # Record the user source line that triggered this wire (first frame
        # outside blockdiagram.py), useful for compile-time error messages.
        frame = inspect.currentframe()
        wire.callsite = None  # type: ignore[attr-defined]
        while frame is not None:
            if os.path.abspath(frame.f_code.co_filename) != BlockDiagram._this_file:
                wire.callsite = (frame.f_code.co_filename, frame.f_lineno)  # type: ignore[attr-defined]
                break
            frame = frame.f_back
        # just add wire to the list, gets instantiated at compile time
        # when add_output_wire and add_input_wire are called on the blocks
        return self.wirelist.append(wire)  # type: ignore[return-value]

    def delete_block(self, block: Block | str) -> None:
        """
        Delete a block and all wires connected to it.

        :param block: the block to delete, or its name
        :type block: Block or str

        Before delete:    [A] ---> [B] ---> [C]
        After delete(B):  [A]               [C]
        Alternative:      [A] ------------> [C]

        TODO: param to control alternative mode of deletion.  Can only work if B.nin=B.nout
        """

        # check block is in blocklist
        if isinstance(block, str):
            # cannot assume self.blocknames is created yet, so search through blocklist for a block with the given name
            for b in self.blocklist:
                if b.name == block:
                    block = b
                    break
            else:
                raise ValueError("block not found")
        elif isinstance(block, Block):
            if block not in self.blocklist:
                raise ValueError("block not in block diagram")
        else:
            raise ValueError("block must be a Block instance or block name")
        # delete a block and all wires connected to it
        self.blocklist.remove(block)
        self.blocknames.pop(block.name, None)  # type: ignore[arg-type]
        for w in self.wirelist[:]:
            if w.start.block == block or w.end.block == block:
                self.wirelist.remove(w)

    # ---------------------------------------------------------------------- #

    def compile(
        self,
        subsystem: bool = False,
        doimport: bool = True,
        evaluate: bool = True,
        report: bool = False,
        verbose: bool = False,
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
        # self.subsystems is kept: once flattened, the diagram has no subsystem blocks
        # left to find again if it is compiled a second time

        if not subsystem and self.name is None:
            # a top-level diagram is not a block, so its name cannot clash;
            # name it for messages and reports.  Not done for a subsystem: its
            # name, if it has one, is the stem of its instances' names.
            self.name = "main"

        if not subsystem and verbose:
            if not self.compiled:
                print(f"\nCompiling blockdiagram '{self.name}':")
            else:
                print(f"\nRecompiling blockdiagram '{self.name}':")
        self.compiled = False
        self._started = False

        # recursively instantiate all subsystem imports
        self.blocklist, self.wirelist = self._subsystem_import(
            self, "", verbose=verbose
        )

        # replace the INPORT and OUTPORT blocks of the subsystems by wires
        for message in self._elide_subsystem_ports():
            print(f"  ERROR: {message}")
            error = True

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
                    f"wire {w} ({self._wire_loc(w)}) starts at unreferenced block {w.start.block}"
                )
            if w.end.block not in self.blocklist:
                raise RuntimeError(
                    f"wire {w} ({self._wire_loc(w)}) ends at unreferenced block {w.end.block}"
                )

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
                self.statenames.extend(_state_labels(b, b.nstates, "x"))
            if b.blockclass == "sampled":
                self.ndstates += b.ndstates

        # the discrete state is held clock by clock, so it is named clock by clock, in
        # the order of each clock's state vector; bd.dstatenames is those in turn
        for clock in self.clocklist:
            clock.statenames = [
                name
                for b in clock.blocklist
                for name in _state_labels(b, b.ndstates, "X")
            ]
            self.dstatenames.extend(clock.statenames)

        # connect the source and destination blocks to each wire
        if verbose:
            print("  ☑ connecting wires to blocks...")
        for w in self.wirelist:
            try:
                w.start.block.add_output_wire(w)
                w.end.block.add_input_wire(w)

            except:
                print(fg("red"))
                print(
                    f"error connecting wire {w.fullname} ({self._wire_loc(w)}): {sys.exc_info()[1]}"
                )
                print(attr(0))
                error = True

        # check connections for every block
        if verbose:
            print("  ☑ checking block inputs/outputs are connected...")
        for b in self.blocklist:
            # check all inputs are connected
            for port, w in enumerate(b._input_wires):  # type: ignore[assignment]
                if w is None:
                    print(f"  ERROR: [{b}] input {port} is not connected")
                    error = True

            # check all outputs are connected
            for port, ws in enumerate(b._output_wires):
                if len(ws) == 0:
                    print(f"  INFORMATION: [{b}] output {port} is not connected")

            if b._inport_names is not None and len(b._inport_names) != b.nin:
                raise ValueError(f"incorrect number of input names given: {b}")
            if b._outport_names is not None and len(b._outport_names) != b.nout:
                raise ValueError(f"incorrect number of output names given: {b}")
            if b._state_names is not None and len(b._state_names) != (
                b.nstates or b.ndstates
            ):
                raise ValueError(f"incorrect number of state names given: {b}")

        # check for cycles of function blocks
        if verbose:
            print("  ☑ checking for algebraic loops...")

        def _is_algebraic_participant(block: Block) -> bool:
            return block.blockclass == "function" or (
                block.hasstate and block.feedthrough
            )

        visited: set[Block] = set()
        active_path: list[Block] = []
        active_set: set[Block] = set()

        def _dfs_upstream(block: Block) -> bool:
            # Walk upstream through each input source because algebraic loops are
            # dependency cycles: a block can only be in the same algebraic loop as
            # the blocks that feed its current inputs.  We traverse only function
            # blocks and stateful blocks with direct feedthrough, since those are
            # the only blocks whose outputs depend on current-time input values.
            visited.add(block)
            active_path.append(block)
            active_set.add(block)

            for source in block.sources:
                if not _is_algebraic_participant(source):
                    continue

                if source in active_set:
                    cycle_start = active_path.index(source)
                    cycle = active_path[cycle_start:] + [source]
                    print(
                        "  ERROR: cycle found:\n   ",
                        "\n    ".join(str(node) for node in cycle),
                    )
                    return True

                if source not in visited and _dfs_upstream(source):
                    return True

            active_set.remove(block)
            active_path.pop()
            return False

        for b in self.blocklist:
            if _is_algebraic_participant(b) and b not in visited:
                if _dfs_upstream(b):
                    error = True
                    break

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
            source_slot = w.start.block.outport_slot(w.start.port)  # type: ignore[arg-type]
            w.bind_slot(source_slot)
            w.end.block.bind_input_slot(w.end.port, source_slot)  # type: ignore[arg-type]

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

            # the values it left on the wires give each wire's signature
            self._record_signatures()

        if error:
            # show report if there was an error
            if not report:
                self.report()
            if not subsystem:
                raise RuntimeError("could not compile system")
        else:
            self.compiled = True

        # --param asks for the table of parameters; it is an explicit request so it
        # is printed even with -q
        options = getattr(getattr(self, "runtime", None), "options", None)
        if not subsystem and options is not None and getattr(options, "param", False):
            self.report_params()

        return self.compiled

    def _record_signatures(self) -> None:
        """Record the signature of every wire from the values now on the slots.

        Called by :meth:`compile` after the trial evaluation, which has run
        every block once in schedule order.  The signature is kept on the slot,
        so it is shared by the producer's output port and every input port wired
        to it, and :meth:`reset` does not clear it.
        """
        for b in self.blocklist:
            for slot in b._outport_slots:
                slot.signature = Signature.of(slot.value)

    def _elide_subsystem_ports(self) -> list[str]:
        """
        Replace the INPORT and OUTPORT blocks of instantiated subsystems by wires.

        :return: error messages, empty if all is well

        Flattening leaves the port blocks of each subsystem in the network, each a pass
        through.  They are blocks with several inputs and outputs, so the loop detector
        and the scheduler see every output depending on every input, which finds loops
        that are not there (Issue #84).  Here the wires that leave a port block are
        started where the signal really comes from, its *source*, and the wires that end
        on a port block are dropped.  Only the wires are needed, so this is done before
        the blocks are compiled.

        The source of each subsystem input and output is kept on the subsystem block,
        see :attr:`SubsystemBlock.inports` and :attr:`SubsystemBlock.outports`, which is
        how the signals of a subsystem are watched.
        """
        pending = [sb for sb in self.subsystems.values() if not sb._ports_elided]
        if not pending:
            return []

        owner: dict[Block, Any] = {}  # port block -> its subsystem block
        for sb in pending:
            owner[sb.inport] = sb
            owner[sb.outport] = sb

        # the wire that feeds each input of a port block
        feeder: dict[tuple[Block, Any], Wire] = {}
        for w in self.wirelist:
            if w.end.block in owner:
                feeder[(w.end.block, w.end.port)] = w

        problems: list[str] = []

        def source(plug: Plug) -> Plug | None:
            """Follow the plug back through port blocks to the output port that drives it."""
            seen: set[tuple[Block, Any]] = set()
            while plug.block in owner:
                key = (plug.block, plug.port)
                if key in seen:
                    problems.append(
                        f"the ports of subsystem {owner[plug.block].name} are wired "
                        "in a loop with nothing in between"
                    )
                    return None
                seen.add(key)
                wire = feeder.get(key)
                if wire is None:
                    return None
                plug = wire.start
            return plug

        for sb in pending:
            sb._source_inports = [
                source(StartPlug(sb.inport, i)) for i in range(sb.inport.nout)
            ]
            sb._source_outports = [
                source(StartPlug(sb.outport, j)) for j in range(sb.outport.nin)
            ]
            for i, plug in enumerate(sb._source_inports):
                if plug is None:
                    problems.append(
                        f"input {i} of subsystem {sb.name} is not connected"
                    )
            sb._ports_elided = True

        wires = []
        for w in self.wirelist:
            if w.end.block in owner:
                continue  # feeds a port block, the wires that leave it start at its source
            if w.start.block in owner:
                plug = source(w.start)
                if plug is None:
                    continue  # reported above
                w.newstart(plug)
            wires.append(w)
        self.wirelist = wires
        self.blocklist = [b for b in self.blocklist if b not in owner]
        for i, w in enumerate(self.wirelist):
            w.id = i  # type: ignore[assignment]
        for i, b in enumerate(self.blocklist):
            b.id = i  # type: ignore[assignment]

        return list(dict.fromkeys(problems))

    def _subsystem_import(
        self, bd: BlockDiagram, sspath: str, verbose: bool = False, depth: int = 0
    ) -> tuple[list[Block], list[Wire]]:
        """Recursively import subsystems

        :param bd: the block diagram in which to instantiate subsystems
        :type bd: BlockDiagram
        :param sspath: subsystem name prefix
        :type sspath: str
        :param verbose: print details of subsystem instantiation, defaults to False
        :type verbose: bool, optional
        :param depth: subsystem import recursion depth, defaults to 0
        :type depth: int, optional
        :return: the blocks and wires of the subsystem, with their names prefixed
        :rtype: tuple[list[Block], list[Wire]]
        """
        blocks = []  # create an empty block list
        wires = bd.wirelist  # start with wires in the current diagram

        for b in bd.blocklist:
            if b.name is None:
                raise RuntimeError("a block in a diagram is always named")
            # rename the block to include subsystem path
            if sspath:
                b.name = sspath + "/" + b.name

            if not isinstance(b, SubsystemBlock):
                # not a Subsystem block, just add the block to the list
                b._depth = depth
                blocks.append(b)
            else:
                # Subsystem block encountered, recurse to find its constituent blocks and wires
                # do not add it to the block list, it was just a container for the subsystem blocks and wires
                if verbose:
                    print(f"{'  ' * (depth + 1)}instantiating subsystem ", b.name)
                self.subsystems[b.name] = b
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
            b.id = i  # type: ignore[assignment]
        for i, w in enumerate(wires):
            w.id = i  # type: ignore[assignment]
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
                if xb is None:
                    raise ValueError(f"block {b} has no state entry")
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

    def evaluate(
        self,
        state_map: dict[Block, np.ndarray | None],
        t: float,
        sinks: bool = True,
        *,
        check: bool | None = None,
        overrides: dict[Block, list[Any]] | None = None,
    ) -> None:
        """
        Evaluate all blocks in the network using the compiled execution schedule

        :param state_map: block->state map
        :type state_map: dict
        :param t: current time
        :type t: float
        :param sinks: evaluate sink blocks, defaults to True
        :type sinks: bool, optional
        :param check: check the block outputs, defaults to the diagram's ``check``
            attribute, which :meth:`~bdsim.BDSim.run` sets from the ``check`` option
        :type check: bool, optional
        :param overrides: output values to publish for some blocks, instead of
            calling their ``output`` method; the list has one value per output
            port.  Used by :meth:`functions` to replace the source blocks.
        :type overrides: dict, optional

        Performs the following steps:

        1. Read state values from the provided runtime state map
        2. Execute the blocks in the order given by the ``plan``. The block
           outputs are "sent" to their connected inputs.

        Sink blocks are not executed here, but after completion their inputs
        will all be valid.

        If ``check`` is true every block's output is checked as it is produced,
        see :meth:`_check_output_form` and :meth:`_check_published`.  The
        checks cost time, ``--no-check`` skips them.
        """
        if check is None:
            check = self.check

        # TODO: don't copy outputs to inputs of next block, have inputs
        # pull the value from connected inputs

        try:
            self.runtime.DEBUG(
                "state", ">>>>>>>>> t={}, x={} >>>>>>>>>>>>>>>>", t, state_map
            )

            self._state_map = state_map

            self.runtime.DEBUG("propagate", "t={:.3f}", t)

            for sequence, group in enumerate(self.plan):
                for b in group:
                    # inports = None if sequence == 0 else b.inport_values
                    inports = b.inport_values
                    block_state = state_map.get(b)
                    if overrides is not None and b in overrides:
                        out = overrides[b]
                    else:
                        out = b.output_safe(t, inports, block_state)

                    self.runtime.DEBUG("propagate", "block {:s}: output = {}", b, out)

                    if check and (type(out) is not list or len(out) != b.nout):
                        self._check_output_form(b, out, t, inports, block_state)

                    b._publish_output_values(out)

                    if check:
                        self._check_published(b, t, inports, block_state)

            if sinks:
                for b in self.blocklist:
                    if isinstance(b, SinkBlock):
                        b.step_safe(t, b.inport_values)
        except BlockRuntimeError as err:
            self._handle_block_runtime_error(err)

    # ---------------------------------------------------------------------- #
    # run-time checks, all switched by ``check``, see evaluate(), deriv(), next()

    @staticmethod
    def _check_failed(
        b: Block, operation: str, message: str, t: float, inputs: Any, state: Any
    ) -> NoReturn:
        b._raise_runtime_error(
            operation, AssertionError(message), t=t, inputs=inputs, state=state
        )
        raise AssertionError(message)  # pragma: no cover, _raise_runtime_error raises

    def _check_output_form(
        self, b: Block, out: Any, t: float, inputs: Any, state: Any
    ) -> None:
        """The block returned a list with one value per output port."""
        if not isinstance(out, (tuple, list)):
            self._check_failed(
                b,
                "output",
                f"block {b} output must be a list: {type(out)}",
                t,
                inputs,
                state,
            )
        if len(out) != b.nout:
            self._check_failed(
                b,
                "output",
                f"block {b} output has incorrect length: {len(out)} instead of {b.nout}",
                t,
                inputs,
                state,
            )

    def _check_published(self, b: Block, t: float, inputs: Any, state: Any) -> None:
        """What the block published is finite and has the signature seen at compile time.

        Looks at the value as published, after the scalar collapse.  An output
        with no recorded signature, because the diagram was compiled with
        ``evaluate=False``, is not compared.

        This runs for every block on every evaluation, so the common cases, a
        float or an int of the type recorded at compile time, are handled
        before any function call.
        """
        for port, slot in enumerate(b._outport_slots):
            value = slot.value
            kind = type(value)

            if kind is float:
                finite = math.isfinite(value)
            elif kind is int or kind is bool:
                finite = True
            else:
                finite = _is_finite(value)
            if not finite:
                self._check_failed(
                    b,
                    "output",
                    f"output {port} contains NaN or Inf",
                    t,
                    inputs,
                    state,
                )

            signature = slot.signature
            if signature is None:
                continue
            if kind is signature.type and kind is not np.ndarray:
                continue
            if not signature.matches_value(value):
                self._check_failed(
                    b,
                    "output",
                    f"output {port} changed signature: "
                    f"was {signature}, now {Signature.of(value)}",
                    t,
                    inputs,
                    state,
                )

    def _check_deriv(self, b: Block, yd: Any, t: float, state: Any) -> None:
        """The derivative is a 1-D ndarray with one element per continuous state."""
        if not isinstance(yd, np.ndarray):
            self._check_failed(
                b,
                "deriv",
                f"deriv: block {b} did not return ndarray",
                t,
                b.inport_values,
                state,
            )
        if yd.ndim != 1 or yd.shape[0] != b.nstates:
            self._check_failed(
                b,
                "deriv",
                f"deriv: block {b} returns wrong shape {yd.shape}, should be ({b.nstates},)",
                t,
                b.inport_values,
                state,
            )

    def _check_next(self, b: Block, xb: Any, t: float, state: Any) -> None:
        """The next discrete state is an ndarray."""
        if not isinstance(xb, np.ndarray):
            self._check_failed(
                b,
                "next",
                f"next: block {b} did not return ndarray",
                t,
                b.inport_values,
                state,
            )

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
            if b.blockclass == "source" or (b.hasstate and not b.feedthrough):
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

        if any(b._sequence is None for b in self.blocklist):
            raise RuntimeError(
                "could not create execution plan, check for algebraic loops"
            )

        self.plan = plan

    # ---------------------------------------------------------------------- #

    def _debugger(self, simstate: SimulationState, integrator: Any = None) -> None:
        if simstate.t_stop is not None and simstate.t < simstate.t_stop:  # type: ignore[operator]
            return

        def print_output(b: Block, t: float, inports: list[Any]) -> None:
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
                print_output(b, t or 0.0, b.inport_values)

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
                        print_output(b, t or 0.0, b.inport_values)
                    else:
                        for b in self.blocklist:
                            if b.nout > 0:
                                print_output(b, t or 0.0, b.inport_values)
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
            for b in self.xindex:  # the blocks that have continuous state, in order
                x0 = np.r_[x0, b.getstate0_safe()]
            return x0
        except BlockRuntimeError as err:
            self._handle_block_runtime_error(err)

    def reset(self) -> None:
        """
        Restore the initial internal state of every block.

        Invokes the ``reset`` method on all blocks.  Called by :meth:`start`,
        once per run, before the blocks are started.  It does not clear the
        values on the wires.

        """
        try:
            for b in self.blocklist:
                b.reset_safe()
        except BlockRuntimeError as err:
            self._handle_block_runtime_error(err)

    def step(self, t: float) -> None:
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

    def record(self, t: float) -> None:
        """
        Record one accepted sample on all sink blocks.

        :param t: simulation time
        :type t: float

        Unlike :meth:`step`, this is called on *every* accepted simulation
        sample, not just periodically for display refresh, so sink blocks
        that log signal data at full resolution (e.g. ``Scope``) do so here
        rather than in ``step``, which may run at a throttled rate.
        """

        try:
            for b in self.blocklist:
                if isinstance(b, SinkBlock):
                    b.record_safe(t, b.inport_values)
        except BlockRuntimeError as err:
            self._handle_block_runtime_error(err)

    def deriv(
        self,
        t: float,
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
                    if self.check:
                        self._check_deriv(b, yd, t, block_state)
                    YD = np.r_[YD, yd]
            self.runtime.DEBUG("deriv", YD)
            return YD
        except BlockRuntimeError as err:
            self._handle_block_runtime_error(err)

    def next(
        self,
        t: float,
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
                if self.check:
                    self._check_next(b, xb, t, block_state)
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

        # undo anything the compile-time trial evaluation or a previous run did
        # to the blocks' own state
        self.reset()

        # let each block read the signatures compile() recorded
        try:
            for b in self.blocklist:
                b.configure_safe()
        except BlockRuntimeError as err:
            self._handle_block_runtime_error(err)

        try:
            for b in self.blocklist:
                b.start_safe(simstate)
        except BlockRuntimeError as err:
            self._handle_block_runtime_error(err)

        try:
            for b in self.blocklist:
                b.validate_start_safe()
        except BlockRuntimeError as err:
            self._handle_block_runtime_error(err)

        self._started = True

    def initialstate(self) -> None:
        self._state_map = self.initial_state_map()

    def done(self, block: bool = False) -> None:
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
        ``None`` (default) allows evaluation with a one-time warning.  A NumPy dtype
        literal such as ``float32([1, 2])`` or ``uint16(5)`` is parsed without
        ``eval``, so it is accepted whatever ``allow_eval`` is, see
        ``bdsim.literals``.
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
                    try:
                        literal = parse_literal(value)
                    except ValueError as err:
                        raise RuntimeError(
                            f"bdload: bad parameter {key} for block [{block['title']}]: {err}"
                        ) from err
                    if literal is not NOT_A_LITERAL:
                        # a NumPy dtype literal, parsed safely, no eval needed
                        newvalue = literal
                    elif value.startswith("="):
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

                # Handle blocks with variable input/output counts (nin=-1 or nout=-1).
                # When bdedit saves a block with inputsNum=2, but SCOPE constructor
                # doesn't get "nin" in the parameters, it defaults to nin=1.
                # Fix: pass the inputsNum/outputsNum from JSON for known variable blocks.
                if block["block_type"] == "SCOPE" and "nin" not in params:
                    params["nin"] = block.get("inputsNum", 1)

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
