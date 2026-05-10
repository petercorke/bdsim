"""Connection primitives used to wire blocks together."""

from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING, TypeVar

import numpy as np

if TYPE_CHECKING:
    from typing import Self
    from bdsim.block import Block

_F = TypeVar("_F", bound=Callable[..., Any])


# decorator for debugging implicit block creation with operator overloading
# kept local to avoid an import cycle with components.py
def oodebug(func: _F) -> _F:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        ret = func(*args, **kwargs)
        # print(f"{func.__qualname__}{args} --> {ret}")
        return ret

    return wrapper  # type: ignore[return-value]


class Wire:
    """
    Create a wire.

    :param start: Plug at the start of a wire
    :type start: Plug
    :param end: Plug at the end of a wire
    :type end: Plug
    :param name: Name of wire, defaults to None
    :type name: str, optional
    :return: A wire object
    :rtype: Wire

    A Wire object connects two block ports.  A Wire has a reference to the
    start and end ports.

    A wire records all the connections defined by the user.  At compile time
    wires are used to build inter-block references.

    Between two blocks, a wire can connect one or more ports, ie. it can connect
    a set of output ports on one block to a same sized set of input ports on
    another block.
    """

    def __init__(self, start: Plug, end: Plug, name: str | None = None) -> None:
        self.name = name
        self.id = None
        self.start = start
        self.end = end
        self.type = None
        self.name = None

    @property
    def value(self) -> Any:
        if self._slot is not None:
            return self._slot.value
        return self._value

    @value.setter
    def value(self, v: Any) -> None:
        if self._slot is not None:
            self._slot.value = v
        else:
            self._value = v

    def bind_slot(self, slot: Any) -> None:
        self._slot = slot
        self._value = None

    @property
    def info(self) -> None:
        """
        Interactive display of wire properties.

        Displays all attributes of the wire for debugging purposes.
        """
        print("wire:")
        for k, v in self.__dict__.items():
            print("  {:8s}{:s}".format(k + ":", str(v)))

    def __repr__(self) -> str:
        """
        Display wire with name and connection details.

        :return: Long-form wire description
        :rtype: str

        String format::

            wire.5: d2goal[0] --> Kv[0]
        """
        return str(self) + ": " + self.fullname

    @property
    def fullname(self) -> str:
        """
        Display wire connection details.

        :return: Wire name
        :rtype: str

        String format::

            d2goal[0] --> Kv[0]
        """
        return "{}[{}] --> {}[{}]".format(
            self.start.block.name,
            self.start.port,
            self.end.block.name,
            self.end.port,
        )

    def __str__(self) -> str:
        """
        Display wire name.

        :return: Wire name
        :rtype: str

        String format::

            wire.5
        """
        s = "wire."
        if self.name is not None:
            s += self.name
        elif self.id is not None:
            s += str(self.id)
        else:
            s += "??"
        return s


class Port:
    """
    A common base class for blocks and plugs, to allow operator overloading for
    implicit block creation.
    """

    pass


class Plug(Port):
    """
    Create a plug.

    :param block: The block being plugged into
    :type block: Block
    :param port: The port on the block, defaults to 0
    :type port: int, optional
    :param type: 'start' or 'end', defaults to None
    :type type: str, optional
    :return: Plug object
    :rtype: Plug

    Plugs are the interface between a wire and block and have information
    about port number and wire end. Plugs are on the end of each wire, and connect a
    Wire to a specific port on a Block.

    The ``type`` argument indicates if the ``Plug`` is at:
        - the start of a wire, ie. the port is an output port
        - the end of a wire, ie. the port is an input port

    A plug can specify a set of ports on a block.
    """

    __array_ufunc__ = None  # allow block operators with NumPy values

    def __init__(self, block: Block, port: int | slice = 0, type: str | None = None) -> None:
        self.block: Block = block
        self.port: int | slice = port
        self.type: str = type or ""

    def __str__(self) -> str:
        return str(self.block) + "[" + str(self.port) + "]"

    def __repr__(self) -> str:
        return "Plug/" + self.type + ":" + str(self)

    @property
    def isslice(self) -> bool:
        return isinstance(self.port, slice)

    @property
    def portlist(self) -> list[int] | range:
        if isinstance(self.port, int):
            return [self.port]
        if isinstance(self.port, slice):
            start: int = self.port.start or 0
            step: int = self.port.step or 1
            stop: int
            if self.port.stop is None:
                if self.type == "start":
                    stop = self.block.nout
                else:
                    stop = self.block.nin
            else:
                stop = self.port.stop
            return range(start, stop, step)
        raise ValueError("bad plug index")

    def __getitem__(self, i: int) -> Self:
        return self.__class__(self.block, self.portlist[i])

    @property
    def width(self) -> int:
        return len(self.portlist)

    @oodebug
    def __rshift__(left: Plug, right: Plug | Block) -> Plug | Block:
        s = left.block.bd
        assert (
            s is not None
        ), "left operand of >> operator must be a plug connected to a block diagram"
        s.connect(left, right)
        return right

    @oodebug
    def __add__(self, other: Block | Plug | int | float | np.ndarray) -> Block:
        from bdsim.blocks import Constant, Sum

        if isinstance(other, (int, float, np.ndarray)):
            other = Constant(other, bd=self.block.bd)
        return Sum("++", inputs=(self, other), bd=self.block.bd)

    @oodebug
    def __radd__(self, other: Block | Plug | int | float | np.ndarray) -> Block:
        from bdsim.blocks import Constant, Sum

        if isinstance(other, (int, float, np.ndarray)):
            other = Constant(other, bd=self.block.bd)
        return Sum("++", inputs=(other, self), bd=self.block.bd)

    @oodebug
    def __sub__(self, other: Block | Plug | int | float | np.ndarray) -> Block:
        from bdsim.blocks import Constant, Sum

        if isinstance(other, (int, float, np.ndarray)):
            other = Constant(other, bd=self.block.bd)
        return Sum("+-", inputs=(self, other), bd=self.block.bd)

    @oodebug
    def __rsub__(self, other: Block | Plug | int | float | np.ndarray) -> Block:
        from bdsim.blocks import Constant, Sum

        if isinstance(other, (int, float, np.ndarray)):
            other = Constant(other, bd=self.block.bd)
        return Sum("+-", inputs=(other, self), bd=self.block.bd)

    @oodebug
    def __neg__(self) -> Block:
        from bdsim.blocks import Gain

        return Gain(-1, inputs=[self], bd=self.block.bd)

    @oodebug
    def __pow__(self, p: int | float) -> Block:
        from bdsim.blocks import Pow

        return Pow(p, inputs=[self], bd=self.block.bd)

    @oodebug
    def __mul__(self, other: Block | Plug | int | float | np.ndarray) -> Block:
        from bdsim.block import Block
        from bdsim.blocks import Prod

        if isinstance(other, (int, float, np.ndarray)):
            return self.block._autogain(other, inputs=[self])
        if isinstance(other, Block):
            bd = other.bd
        elif isinstance(other, Plug):
            bd = self.block.bd
        else:
            raise ValueError("unsupported operand type for *: " + str(type(other)))

        assert (
            bd is not None
        ), "left operand of * operator must be a plug connected to a block diagram"
        name = "_prod.{:d}".format(next(bd.n_auto_prod))
        return Prod("**", matrix=True, name=name, inputs=[self, other], bd=bd)

    @oodebug
    def __rmul__(self, other: Block | Plug | int | float | np.ndarray) -> Block | Any:
        if isinstance(other, (int, float, np.ndarray)):
            matrix: bool = isinstance(other, np.ndarray)
            return self.block._autogain(other, premul=matrix, inputs=[self])
        return NotImplemented

    @oodebug
    def __truediv__(self, other: Block | Plug | int | float | np.ndarray) -> Block:
        from bdsim.blocks import Constant, Prod

        if isinstance(other, (int, float, np.ndarray)):
            other = Constant(other, bd=self.block.bd)
        return Prod("*/", inputs=(self, other), bd=self.block.bd)

    @oodebug
    def __rtruediv__(self, other: Block | Plug | int | float | np.ndarray) -> Block:
        from bdsim.blocks import Constant, Prod

        if isinstance(other, (int, float, np.ndarray)):
            other = Constant(other, bd=self.block.bd)
        return Prod("*/", inputs=(other, self), bd=self.block.bd)


class StartPlug(Plug):
    def __init__(self, block: Block, port: int | slice = 0) -> None:
        super().__init__(block, port, type="start")


class EndPlug(Plug):
    def __init__(self, block: Block, port: int | slice = 0) -> None:
        super().__init__(block, port, type="end")


if __name__ == "__main__":
    try:
        from ._selftest import run_module_test
    except ImportError:
        from bdsim._selftest import run_module_test

    raise SystemExit(run_module_test(__file__))
