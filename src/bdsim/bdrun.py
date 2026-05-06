# Backwards-compatibility shim.  bdrun has moved to bdsim.bin.bdrun.
# Importing from this module (e.g. ``from bdsim.bdrun import bdrun, bdload``)
# continues to work.
from bdsim.bin.bdrun import (  # noqa: F401
    bdload,
    bdrun,
)
