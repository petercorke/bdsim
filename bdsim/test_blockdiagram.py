#!/usr/bin/env python3

import numpy as np
import scipy.interpolate
import math

import bdsim
import unittest
import numpy.testing as nt


class BlockTest(unittest.TestCase):
    pass

class BlockDiagramTest(unittest.TestCase):
    pass

class WiringTest(unittest.TestCase):

    def test_connect_1(self):

        bd = bdsim.BlockDiagram()

        src = bd.CONSTANT(2)
        dst = bd.OUTPORT(1)  # 1 port
        bd.connect(src, dst)
        bd.compile()
        bd.evaluate(x=[], t=0)
        self.assertEqual(dst.inputs[0], 2)

    def test_connect_2(self):

        bd = bdsim.BlockDiagram()

        src = bd.CONSTANT(2)
        dst1 = bd.OUTPORT(1)  # 1 port
        dst2 = bd.OUTPORT(1)  # 1 port
        bd.connect(src, dst1)
        bd.connect(src, dst2)
        bd.compile()
        bd.evaluate(x=[], t=0)
        self.assertEqual(dst1.inputs[0], 2)
        self.assertEqual(dst2.inputs[0], 2)

    def test_multi_connect(self):

        bd = bdsim.BlockDiagram()

        src = bd.CONSTANT(2)
        dst1 = bd.OUTPORT(1)  # 1 port
        dst2 = bd.OUTPORT(1)  # 1 port
        bd.connect(src, dst1, dst2)
        bd.compile()
        bd.evaluate(x=[], t=0)
        self.assertEqual(dst1.inputs[0], 2)
        self.assertEqual(dst2.inputs[0], 2)

    def test_ports1(self):

        bd = bdsim.BlockDiagram()

        const1 = bd.CONSTANT(2)
        const2 = bd.CONSTANT(3)

        dst = bd.OUTPORT(2)  # 2 ports
        bd.connect(const1, dst[0])
        bd.connect(const2, dst[1])
        bd.compile()
        bd.evaluate(x=[], t=0)
        self.assertEqual(dst.inputs, [2, 3])

    def test_ports2(self):

        bd = bdsim.BlockDiagram()

        const = bd.CONSTANT([2, 3])
        src = bd.DEMUX(2)
        bd.connect(const, src)

        dst1 = bd.OUTPORT(1)  # 1 port
        dst2 = bd.OUTPORT(1)  # 1 port

        bd.connect(src[0], dst1)
        bd.connect(src[1], dst2)
        bd.compile()
        bd.evaluate(x=[], t=0)
        self.assertEqual(dst.inputs, [2, 3, 4, 5])

    def test_ports2(self):

        bd = bdsim.BlockDiagram()

        const = bd.CONSTANT([2, 3, 4, 5])
        src = bd.DEMUX(4)
        bd.connect(const, src)

        dst = bd.OUTPORT(4)  # 4 ports
        bd.connect(src[0], dst[0])
        bd.connect(src[1], dst[1])
        bd.connect(src[2], dst[2])
        bd.connect(src[3], dst[3])
        bd.compile()
        bd.evaluate(x=[], t=0)
        self.assertEqual(dst.inputs, [2, 3, 4, 5])

    def test_slice1(self):

        bd = bdsim.BlockDiagram()

        src = bd.CONSTANT(2)
        dst = bd.OUTPORT(2)  # 1 port
        bd.connect(src, dst[0])
        bd.connect(src, dst[1])
        bd.compile()
        bd.evaluate(x=[], t=0)
        self.assertEqual(dst.inputs, [2, 2])

    def test_slice2(self):

        bd = bdsim.BlockDiagram()

        const = bd.CONSTANT([2, 3, 4, 5])
        src = bd.DEMUX(4)
        bd.connect(const, src)

        dst = bd.OUTPORT(4)  # 4 ports
        bd.connect(src[0:4], dst[0:4])
        bd.compile()
        bd.evaluate(x=[], t=0)
        self.assertEqual(dst.inputs, [2, 3, 4, 5])

    def test_slice3(self):

        bd = bdsim.BlockDiagram()

        const = bd.CONSTANT([2, 3, 4, 5])
        src = bd.DEMUX(4)
        bd.connect(const, src)

        dst = bd.OUTPORT(4)  # 4 ports
        bd.connect(src[0:4], dst[3:-1:-1])
        bd.compile()
        bd.evaluate(x=[], t=0)
        self.assertEqual(dst.inputs, [5, 4, 3, 2])

    def test_slice4(self):

        bd = bdsim.BlockDiagram()

        const = bd.CONSTANT([2, 3, 4, 5])
        src = bd.DEMUX(4)
        bd.connect(const, src)

        dst = bd.OUTPORT(4)  # 4 ports
        bd.connect(src[3:-1:-1], dst[0:4])
        bd.compile()
        bd.evaluate(x=[], t=0)
        self.assertEqual(dst.inputs, [5, 4, 3, 2])

    def test_slice5(self):

        bd = bdsim.BlockDiagram()

        const = bd.CONSTANT([2, 3, 4, 5])
        src = bd.DEMUX(4)
        bd.connect(const, src)

        dst = bd.OUTPORT(4)  # 4 ports
        bd.connect(src[0:4:2], dst[0:4:2])
        bd.connect(src[1:4:2], dst[1:4:2])
        bd.compile()
        bd.evaluate(x=[], t=0)
        self.assertEqual(dst.inputs, [2, 4, 3, 5])

    def test_slice5(self):

        bd = bdsim.BlockDiagram()

        const = bd.CONSTANT([2, 3, 4, 5])
        src = bd.DEMUX(4)
        bd.connect(const, src)

        dst = bd.OUTPORT(4)  # 4 ports
        bd.connect(src[3:-1:-1], dst[3:-1:-1])
        bd.compile()
        bd.evaluate(x=[], t=0)
        self.assertEqual(dst.inputs, [2, 3, 4, 5])

        
    def test_assignment11(self):

        bd = bdsim.BlockDiagram()

        src = bd.CONSTANT(2)
        dst = bd.OUTPORT(1)  # 1 port
        
        dst[0] = src

        bd.compile()
        bd.evaluate(x=[], t=0)
        self.assertEqual(dst.inputs[0], 2)

    def test_assignment2(self):
        
        bd = bdsim.BlockDiagram()

        const1 = bd.CONSTANT(2)
        const2 = bd.CONSTANT(3)

        dst = bd.OUTPORT(2)  # 2 ports

        dst[0] = const1
        dst[1] = const2

        bd.compile()
        bd.evaluate(x=[], t=0)
        self.assertEqual(dst.inputs, [2, 3])


    def test_assignment3(self):
        bd = bdsim.BlockDiagram()

        const = bd.CONSTANT([2, 3, 4, 5])
        src = bd.DEMUX(4)
        bd.connect(const, src)

        dst = bd.OUTPORT(4)  # 4 ports

        dst[3:-1:-1] = src[0:4]

        bd.compile()
        bd.evaluate(x=[], t=0)
        self.assertEqual(dst.inputs, [5, 4, 3, 2])

    def test_multiply1(self):
        bd = bdsim.BlockDiagram()

        dst = bd.OUTPORT(1)  # 1 ports

        dst[0] = bd.CONSTANT(2) * bd.GAIN(3)

        bd.compile()
        bd.evaluate(x=[], t=0)
        self.assertEqual(dst.inputs, [6])

    def test_multiply2(self):
        bd = bdsim.BlockDiagram()

        dst = bd.OUTPORT(1)  # 1 ports

        dst[0] = bd.CONSTANT(2) * bd.GAIN(3) * bd.GAIN(4)

        bd.compile()
        bd.evaluate(x=[], t=0)
        self.assertEqual(dst.inputs, [24])

    def test_multiply3(self):
        bd = bdsim.BlockDiagram()

        const = bd.CONSTANT([2, 3])
        src = bd.DEMUX(2)
        bd.connect(const, src)

        dst = bd.OUTPORT(2)  # 2 ports

        dst[0] = src[0] * bd.GAIN(2)
        dst[1] = src[1] * bd.GAIN(3)

        bd.compile()
        bd.evaluate(x=[], t=0)
        self.assertEqual(dst.inputs, [4, 9])

    def test_inline1(self):
        bd = bdsim.BlockDiagram()

        dst = bd.OUTPORT(1)  # 1 ports
        const1 = bd.CONSTANT(2)
        const2 = bd.CONSTANT(3)

        dst[0] = bd.SUM('++', const1, const2)

        bd.compile()
        bd.evaluate(x=[], t=0)
        self.assertEqual(dst.inputs, [5])

    def test_inline2(self):
        bd = bdsim.BlockDiagram()

        dst = bd.OUTPORT(1)  # 1 ports
        const1 = bd.CONSTANT(2)
        const2 = bd.CONSTANT(3)

        dst[0] = bd.SUM('++', const1, const2) * bd.GAIN(2)

        bd.compile()
        bd.evaluate(x=[], t=0)
        self.assertEqual(dst.inputs, [10])

class ImportTest(unittest.TestCase):
    
    def test_import1(self):
        # create a subsystem
        ss = bdsim.BlockDiagram(name='subsystem1')
    
        f = ss.FUNCTION(lambda x: x)
        inp = ss.INPORT(1)
        outp = ss.OUTPORT(1)
        
        ss.connect(inp, f)
        ss.connect(f, outp)
    
        # create main system
        bd = bdsim.BlockDiagram()
    
        const = bd.CONSTANT(1)
        scope = bd.SCOPE()
        
        f = bd.SUBSYSTEM(ss, name='subsys')
        
        bd.connect(const, f)
        bd.connect(f, scope)
        
        bd.compile()
        
        self.assertEqual(len(bd.blocklist), 3)
        self.assertEqual(len(bd.wirelist), 2)

    def test_import2(self):
        # create a subsystem
        ss = bdsim.BlockDiagram(name='subsystem1')
    
        f = ss.FUNCTION(lambda x: x)
        inp = ss.INPORT(1)
        outp = ss.OUTPORT(1)
        
        ss.connect(inp, f)
        ss.connect(f, outp)
    
        # create main system
        bd = bdsim.BlockDiagram()
    
        const = bd.CONSTANT(1)
        scope1 = bd.SCOPE()
        scope2 = bd.SCOPE()
        
        f1 = bd.SUBSYSTEM(ss, name='subsys1')
        f2 = bd.SUBSYSTEM(ss, name='subsys2')
        
        bd.connect(const, f1, f2)
        bd.connect(f1, scope1)
        bd.connect(f2, scope2)
        
        bd.compile()
        

# ---------------------------------------------------------------------------------------#
if __name__ == '__main__':

    unittest.main()
    
