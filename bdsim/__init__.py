# from bdsim.bdsim import *
# from bdsim.blockdiagram import *
# from bdsim.components import *
# from bdsim.graphics import GraphicsBlock
# from bdsim.bdrun import bdrun, bdload

from .run_sim import *
from .run_realtime import *
from .blockdiagram import *
from .components import *
from .graphics import GraphicsBlock
from .bdrun import bdrun, bdload

try:
    import importlib.metadata

    __version__ = importlib.metadata.version("bdsim")
except:
    pass
