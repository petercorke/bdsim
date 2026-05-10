"""Per-run context and job wrappers shared by simulation runners."""

from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bdsim.components import OptionsBase, SimulationState
    from bdsim.run_sim import Progress


@dataclass(slots=True)
class SimulationContext:
    """Per-run execution context for a single block diagram simulation."""

    bd: Any
    simstate: SimulationState
    options: OptionsBase
    progress: Progress | None = None
    threaded: bool = False


class SimulationJob:
    """Thin wrapper around a submitted simulation future."""

    def __init__(self, future: Future) -> None:
        self._future = future

    def done(self) -> bool:
        return self._future.done()

    def wait(self, timeout: float | None = None) -> None:
        self._future.result(timeout=timeout)

    def result(self, timeout: float | None = None) -> Any:
        return self._future.result(timeout=timeout)

    def cancel(self) -> bool:
        return self._future.cancel()

    def exception(self, timeout: float | None = None) -> BaseException | None:
        return self._future.exception(timeout=timeout)
