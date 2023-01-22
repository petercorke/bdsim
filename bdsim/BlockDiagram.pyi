import numpy as np
from bdsim.components import FunctionBlock
from typing import Callable, Union

ArrayLike = Union[np.ndarray, int, float, list, tuple]

class BlockDiagram:
    def SUM(self, signs: str = ..., mode: str = ..., **blockargs) -> None: ...
    def PROD(self, ops: str = ..., matrix: bool = ..., **blockargs) -> None: ...
    def GAIN(
        self, K: Union[int, float, np.ndarray] = ..., premul: bool = ..., **blockargs
    ) -> None: ...

# class Clip(FunctionBlock):
#     nin: int
#     nout: int
#     min: Incomplete
#     max: Incomplete
#     def __init__(self, min: ArrayLike = ..., max: ArrayLike = ..., **blockargs) -> None: ...
#     def output(self, t: Incomplete | None = ...): ...

# class Function(FunctionBlock):
#     nin: int
#     nout: int
#     func: Incomplete
#     userdata: Incomplete
#     args: Incomplete
#     kwargs: Incomplete
#     def __init__(self, func: Callable = ..., nin: int = ..., nout: int = ..., persistent: bool = ..., fargs: list = ..., fkwargs: dict = ..., **blockargs) -> None: ...
#     def start(self, state: Incomplete | None = ...) -> None: ...
#     def output(self, t: Incomplete | None = ...): ...

# class Interpolate(FunctionBlock):
#     nin: int
#     nout: int
#     time: Incomplete
#     blockclass: str
#     f: Incomplete
#     x: Incomplete
#     def __init__(self, x: Union[list, tuple, np.ndarray] = ..., y: Union[list, tuple, np.ndarray] = ..., xy: np.ndarray = ..., time: bool = ..., kind: str = ..., **blockargs) -> None: ...
#     def start(self, state, **blockargs) -> None: ...
#     def output(self, t: Incomplete | None = ...): ...
