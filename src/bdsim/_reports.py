"""Reports on a block diagram: summaries, lists, parameters and the schedule.

These methods are split out of :mod:`bdsim.blockdiagram` as a mixin, so that
``bd.report()`` and friends are unchanged for callers.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any, Callable

import numpy as np
from ansitable import ANSITable, Column  # type: ignore[import-not-found]

from bdsim.components import EventSource
from bdsim.signature import Signature

if TYPE_CHECKING:
    from bdsim.components import Block, Clock, SimulationState, Wire


def _value_str(value: Any, width: int = 40) -> str:
    """A value for display in a table: on one line, abbreviated if it is long."""
    if isinstance(value, np.ndarray):
        text = np.array2string(
            value, precision=4, threshold=6, edgeitems=2, max_line_width=1000
        )
    elif callable(value):
        text = f"<{getattr(value, '__name__', type(value).__name__)}>"
    else:
        text = repr(value)
    text = " ".join(text.split())
    return text if len(text) <= width else text[: width - 1] + "…"


def _signature_str(signature: Signature | None) -> str:
    """Signature for display in a report, ``?`` if the wire was not observed."""
    return "?" if signature is None else str(signature)


class ReportMixin:
    """Methods of :class:`~bdsim.blockdiagram.BlockDiagram` that print reports.

    The attributes declared below are the ones these methods read; they are set
    by ``BlockDiagram``.
    """

    if TYPE_CHECKING:
        blocklist: list[Block]
        wirelist: list[Wire]
        blocknames: dict[str, Any]
        clocklist: list[Clock]
        subsystems: dict[str, Any]
        plan: Any

    def ls(self) -> None:
        """
        List the blocks in the diagram, grouped by block type

        Each line is a block type followed by the names of the blocks of that
        type, in the order they were added.  The types are in order of first use.

        :seealso: :meth:`report_lists`
        """
        names_by_type: dict[str, list[str]] = {}
        for name, block in self.blocknames.items():
            names_by_type.setdefault(block.type, []).append(name)
        for blocktype, names in names_by_type.items():
            print(f"{blocktype:12s}: ", ", ".join(names))

    def report_summary(
        self, sortby: str = "name", depth: int | None = None, **kwargs: Any
    ) -> None:
        """
        Print a summary of block diagram.

        :param sortby: sort rows by specified block attribute: "name" [default] or "type"
        :type sortby: str, optional
        :param depth: only show blocks with subsystem depth less than or equal to this value, defaults to None (show all)
        :type depth: int, optional
        :param kwargs: options passed to :meth:`ansitable.table.ANSIMatrix.print`
        :type kwargs: dict

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
            sortfunc: Callable[[Block], Any] = lambda x: x.name
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
            name: str = b.name or ""
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
                    typ = _signature_str(b.insig[port])
                    src_name = source.block.name or ""
                    if source.block.nout > 1:
                        src_name += f"[{source.port}]"
                    if port == 0:
                        # first row for this block
                        table.row(
                            name,
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

    def report(self, **kwargs: Any) -> None:
        warnings.warn("use reports_lists() method instead", DeprecationWarning)
        self.report_lists(**kwargs)

    def report_lists(self, **kwargs: Any) -> None:
        """
        Print a tabular report about the block diagram.

        :param kwargs: options passed to :meth:`ansitable.table.ANSIMatrix.print`
        :type kwargs: dict

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
        nstates = 0
        ndstates = 0
        for b in self.blocklist:
            table.row(b.id, b.name, b.nin, b.nout, b.nstates, b.ndstates, b.type)
            nstates += b.nstates
            ndstates += b.ndstates
        table.rule()
        table.row("", "total", "", "", nstates, ndstates, "")
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
            start: str = f"{wire.start.block.id}[{wire.start.port}]"
            end: str = f"{wire.end.block.id}[{wire.end.port}]"

            typ = _signature_str(wire.end.block.insig[wire.end.port])  # type: ignore[index, arg-type]
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
                    if c is None:
                        raise ValueError(f"sampled block {b} has no clock")
                    table.row(b.id, b.name, c.name, c.T, c.offset)
            table.print(**kwargs)

    def report_subsystems(self, **kwargs: Any) -> None:
        """
        Print a table of the inputs and outputs of the subsystems.

        :param kwargs: options passed to :meth:`ansitable.table.ANSIMatrix.print`
        :type kwargs: dict

        A subsystem block is not part of the compiled network, and its INPORT and OUTPORT
        blocks have been replaced by wires, so the signals that cross its boundary are
        listed here.  The columns are

        1. the port, such as ``pid.0[1]``, which is what can be watched
        2. ``in`` or ``out``
        3. the block and port that the signal comes from, the *source*, which for an
           output is a block inside the subsystem (looking through nested subsystems) and
           for an input is a block outside it
        4. the type of the signal, as the signature recorded when the diagram was compiled

        :seealso: :attr:`SubsystemBlock.inports` :attr:`SubsystemBlock.outports`
        """
        table = ANSITable(
            Column("port", headalign="^", colalign="<"),
            Column("", headalign="^", colalign="<"),
            Column("source", headalign="^", colalign="<"),
            Column("type", headalign="^", colalign="<"),
            border="thin",
        )
        for name, sub in self.subsystems.items():
            for direction, plugs in (("in", sub.inports), ("out", sub.outports)):
                for port, plug in enumerate(plugs):
                    if plug is None:
                        source, signature = "?", None
                    else:
                        source = f"{plug.block.name}[{plug.port}]"
                        sigs = getattr(plug.block, "outsig", None)
                        signature = sigs[plug.port] if sigs else None
                    table.row(
                        f"{name}[{port}]", direction, source, _signature_str(signature)
                    )
        table.print(**kwargs)

    def report_params(self, fixed: bool = False, **kwargs: Any) -> None:
        """
        Print a table of the parameters of all blocks and their current values.

        :param fixed: also list the parameters that are fixed when the block is
            created, defaults to False
        :type fixed: bool, optional
        :param kwargs: options passed to :meth:`ansitable.table.ANSIMatrix.print`
        :type kwargs: dict

        The first column is the name exactly as it is used by the ``--set`` option,
        ``block:param``, and by :meth:`Block.set_param`.  The columns are

        1. the name, ``block:param``
        2. the current value, abbreviated if it is long
        3. its type, as the signature of the value
        4. when it can be set: ``anytime``, ``setup`` (before the run starts), or
           ``never`` (only with ``fixed=True``)

        Blocks inside a subsystem are listed with the path of the subsystem, such as
        ``sub/gain.0:K``.  A subsystem block that declares parameters of its own, such
        as ``PID``, is listed by its own name, ``pid.0:P``, instead of the blocks inside
        it, which can still be set by their own names.  The ``--param`` option prints
        this table when the diagram is compiled.

        :seealso: :meth:`Block.add_param` :meth:`Block.set_param`
        """
        table = ANSITable(
            Column("parameter", headalign="^", colalign="<"),
            Column("value", headalign="^", colalign="<"),
            Column("type", headalign="^", colalign="<"),
            Column("when", headalign="^", colalign="<"),
            border="thin",
        )
        # A subsystem that declares parameters presents those, and its inner blocks, which
        # can still be set by their own names, are not listed.  Names are full paths,
        # so a subsystem inside a subsystem is under the prefix of the outer one.
        declared = [
            name
            for name, sub in self.subsystems.items()
            if any(
                p.forward is not None or p.unavailable is not None
                for p in sub._parameters.values()
            )
        ]
        inside = tuple(name + "/" for name in declared)
        owners: list[Any] = [
            self.subsystems[name] for name in declared if not name.startswith(inside)
        ]

        for b in [*owners, *self.blocklist]:
            if b.name.startswith(inside) and b not in owners:
                continue
            for name, param in b._parameters.items():
                when = b._param_when(param)
                if when == "never" and not fixed:
                    continue
                value = b._param_value(name)
                table.row(
                    f"{b.name}:{name}",
                    _value_str(value),
                    _signature_str(Signature.of(value)),
                    when,
                )
        table.print(**kwargs)

    def report_schedule(self, **kwargs: Any) -> None:
        """
        Display execution schedule in tabular form

        :param kwargs: options passed to :meth:`ansitable.table.ANSIMatrix.print`
        :type kwargs: dict

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

    def blockvalues(
        self, t: float | None = None, simstate: SimulationState | None = None
    ) -> None:
        for b in self.blocklist:
            print(f"Block {b.name}:")
            print("  inputs:  ", b.inport_values)
            if b.nout > 0:
                print("  outputs: ", [b.outport_value(i) for i in range(b.nout)])
