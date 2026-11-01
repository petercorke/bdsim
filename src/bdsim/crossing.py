"""
Zero-crossing events for blocks with discontinuities.

A block that changes behaviour when a signal crosses a threshold (a limited
integrator reaching its limit, a saturation, a dead band) must not let the
solver step over the corner.  It registers one scalar *detector* per threshold
and solve_ivp root-finds each one.  :class:`CrossingMixin` holds the boilerplate
so that a block only supplies the scalar function and the response.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np


class CrossingMixin:
    """
    Mixin for blocks that register zero-crossing detectors.

    Blocks that do not need events do not inherit from this and pay nothing.

    A subclass registers detectors from :meth:`start` with :meth:`declare_crossing`
    and overrides :meth:`crossing_event` to respond.  Detectors are sized in
    :meth:`~bdsim.Block.configure`, where :attr:`~bdsim.Block.insig` is known, and
    any mode kept by the block is restored in :meth:`~bdsim.Block.reset`.

    A block changes mode only in :meth:`crossing_event`, which runs between
    solve_ivp calls.  It must not change mode in ``deriv`` or in a detector,
    since the solver would then see a discontinuous right-hand side within a step.
    """

    def declare_crossing(
        self,
        simstate: Any,
        func: Callable[[np.ndarray, list[Any]], float],
        direction: float,
        tag: Any,
    ) -> None:
        """
        Register one terminal scalar detector.

        :param simstate: the run's simulation state, as passed to ``start``
        :param func: ``func(x, u) -> float``, given the block's state vector and
            its input port values at the probe point
        :param direction: ``+1`` fires on a rising zero crossing, ``-1`` on a
            falling one, ``0`` on either
        :param tag: identifies the detector, handed back to :meth:`crossing_event`
            when it fires; must not be ``None``

        A detector that is currently inactive should return a nonzero constant, not
        zero: solve_ivp counts a value of exactly zero at the start of an interval
        as a crossing.
        """
        if tag is None:
            raise ValueError("a crossing detector needs a tag")
        if not hasattr(simstate, "declare_crossing_event"):
            raise RuntimeError(
                f"{self.name} requires runtime support for zero-crossing detection"  # type: ignore[attr-defined]
            )

        def detector(t: float, y: Any) -> float:
            simstate.t = t
            simstate.count += 1
            # one shared propagation per probe point, however many detectors
            simstate.ensure_event_probe_evaluated(self.bd, t, y)  # type: ignore[attr-defined]
            x = self.bd._state_map[self]  # type: ignore[attr-defined]
            return float(func(x, self.inport_values))  # type: ignore[attr-defined]

        detector.terminal = True  # type: ignore[attr-defined]
        detector.direction = float(direction)  # type: ignore[attr-defined]
        detector.tag = tag  # type: ignore[attr-defined]
        simstate.declare_crossing_event(detector, self)

    def crossing_event(
        self,
        tag: Any,
        t_crossing: float,
        y_crossing: Any,
        state_map: dict[Any, Any],
        simstate: Any,
    ) -> None:
        """
        Respond to a detector firing.

        :param tag: the tag the detector was declared with
        :param t_crossing: time of the crossing
        :param y_crossing: continuous state vector of the whole diagram at the crossing
        :param state_map: block to state map, the diagram already evaluated at the
            crossing; write into ``state_map[self]`` to change this block's state
        :param simstate: the run's simulation state

        The solver restarts from the state map after this returns.
        """
        raise NotImplementedError(
            f"{type(self).__name__} declares crossings but does not implement crossing_event"
        )
