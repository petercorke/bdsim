import unittest
import numpy.testing as nt
from bdsim.components import *
from bdsim.blocks import *
from bdsim import bdsim

class WireTest(unittest.TestCase):

    def test_init(self):

        b1 = Constant(2, name='block1')
        b2 = Null()

        w = Wire(b1, b2, name='wire1')

        w.info
        self.assertIsInstance(str(w), str)

    def test_bd(self):
        sim = bdsim.BDSim()  # create simulator
        bd = sim.blockdiagram()
        b1 = bd.CONSTANT(2, name='block1')
        b2 = bd.NULL()

        bd.connect(b1, b2)
        bd.compile()

        w = bd.wirelist[0]
        self.assertIsInstance(str(w), str)
        self.assertEqual(str(w), 'wire.0')

        self.assertIsInstance(w.fullname, str)
        self.assertEqual(w.fullname, 'block1[0] --> null.0[0]')

        self.assertIsInstance(repr(w), str)
        self.assertEqual(repr(w), 'wire.0: block1[0] --> null.0[0]')


class PlugTest(unittest.TestCase):

    def test_portlist(self):

        block = Mux(5)
        p = Plug(block, type='end')

        p = block[3]
        pl = p.portlist
        self.assertEqual(len(pl), 1)
        self.assertEqual(pl[0], 3)

        p = block[1:4]
        pl = p.portlist
        self.assertEqual(len(pl), 3)
        self.assertEqual(list(pl), [1, 2, 3])

        p = block[:4]
        pl = p.portlist
        self.assertEqual(len(pl), 4)
        self.assertEqual(list(pl), [0, 1, 2, 3])

        p = block[2:]
        pl = p.portlist
        self.assertEqual(len(pl), 3)
        self.assertEqual(list(pl), [2, 3, 4])


class BlockTest(unittest.TestCase):

    def test_init(self):
        b1 = Constant(2)

        b1.info

    def test_predicates(self):

        b1 = Scope()
        b2 = Constant(2)
        b3 = ZOH(Clock(1))

        self.assertTrue(b1.isgraphics)
        self.assertFalse(b2.isgraphics)

        self.assertFalse(b2.isclocked)
        self.assertTrue(b3.isclocked)


class PriorityQTest(unittest.TestCase):

    def test_pushpop(self):
        q = PriorityQ()

        q.push((0, 'a'))
        q.push((3, 'd'))
        q.push((2, 'c'))
        q.push((1, 'b'))

        self.assertEqual(len(q), 4)

        self.assertIsInstance(str(q), str)
        self.assertIsInstance(repr(q), str)
        self.assertEqual(str(q), "PriorityQ: len=4, first out (0, 'a')")

        x = q.pop()
        self.assertIsInstance(x, tuple)
        self.assertEqual(x, (0, ['a']))
        x = q.pop()
        self.assertEqual(x, (1, ['b']))
        x = q.pop()
        self.assertEqual(x, (2, ['c']))
        x = q.pop()
        self.assertEqual(x, (3, ['d']))
        x = q.pop()
        self.assertEqual(x, (None, []))


    def test_threshold(self):
        q = PriorityQ()
        q.push((0, 'a'))
        q.push((3, 'd'))
        q.push((2, 'c'))
        q.push((0.001, 'b'))

        x = q.pop(dt=0.1)
        self.assertEqual(x, (0, ['a', 'b']))
        x = q.pop(dt=0.1)
        self.assertEqual(x, (2, ['c']))
        x = q.pop(dt=0.1)
        self.assertEqual(x, (3, ['d']))


    def test_until(self):
        q = PriorityQ()

        q.push((0, 'a'))
        q.push((3, 'd'))
        q.push((2, 'c'))
        q.push((0.5, 'b'))

        x = q.pop_until(2)
        self.assertEqual(len(x), 3)
        for i in x:
            self.assertTrue(i[0] <= 2)
        self.assertEqual(len(q), 1)

        x = q.pop_until(2.5)
        self.assertEqual(len(x), 0)


class ClockTest(unittest.TestCase):
    def test_init(self):

        c = Clock(2)
        self.assertEqual(c.T, 2)
        self.assertEqual(c.offset, 0)

        c = Clock(2, offset=1)
        self.assertEqual(c.T, 2)
        self.assertEqual(c.offset, 1)

        c = Clock(2, 'ms')
        self.assertEqual(c.T, 0.002)

        c = Clock(2, 'Hz')
        self.assertEqual(c.T, 0.5)

    def test_block(self):
        c = Clock(2)
        block = ZOH(c)
        self.assertEqual(len(c.blocklist), 1)
        self.assertEqual(c.blocklist[0], block)
        
    def test_str(self):

        global clocklist
        clocklist.clear()

        c = Clock(2)
        block = ZOH(c)

        self.assertIsInstance(str(c), str)
        self.assertEqual(str(c), 'clock.0: T=2 sec, clocking 1 blocks')

        self.assertIsInstance(repr(c), str)
        self.assertEqual(repr(c), 'clock.0: T=2 sec, clocking 1 blocks')

        c = Clock(2, offset=1, name='myclock')
        block = ZOH(c)
        self.assertIsInstance(repr(c), str)
        self.assertEqual(repr(c), 'myclock: T=2 sec, offset=1, clocking 1 blocks')

    def test_state(self):
        global clocklist
        clocklist.clear()

        c = Clock(2)
        block1 = ZOH(c, x0=3)
        block2 = ZOH(c, x0=4)
        block1.test_inputs = [13]
        block2.test_inputs = [14]

        self.assertEqual(len(c.blocklist), 2)
        nt.assert_almost_equal(c.getstate0(), np.r_[3, 4])

        c._x = np.r_[5, 6]
        c.setstate()
        nt.assert_almost_equal(block1._x, np.r_[5])
        nt.assert_almost_equal(block2._x, np.r_[6])

        nt.assert_almost_equal(c.getstate(), np.r_[13, 14])

    def test_time(self):
        global clocklist
        clocklist.clear()

        c = Clock(2, offset=1)
        block1 = ZOH(c, x0=3)

        self.assertEqual(c.time(0), 1)
        self.assertEqual(c.time(1), 3)
        self.assertEqual(c.time(2), 5)

        # c.start()
        # t = c.next_event()

class StructTest(unittest.TestCase):
    # test struct for simuluation results return

    def test_init(self):

        s = Struct(a=2, b=3)
        self.assertEqual(s.a, 2)
        self.assertEqual(s.b, 3)
        with self.assertRaises(AttributeError):
            z = s.c
        
        s.c = 4
        self.assertEqual(s.c, 4)
        s.c = 5
        self.assertEqual(s.c, 5)

        s.add('d', 6)
        self.assertEqual(s.d, 6)

        self.assertIsInstance(str(s), str)
        self.assertIsInstance(repr(s), str)
        self.assertEqual(str(s), 'Struct:\na           | int = 2\nb           | int = 3\nc           | int = 5\nd           | int = 6\n')

# ---------------------------------------------------------------------------------------#
if __name__ == '__main__':

    unittest.main()