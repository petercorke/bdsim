#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun 14 15:11:30 2020

@author: corkep
"""

import bdsim

bd = bdsim.BlockDiagram()

f = bd.FUNCTION(lambda x: x)
inp = bd.INPORT(1)
outp = bd.OUTPORT(1)

bd.connect(inp, f)
bd.connect(f, outp)

# compiling is optional
#bd.compile()
