import inspect

import pytest

from bdsim.block import Block
from bdsim.connect import Plug


@pytest.mark.parametrize("cls", [Block, Plug])
@pytest.mark.parametrize(
    "name",
    [
        "__add__",
        "__radd__",
        "__sub__",
        "__rsub__",
        "__mul__",
        "__rmul__",
        "__truediv__",
        "__rtruediv__",
        "__pow__",
        "__neg__",
        "__rshift__",
    ],
)
def test_operator_metadata(cls: type[Block] | type[Plug], name: str) -> None:
    method = getattr(cls, name)
    original = method.__wrapped__

    assert original is not method
    assert inspect.unwrap(method) is original
    assert inspect.signature(method) == inspect.signature(original)
    assert method.__doc__ == original.__doc__
    assert method.__name__ == original.__name__ == name
    assert method.__qualname__ == original.__qualname__ == f"{cls.__name__}.{name}"
    assert method.__module__ == original.__module__ == cls.__module__
    assert method.__annotations__ == original.__annotations__
