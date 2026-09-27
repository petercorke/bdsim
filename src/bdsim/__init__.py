# from bdsim.bdsim import *
# from bdsim.blockdiagram import *
# from bdsim.components import *
# from bdsim.block_types import GraphicsBlock

# Deliberate flat re-export of the public API (bdsim.BDSim, bdsim.BlockDiagram,
# ...); nothing here consumes these names, so noqa rather than enumerate them.
from .run_sim import *  # noqa: F401,F403

# from .run_realtime import *
from .blockdiagram import *  # noqa: F401,F403
from .components import *  # noqa: F401,F403
from .block_types import GraphicsBlock  # noqa: F401
from .blockdiagram import bdload  # noqa: F401
from .bin.bdrun import bdrun  # noqa: F401

try:
    import importlib.metadata

    __version__ = importlib.metadata.version("bdsim")
except:
    pass
