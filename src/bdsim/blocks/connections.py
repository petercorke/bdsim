"""
Connection blocks are in two categories:

1. Signal manipulation:
    - have inputs and outputs
    - have no state variables
    - are a subclass of ``FunctionBlock`` |rarr| ``Block``
2. Subsystem support
    - have inputs or outputs
    - have no state variables
    - are a subclass of ``SubsysytemBlock`` |rarr| ``Block``

"""

from __future__ import annotations

import importlib
import types
import copy
from pathlib import Path
from typing import Any, cast

import numpy as np

import bdsim
from bdsim.blockdiagram import bdload
from bdsim.blockdiagram import BlockDiagram
from bdsim.components import SubsystemBlock, SourceBlock, SinkBlock, FunctionBlock


# ------------------------------------------------------------------------ #
class Item(FunctionBlock):
    """
    :blockname:`ITEM`

    Select item from a dictionary signal.

    :inputs: 1
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - 0
            - dict
            - ``D``
        *   - Output
            - 0
            - any
            - ``D[i]``

    For a dictionary type input signal, select one item as the output signal.
    For example::

        item = bd.ITEM("xd")

    selects the ``xd`` item from the dictionary signal input to the block.

    This is somewhat like a demultiplexer :class:`DeMux` but allows for
    named heterogeneous data.
    A dictionary signal can serve a similar purpose to a "bus" in Simulink(R).

    :seealso: :class:`Dict`
    """

    nin = 1  # type: ignore[assignment]
    nout = 1  # type: ignore[assignment]

    def __init__(self, item: Any, **blockargs: Any) -> None:
        """
        :param item: name of dictionary item
        :type item: str
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """

        super().__init__(**blockargs)
        self.item: Any = item

    def output(self, t: float, inputs: list[Any], x: Any) -> list[Any]:
        input = inputs[0]
        # TODO, handle inputs that are vectors themselves
        assert isinstance(input, dict), "Input signal must be a dict"
        assert self.item in input, "Item is not in input dict"
        return [input[self.item]]


class Dict(FunctionBlock):
    """
    :blockname:`DICT`

    Create a dictionary signal.

    :inputs: N
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - i
            - any
            - :math:`x_i`
        *   - Output
            - 0
            - dict
            - ``{key: x[i] for i, key in enumerate(keys)}``

    Inputs are assigned to a dictionary signal, using the corresponding
    names from ``keys``.
    For example::

        dd = bd.DICT(["x", "xd", "xdd"])

    expects three inputs and assigns them to dictionary items ``x``, ``xd``, ``xdd`` of
    the output dictionary respectively.

    This is somewhat like a multiplexer :class:`Mux` but allows for named heterogeneous
    data.  A dictionary signal can serve a similar purpose to a "bus" in Simulink(R).


    :seealso: :class:`Item` :class:`Mux`
    """

    nin = 1  # type: ignore[assignment]
    nout = 1  # type: ignore[assignment]

    def __init__(self, keys: list[str], **blockargs: Any) -> None:
        """
        :param keys: list of dictionary keys
        :type keys: list
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """

        super().__init__(**blockargs)
        self.keys: list[str] = keys

    def output(self, t: float, inputs: list[Any], x: Any) -> Any:
        return {key: inputs[i] for i, key in enumerate(self.keys)}


# ------------------------------------------------------------------------ #
class Mux(FunctionBlock):
    r"""
    :blockname:`MUX`

    Multiplex signals.

    :inputs: N
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - i
            - float, ndarray
            - :math:`x_i`
        *   - Output
            - 0
            - ndarray
            - :math:`[x_0 \ldots x_{N-1}]`

    This block takes a number of scalar or 1D-array signals and concatenates
    them into a single 1-D array signal.  For example::

        mux = bd.MUX(2)

    :seealso: :class:`Demux` :class:`Dict`
    """

    # TODO could be generalized to creating a list of non numeric data

    nin: int = -1
    nout = 1  # type: ignore[assignment]

    def __init__(self, nin: int = 1, **blockargs: Any) -> None:
        """
        :param nin: Number of input ports, defaults to 1
        :type nin: int, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(nin=nin, **blockargs)

    def output(self, t: float, inputs: list[Any], x: Any) -> list[Any]:
        # TODO, handle inputs that are vectors themselves
        out = []
        for input in inputs:
            if isinstance(input, (int, float, bool)):
                out.append(input)
            elif isinstance(input, np.ndarray):
                out.extend(input.flatten().tolist())
        return [np.array(out)]


# ------------------------------------------------------------------------ #
class DeMux(FunctionBlock):
    """
    :blockname:`DEMUX`

    Demultiplex signals.

    :inputs: 1
    :outputs: N
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - 0
            - iterable
            - :math:`x`
        *   - Output
            - i
            - any
            - :math:`x_i`

    This block has a single input port and ``nout`` output ports.  The input signal is
    an iterable whose ``nout`` elements are routed element-wise to individual scalar
    output ports.  If the input is a 1D Numpy array, then each output port is an
    element of that array.

    :seealso: :class:`Mux`
    """

    nin = 1  # type: ignore[assignment]
    nout: int = -1

    def __init__(self, nout: int = 1, **blockargs: Any) -> None:
        """
        :param nout: number of outputs, defaults to 1
        :type nout: int, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(nout=nout, **blockargs)

    def output(self, t: float, inputs: list[Any], x: Any) -> list[Any]:
        input = inputs[0]
        # TODO, handle inputs that are vectors themselves
        assert (
            len(input) == self.nout
        ), "Input width not equal to number of output ports"
        return list(input)


# ------------------------------------------------------------------------ #


class Index(FunctionBlock):
    """
    :blockname:`INDEX`

    :inputs: 1
    :outputs: 1
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - i
            - iterable
            - :math:`x`
        *   - Output
            - j
            - iterable
            - :math:`x_i`

    The specified element(s) of the input iterable (list, string, etc.)
    are output.  The index can be an integer, sequence of integers, a Python slice
    object, or a string with Python slice notation, eg. ``"::-1"``.

    :seealso: :class:`Slice1` :class:`Slice2`
    """

    nin = 1  # type: ignore[assignment]
    nout = 1  # type: ignore[assignment]

    def __init__(
        self, index: list[int] | slice | str | None = None, **blockargs: Any
    ) -> None:
        """
        Index an iterable signal.

        :param index: elements of input array, defaults to []
        :type index: list, slice or str, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(**blockargs)

        if index is None:
            self.index: Any = []
        elif isinstance(index, str):
            args: list[int | None] = [
                None if a == "" else int(a) for a in index.split(":")
            ]
            self.index = slice(*args)
        else:
            self.index = index

    def output(self, t: float, inputs: list[Any], x: Any) -> list[Any]:
        input = inputs[0]
        if len(self.index) == 1:
            return [input[self.index[0]]]
        elif isinstance(input, np.ndarray):
            return [np.array([input[i] for i in self.index])]
        else:
            return [[input[i] for i in self.index]]


# ------------------------------------------------------------------------ #


class SubSystem(SubsystemBlock):
    """
    :blockname:`SUBSYSTEM`

    Instantiate a subsystem.

    :inputs: N
    :outputs: M
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - i
            - any
            - :math:`x_i`
        *   - Output
            - j
            - any
            - :math:`y_j`

    This block represents a subsystem in a block diagram.  The definition
    of the subsystem can be:

    - a path to a ``.bd`` JSON model file, which is loaded via :func:`~bdsim.bdload.bdload`, or
    - the name of a Python module which is imported and must create exactly
      one ``BlockDiagram`` instance, or
    - a ``BlockDiagram`` instance

    .. warning::

        **Module name mode** (non-``.bd`` string): importing a module executes
        all top-level Python code in that file. Only use this with modules you
        trust completely.

        **File mode** (``.bd`` path): loads a JSON file safely. ``eval()`` is
        only used for parameters starting with ``"="``; control this with
        ``allow_eval``.

    The referenced block diagram must contain either or both of:

    - one ``InPort`` block, which has outputs but no inputs. These
      outputs are connected to the inputs to the enclosing ``SubSystem`` block.
    - one ``OutPort`` block, which has inputs but no outputs. These
      inputs are connected to the outputs to the enclosing ``SubSystem`` block.

    .. note::

        - The referenced block diagram is treated like a macro and copied into
          the parent block diagram at compile time. The ``SubSystem``, ``InPort`` and
          ``OutPort`` blocks are eliminated, that is, all hierarchical structure is
          lost.
        - The same subsystem can be used multiple times, its blocks and wires
          will be cloned.  Subsystems can also include subsystems.
        - The number of input and output ports is not specified, they are computed
          from the number of ports on the ``InPort`` and ``OutPort`` blocks within the
          subsystem.
    """

    nin: int = -1
    nout: int = -1

    def __init__(
        self,
        subsys: str | BlockDiagram,
        nin: int = 1,
        nout: int = 1,
        allow_eval: bool | None = None,
        trace_eval: bool = False,
        globalvars: dict[str, Any] | None = None,
        **blockargs: Any,
    ) -> None:
        """
        :param subsys: Subsystem as a ``.bd`` filepath, module name, or ``BlockDiagram`` instance
        :type subsys: str or BlockDiagram
        :param nin: Number of input ports, defaults to 1
        :type nin: int, optional
        :param nout: Number of output ports, defaults to 1
        :type nout: int, optional
        :param allow_eval: (``.bd`` mode only) ``True`` enables eval silently,
            ``False`` refuses ``=...`` expressions, ``None`` (default) warns once.
        :type allow_eval: bool, optional
        :param trace_eval: (``.bd`` mode only) print each expression before evaluation.
        :type trace_eval: bool, optional
        :param globalvars: (``.bd`` mode only) extra names available when evaluating
            ``"=..."`` parameter expressions.
        :type globalvars: dict, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        :raises ImportError: module not found or no BlockDiagram in it
        :raises ValueError: invalid argument type or .bd load constraints not met
        """

        resolved_subsys: BlockDiagram

        name = None

        if isinstance(subsys, str):
            p = Path(subsys)
            if p.exists() and p.suffix == ".bd":
                # .bd file mode: safe JSON load via bdload

                if self._bd is None or self._bd.runtime is None:
                    raise ValueError(
                        "SubSystem: loading a .bd file requires the block to be part "
                        "of a BDSim-managed diagram (created via sim.blockdiagram())"
                    )
                new_subsystem = bdload(
                    self._bd,
                    str(p),
                    globalvars=globalvars,
                    allow_eval=allow_eval,
                    trace_eval=trace_eval,
                )
                name = p.stem
            else:
                # module import mode: executes the module — use only with trusted code

                try:
                    module: types.ModuleType = importlib.import_module(
                        subsys, package="."
                    )
                except SyntaxError as exc:
                    raise ImportError(
                        "-- syntax error in block definition: " + subsys
                    ) from exc
                except ModuleNotFoundError as exc:
                    raise ImportError("-- module not found " + subsys) from exc
                # get all bdsim.BlockDiagram instances
                diagrams: list[str] = [
                    name
                    for name, ref in module.__dict__.items()
                    if isinstance(ref, BlockDiagram)
                ]
                if len(diagrams) == 0:
                    raise ImportError(
                        "no bdsim.BlockDiagram instances in imported module"
                    )
                elif len(diagrams) > 1:
                    raise ImportError(
                        "multiple bdsim.BlockDiagram instances in imported module: "
                        + str(diagrams)
                    )
                new_subsystem = cast(BlockDiagram, module.__dict__[diagrams[0]])
                name = diagrams[0]
        elif isinstance(subsys, BlockDiagram):
            # use an in-memory diagram

            new_subsystem = copy.deepcopy(subsys) # make a snapshot copy to avoid later changes to the original affecting this block
            name = new_subsystem.name
        else:
            raise ValueError("argument must be filename or BlockDiagram instance")

        if "name" not in blockargs and name is not None:
            blockargs["name"] = name
        super().__init__(subsystem=new_subsystem, **blockargs)


# ------------------------------------------------------------------------ #


class InPort(FunctionBlock):
    """
    :blockname:`INPORT`

    Input ports for a subsystem.

    :inputs: 0
    :outputs: N
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Output
            - j
            - any
            - :math:`y_j`

    This block connects a subsystem to a parent block diagram.  Inputs to the
    parent-level ``SubSystem`` block appear as the outputs of this block.

    .. note:: Only one ``INPORT`` block can appear in a block diagram but it
        can have multiple ports.  This is different to Simulink(R) which
        would require multiple single-port input blocks.
    """

    nin = 0  # type: ignore[assignment]
    nout: int = -1

    def __init__(self, nout: int = 1, **blockargs: Any) -> None:
        """
        :param nout: Number of output ports, defaults to 1
        :type nout: int, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(nout=nout, **blockargs)

    def output(self, t: float, inputs: list[Any], x: Any) -> list[Any]:
        # signal feed through

        return inputs


# ------------------------------------------------------------------------ #


class OutPort(FunctionBlock):
    """
    :blockname:`OUTPORT`

    Output ports for a subsystem.

    :inputs: N
    :outputs: 0
    :states: 0

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - i
            - any
            - :math:`x_i`

    This block connects a subsystem to a parent block diagram.  The
    inputs of this block become the outputs of the parent-level ``SubSystem``
    block.

    .. note:: Only one ``OUTPORT`` block can appear in a block diagram but it
        can have multiple ports.  This is different to Simulink(R) which
        would require multiple single-port output blocks.
    """

    nin: int = -1
    nout = 0  # type: ignore[assignment]

    def __init__(self, nin: int = 1, **blockargs: Any) -> None:
        """
        :param nin: Number of input ports, defaults to 1
        :type nin: int, optional
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(nin=nin, **blockargs)

    def output(self, t: float, inputs: list[Any], x: Any) -> list[Any]:
        # signal feed through
        return inputs


if __name__ == "__main__":  # pragma: no cover
    from pathlib import Path
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[3]
    test_file = (
        root / "tests" / "blocks" / f"test_blocks_{Path(__file__).stem.lower()}.py"
    )

    if not test_file.exists():
        print(f"No module unit tests found for {Path(__file__).name}: {test_file}")
        raise SystemExit(0)

    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", str(test_file)]))
