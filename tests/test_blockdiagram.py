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

    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(animation=False)  # create simulator

    def test_bd(self):

        bd1 = self.sim.blockdiagram()
        bd2 = self.sim.blockdiagram()
        self.assertEqual(len(bd1), 0)
        self.assertEqual(len(bd2), 0)
        bd1.CONSTANT(2)
        self.assertEqual(len(bd1), 1)
        bd1.CONSTANT(2)
        self.assertEqual(len(bd1), 2)
        self.assertEqual(len(bd2), 0)
        bd2.CONSTANT(2)
        self.assertEqual(len(bd1), 2)
        self.assertEqual(len(bd2), 1)

    def test_connect_1(self):

        bd = self.sim.blockdiagram()
        src = bd.CONSTANT(2)
        dst = bd.NULL(1)  # 1 port
        bd.connect(src, dst)
        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs[0], 2)

    def test_connect_2(self):

        bd = self.sim.blockdiagram()
        src = bd.CONSTANT(2)
        dst1 = bd.NULL(1)  # 1 port
        dst2 = bd.NULL(1)  # 1 port
        bd.connect(src, dst1)
        bd.connect(src, dst2)
        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst1.inputs[0], 2)
        self.assertEqual(dst2.inputs[0], 2)

    def test_multi_connect(self):

        bd = self.sim.blockdiagram()
        src = bd.CONSTANT(2)
        dst1 = bd.NULL(1)  # 1 port
        dst2 = bd.NULL(1)  # 1 port
        bd.connect(src, dst1, dst2)
        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst1.inputs[0], 2)
        self.assertEqual(dst2.inputs[0], 2)

    def test_ports1(self):

        bd = self.sim.blockdiagram()
        const1 = bd.CONSTANT(2)
        const2 = bd.CONSTANT(3)

        dst = bd.NULL(2)  # 2 ports
        bd.connect(const1, dst[0])
        bd.connect(const2, dst[1])
        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [2, 3])

    def test_ports2(self):

        bd = self.sim.blockdiagram()
        const = bd.CONSTANT([2, 3])
        src = bd.DEMUX(2)
        bd.connect(const, src)

        dst1 = bd.NULL(1)  # 1 port
        dst2 = bd.NULL(1)  # 1 port

        bd.connect(src[0], dst1)
        bd.connect(src[1], dst2)
        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst1.inputs, [2])
        self.assertEqual(dst2.inputs, [3])

    def test_ports3(self):

        bd = self.sim.blockdiagram()

        const = bd.CONSTANT([2, 3, 4, 5])
        src = bd.DEMUX(4)
        bd.connect(const, src)

        dst = bd.NULL(4)  # 4 ports
        bd.connect(src[0], dst[0])
        bd.connect(src[1], dst[1])
        bd.connect(src[2], dst[2])
        bd.connect(src[3], dst[3])
        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [2, 3, 4, 5])

    def test_slice1(self):

        bd = self.sim.blockdiagram()

        src = bd.CONSTANT(2)
        dst = bd.NULL(2)  # 1 port
        bd.connect(src, dst[0])
        bd.connect(src, dst[1])
        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [2, 2])

    def test_slice2(self):

        bd = self.sim.blockdiagram()

        const = bd.CONSTANT([2, 3, 4, 5])
        src = bd.DEMUX(4)
        bd.connect(const, src)

        dst = bd.NULL(4)  # 4 ports
        bd.connect(src[0:4], dst[0:4])
        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [2, 3, 4, 5])

    def test_slice3(self):

        bd = self.sim.blockdiagram()

        const = bd.CONSTANT([2, 3, 4, 5])
        src = bd.DEMUX(4)
        bd.connect(const, src)

        dst = bd.NULL(4)  # 4 ports
        bd.connect(src[0:4], dst[3:-1:-1])
        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [5, 4, 3, 2])

    def test_slice4(self):

        bd = self.sim.blockdiagram()

        const = bd.CONSTANT([2, 3, 4, 5])
        src = bd.DEMUX(4)
        bd.connect(const, src)

        dst = bd.NULL(4)  # 4 ports
        bd.connect(src[3:-1:-1], dst[0:4])
        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [5, 4, 3, 2])

    def test_slice5(self):

        bd = self.sim.blockdiagram()

        const = bd.CONSTANT([2, 3, 4, 5])
        src = bd.DEMUX(4)
        bd.connect(const, src)

        dst = bd.NULL(4)  # 4 ports
        bd.connect(src[0:4:2], dst[0:4:2])  # 0, 2
        bd.connect(src[1:4:2], dst[1:4:2])  # 1, 3
        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [2, 3, 4, 5])

    def test_slice5a(self):

        bd = self.sim.blockdiagram()

        const = bd.CONSTANT([2, 3, 4, 5])
        src = bd.DEMUX(4)
        bd.connect(const, src)

        dst = bd.NULL(4)  # 4 ports
        bd.connect(src[0:4:2], dst[0:2])  # 0, 2
        bd.connect(src[1:4:2], dst[2:4])  # 1, 3
        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [2, 4, 3, 5])

    def test_slice6(self):

        bd = self.sim.blockdiagram()

        const = bd.CONSTANT([2, 3, 4, 5])
        src = bd.DEMUX(4)
        bd.connect(const, src)

        dst = bd.NULL(4)  # 4 ports
        bd.connect(src[3:-1:-1], dst[3:-1:-1])
        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [2, 3, 4, 5])

        
    def test_assignment11(self):

        bd = self.sim.blockdiagram()

        src = bd.CONSTANT(2)
        dst = bd.NULL(1)  # 1 port
        
        dst[0] = src

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs[0], 2)

    def test_assignment2(self):
        
        bd = self.sim.blockdiagram()

        const1 = bd.CONSTANT(2)
        const2 = bd.CONSTANT(3)

        dst = bd.NULL(2)  # 2 ports

        dst[0] = const1
        dst[1] = const2

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [2, 3])


    def test_assignment3(self):
        bd = self.sim.blockdiagram()

        const = bd.CONSTANT([2, 3, 4, 5])
        src = bd.DEMUX(4)
        bd.connect(const, src)

        dst = bd.NULL(4)  # 4 ports

        dst[3:-1:-1] = src[0:4]

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [5, 4, 3, 2])

    def test_chain1(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports

        dst[0] = bd.CONSTANT(2) >> bd.GAIN(3)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [6])

    def test_chain2(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports

        dst[0] = bd.CONSTANT(2) >> bd.GAIN(3) >> bd.GAIN(4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [24])

    def test_chain3(self):
        bd = self.sim.blockdiagram()

        const = bd.CONSTANT([2, 3])
        src = bd.DEMUX(2)
        bd.connect(const, src)

        dst = bd.NULL(2)  # 2 ports

        dst[0] = src[0] >> bd.GAIN(2)
        dst[1] = src[1] >> bd.GAIN(3)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [4, 9])

    def test_inline1(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(2)
        const2 = bd.CONSTANT(3)

        dst[0] = bd.SUM('++', inputs=(const1, const2))

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [5])

    def test_inline2(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(2)
        const2 = bd.CONSTANT(3)

        dst[0] = bd.SUM('++', inputs=(const1, const2)) >> bd.GAIN(2)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [10])

    def test_autosum1(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(2)
        const2 = bd.CONSTANT(3)

        dst[0] = const1 + const2

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [5])

    def test_autosum2a(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(2)
        const2 = bd.CONSTANT(3)

        dst[0] = const1 + const2[0]

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [5])

    def test_autosum2b(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(2)
        const2 = bd.CONSTANT(3)

        dst[0] = const1[0] + const2

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [5])

    def test_autosum2c(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(2)
        const2 = bd.CONSTANT(3)

        dst[0] = const1[0] + const2[0]

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [5])

    def test_autosum3a(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(2)

        dst[0] = const1 + 3

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [5])

    def test_autosum3b(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const2 = bd.CONSTANT(3)

        dst[0] = 2 + const2

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [5])

    # ----------------------------------------------
    def test_autosub1(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(2)
        const2 = bd.CONSTANT(3)

        dst[0] = const1 - const2

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [-1])

    def test_autosub2a(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(2)
        const2 = bd.CONSTANT(3)

        dst[0] = const1 - const2[0]

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [-1])

    def test_autosub2b(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(2)
        const2 = bd.CONSTANT(3)

        dst[0] = const1[0] - const2

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [-1])

    def test_autosub2c(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(2)
        const2 = bd.CONSTANT(3)

        dst[0] = const1[0] - const2[0]

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [-1])

    def test_autosub3a(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(2)

        dst[0] = const1 - 3

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [-1])

    def test_autosub3b(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const2 = bd.CONSTANT(3)

        dst[0] = 2 - const2

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [-1])

    # ----------------------------------------------

    def test_autoneg1(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(2)

        dst[0] = -const1

        self.assertEqual(len(bd), 3)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [-2])

    def test_autoneg2(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(2)

        dst[0] = -const1[0]

        self.assertEqual(len(bd), 3)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [-2])

    # ----------------------------------------------

    def test_autoprod1(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(2)
        const2 = bd.CONSTANT(3)

        dst[0] = const1 * const2

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [6])

    def test_autoprod2a(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(3)
        const2 = bd.CONSTANT(2)

        dst[0] = const1[0] / const2

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [1.5])

    def test_autoprod2b(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(3)
        const2 = bd.CONSTANT(2)

        dst[0] = const1[0] / const2[0]

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [1.5])

    def test_autoprod2c(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(3)
        const2 = bd.CONSTANT(2)

        dst[0] = const1[0] / const2[0]

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [1.5])

    def test_autoprod3a(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(2)
        const2 = 3

        dst[0] = const1 * const2

        self.assertEqual(len(bd), 3)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [6])

    def test_autoprod3b(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = 2
        const2 = bd.CONSTANT(3)

        dst[0] = const1 * const2

        self.assertEqual(len(bd), 3)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [6])

    # ----------------------------------------------

    def test_autodiv1(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(3)
        const2 = bd.CONSTANT(2)

        dst[0] = const1 / const2

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [1.5])

    def test_autodiv2a(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(3)
        const2 = bd.CONSTANT(2)

        dst[0] = const1[0] / const2

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [1.5])

    def test_autodiv2b(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(3)
        const2 = bd.CONSTANT(2)

        dst[0] = const1[0] / const2[0]

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [1.5])

    def test_autodiv2c(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(3)
        const2 = bd.CONSTANT(2)

        dst[0] = const1[0] / const2[0]

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [1.5])

    def test_autodiv3a(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = bd.CONSTANT(3)
        const2 = 2

        dst[0] = const1 / const2

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [1.5])

        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [1.5])

    def test_autodiv3b(self):
        bd = self.sim.blockdiagram()

        dst = bd.NULL(1)  # 1 ports
        const1 = 3
        const2 = bd.CONSTANT(2)

        dst[0] = const1 / const2

        self.assertEqual(len(bd), 4)

        bd.compile(verbose=False)
        bd.evaluate_plan(x=[], t=0)
        self.assertEqual(dst.inputs, [1.5])

class ImportTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(animation=False)  # create simulator

    def test_import1(self):
        # create a subsystem
        ss = self.sim.blockdiagram(name='subsystem1')

        f = ss.FUNCTION(lambda x: x)
        inp = ss.INPORT(1)
        outp = ss.OUTPORT(1)
        
        ss.connect(inp, f)
        ss.connect(f, outp)
    
        # create main system
        bd = self.sim.blockdiagram()
    
        const = bd.CONSTANT(1)
        scope = bd.SCOPE()
        
        ff = bd.SUBSYSTEM(ss, name='subsys')
        
        bd.connect(const, ff)
        bd.connect(ff, scope)
        
        bd.compile(verbose=False)
        
        self.assertEqual(len(bd.blocklist), 5)
        self.assertEqual(len(bd.wirelist), 4)

#     def test_import2(self):
#         # create a subsystem
#         ss = bdsim.BlockDiagram(name='subsystem1')
    
#         f = ss.FUNCTION(lambda x: x)
#         inp = ss.INPORT(1)
#         outp = ss.NULL(1)
        
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
        
#         bd.compile(verbose=False)

# ---------------------------------------------------------------------------------------#
if __name__ == '__main__':

    unittest.main()
    
