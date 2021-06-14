import time
from typing import Callable, Dict, List, Optional, Set
import sched
from bdsim import Block, BlockDiagram, BDSimState
from bdsim.components import Clock, SinkBlock, SourceBlock
import gc


def run(bd: BlockDiagram, max_time: Optional[float]=None):
    scheduler = sched.scheduler()
    state = bd.state = BDSimState()
    state.T = max_time

    # TODO: implement sim mode context manager
    assert not any(b.blockclass == 'transfer' for b in bd.blocklist), \
        "Tranfer blocks are not supported in realtime execution mode (yet). Sorry!"

    bd.start()

    prev_clock_period = 0
    # track to make sure we're actually executing all blocks on clock cycles properly.
    # otherwise the realtime blockdiagram is not fit for realtime execution
    in_clocked_plan: Dict[Block, bool] = {block: False for block in bd.blocklist}

    for clock in bd.clocklist:

        # assert that all clocks' periods are integer multiples of eachother so that they don't overlap.
        # Should really be done at clock definition time.
        # May be avoided with some multiprocess magic - but only on multicore systems.
        assert (prev_clock_period % clock.T == 0) or (clock.T % prev_clock_period == 0)
        prev_clock_period = clock.T

        # Need to find all the blocks that require execution on this Clock's tick.
        to_exec_on_tick: Set[Block] = set()
        # Recurse backwards and forwards to collect these
        for block in clock.blocklist:
            _collect_connected(block, to_exec_on_tick, forward=False) # Backwards
            _collect_connected(block, to_exec_on_tick, forward=True) # Forwards
        
        # plan out an order of block .output() execution and propagation. From sources -> sinks
        plan = [b for b in to_exec_on_tick if isinstance(b, SourceBlock)]

        for idx in range(len(to_exec_on_tick)):
            for port, outwires in enumerate(plan[idx].outports):
                for w in outwires:
                    block: Block = w.end.block

                    if block in to_exec_on_tick: # make sure we actually need .output() this block on this clock tick
                        if block in plan:
                            continue

                        block.inputs[port] = True
                        if all(in_plan for in_plan in block.inputs):
                            plan.append(block)
                            in_clocked_plan[block] = True
        
        assert len(plan) == len(to_exec_on_tick)

        def reschedule():
            scheduler.enter(clock.offset, 1, exec_plan_scheduled, argument=(clock, plan, state, reschedule))
    
    not_planned = set(block for block, planned in in_clocked_plan.items() if not planned)
    # TODO: implement sim mode context manager
    assert not not_planned, """Blocks {} do not depend or are a dependency of any ClockedBlocks.
This is required for its real-time execution.
Mark the blocks as sim_only=True if they are not required for realtime execution, or declare them within the `with bdsim.simulation_only: ...` context manager""" \
    .format(not_planned)

    scheduler.run()


def exec_plan_scheduled(clock: Clock, plan: List[Block], state: BDSimState, reschedule_this: Callable[[], None]):
    state.t = time.time()
    
    # execute the 'ontick' steps for each clock, ie read ADC's output PWM's, send/receive datas
    for b in clock.blocklist:
        b._x = b.next()
    
    # now execute the given plan
    for b in plan:
        if isinstance(b, SinkBlock):
            b.step() # step sink blocks
        else:
            # propagate all other blocks
            out = b.output(state.t)
            for (n, ws) in enumerate(b.outports):
                for w in ws:
                    w.end.block.inputs[w.end.port] = out[n]

    # forcibly collect garbage to assist in fps constancy
    gc.collect()

    if not state.stop and (state.T is None or state.t < state.T):
        reschedule_this()



def _collect_connected(block: Block, collected: Set[Block], forward: bool):
    """Recurses connections in the block diagram, either forward or backward from a given block.
    Collects the blocks into the provided "collected" set.
    if inports=True, will recurse through inputs, otherwise will recurse through outputs
    """
    collected.add(block)

    ports_attr, plug_attr = ('inports', 'start') if forward else ('outports', 'end')

    for wires in getattr(block, ports_attr):
        for wire in wires:
            plug = getattr(wire, plug_attr)
            _collect_connected(plug.block, collected, forward)