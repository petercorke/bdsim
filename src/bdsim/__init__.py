# from bdsim.bdsim import *
# from bdsim.blockdiagram import *
# from bdsim.components import *
# from bdsim.block_types import GraphicsBlock

from .run_sim import *
from .run_realtime import *
from .blockdiagram import *
from .components import *
from .block_types import GraphicsBlock
from .blockdiagram import bdload
from .bin.bdrun import bdrun

try:
    import importlib.metadata

    __version__ = importlib.metadata.version("bdsim")
except:
    pass
