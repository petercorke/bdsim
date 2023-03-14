#!/usr/bin/env python3

import bdsim
import inspect

sim = bdsim.BDSim()
filename = "blockdiagram.pyi"

with open(filename, "w") as f:
    print("writing stubs --> ", filename)
    print("""from spatialmath.base.types import *
import numpy as np
import math

class BlockDiagram:""", file=f)

    for block, info in sim._blocklibrary.items():
        meth = info["class"]
        sig = inspect.signature(meth.__init__)

        print("\n", file=f)
        print(f"    # {info['module']}.{info['classname']}", file=f)
        print(f"    def {block}{str(sig)}:", file=f)
        print('        """', end="", file=f)
        print(meth.__init__.__doc__, end="", file=f)
        print('\n        """\n        ...', file=f)

