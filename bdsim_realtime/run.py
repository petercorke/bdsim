import time
from typing import Dict, List, Optional, Set
import sched
from bdsim import Block, BlockDiagram, BDSimState
from bdsim.components import Clock, SinkBlock, SourceBlock


def run(bd: BlockDiagram, max_time: Optional[float]=None):
    scheduler = sched.scheduler()
    state = bd.state = BDSimState()
    state.T = max_time
    if not bd.compiled:
        bd.compile()

    # TODO: implement sim mode context manager
    assert not any(b.blockclass == 'transfer' for b in bd.blocklist), \
        "Tranfer blocks are not supported in realtime execution mode (yet). Sorry!"

    bd.start()

    prev_clock_period = 0
    # track to make sure we're actually executing all blocks on clock cycles properly.
    # otherwise the realtime blockdiagram is not fit for realtime execution
    in_clocked_plan: Dict[Block, bool] = {block: False for block in bd.blocklist}

    before_planning_start = time.monotonic()
    SETUP_WAIT_BUFFER = 1 # in seconds, to give time for the planning and scheduling

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

        # collect sources
        plan = []
        for b in to_exec_on_tick:
            if isinstance(b, SourceBlock):
                plan.append(b)
                in_clocked_plan[b] = True


        # then propagate, updating plan as we go
        for idx in range(len(to_exec_on_tick)):
            for port, outwires in enumerate(plan[idx].outports):
                for w in outwires:
                    block: Block = w.end.block

                    if block in to_exec_on_tick: # make sure we actually need .output() this block on this clock tick
                        if block in plan:
                            continue

                        block.inputs[w.end.port] = True
                        if all(in_plan for in_plan in block.inputs):
                            plan.append(block)
                            in_clocked_plan[block] = True
                            # reset the inputs
                            block.inputs = [None] * len(block.inputs)
        
        assert len(plan) == len(to_exec_on_tick)

        scheduled_time = before_planning_start + clock.offset + SETUP_WAIT_BUFFER
        scheduler.enterabs(
            scheduled_time,
            priority=1,
            action=exec_plan_scheduled,
            argument=(
                clock,
                plan,
                state,
                scheduler,
                scheduled_time,
                scheduled_time))
    
    not_planned = set(block for block, planned in in_clocked_plan.items() if not planned)
    # TODO: implement sim mode context manager
    assert not not_planned, """Blocks {} do not depend on or are a dependency of any ClockedBlocks.
This is required for its real-time execution.
Mark the blocks as sim_only=True if they are not required for realtime execution, or declare them within the `with bdsim.simulation_only: ...` context manager""" \
    .format(not_planned)

    scheduler.run()


def exec_plan_scheduled(
    clock: Clock,
    plan: List[Block],
    state: BDSimState,
    scheduler: sched.scheduler,
    scheduled_time: int,
    start_time: int
):
    state.t = scheduled_time - start_time
    
    # execute the 'ontick' steps for each clock, ie read ADC's output PWM's, send/receive datas
    for b in clock.blocklist:
        # if this block requires inputs, only run .next() the second time this was scheduled.
        # this way, its data-dependencies are met before .next() executes
        if scheduled_time == start_time and not isinstance(b, SourceBlock):
            continue
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
    # gc.collect()

    # print('after collect()', time.monotonic() - scheduled_time)

    if not state.stop and (state.T is None or state.t < state.T):
        next_scheduled_time = scheduled_time + clock.T
        scheduler.enterabs(
            next_scheduled_time,
            priority=1,
            action=exec_plan_scheduled,
            argument=(
                clock,
                plan,
                state,
                scheduler,
                next_scheduled_time,
                start_time))



def _collect_connected(block: Block, collected: Set[Block], forward: bool):
    """Recurses connections in the block diagram, either forward or backward from a given block.
    Collects the blocks into the provided "collected" set.
    if inports=True, will recurse through inputs, otherwise will recurse through outputs
    """
    collected.add(block)
    
    sub_blocks = (
        wire.end.block
        for wires in block.outports
        for wire in wires
    ) if forward else (
        wire.start.block for wire in block.inports
    )
    for block in sub_blocks:
        _collect_connected(block, collected, forward)