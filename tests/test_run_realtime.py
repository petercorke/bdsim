#!/usr/bin/env python3

import unittest

import bdsim


class BDRealTimeTest(unittest.TestCase):
    def setUp(self):
        self.sim = bdsim.BDRealTime(
            graphics=None,
            progress=False,
            banner=False,
            quiet=True,
            sysargs=False,
        )

    def _sampled_bd(self):
        bd = self.sim.blockdiagram()
        clk = bd.clock(20, "Hz")
        src = bd.WAVEFORM("sine", freq=1)
        zoh = bd.ZOH(clk)
        sink = bd.NULL()
        bd.connect(src, zoh)
        bd.connect(zoh, sink)
        bd.compile(verbose=False)
        return bd, clk, zoh

    def _continuous_bd(self):
        bd = self.sim.blockdiagram()
        src = bd.STEP(t=0.1)
        integ = bd.INTEGRATOR()
        sink = bd.NULL()
        bd.connect(src, integ)
        bd.connect(integ, sink)
        bd.compile(verbose=False)
        return bd

    def test_sampled_only_guard(self):
        bd = self._continuous_bd()
        with self.assertRaises(RuntimeError):
            self.sim.run(bd, tf=0.1, backend="thread")

    def test_run_without_signal_logging(self):
        bd, _, _ = self._sampled_bd()
        out = self.sim.run(
            bd,
            tf=0.15,
            backend="thread",
            log_signals=False,
            log_clock_state=False,
        )

        self.assertFalse(hasattr(out, "t"))
        self.assertFalse(hasattr(out, "y0"))
        self.assertTrue(hasattr(out, "stats"))
        self.assertGreaterEqual(out.stats["eval_count"], 1)

    def test_run_with_signal_logging(self):
        bd, _, integ = self._sampled_bd()
        out = self.sim.run(
            bd,
            tf=0.2,
            backend="thread",
            watch=[integ],
            log_signals=True,
            log_clock_state=False,
        )

        self.assertTrue(hasattr(out, "t"))
        self.assertTrue(hasattr(out, "y0"))
        self.assertTrue(hasattr(out, "ynames"))
        self.assertGreaterEqual(len(out.t), 1)
        self.assertEqual(len(out.t), len(out.y0))

    def test_run_with_clock_logging(self):
        bd, _, _ = self._sampled_bd()
        out = self.sim.run(
            bd,
            tf=0.15,
            backend="thread",
            log_signals=False,
            log_clock_state=True,
        )

        self.assertTrue(hasattr(out, "clock0"))
        self.assertTrue(hasattr(out.clock0, "t"))
        self.assertTrue(hasattr(out.clock0, "x"))
        self.assertGreaterEqual(len(out.clock0.t), 1)

    def test_invalid_policy(self):
        bd, _, _ = self._sampled_bd()
        with self.assertRaises(ValueError):
            self.sim.run(
                bd,
                tf=0.1,
                backend="thread",
                catchup_policy="invalid",
            )


if __name__ == "__main__":
    unittest.main()
