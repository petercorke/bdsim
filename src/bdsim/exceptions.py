"""Centralized exception types for bdsim runtime and block APIs."""

from __future__ import annotations

from typing import Any


class BDSimError(RuntimeError):
    """Base class for bdsim-specific runtime errors."""


class SimulationContextError(BDSimError):
    """Raised when runtime code is called outside an active simulation context."""


class IntegrationFailureError(BDSimError):
    """Raised when numerical integration fails for a simulation interval."""

    def __init__(
        self,
        *,
        t0: float,
        tf: float,
        status: int,
        message: str,
    ) -> None:
        super().__init__(
            "integration failed over interval "
            f"[{t0}, {tf}] with status '{status}': {message}"
        )
        self.t0 = t0
        self.tf = tf
        self.status = status
        self.message = message


class EventProbeOutsideIntervalError(BDSimError):
    """Raised when solve_ivp probes events outside the active interval.

    Sampled-state values are only well-defined between the last clock tick and
    the next scheduled boundary for the current interval.
    """

    def __init__(self, *, probe_t: float, t0: float, t1: float) -> None:
        super().__init__(
            "event probe time is outside the active integration interval: "
            f"t={probe_t} not in [{t0}, {t1}]; sampled states are indeterminable"
        )
        self.probe_t = probe_t
        self.t0 = t0
        self.t1 = t1


class BlockCreationError(BDSimError):
    """Raised when block construction fails via a runtime factory."""


class BlockApiError(TypeError):
    """Raised when a block class violates bdsim block API rules."""

    def __init__(self, *args: object, traceback: bool = True) -> None:
        super().__init__(*args)
        self.traceback = traceback


class BlockRuntimeError(RuntimeError):
    """Raised when execution of a block callback fails at runtime."""

    def __init__(
        self,
        *,
        operation: str,
        block: Any,
        cause: Exception,
        t: float | None = None,
        inputs: Any = None,
        state: Any = None,
    ) -> None:
        super().__init__(f"{operation} failed for block {block}")
        self.operation = operation
        self.block = block
        self.cause = cause
        self.t = t
        self.inputs = inputs
        self.state = state
