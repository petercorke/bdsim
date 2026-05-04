#!/usr/bin/env python3

import platform
import threading
import time
import unittest

from bdsim.timers import (
    GCDTimerBackend,
    ThreadPeriodicTimerBackend,
    create_timer_backend,
)


class TimerBackendFactoryTest(unittest.TestCase):
    def test_thread_backend_explicit(self):
        backend = create_timer_backend("thread")
        self.assertIsInstance(backend, ThreadPeriodicTimerBackend)

    def test_auto_backend_constructs(self):
        backend = create_timer_backend("auto")
        self.assertIsNotNone(backend)


@unittest.skipUnless(platform.system().lower() == "darwin", "macOS only")
class GCDTimerBackendTest(unittest.TestCase):
    def test_gcd_backend_emits_ticks(self):
        backend = GCDTimerBackend()
        fired = []
        done = threading.Event()

        def cb(timer_id: str, scheduled_ns: int, fired_ns: int) -> None:
            fired.append((timer_id, scheduled_ns, fired_ns))
            if len(fired) >= 3:
                done.set()

        backend.start_periodic(
            timer_id="clock.test",
            period_ns=10_000_000,  # 10 ms
            phase_ns=1_000_000,  # 1 ms
            callback=cb,
        )
        backend.start_all()
        try:
            done.wait(timeout=0.25)
        finally:
            backend.stop_all()

        self.assertGreaterEqual(len(fired), 1)
        for timer_id, scheduled_ns, fired_ns in fired:
            self.assertEqual(timer_id, "clock.test")
            self.assertGreaterEqual(fired_ns, 0)
            self.assertGreaterEqual(scheduled_ns, 0)


if __name__ == "__main__":
    unittest.main()
