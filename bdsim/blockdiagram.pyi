from bdsim.blocks.sources import Constant, WaveForm, Piecewise, Step
from bdsim.blocks.sinks import Print, Stop
from bdsim.blocks.connections import Item, Mux, DeMux, SubSystem, InPort, OutPort
from bdsim.blocks.displays import Scope, ScopeXY, VehiclePlot, MultiRotorPlot
from bdsim.blocks.robots import Bicycle, Unicycle, DiffSteer, MultiRotor
from bdsim.blocks.transfers import Integrator, LTI_SS as LTI_SS_, LTI_SISO as LTI_SISO_
from bdsim.blocks.functions import Sum, Prod, Gain, Clip, Function, Interpolate
from __main__ import CustomBlock
from bdsim.components import *
from typing import Any, List, Optional
from typing_extensions import Literal as Literal

debuglist: Any

def DEBUG(debug: Any, *args: Any) -> None: ...
def printProgressBar(fraction: Any, prefix: str = ..., suffix: str = ..., decimals: int = ..., length: int = ..., fill: str = ..., printEnd: str = ...) -> None: ...
def blockname(cls): ...

class BlockDiagram:
    wirelist: Any = ...
    blocklist: Any = ...
    x: Any = ...
    compiled: bool = ...
    T: Any = ...
    t: Any = ...
    fignum: int = ...
    stop: Any = ...
    checkfinite: bool = ...
    blockcounter: Any = ...
    name: Any = ...
    def __init__(self, name: str=..., sysargs: bool=..., graphics: bool=..., animation: bool=..., progress: bool=..., debug: str=..., backend: str=..., tiles: str=...) -> None: ...
    def add_block(self, block: Any) -> None: ...
    def add_wire(self, wire: Any, name: Optional[Any] = ...): ...
    def ls(self) -> None: ...
    def connect(self, *args: Union[Block, Plug], name: Optional[str]=...) -> Any: ...
    nblocks: Any = ...
    nwires: Any = ...
    nstates: int = ...
    statenames: Any = ...
    blocknames: Any = ...
    def compile(self, subsystem: bool=..., doimport: bool=...) -> Any: ...
    count: int = ...
    def run(self, T: float=..., dt: float=..., solver: Literal[RK23, RK45, DOP853, Radau, BDF, LSODA]=..., block: bool=..., checkfinite: bool=..., watch: List[Union[str, Block, Plug]]=...) -> Any: ...
    def evaluate(self, x: ndarray, t: float) -> Any: ...
    def report(self) -> None: ...
    def getstate(self): ...
    def reset(self) -> None: ...
    def step(self) -> None: ...
    def start(self, **kwargs: Any) -> Any: ...
    def done(self, **kwargs: Any) -> Any: ...
    def savefig(self, format: str=..., **kwargs: Any) -> Any: ...
    def dotfile(self, file: str) -> Any: ...
    def blockvalues(self) -> None: ...
    def stubgen(self): ...

    def CUSTOMBLOCK(self, x: int) -> CustomBlock:
        pass

    def SUM(self, signs: Union[str, Sequence[Literal['+', '-']]], *inputs: Union[Block, Plug], angles: bool=..., **kwargs: Any) -> Sum:
        pass

    def PROD(self, ops: Sequence[Literal['*', '/']], *inputs: Union[Block, Plug], matrix: bool=..., **kwargs: Any) -> Prod:
        pass

    def GAIN(self, gain: Union[float, ndarray], *inputs: Union[Block, Plug], premul: bool=..., **kwargs: Any) -> Gain:
        pass

    def CLIP(self, *inputs: Any, min: Any = ..., max: Any = ..., **kwargs: Any) -> Clip:
        pass

    def FUNCTION(self, func: Union[Callable[..., Sequence[Any]], Sequence[Callable[..., Any]]], *inputs: Union[Block, Plug], nin: int=..., nout: int=..., dict: bool=..., args: Tuple[Any, ...]=..., kwargs: Dict[str, Any]=..., **kwargs_: Any) -> Function:
        pass

    def INTERPOLATE(self, *inputs: Union[Block, Plug], x: Optional[ArrayLike]=..., y: Optional[ArrayLike]=..., xy: Optional[ArrayLike]=..., time: bool=..., kind: Literal[linear, nearest, zero, slinear, quadratic, cubic, previous, next]=..., **kwargs: Any) -> Interpolate:
        pass

    def INTEGRATOR(self, *inputs: Union[Block, Plug], x0: ArrayLike=..., min: Optional[ArrayLike]=..., max: Optional[ArrayLike]=..., **kwargs: Any) -> Integrator:
        pass

    def LTI_SS(self, *inputs: Union[Block, Plug], A: ArrayLike, B: ArrayLike, C: ArrayLike, x0: Optional[ArrayLike]=..., verbose: bool=..., **kwargs: Any) -> LTI_SS_:
        pass

    def LTI_SISO(self, N: ArrayLike=..., D: ArrayLike=..., *inputs: Union[Block, Plug], x0: Optional[ArrayLike]=..., verbose: bool=..., **kwargs: Any) -> LTI_SISO_:
        pass

    def BICYCLE(self, *inputs: Union[Block, Plug], x0: Optional[ArrayLike]=..., L: float=..., vlim: float=..., slim: float=..., **kwargs: Any) -> Bicycle:
        pass

    def UNICYCLE(self, *inputs: Union[Block, Plug], x0: Optional[ArrayLike]=..., **kwargs: Any) -> Unicycle:
        pass

    def DIFFSTEER(self, *inputs: Union[Block, Plug], R: float=..., W: float=..., x0: Optional[ArrayLike]=..., **kwargs: Any) -> DiffSteer:
        pass

    def MULTIROTOR(self, model: MultiRotorModel, *inputs: Union[Block, Plug], groundcheck: bool=..., speedcheck: bool=..., x0: Optional[ArrayLike]=..., **kwargs: Any) -> MultiRotor:
        pass

    def SCOPE(self, nin: Opt[int]=..., styles: Opt[Union[StyleSpec, List[StyleSpec]]]=..., scale: ScaleSpec=..., labels: Opt[Sequence[str]]=..., grid: Union[bool, Tuple[Any]]=..., *inputs: Union[Block, Plug], **kwargs: Any) -> Scope:
        pass

    def SCOPEXY(self, style: Opt[StyleSpec]=..., *inputs: Any, scale: ScaleSpec=..., labels: List[str]=..., init: Opt[FigInitFn]=..., **kwargs: Any) -> ScopeXY:
        pass

    def VEHICLEPLOT(self, *inputs: Union[Block, Plug], path: bool=..., pathstyle: Opt[StyleSpec]=..., shape: Literal[triangle, box]=..., color: ColorLike=..., fill: ColorLike=..., size: float=..., scale: ScaleSpec=..., labels: List[str]=..., square: bool=..., init: Opt[FigInitFn]=..., **kwargs: Any) -> VehiclePlot:
        pass

    def MULTIROTORPLOT(self, model: MultiRotorModel, *inputs: Union[Block, Plug], scale: Tuple[float, float, float, float, float]=..., flapscale: float=..., projection: Literal[ortho, perspective]=..., **kwargs: Any) -> MultiRotorPlot:
        pass

    def ITEM(self, item: str, *inputs: Union[Block, Plug], **kwargs: Any) -> Item:
        pass

    def MUX(self, nin: int=..., *inputs: Union[Block, Plug], **kwargs: Any) -> Mux:
        pass

    def DEMUX(self, nout: int=..., *inputs: Union[Block, Plug], **kwargs: Any) -> DeMux:
        pass

    def SUBSYSTEM(self, subsys: Union[str, BlockDiagram], *inputs: Union[Block, Plug], **kwargs: Any) -> SubSystem:
        pass

    def INPORT(self, nout: int=..., **kwargs: Any) -> InPort:
        pass

    def OUTPORT(self, nin: int=..., *inputs: Union[Block, Plug], **kwargs: Any) -> OutPort:
        pass

    def PRINT(self, fmt: Optional[str]=..., *inputs: Union[Block, Plug], **kwargs: Any) -> Print:
        pass

    def STOP(self, stop: Union[bool, Callable[[Any], bool]], *inputs: Union[Block, Plug], **kwargs: Any) -> Stop:
        pass

    def CONSTANT(self, value: Any, **kwargs: Any) -> Constant:
        pass

    def WAVEFORM(self, wave: Literal[sine, square, triangle]=..., freq: float=..., unit: Literal['rad/s', Hz]=..., phase: float=..., amplitude: float=..., offset: float=..., min: float=..., max: float=..., duty: float=..., **kwargs: Any) -> WaveForm:
        pass

    def PIECEWISE(self, *seq: Sequence[Tuple[float, Any]], **kwargs: Any) -> Piecewise:
        pass

    def STEP(self, T: float=..., off: float=..., on: float=..., **kwargs: Any) -> Step:
        pass

