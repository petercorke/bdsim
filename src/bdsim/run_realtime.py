"""Real-time execution support for block diagrams."""

from __future__ import annotations

import math
import re
import sys
import time
import warnings
from typing import Any

import numpy as np
from colored import attr, fg

from bdsim.exceptions import BlockRuntimeError
from bdsim.components import BDStruct, Block, OptionsBase, SimulationState
from bdsim.connect import Plug
from bdsim.run_context import SimulationContext
from bdsim.run_sim import BDSim


# class TimeQRT(TimeQ):
#     """
#     Time-ordered queue for events

#     The list comprises tuples of (time, block) to reflect an event associated
#     with the specified block at the specified time.

#     The list is not ordered, and is sorted on a pop event.
#     """

#     def __init__(self):
#         self.q = []
#         self.dirty = False

#         # super().__init__()  # init threading class

#         self.sem = threading.Semaphore(0)
#         self.done = False
#         self.t = None

#     # def wait(self):
#     #     self.sem.acquire()
#     #     # print(f'  wake at {self.t}')
#     #     return self.t, self.clocks

#     def run(self, callback):
#         nok = 0
#         noverrun = 0

#         print('run')
#         t0 = time.time()
#         stop = t0
#         tmax = 0
#         while not self.done:
#             t, clocks = self.pop()
#             if t is None:
#                 print('E', end='')
#                 time.sleep(0.02)
#                 continue
#             # print('dequeue', t)
#             stop = t0 + t
#             ts = time.time()
#             sleep_time = stop - ts
#             if sleep_time > 0:
#                 # print('sleeping for', sleep_time)
#                 time.sleep(sleep_time)
#                 tmax = max(tmax, time.time()-ts)
#                 # if tmax > 0.2:
#                 #     print(tmax, sleep_time)
#                 print('.', end='')
#                 nok += 1
#             else:
#                 # print('timer overrun')
#                 print('x', end='')
#                 noverrun += 1
#             # self.t = t
#             # self.clocks = clocks
#             # self.sem.release()
#             callback(t, clocks)

#             sys.stdout.flush()

#         print(fg('yellow'))
#         print(f'tmax {tmax}')
#         print(f'n ok      {nok} ({nok/(nok+noverrun)*100:.1f}%)')
#         print(f'n overrun {noverrun} ({noverrun/(nok+noverrun)*100:.1f}%)')
#         print(attr(0))

#     def stop(self):
#         self.done = True
#         self.join()


class BDRealTimeState(SimulationState):
    """
    Realtime-specific simulation state, extending SimulationState
    with realtime-specific fields.

    :ivar dt: sample time interval (seconds)
    :ivar watchlist: list of plugs to watch
    :ivar watchnamelist: list of watch port names
    :ivar tlist: list of time samples
    :ivar plist: list of output port records
    """

    def __init__(self) -> None:
        super().__init__()
        # realtime-specific fields
        self.dt: float | None = None
        self.watchlist: list = []
        self.watchnamelist: list = []
        self.tlist: list = []
        self.xlist: list = []
        self.plist: list = []


class SimpleStats:
    def __init__(self) -> None:
        self._n = 0
        self._sum = 0
        self._sum2 = 0
        self._max = 0

    def update(self, x) -> None:
        self._n += 1
        self._sum += x
        self._sum2 += x**2
        self._max: int = max(self._max, x)

    @property
    def n(self) -> int:
        return self._n

    @property
    def mean(self):
        return self._sum / self._n

    @property
    def sdev(self) -> float:
        return math.sqrt((self._sum2 - self._sum**2 / self._n) / (self._n - 1))

    @property
    def max(self) -> int:
        return self._max


class BDRealTime(BDSim):
    def run(
        self,
        bd,
        tf=5,
        dt=None,
        block=None,
        checkfinite=True,
        watch=[],
        samples=True,
        T=None,
    ) -> BDStruct:
        """
        Run the block diagram

        :param T: maximum integration time, defaults to 10.0
        :type T: float, optional
        :param dt: maximum time step
        :type dt: float, optional
        :param solver: integration method, defaults to ``RK45``
        :type solver: str, optional
        :param block: matplotlib block at end of run, default False
        :type block: bool
        :param checkfinite: error if inf or nan on any wire, default True
        :type checkfinite: bool
        :param minstepsize: minimum step length, default 1e-6
        :type minstepsize: float
        :param watch: list of input ports to log
        :type watch: list
        :param solver_args: arguments passed to ``scipy.integrate``
        :type solver_args: dict
        :return: time history of signals and states
        :rtype: Sim class

        Assumes that the network has been compiled.

        The system is simulated from time 0 to ``T``.

        The integration step time ``dt`` defaults to ``T/100`` but can be
        specified.  Finer control can be achieved using ``max_step`` and
        ``first_step`` parameters to the underlying integrator using the
        ``solver_args`` parameter.

        Results are returned in a class with attributes:

        - ``t`` the time vector: ndarray, shape=(M,)
        - ``x`` is the state vector: ndarray, shape=(M,N)
        - ``xnames`` is a list of the names of the states corresponding to columns of `x`, eg. "plant.x0",
            defined for the block using the ``snames`` argument
        - ``yN`` for a watched input where N is the index of the port mentioned in the ``watch`` argument
        - ``ynames`` is a list of the names of the input ports being watched, same order as in ``watch`` argument

        If there are no dynamic elements in the diagram, ie. no states, then ``x`` and ``xnames`` are not
        present.

        The ``watch`` argument is a list of one or more input ports whose value during simulation
        will be recorded.  The elements of the list can be:
            - a ``Block`` reference, which is interpretted as input port 0
            - a ``Plug`` reference, ie. a block with an index or attribute
            - a string of the form "block[i]" which is port i of the block named block.

        The debug string comprises single letter flags:

                - 'p' debug network value propagation
                - 's' debug state vector
                - 'd' debug state derivative

        .. note:: Simulation stops if the step time falls below ``minsteplength``
            which typically indicates that the solver is struggling with a very
            harsh non-linearity.
        """

        assert bd.compiled, "Network has not been compiled"

        if T is not None:
            warnings.warn(
                "run(T=...) is deprecated, use run(tf=...) instead",
                DeprecationWarning,
                stacklevel=2,
            )
            tf = T

        simstate = BDRealTimeState()
        assert self.options is not None
        options: OptionsBase = self.options.copy()
        if dt is None:
            dt = tf / 100

        # Create per-run context
        context = SimulationContext(
            bd=bd, simstate=simstate, options=options, progress=None, threaded=False
        )
        self._set_context(context)

        try:
            simstate.tf = tf
            simstate.dt = dt
            simstate.options = options

            # process the watchlist
            #  elements can be:
            #   - block or Plug reference
            #   - str in the form BLOCKNAME[PORT]
            watchlist = []
            watchnamelist = []
            re_block: re.Pattern[str] = re.compile(
                r"(?P<name>[^[]+)(\[(?P<port>[0-9]+)\])"
            )
            for w in watch:
                if isinstance(w, str):
                    # a name was given, with optional port number
                    m: re.Match[str] | None = re_block.match(w)
                    if m is None:
                        raise ValueError("watch block[port] not found: " + w)
                    name: str | Any = m.group("name")
                    port = int(m.group("port"))
                    b = bd.blocknames[name]
                    plug = b[port]
                elif isinstance(w, Block):
                    # a block was given, defaults to port 0
                    plug: Plug = w[0]
                elif isinstance(w, Plug):
                    # a plug was given
                    plug: Plug = w
                watchlist.append(plug)
                watchnamelist.append(str(plug))
            simstate.watchlist = watchlist
            simstate.watchnamelist = watchnamelist

            # for clock in bd.clocklist:
            #     clock.start(simstate)

            # tell all blocks we're starting a BlockDiagram
            bd.start(simstate)

            simstate.tlist = []
            simstate.xlist = []
            simstate.plist = [[] for p in simstate.watchlist]

            print("run")
            nok = 0
            decimate = 0
            noverrun = 0
            self.running = True
            stats = SimpleStats()
            t0: float = time.time()
            t = 0

            while self.running:
                try:
                    # evaluate the block diagram
                    te_0: float = time.time()
                    bd.evaluate([], t)

                    # record the ports on the watchlist
                    for i, p in enumerate(simstate.watchlist):
                        b = p.block
                        output = b.output_safe(t, b.inport_values, b.x)[p.port]
                        simstate.plist[i].append(output)
                except BlockRuntimeError as err:
                    bd._handle_block_runtime_error(err)

                simstate.tlist.append(t)

                # check execution time for this sample step
                te_1: float = time.time()
                dte: float = te_1 - te_0
                stats.update(dte)  # compute stats on time to execute the block diagram
                if samples:
                    if dte > dt:
                        print("x", end="")  # overrun
                    else:
                        print(".", end="")
                    sys.stdout.flush()

                if dte > dt:
                    noverrun += 1
                else:
                    nok += 1

                # check whether to continue, and pause till next sample time
                tnow: float = time.time() - t0
                if tnow > tf:
                    break

                t += dt  # time of next sample

                t_sleep = t - tnow
                if t_sleep < 0:  # be tolerant to a sample overrun
                    t_sleep = 0
                time.sleep(t_sleep)  # sleep till next tick

            # save buffered data in a Struct
            out = BDStruct(name="results")
            out["t"] = np.array(simstate.tlist)
            # out.x = np.array(simstate.xlist)
            # out.xnames = bd.statenames

            # save the watchlist into variables named y0, y1 etc.
            for i, p in enumerate(watchlist):
                out["y" + str(i)] = np.array(simstate.plist[i])
            out["ynames"] = watchnamelist

            if noverrun > 0:
                print(fg("red"))
            else:
                print(fg("yellow"))
            print("run time performance:")
            print(
                f"  overrun    {noverrun} / {nok} ({noverrun/(nok+noverrun)*100:.1f}%)"
            )
            print(f"  t_max      {stats.max*1000:.1f} ms")
            print(f"  t_mean     {stats.mean*1000:.1f} ms")
            print(f"  t_sdev     {stats.sdev*1000:.1f} ms")
            print(f"  t_max / dt {stats.max/dt*100:.1f}%")
            print(attr(0))

            return out
        finally:
            # Clean up context
            self._set_context(None)

        # assert bd.compiled, "Network has not been compiled"

        # state = BDRealTimeState()
        # self.state = state

        # # process the watchlist
        # #  elements can be:
        # #   - block or Plug reference
        # #   - str in the form BLOCKNAME[PORT]
        # watchlist = []
        # watchnamelist = []
        # re_block = re.compile(r"(?P<name>[^[]+)(\[(?P<port>[0-9]+)\])")
        # for w in watch:
        #     if isinstance(w, str):
        #         # a name was given, with optional port number
        #         m = re_block.match(w)
        #         if m is None:
        #             raise ValueError("watch block[port] not found: " + w)
        #         name = m.group("name")
        #         port = int(m.group("port"))
        #         b = bd.blocknames[name]
        #         plug = b[port]
        #     elif isinstance(w, Block):
        #         # a block was given, defaults to port 0
        #         plug = w[0]
        #     elif isinstance(w, Plug):
        #         # a plug was given
        #         plug = w
        #     watchlist.append(plug)
        #     watchnamelist.append(str(plug))
        # state.watchlist = watchlist
        # state.watchnamelist = watchnamelist

        # for clock in bd.clocklist:
        #     clock.start(state)

        # state.tlist = []
        # state.xlist = []
        # state.plist = [[] for p in state.watchlist]

        # print("run")
        # t0 = time.time()
        # stop = t0
        # tmax = 0
        # nok = 0
        # n = 0
        # tsum = 0
        # tsum2 = 0
        # tmax = 0
        # noverrun = 0
        # self.running = True
        # while self.running:
        #     tnext, sources = self.state.eventq.pop()

        #     if tnext is None:
        #         print("E", end="")
        #         time.sleep(0.02)
        #         continue

        #     if tnext > T:
        #         break

        #     # print('dequeue', t)
        #     stop = t0 + tnext
        #     ts = time.time()
        #     sleep_time = stop - ts
        #     if sleep_time > 0:
        #         # print('sleeping for', sleep_time)
        #         time.sleep(sleep_time)
        #         tmax = max(tmax, time.time() - ts)
        #         # if tmax > 0.2:
        #         #     print(tmax, sleep_time)
        #         print(".", end="")
        #         nok += 1
        #     else:
        #         # print('timer overrun')
        #         print("x", end="")
        #         noverrun += 1

        #     # self.t = t
        #     # self.clocks = clocks
        #     # self.sem.release()

        #     # evaluate the block diagram
        #     te_0 = time.time()
        #     bd.evaluate_plan([], tnext)
        #     te_1 = time.time()

        #     dt = te_1 - te_0
        #     n += 1
        #     tsum += dt
        #     tsum2 += dt * dt
        #     tmax = max(tmax, dt)

        #     # visit all the blocks and clocks that have an event now
        #     for source in sources:
        #         # if isinstance(source, Clock):
        #         #     # clock ticked, save its state
        #         #     clock.savestate(tnext)
        #         source.next_event(self.state)

        #     # visit all the blocks and clocks that have an event now
        #     for source in sources:
        #         if isinstance(source, Clock):
        #             # clock ticked, save its state
        #             clock.savestate(tnext)
        #             clock.next_event(self.state)

        #             # get the new state
        #             clock._x = clock.getstate()

        #     # stash the results
        #     state.tlist.append(tnext)

        #     # record the ports on the watchlist
        #     for i, p in enumerate(state.watchlist):
        #         state.plist[i].append(p.block.output(tnext)[p.port])

        #     sys.stdout.flush()

        # # save buffered data in a Struct
        # out = BDStruct(name="results")
        # # out.t = np.array(state.tlist)
        # # out.x = np.array(state.xlist)
        # # out.xnames = bd.statenames

        # # save clocked states
        # for c in bd.clocklist:
        #     name = c.name.replace(".", "")
        #     clockdata = BDStruct(name)
        #     clockdata.t = np.array(c.t)
        #     clockdata.x = np.array(c.x)
        #     out.add(name, clockdata)

        # # save the watchlist into variables named y0, y1 etc.
        # for i, p in enumerate(watchlist):
        #     out["y" + str(i)] = np.array(state.plist[i])
        # out.ynames = watchnamelist

        # print(fg("yellow"))
        # print(f"tmax {tmax}")
        # print(f"n ok      {nok} ({nok/(nok+noverrun)*100:.1f}%)")
        # print(f"n overrun {noverrun} ({noverrun/(nok+noverrun)*100:.1f}%)")
        # print(f"t mean {tsum/n*1000:.1f} ms")
        # print(f"t sdev {math.sqrt((tsum2 - tsum**2/n)/(n-1)*1000):.1f} ms")
        # print(f"t max {tmax*1000:.1f} ms")
        # print(attr(0))

        # return out
        # self.state.eventq.start()

        # n = 0
        # tsum = 0
        # tsum2 = 0
        # tmax = 0

        # while True:
        #     t, clocks = self.state.eventq.wait()
        #     # print('run wakes up', t, clocks)
        #     state.t = t

        #     if t > T:
        #         break

        #     # evaluate the block diagram
        #     t0 = time.time()
        #     bd.evaluate_plan([], t)
        #     t1 = time.time()

        #     # visit all the blocks and clocks that have an event now
        #     for clock in clocks:
        #         # if isinstance(source, Clock):
        #         #     # clock ticked, save its state
        #         #     clock.savestate(tnext)
        #         clock.next_event(self.state)

        #     # update some stats about block diagram execution time
        #     dt = t1 - t0
        #     n += 1
        #     tsum += dt
        #     tsum2 += dt*dt
        #     tmax = max(tmax, dt)

        # self.state.eventq.stop()

        # print(fg('yellow'))
        # print(f't mean {tsum/n*1000:.1f} ms')
        # print(f't sdev {math.sqrt((tsum2 - tsum**2/n)/(n-1)*1000):.1f} ms')
        # print(f't max {tmax*1000:.1f} ms')
        # print(attr(0))


if __name__ == "__main__":
    try:
        from ._selftest import run_module_test
    except ImportError:
        from bdsim._selftest import run_module_test

    raise SystemExit(run_module_test(__file__))
