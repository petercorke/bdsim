#!/usr/bin/env python3

from typing import List
from numpy.lib.arraysetops import isin
import bdsim
# from bdsim.blocks.functions import Sum
import numpy as np
import scipy.interpolate
import math

import unittest
import numpy.testing as nt


class BlockTest(unittest.TestCase):
    pass

sim = bdsim.BDSim()

class TestSignalOperators(unittest.TestCase):

    def assertEqual(self, a, b):
        if isinstance(a, np.ndarray):
            self.assertTrue((a == b).all())
        else:
            unittest.TestCase.assertEqual(self, a, b)
    
    def _test_op(self, bd, x, *operands, expected, block_type, default_op, ops_attr_name, ops=None, operand_types=None):
        n = len(operands)

        if not ops:
            ops = default_op * n

        if not operand_types:
            operand_types = ['constant'] * n

        self.assertIs(x.type, block_type)
        self.assertEqual(x.nin, len(ops))
        self.assertEqual(getattr(x, ops_attr_name), ops)
        
        is_compiled = bd.compile()
        self.assertTrue(is_compiled)

        for i, (operand, blocktype) in enumerate(zip(operands, operand_types)):
            block = x.inports[i].start.block
            self.assertEqual(block.type, blocktype)
            
            if blocktype == 'constant':
                self.assertEqual(block.value, operand)

        [out] = x.output()
        self.assertEqual(out, expected)

    

    def _test_add(self, bd, x, *operands, signs=None, operand_types=None):
        self._test_op(bd, x, *operands,
            expected = sum(operands),
            block_type = 'sum',
            default_op = '+',
            ops_attr_name = 'signs',
            ops = signs,
            operand_types = operand_types)
    

    def _test_mul(self, bd, x, *operands, ops=None, operand_types=None):
        expected = 1
        for operand in operands:
            expected *= operand

        self._test_op(bd, x, *operands,
            expected = expected,
            block_type = 'prod',
            default_op = '*',
            ops_attr_name = 'ops',
            ops = ops,
            operand_types = operand_types)

    def test_add_constblock_and_constblock(self):
        a = np.random.rand(1, 1)
        b = np.random.rand(1, 1)
        bd = sim.blockdiagram()
        x = bd.CONSTANT(a) + bd.CONSTANT(b)
        self._test_add(bd, x, a, b)


    def test_add_constblock_and_num(self):
        a = np.random.rand(1, 1)
        b = np.random.rand(1, 1)
        bd = sim.blockdiagram()
        x = bd.CONSTANT(a) + b
        self._test_add(bd, x, a, b)


    def test_add_num_and_constblock(self):
        a = np.random.rand(1, 1)
        b = np.random.rand(1, 1)
        bd = sim.blockdiagram()
        x = a + bd.CONSTANT(b)
        self._test_add(bd, x, a, b)

    def test_add_nested(self):
        a = np.random.rand(1, 1)
        b = np.random.rand(1, 1)
        c = np.random.rand(1, 1)
        bd = sim.blockdiagram()
        x = (a + bd.CONSTANT(b)) + c
        self._test_add(bd, x, a, b, c)

    def test_add_ndarrays(self):
        a = np.random.rand(5, 5, 5)
        b = np.random.rand(5, 5, 5)
        c = np.random.rand(5, 5, 5)
        bd = sim.blockdiagram()
        x = a + (bd.CONSTANT(b) + c)
        self._test_add(bd, x, a, b, c)
    
    def test_add_multioutputblocks_fail(self):
        a = np.random.rand(1, 1)
        b = np.random.rand(1, 1)
        bd = sim.blockdiagram()

        inp = bd.CONSTANT(a)
        doubleup = bd.FUNCTION(lambda z: [z, z], inp, nout=2)

        with self.assertRaises(AssertionError) as cm:
            doubleup + b
        self.assertIn("Attempted to use a Signal.__operator__ with a Block with multiple outputs (must have just 1)", str(cm.exception))

    def test_mul_constblock_and_constblock(self):
        a = np.random.rand(1, 1)
        b = np.random.rand(1, 1)
        bd = sim.blockdiagram()
        x = bd.CONSTANT(a) * bd.CONSTANT(b)
        self._test_mul(bd, x, a, b)
    
    def test_mul_constblock_and_num(self):
        a = np.random.rand(1, 1)
        b = np.random.rand(1, 1)
        bd = sim.blockdiagram()
        x = bd.CONSTANT(a) * b
        self._test_mul(bd, x, a, b)


    def test_mul_num_and_constblock(self):
        a = np.random.rand(1, 1)
        b = np.random.rand(1, 1)
        bd = sim.blockdiagram()
        x = a * bd.CONSTANT(b)
        self._test_mul(bd, x, a, b)

    def test_mul_nested(self):
        a = np.random.rand(1, 1)
        b = np.random.rand(1, 1)
        c = np.random.rand(1, 1)
        bd = sim.blockdiagram()
        x = (a * bd.CONSTANT(b)) * c
        self._test_mul(bd, x, a, b, c)

    def test_mul_ndarrays(self):
        a = np.random.rand(5, 5, 5)
        b = np.random.rand(5, 5, 5)
        c = np.random.rand(5, 5, 5)
        bd = sim.blockdiagram()
        x = a * (bd.CONSTANT(b) * c)
        self._test_mul(bd, x, a, b, c)
    
    def test_mul_multioutputblocks_fail(self):
        a = np.random.rand(1, 1)
        b = np.random.rand(1, 1)
        bd = sim.blockdiagram()

        inp = bd.CONSTANT(a)
        doubleup = bd.FUNCTION(lambda z: [z, z], inp, nout=2)

        with self.assertRaises(AssertionError) as cm:
            doubleup + b
        self.assertIn("Attempted to use a Signal.__operator__ with a Block with multiple outputs (must have just 1)", str(cm.exception))





class BlockDiagramTest(unittest.TestCase):
    pass

# class WiringTest(unittest.TestCase):

#     def test_connect_1(self):

#         bd = bdsim.BlockDiagram()

#         src = bd.CONSTANT(2)
#         dst = bd.OUTPORT(1)  # 1 port
#         bd.connect(src, dst)
#         bd.compile()
#         bd.evaluate(x=[], t=0)
#         self.assertEqual(dst.inputs[0], 2)

#     def test_connect_2(self):

#         bd = bdsim.BlockDiagram()

#         src = bd.CONSTANT(2)
#         dst1 = bd.OUTPORT(1)  # 1 port
#         dst2 = bd.OUTPORT(1)  # 1 port
#         bd.connect(src, dst1)
#         bd.connect(src, dst2)
#         bd.compile()
#         bd.evaluate(x=[], t=0)
#         self.assertEqual(dst1.inputs[0], 2)
#         self.assertEqual(dst2.inputs[0], 2)

#     def test_multi_connect(self):

#         bd = bdsim.BlockDiagram()

#         src = bd.CONSTANT(2)
#         dst1 = bd.OUTPORT(1)  # 1 port
#         dst2 = bd.OUTPORT(1)  # 1 port
#         bd.connect(src, dst1, dst2)
#         bd.compile()
#         bd.evaluate(x=[], t=0)
#         self.assertEqual(dst1.inputs[0], 2)
#         self.assertEqual(dst2.inputs[0], 2)

#     def test_ports1(self):

#         bd = bdsim.BlockDiagram()

#         const1 = bd.CONSTANT(2)
#         const2 = bd.CONSTANT(3)

#         dst = bd.OUTPORT(2)  # 2 ports
#         bd.connect(const1, dst[0])
#         bd.connect(const2, dst[1])
#         bd.compile()
#         bd.evaluate(x=[], t=0)
#         self.assertEqual(dst.inputs, [2, 3])

#     def test_ports2(self):

#         bd = bdsim.BlockDiagram()

#         const = bd.CONSTANT([2, 3])
#         src = bd.DEMUX(2)
#         bd.connect(const, src)

#         dst1 = bd.OUTPORT(1)  # 1 port
#         dst2 = bd.OUTPORT(1)  # 1 port

#         bd.connect(src[0], dst1)
#         bd.connect(src[1], dst2)
#         bd.compile()
#         bd.evaluate(x=[], t=0)
#         self.assertEqual(dst.inputs, [2, 3, 4, 5])

#     def test_ports3(self):

#         bd = bdsim.BlockDiagram()

#         const = bd.CONSTANT([2, 3, 4, 5])
#         src = bd.DEMUX(4)
#         bd.connect(const, src)

#         dst = bd.OUTPORT(4)  # 4 ports
#         bd.connect(src[0], dst[0])
#         bd.connect(src[1], dst[1])
#         bd.connect(src[2], dst[2])
#         bd.connect(src[3], dst[3])
#         bd.compile()
#         bd.evaluate(x=[], t=0)
#         self.assertEqual(dst.inputs, [2, 3, 4, 5])

#     def test_slice1(self):

#         bd = bdsim.BlockDiagram()

#         src = bd.CONSTANT(2)
#         dst = bd.OUTPORT(2)  # 1 port
#         bd.connect(src, dst[0])
#         bd.connect(src, dst[1])
#         bd.compile()
#         bd.evaluate(x=[], t=0)
#         self.assertEqual(dst.inputs, [2, 2])

#     def test_slice2(self):

#         bd = bdsim.BlockDiagram()

#         const = bd.CONSTANT([2, 3, 4, 5])
#         src = bd.DEMUX(4)
#         bd.connect(const, src)

#         dst = bd.OUTPORT(4)  # 4 ports
#         bd.connect(src[0:4], dst[0:4])
#         bd.compile()
#         bd.evaluate(x=[], t=0)
#         self.assertEqual(dst.inputs, [2, 3, 4, 5])

#     def test_slice3(self):

#         bd = bdsim.BlockDiagram()

#         const = bd.CONSTANT([2, 3, 4, 5])
#         src = bd.DEMUX(4)
#         bd.connect(const, src)

#         dst = bd.OUTPORT(4)  # 4 ports
#         bd.connect(src[0:4], dst[3:-1:-1])
#         bd.compile()
#         bd.evaluate(x=[], t=0)
#         self.assertEqual(dst.inputs, [5, 4, 3, 2])

#     def test_slice4(self):

#         bd = bdsim.BlockDiagram()

#         const = bd.CONSTANT([2, 3, 4, 5])
#         src = bd.DEMUX(4)
#         bd.connect(const, src)

#         dst = bd.OUTPORT(4)  # 4 ports
#         bd.connect(src[3:-1:-1], dst[0:4])
#         bd.compile()
#         bd.evaluate(x=[], t=0)
#         self.assertEqual(dst.inputs, [5, 4, 3, 2])

#     def test_slice5(self):

#         bd = bdsim.BlockDiagram()

#         const = bd.CONSTANT([2, 3, 4, 5])
#         src = bd.DEMUX(4)
#         bd.connect(const, src)

#         dst = bd.OUTPORT(4)  # 4 ports
#         bd.connect(src[0:4:2], dst[0:4:2])
#         bd.connect(src[1:4:2], dst[1:4:2])
#         bd.compile()
#         bd.evaluate(x=[], t=0)
#         self.assertEqual(dst.inputs, [2, 4, 3, 5])

#     def test_slice6(self):

#         bd = bdsim.BlockDiagram()

#         const = bd.CONSTANT([2, 3, 4, 5])
#         src = bd.DEMUX(4)
#         bd.connect(const, src)

#         dst = bd.OUTPORT(4)  # 4 ports
#         bd.connect(src[3:-1:-1], dst[3:-1:-1])
#         bd.compile()
#         bd.evaluate(x=[], t=0)
#         self.assertEqual(dst.inputs, [2, 3, 4, 5])

        
#     def test_assignment11(self):

#         bd = bdsim.BlockDiagram()

#         src = bd.CONSTANT(2)
#         dst = bd.OUTPORT(1)  # 1 port
        
#         dst[0] = src

#         bd.compile()
#         bd.evaluate(x=[], t=0)
#         self.assertEqual(dst.inputs[0], 2)

#     def test_assignment2(self):
        
#         bd = bdsim.BlockDiagram()

#         const1 = bd.CONSTANT(2)
#         const2 = bd.CONSTANT(3)

#         dst = bd.OUTPORT(2)  # 2 ports

#         dst[0] = const1
#         dst[1] = const2

#         bd.compile()
#         bd.evaluate(x=[], t=0)
#         self.assertEqual(dst.inputs, [2, 3])


#     def test_assignment3(self):
#         bd = bdsim.BlockDiagram()

#         const = bd.CONSTANT([2, 3, 4, 5])
#         src = bd.DEMUX(4)
#         bd.connect(const, src)

#         dst = bd.OUTPORT(4)  # 4 ports

#         dst[3:-1:-1] = src[0:4]

#         bd.compile()
#         bd.evaluate(x=[], t=0)
#         self.assertEqual(dst.inputs, [5, 4, 3, 2])

#     def test_multiply1(self):
#         bd = bdsim.BlockDiagram()

#         dst = bd.OUTPORT(1)  # 1 ports

#         dst[0] = bd.CONSTANT(2) * bd.GAIN(3)

#         bd.compile()
#         bd.evaluate(x=[], t=0)
#         self.assertEqual(dst.inputs, [6])

#     def test_multiply2(self):
#         bd = bdsim.BlockDiagram()

#         dst = bd.OUTPORT(1)  # 1 ports

#         dst[0] = bd.CONSTANT(2) * bd.GAIN(3) * bd.GAIN(4)

#         bd.compile()
#         bd.evaluate(x=[], t=0)
#         self.assertEqual(dst.inputs, [24])

#     def test_multiply3(self):
#         bd = bdsim.BlockDiagram()

#         const = bd.CONSTANT([2, 3])
#         src = bd.DEMUX(2)
#         bd.connect(const, src)

#         dst = bd.OUTPORT(2)  # 2 ports

#         dst[0] = src[0] * bd.GAIN(2)
#         dst[1] = src[1] * bd.GAIN(3)

#         bd.compile()
#         bd.evaluate(x=[], t=0)
#         self.assertEqual(dst.inputs, [4, 9])

#     def test_inline1(self):
#         bd = bdsim.BlockDiagram()

#         dst = bd.OUTPORT(1)  # 1 ports
#         const1 = bd.CONSTANT(2)
#         const2 = bd.CONSTANT(3)

#         dst[0] = bd.SUM('++', const1, const2)

#         bd.compile()
#         bd.evaluate(x=[], t=0)
#         self.assertEqual(dst.inputs, [5])

#     def test_inline2(self):
#         bd = bdsim.BlockDiagram()

#         dst = bd.OUTPORT(1)  # 1 ports
#         const1 = bd.CONSTANT(2)
#         const2 = bd.CONSTANT(3)

#         dst[0] = bd.SUM('++', const1, const2) * bd.GAIN(2)

#         bd.compile()
#         bd.evaluate(x=[], t=0)
#         self.assertEqual(dst.inputs, [10])

# class ImportTest(unittest.TestCase):
    
#     def test_import1(self):
#         # create a subsystem
#         ss = bdsim.BlockDiagram(name='subsystem1')
    
#         f = ss.FUNCTION(lambda x: x)
#         inp = ss.INPORT(1)
#         outp = ss.OUTPORT(1)
        
#         ss.connect(inp, f)
#         ss.connect(f, outp)
    
#         # create main system
#         bd = bdsim.BlockDiagram()
    
#         const = bd.CONSTANT(1)
#         scope = bd.SCOPE()
        
#         f = bd.SUBSYSTEM(ss, name='subsys')
        
#         bd.connect(const, f)
#         bd.connect(f, scope)
        
#         bd.compile()
        
#         self.assertEqual(len(bd.blocklist), 3)
#         self.assertEqual(len(bd.wirelist), 2)

#     def test_import2(self):
#         # create a subsystem
#         ss = bdsim.BlockDiagram(name='subsystem1')
    
#         f = ss.FUNCTION(lambda x: x)
#         inp = ss.INPORT(1)
#         outp = ss.OUTPORT(1)
        
#         ss.connect(inp, f)
#         ss.connect(f, outp)
    
#         # create main system
#         bd = bdsim.BlockDiagram()
    
#         const = bd.CONSTANT(1)
#         scope1 = bd.SCOPE()
#         scope2 = bd.SCOPE()
        
#         f1 = bd.SUBSYSTEM(ss, name='subsys1')
#         f2 = bd.SUBSYSTEM(ss, name='subsys2')
        
#         bd.connect(const, f1, f2)
#         bd.connect(f1, scope1)
#         bd.connect(f2, scope2)
        
#         bd.compile()

# ---------------------------------------------------------------------------------------#
if __name__ == '__main__':

    unittest.main()
    
