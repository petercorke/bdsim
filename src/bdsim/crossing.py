"""
Zero-crossing events for blocks with discontinuities.

A block that changes behaviour when a signal crosses a threshold (a limited
integrator reaching its limit, a saturation, a dead band) must not let the
solver step over the corner.  It registers one scalar *detector* per threshold
and solve_ivp root-finds each one.  :class:`CrossingMixin` holds the boilerplate
so that a block only supplies the scalar function and the response.
"""

from __future__ import annotations

from typing import Any, Callable, Sequence

import numpy as np

# A signal exactly on a threshold counts as being above it.  Otherwise a signal that
# dwells on a threshold, such as an integrator held at a limit feeding a CLIP with
# the same limit, would read as a crossing at every restart.
_ABOVE = 1e-300


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
        func: Callable[[np.ndarray, list[Any], bool], float],
        direction: float,
        tag: Any,
    ) -> None:
        """
        Register one terminal scalar detector.

        :param simstate: the run's simulation state, as passed to ``start``
        :param func: ``func(x, u, at_start) -> float``, given the block's state
            vector, its input port values at the probe point, and whether the
            probe is the first point of the solver interval
        :param direction: ``+1`` fires on a rising zero crossing, ``-1`` on a
            falling one, ``0`` on either
        :param tag: identifies the detector, handed back to :meth:`crossing_event`
            when it fires; must not be ``None``

        A detector that is currently inactive should return a nonzero constant, not
        zero: solve_ivp counts a value of exactly zero at the start of an interval
        as a crossing.

        The solver reports only the earliest of several simultaneous crossings and
        restarts just beyond it, so another detector may by then be past its
        threshold and would never fire.  At the start of an interval, and only
        there, a detector that is already past its threshold in its direction
        should return exactly zero, which reports the crossing at once.  Elsewhere
        it must return the true value, or the root is found at the step end and
        not at the crossing.
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
            # stateless blocks have no entry in the state map
            x = self.bd._state_map.get(self, np.empty(0))  # type: ignore[attr-defined]
            return float(
                func(
                    x,
                    self.inport_values,  # type: ignore[attr-defined]
                    simstate.at_event_interval_start(t),
                )
            )

        detector.terminal = True  # type: ignore[attr-defined]
        detector.direction = float(direction)  # type: ignore[attr-defined]
        detector.tag = tag  # type: ignore[attr-defined]
        simstate.declare_crossing_event(detector, self)

    def signal_size(self, port: int = 0) -> int:
        """
        Number of elements in the signal on an input port.

        :param port: input port index, defaults to 0
        :return: 1 for a scalar, the size of an array otherwise; 1 if the diagram
            has not been compiled with evaluation, so the signal is unknown
        """
        sig = self.insig[port]  # type: ignore[attr-defined]
        if sig is None or sig.shape is None:
            return 1
        return int(np.prod(sig.shape))

    def declare_thresholds(
        self,
        simstate: Any,
        thresholds: Sequence[tuple[int, float]],
        port: int = 0,
    ) -> None:
        """
        Break the solver step wherever an input signal crosses a threshold.

        :param simstate: the run's simulation state, as passed to ``start``
        :param thresholds: ``(element, value)`` pairs; infinite values are skipped
        :param port: input port whose signal is watched, defaults to 0

        For a stateless block whose output is continuous but whose slope jumps
        (CLIP, DEADBAND, ABS) or whose output jumps (SIGN) at a threshold.  Nothing
        changes at the crossing: the point is that the solver restarts exactly
        there, so no step straddles the corner.  Crossings in either direction
        are found, and a signal exactly on a threshold counts as above it.

        Several thresholds crossed at the same instant are harmless: the restart
        is just beyond the earliest, and the others lie within that gap.
        """
        if not hasattr(simstate, "declare_crossing_event"):
            return  # a refinement only: runtimes without detectors lose accuracy, not correctness
        for element, value in thresholds:
            if not np.isfinite(value):
                continue
            self.declare_crossing(
                simstate,
                self._threshold_detector(element, float(value), port),
                0,
                ("threshold", element, float(value)),
            )

    @staticmethod
    def _threshold_detector(
        element: int, value: float, port: int
    ) -> Callable[[np.ndarray, list[Any], bool], float]:
        def detector(x: np.ndarray, u: list[Any], at_start: bool) -> float:
            g = float(np.atleast_1d(u[port])[element]) - value
            return g if g != 0.0 else _ABOVE

        return detector

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

        The default does nothing for the threshold crossings declared by
        :meth:`declare_thresholds` and raises for anything else.
        """
        if isinstance(tag, tuple) and tag and tag[0] == "threshold":
            return
        raise NotImplementedError(
            f"{type(self).__name__} declares crossings but does not implement crossing_event"
        )
