"""Graph output for a block diagram: GraphViz dot files and rendered graphs.

These methods are split out of :mod:`bdsim.blockdiagram` as a mixin, so that
``bd.graph()`` and friends are unchanged for callers.  They read only the
diagram's ``blocklist``, ``wirelist`` and ``plan``.
"""

from __future__ import annotations

import io
import json
from tempfile import _TemporaryFileWrapper
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bdsim.components import Block, Wire


class GraphMixin:
    """Methods of :class:`~bdsim.BlockDiagram` that draw it as a graph.

    The attributes declared below are the ones these methods read; they are set
    by ``BlockDiagram``.
    """

    if TYPE_CHECKING:
        blocklist: list[Block]
        wirelist: list[Wire]
        plan: Any

    def schedule_dotfile(self, filename: str | io.TextIOWrapper) -> None:
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
            file.write(f"\tsubgraph step{sequence} {{\n")
            file.write("\t\trank=same;\n")

            for b in group:
                file.write(f'\t\t"{b.name}"\n')

            file.write("\t}\n\n")

        # connect them to their sources, except if a transfer block
        for b in self.blocklist:
            if not b.blockclass == "continuous":
                for p in b.sources:
                    file.write(f'\t"{p.name}" -> "{b.name}"\n')

        file.write("}\n")

    def dotfile(self, filename: str | io.TextIOWrapper, shapes: Any = None) -> None:
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

        :seealso: :meth:`graph` :meth:`showgraph`
        """
        if shapes is None:
            shapes = dict(
                source="record",
                sink="Mrecord",
                graphics="Mrecord",
                continuous="box3d",
                sampled="box3d",
            )

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
                options.append(f"shape={shapes[b.blockclass]}")
            if b.blockclass == "source":
                options.append('rank="source"')
            if b.blockclass in ("sink", "graphics"):
                options.append('rank="sink"')
            if b.pos is not None:
                options.append(f'pos="{b.pos[0]:g},{b.pos[1]:g}!"')
            # options.append(
            #     'xlabel=<<BR/><FONT POINT-SIZE="8" COLOR="blue">{:s}</FONT>>'.format(
            #         b.type
            #     )
            # )
            if b.label != b.name:
                # the node is the name, which identifies the block; show the value too
                options.append('label="{:s}"'.format(b.label.replace('"', r"\"")))
            if len(options) > 0:
                file.write('\t"{:s}" [{:s}]\n'.format(b.name, ", ".join(options)))
        file.write("\n")

        # add the wires
        for w in self.wirelist:
            options = []
            # options.append('xlabel="{:s}"'.format(w.name))
            if w.end.block.type == "sum":
                options.append(f'headlabel="{w.end.block.signs[w.end.port]} "')
                options.append("labeldistance=1.5")
            if w.end.block.type == "prod":
                options.append(f'headlabel="{w.end.block.ops[w.end.port]} "')
                options.append("labeldistance=1.5")
            file.write(
                '\t"{:s}" -> "{:s}" [{:s}]\n'.format(
                    w.start.block.name, w.end.block.name, ", ".join(options)
                )
            )

        file.write("}\n")

    def graph(
        self,
        format: str = "dot",  # pylint: disable=redefined-builtin
        filename: str | io.TextIOWrapper | None = None,
        shapes: Any = None,
    ) -> str:
        r"""Render diagram text in DOT, Mermaid, GraphML, or ELK JSON format.

        :param format: graph output format: ``"dot"``, ``"mermaid"``,
            ``"mermaid_fenced"``, ``"graphml"`` or ``"elk"``
        :type format: str, optional
        :param filename: destination path or open text stream, defaults to None
        :type filename: str | file handle | None, optional
        :param shapes: optional DOT block shape mapping (DOT output only)
        :type shapes: dict, optional
        :return: rendered graph text
        :rtype: str

        If ``filename`` is provided the rendered text is also written to it.

        ``"mermaid_fenced"`` is identical to ``"mermaid"`` but wraps the output in
        a ``\`\`\`mermaid`` fenced code block, ready to paste into Markdown or a
        Jupyter notebook cell.

        Mermaid format can be rendered in Markdown files and on GitHub, and GraphML and
        ELK JSON can be imported into graph visualization tools such as yEd and Eclipse
        ELK respectively.

        **Node shapes by block kind** (``dot`` and ``mermaid`` only)

        .. list-table::
           :header-rows: 1

           * - Block kind
             - DOT shape
             - Mermaid shape
           * - source
             - ``record``
             - rectangle ``[label]``
           * - stateful (continuous, sampled, or ``hasstate``)
             - ``box3d``
             - subroutine ``[[label]]``
           * - sum / prod
             - (default ellipse)
             - circle ``((label))``
           * - graphics / display
             - ``Mrecord``
             - asymmetric ``>label]``
           * - sink
             - ``Mrecord``
             - rectangle ``[label]``
           * - function / other
             - (default ellipse)
             - rectangle ``[label]``

        In a Jupyter notebook, the graph can be rendered directly by exporting in `mermaid_fenced` format
        and using using IPython's ``display`` function::

            from IPython.display import Markdown, display

            display(Markdown(bd.graph(format="mermaid_fenced"))) # Render dynamically via Jupyter's built-in Mermaid engine

        :seealso: :func:`dotfile`
        """

        graph_format = format.lower()
        if graph_format == "dot":
            stream: Any = io.StringIO()
            self.dotfile(stream, shapes=shapes)
            text = stream.getvalue()
        elif graph_format in ("mermaid", "mermaid_fenced"):
            lines = ["flowchart LR"]
            node_ids: dict[Any, str] = {}

            for i, b in enumerate(self.blocklist):
                node_id = f"b{i}"
                node_ids[b] = node_id
                label_raw = b.label if b.name is not None else f"{b.type}_{i}"
                label = label_raw.replace('"', r"\"")
                if b.type == "sum":
                    # circle
                    node_str = f'{node_id}(("{label}"))'
                elif b.isgraphics:
                    # asymmetric (display/sink)
                    node_str = f'{node_id}>"{label}"]'
                elif b.hasstate:
                    # subroutine-style (stateful)
                    node_str = f'{node_id}[["{label}"]]'
                else:
                    node_str = f'{node_id}["{label}"]'
                lines.append(f"    {node_str}")

            for w in self.wirelist:
                start = node_ids[w.start.block]
                end = node_ids[w.end.block]
                edge_label = ""
                if w.end.block.type == "sum":
                    edge_label = str(w.end.block.signs[w.end.port])
                elif w.end.block.type == "prod":
                    edge_label = str(w.end.block.ops[w.end.port])

                if edge_label:
                    edge_label = edge_label.replace('"', r"\"")
                    lines.append(f'    {start} -->|"{edge_label}"| {end}')
                else:
                    lines.append(f"    {start} --> {end}")

            text = "\n".join(lines) + "\n"
            if graph_format == "mermaid_fenced":
                text = "```mermaid\n" + text + "```\n"
        elif graph_format == "graphml":
            node_ids = {}

            def _xml_escape(value: str) -> str:
                return (
                    value.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&apos;")
                )

            lines = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"',
                '         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
                '         xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns',
                '         http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">',
                '  <key id="node_label" for="node" attr.name="label" attr.type="string"/>',
                '  <key id="node_type" for="node" attr.name="type" attr.type="string"/>',
                '  <key id="node_class" for="node" attr.name="class" attr.type="string"/>',
                '  <key id="edge_label" for="edge" attr.name="label" attr.type="string"/>',
                '  <graph id="G" edgedefault="directed">',
            ]

            for i, b in enumerate(self.blocklist):
                node_id = f"n{i}"
                node_ids[b] = node_id
                label_raw = b.label if b.name is not None else f"{b.type}_{i}"
                lines.extend(
                    [
                        f'    <node id="{node_id}">',
                        f'      <data key="node_label">{_xml_escape(label_raw)}</data>',
                        f'      <data key="node_type">{_xml_escape(b.type)}</data>',
                        f'      <data key="node_class">{_xml_escape(b.blockclass)}</data>',
                        "    </node>",
                    ]
                )

            for i, w in enumerate(self.wirelist):
                source = node_ids[w.start.block]
                target = node_ids[w.end.block]
                edge_label = ""
                if w.end.block.type == "sum":
                    edge_label = str(w.end.block.signs[w.end.port])
                elif w.end.block.type == "prod":
                    edge_label = str(w.end.block.ops[w.end.port])

                lines.append(
                    f'    <edge id="e{i}" source="{source}" target="{target}">'
                )
                if edge_label:
                    lines.append(
                        f'      <data key="edge_label">{_xml_escape(edge_label)}</data>'
                    )
                lines.append("    </edge>")

            lines.extend(["  </graph>", "</graphml>"])
            text = "\n".join(lines) + "\n"
        elif graph_format == "elk":
            node_ids = {}
            port_ids: dict[tuple[Any, str, int], str] = {}

            children = []
            edges = []

            for i, b in enumerate(self.blocklist):
                node_id = f"n{i}"
                node_ids[b] = node_id
                label_raw = b.label if b.name is not None else f"{b.type}_{i}"

                ports = []
                for p in range(b.nin):
                    pid = f"{node_id}:in{p}"
                    port_ids[(b, "in", p)] = pid
                    ports.append(
                        {
                            "id": pid,
                            "properties": {
                                "org.eclipse.elk.port.side": "WEST",
                            },
                        }
                    )

                for p in range(b.nout):
                    pid = f"{node_id}:out{p}"
                    port_ids[(b, "out", p)] = pid
                    ports.append(
                        {
                            "id": pid,
                            "properties": {
                                "org.eclipse.elk.port.side": "EAST",
                            },
                        }
                    )

                children.append(
                    {
                        "id": node_id,
                        "labels": [{"text": label_raw}],
                        "width": 120,
                        "height": 50,
                        "ports": ports,
                        "properties": {
                            "bdsim.type": b.type,
                            "bdsim.class": b.blockclass,
                        },
                    }
                )

            for i, w in enumerate(self.wirelist):
                if not isinstance(w.start.port, int) or not isinstance(w.end.port, int):
                    continue

                source_port = port_ids.get((w.start.block, "out", w.start.port))
                target_port = port_ids.get((w.end.block, "in", w.end.port))
                if source_port is None or target_port is None:
                    continue

                edge: dict[str, Any] = {
                    "id": f"e{i}",
                    "sources": [source_port],
                    "targets": [target_port],
                }

                edge_label = ""
                if w.end.block.type == "sum":
                    edge_label = str(w.end.block.signs[w.end.port])
                elif w.end.block.type == "prod":
                    edge_label = str(w.end.block.ops[w.end.port])
                if edge_label:
                    edge["labels"] = [{"text": edge_label}]

                edges.append(edge)

            elk_graph = {
                "id": "root",
                "layoutOptions": {
                    "org.eclipse.elk.algorithm": "layered",
                    "org.eclipse.elk.direction": "RIGHT",
                    "org.eclipse.elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
                    "org.eclipse.elk.edgeRouting": "ORTHOGONAL",
                },
                "children": children,
                "edges": edges,
            }
            text = json.dumps(elk_graph, indent=2) + "\n"
        else:
            raise ValueError(
                "unsupported graph format "
                f"'{format}', expected 'dot', 'mermaid', 'mermaid_fenced', 'graphml' or 'elk'"
            )

        if filename is not None:
            if isinstance(filename, str):
                with open(filename, "w") as file:
                    file.write(text)
            else:
                filename.write(text)

        return text

    def showgraph(self) -> None:
        """
        Display diagram as a graph in browser tab

        :seealso: :meth:`dotfile` :meth:`graph`
        """

        # Lazy import
        try:
            import tempfile
            import subprocess  # nosec B404
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
        # constant command string, but see #198 about shell=True
        subprocess.run(  # nosec B602 B607  # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit.dangerous-subprocess-use-audit
            "dot -Tpdf", shell=True, stdin=dotfile, stdout=pdffile
        )

        # open the PDF file in browser (hopefully portable), then cleanup
        webbrowser.open(f"file://{pdffile.name}")
