"""
Sampled-time blocks:

- have inputs and outputs
- have discrete-time state variables that are sampled/updated at the times
  specified by the associated clock
- are a subclass of ``SampledBlock`` |rarr| ``Block``
"""

from __future__ import annotations

import numpy as np
import math
from math import sin, cos, atan2, sqrt, pi

import inspect
from spatialmath import Twist3, SE3  # type: ignore[import-not-found]
import spatialmath.base as smb  # type: ignore[import-not-found]

from typing import Any

from bdsim.components import SampledBlock, Clock, SubsystemBlock, deprecated_block
from bdsim.blocks.continuous import _tf2ss

Vector1D = int | float | tuple[float, ...] | list[float] | np.ndarray

# ------------------------------------------------------------------------


class ZOH(SampledBlock):
    """
    :blockname:`ZOH`

    Zero-order hold.

    :inputs: 1
    :outputs: 1
    :states: N

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - 0
            - float, ndarray
            - :math:`x`
        *   - Output
            - 0
            - float, ndarray
            - :math:`y`

    Output is the input at the previous clock time $y_{k} = x_{k-1}.  The state can be a
    scalar or a vector, this is given by the type of ``x0``.

    .. note:: If input is not a scalar, ``x0`` must have the shape of the
        input signal.
    """

    nin = 1
    nout = 1

    def __init__(
        self, clock: Clock, x0: int | float | np.ndarray = 0, **blockargs: Any
    ) -> None:
        """
        :param clock: clock source
        :type clock: Clock
        :param x0: Initial value of the hold, defaults to 0
        :type x0: array_like, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        x0 = np.array(smb.getvector(x0), dtype=float).reshape(-1)
        self._x0 = x0
        ndstates = len(x0)

        super().__init__(nin=1, nout=1, ndstates=ndstates, clock=clock, **blockargs)

        # print('nstates', self.nstates)

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        # print('* output, x is ', self._x)
        return [x]

    def next(self, t: float, inputs: list[Any], x: np.ndarray) -> np.ndarray:
        u = smb.getvector(inputs[0])
        return u  # must be an ndarray


# ------------------------------------------------------------------------


class Integrator_S(SampledBlock):
    """
    :blockname:`INTEGRATOR_S`

    Discrete-time integrator.

    :inputs: 1
    :outputs: 1
    :states: N

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - 0
            - float, ndarray
            - :math:`x`
        *   - Output
            - 0
            - float, ndarray
            - :math:`y`

    Create a discrete-time integrator block.

    Output is the time integral of the input.  The state can be a scalar or a
    vector, this is given by the type of ``x0``.

    The minimum and maximum values can be:

        - a scalar, in which case the same value applies to every element of
          the state vector, or
        - a vector, of the same shape as ``x0`` that applies elementwise to
          the state.
    """

    nin = 1
    nout = 1

    def __init__(
        self,
        clock: Clock,
        x0: int | float | np.ndarray = 0,
        gain: float = 1.0,
        min: float | np.ndarray | None = None,
        max: float | np.ndarray | None = None,
        **blockargs: Any,
    ) -> None:
        """
        :param clock: clock source
        :type clock: Clock
        :param x0: Initial state, defaults to 0
        :type x0: array_like, optional
        :param gain: gain or scaling factor, defaults to 1
        :type gain: float
        :param min: Minimum value of state, defaults to None
        :type min: float or array_like, optional
        :param max: Maximum value of state, defaults to None
        :type max: float or array_like, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """

        if isinstance(x0, (int, float)):
            x0 = np.r_[x0]

        elif isinstance(x0, np.ndarray):
            if x0.ndim > 1:
                raise ValueError("state must be a 1D vector")
        else:
            x0 = smb.getvector(x0)

        x0 = np.array(x0, dtype=float).reshape(-1)
        ndstates = x0.shape[0]
        super().__init__(ndstates=ndstates, clock=clock, **blockargs)

        if min is not None:
            min = smb.getvector(min, ndstates)
        if max is not None:
            max = smb.getvector(max, ndstates)

        self._x0 = x0
        self.min = min
        self.max = max
        self.gain: float = gain

    def output(self, t: float, u: list[Any], x: np.ndarray) -> list[Any]:
        return [x]

    def next(self, t: float, u: list[Any], x: np.ndarray) -> np.ndarray:
        assert self._clock is not None
        xnext = x + self.gain * self._clock.T * np.array(u[0])
        if self.min is not None or self.max is not None:
            xnext = np.clip(xnext, self.min, self.max)
        return xnext


class PoseIntegrator_S(SampledBlock):
    r"""
    :blockname:`POSEINTEGRATOR_S`

    Discrete-time spatial velocity integrator.

    :inputs: 1
    :outputs: 1
    :states: 6

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - 0
            - ndarray(6,)
            - :math:`x`
        *   - Output
            - 0
            - SE3
            - :math:`y`

    This block integrates spatial velocity over time.
    The block input is a spatial velocity as a 6-vector
    :math:`(v_x, v_y, v_z, \omega_x, \omega_y, \omega_z)` and the output
    is pose as an ``SE3`` instance.

    .. note:: State is a velocity twist.
    """

    nin = 1
    nout = 1
    inlabels = ("ν",)
    outlabels = ("ξ",)

    def __init__(
        self,
        clock: Clock,
        x0: SE3 | Twist3 | np.ndarray | None = None,
        **blockargs: Any,
    ) -> None:
        r"""
        :param clock: clock source
        :type clock: Clock
        :param x0: Initial pose, defaults to null
        :type x0: SE3, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """

        if x0 is None:
            x0 = Twist3()
        elif isinstance(x0, SE3):
            x0 = Twist3(x0).A
        elif hasattr(x0, "A"):
            x0 = np.array(getattr(x0, "A"), dtype=float).reshape(-1)
        elif smb.isvector(x0, 6):
            x0 = smb.getvector(x0, 6)

        self.ndstates = 6
        super().__init__(ndstates=self.ndstates, clock=clock, **blockargs)

        self._x0 = x0

        # print("nstates", self.nstates, x0)

    def output(self, t: float, u: list[Any], x: np.ndarray) -> list[SE3]:
        return [Twist3(x).SE3()]

    def next(self, t: float, u: list[Any], x: np.ndarray) -> np.ndarray:
        assert self._clock is not None
        T_delta: SE3 = SE3.Delta(u[0] * self._clock.T)
        pose = Twist3(x).SE3() * T_delta
        return Twist3(pose).A


# ------------------------------------------------------------------------ #



        if D is None:
            D = np.zeros((nout, nin))
        elif len(D.shape) == 1:
            assert len(D) == nin * nout, "D must conform to B and C dimensions"
            D = D.reshape((nout, nin))
        else:
            assert D.shape == (nout, nin), "D must conform to B and C dimensions"

        self.A = A
        self.B = B
        self.C = C

        # if D is nonzero then we have feedthrough, which may create an algebraic loop, so flag this to the base class
        if np.any(D != 0):
            # flag we have feedthrough, which may create an algebraic loop
            self.D = D
            feedthrough = True
        else:
            self.D = None
            feedthrough = False

        super().__init__(clock=clock, x0=x0, feedthrough=feedthrough, **blockargs)

        if self.D is not None:
            return list(self.C @ x + self.D @ u)
        else:
            return list(self.C @ x)

            - The state-space matrices are available in the ``A``, ``B``, ``C``, and ``D`` attributes of the block.
            - If D is zero, then the block has no feedthrough and the D matrix is set to None. If D is nonzero, then the block has feedthrough and the D matrix is stored in the D attribute.
            - The ``_feedthrough`` attribute of the block is set to True if D is nonzero. This can be used to check for feedthrough without having to check the D matrix directly, and is used
              by the scheduler to ensure correct block evaluation order.

# ---------------------------------------------------------------------------
# Compatibility shims


@deprecated_block("Integrator_S")
class DIntegrator(Integrator_S):
    """Deprecated: use ``Integrator_S`` instead."""


@deprecated_block("PoseIntegrator_S")
class DPoseIntegrator(PoseIntegrator_S):
    """Deprecated: use ``PoseIntegrator_S`` instead."""


if __name__ == "__main__":  # pragma: no cover
    from pathlib import Path
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[3]
    test_file = (
        root / "tests" / "blocks" / f"test_blocks_{Path(__file__).stem.lower()}.py"
    )

    if not test_file.exists():
        print(f"No module unit tests found for {Path(__file__).name}: {test_file}")
        raise SystemExit(0)

    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", str(test_file)]))
