import unittest
import numpy.testing as nt
import tempfile
import os
from bdsim.components import *
from bdsim.blocks import *
from bdsim import BDSim, TimeQ, BlockDiagram


class WireTest(unittest.TestCase):
    def test_init(self):
        b1 = Constant(2, name="block1")
        b2 = Null()

        w = Wire(b1, b2, name="wire1")

        w.info
        self.assertIsInstance(str(w), str)

    def test_bd(self):
        sim = bdsim.BDSim()  # create simulator
        bd = sim.blockdiagram()
        b1 = bd.CONSTANT(2, name="block1")
        b2 = bd.NULL()

        bd.connect(b1, b2)
        bd.compile()

        w = bd.wirelist[0]
        self.assertIsInstance(str(w), str)
        self.assertEqual(str(w), "wire.0")

        self.assertIsInstance(w.fullname, str)
        self.assertEqual(w.fullname, "block1[0] --> null.0[0]")

        self.assertIsInstance(repr(w), str)
        self.assertEqual(repr(w), "wire.0: block1[0] --> null.0[0]")


class PlugTest(unittest.TestCase):
    def test_portlist(self):
        block = Mux(5)
        p = Plug(block, type="end")
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
        q = TimeQ()

        q.push((0, "a"))
        q.push((3, "d"))
        q.push((2, "c"))
        q.push((1, "b"))

        self.assertEqual(len(q), 4)

        self.assertIsInstance(str(q), str)
        self.assertIsInstance(repr(q), str)
        self.assertEqual(str(q), "TimeQ: len=4, first out (0, 'a')")

        x = q.pop()
        self.assertIsInstance(x, tuple)
        self.assertEqual(x, (0, ["a"]))
        x = q.pop()
        self.assertEqual(x, (1, ["b"]))
        x = q.pop()
        self.assertEqual(x, (2, ["c"]))
        x = q.pop()
        self.assertEqual(x, (3, ["d"]))
        x = q.pop()
        self.assertEqual(x, (None, []))

    def test_threshold(self):
        q = TimeQ()
        q.push((0, "a"))
        q.push((3, "d"))
        q.push((2, "c"))
        q.push((0.001, "b"))

        x = q.pop(dt=0.1)
        self.assertEqual(x, (0, ["a", "b"]))
        x = q.pop(dt=0.1)
        self.assertEqual(x, (2, ["c"]))
        x = q.pop(dt=0.1)
        self.assertEqual(x, (3, ["d"]))

    def test_until(self):
        q = TimeQ()

        q.push((0, "a"))
        q.push((3, "d"))
        q.push((2, "c"))
        q.push((0.5, "b"))

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

        c = Clock(2, "ms")
        self.assertEqual(c.T, 0.002)

        c = Clock(2, "Hz")
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

        s = str(c)
        self.assertIsInstance(s, str)
        self.assertIn("clock.0", s)
        self.assertIn("T = 2", s)

        r = repr(c)
        self.assertIsInstance(r, str)
        self.assertIn("Clock(name=clock.0", r)
        self.assertIn("T=2", r)

        c = Clock(2, offset=1, name="myclock")
        block = ZOH(c)
        r = repr(c)
        self.assertIsInstance(r, str)
        self.assertIn("myclock", r)
        self.assertIn("offset=1", r)

    @unittest.skip
    def test_state(self):
        global clocklist
        clocklist.clear()

        c = Clock(2)
        bd = BlockDiagram()
        const = Constant(0, bd=bd)
        block1 = ZOH(c, x0=3, bd=bd)
        block2 = ZOH(c, x0=4, bd=bd)
        null = Null(bd=bd)
        bd.connect(const, block1)
        bd.connect(block1, block2)
        bd.connect(block2, null)
        bd.compile()

        self.assertEqual(len(c.blocklist), 2)
        nt.assert_almost_equal(c.getstate0(), np.r_[3, 4])

        c._compile_state = np.r_[5, 6]

        nt.assert_almost_equal(c.getstate(0.0), np.r_[13, 14])

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
    def test_struct_empty_str(self):
        x = BDStruct()
        self.assertEqual(str(x), "")

    def test_struct(self):
        x = BDStruct()
        x.a = 1
        x.b = "hello"
        x.c = 4.56
        x.d = [1, 2, 3]
        self.assertEqual(x.a, 1)
        self.assertEqual(x.b, "hello")
        self.assertEqual(x.c, 4.56)
        self.assertEqual(x.d, [1, 2, 3])
        s = str(x)
        print(s)
        self.assertEqual(len(s.split("\n")), 4)

    def test_struct_struct(self):
        x = BDStruct(f=2)
        x.a = BDStruct(name="baz", a=1, b=4.56)
        self.assertEqual(
            str(x),
            (
                "a    .baz::\n        a     = 1 (int)\n        b     = 4.56 (float)\nf "
                "    = 2 (int)"
            ),
        )

    def test_item(self):
        x = BDStruct()
        x["a"] = 1
        x["b"] = "hello"
        self.assertEqual(x.a, 1)
        self.assertEqual(x.b, "hello")

        self.assertEqual(x["a"], 1)
        self.assertEqual(x["b"], "hello")

    def test_init(self):
        s = BDStruct(a=2, b=3)
        self.assertEqual(s.a, 2)
        self.assertEqual(s.b, 3)
        with self.assertRaises(AttributeError):
            z = s.c

        s.c = 4
        self.assertEqual(s.c, 4)
        s.c = 5
        self.assertEqual(s.c, 5)

        s.d = 6
        self.assertEqual(s.d, 6)

        self.assertIsInstance(str(s), str)
        self.assertIsInstance(repr(s), str)
        self.assertEqual(
            str(s), "a     = 2 (int)\nb     = 3 (int)\nc     = 5 (int)\nd     = 6 (int)"
        )

    def test_len(self):
        s = BDStruct(a=2, c=1, b=3)
        self.assertEqual(len(s), 3)

    def test_add_and_array_and_dump(self):
        s = BDStruct(name="arr")
        s.add("arr", np.array([1, 2, 3]))
        txt = str(s)
        self.assertIn("ndarray", txt)

        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name
        try:
            s.dump(path)
            self.assertTrue(os.path.exists(path))
            self.assertGreater(os.path.getsize(path), 0)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_getattr_private_name_raises(self):
        s = BDStruct(a=1)
        with self.assertRaises(AttributeError):
            s.__getattr__("_private")


class OptionTest(unittest.TestCase):
    def test_init(self):
        opt = OptionsBase()

    def test_init1(self):
        opt = OptionsBase(dict(foo=1, bar="hello"))

        self.assertEqual(opt.foo, 1)
        self.assertEqual(opt.bar, "hello")

    def test_init2(self):
        opt = OptionsBase({}, dict(foo=1, bar="hello"))

        self.assertEqual(opt.foo, 1)
        self.assertEqual(opt.bar, "hello")

    def test_init1(self):
        opt = OptionsBase(dict(foo=1, bar="hello"), dict(foo=2, baz=3))

        self.assertEqual(opt.foo, 1)
        self.assertEqual(opt.bar, "hello")
        self.assertEqual(opt.baz, 3)

    def test_set(self):
        opt = OptionsBase(dict(foo=1, bar="hello"))

        opt.foo = 2
        self.assertEqual(opt.foo, 1)
        self.assertEqual(opt.bar, "hello")

    def test_set2(self):
        opt = OptionsBase(dict(foo=1, bar="hello"))

        opt.set(foo=3)
        self.assertEqual(opt.foo, 1)
        self.assertEqual(opt.bar, "hello")

    def test_set3(self):
        opt = OptionsBase({}, dict(foo=1, bar="hello"))

        opt.set(foo=3)
        self.assertEqual(opt.foo, 3)
        self.assertEqual(opt.bar, "hello")

    def test_items_str_repr(self):
        opt = OptionsBase({}, dict(alpha=1, beta="x"))
        items = dict(opt.items())
        self.assertEqual(items["alpha"], 1)
        s = str(opt)
        self.assertIn("alpha", s)
        self.assertIn("beta", s)
        r = repr(opt)
        self.assertIn("alpha", r)
        self.assertIn("beta", r)

    def test_getattr_missing_raises(self):
        opt = OptionsBase({}, dict(foo=1))
        with self.assertRaises(AttributeError):
            _ = opt.does_not_exist

    def test_getattr_private_missing_raises(self):
        opt = OptionsBase({}, dict(foo=1))
        with self.assertRaises(AttributeError):
            opt.__getattr__("_does_not_exist")


# ---------------------------------------------------------------------------------------#
if __name__ == "__main__":
    # opt = OptionsBase(dict(foo=1, bar='hello'), dict(foo=2))

    # opt.set(foo=3)
    # print(opt.foo)

    unittest.main()
