import unittest
import numpy.testing as nt
from bdsim.components import *


class PriorityQTest(unittest.TestCase):

    def test_pushpop(self):
        q = PriorityQ()

        q.push((0, 'a'))
        q.push((3, 'd'))
        q.push((2, 'c'))
        q.push((1, 'b'))

        self.assertEqual(len(q), 4)

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

# ---------------------------------------------------------------------------------------#
if __name__ == '__main__':

    unittest.main()