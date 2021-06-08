#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example of using a subsystem.  The blocks are imported and wired into the top level diagram

@author: corkep
"""


import bdsim


bd = bdsim.BlockDiagram()

const = bd.CONSTANT(1)
scope = bd.SCOPE()

f = bd.SUBSYSTEM('subsys1', name='subsys')

bd.connect(const, f)
bd.connect(f, scope)

bd.compile()
bd.report()
