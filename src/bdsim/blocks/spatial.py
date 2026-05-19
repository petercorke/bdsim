from __future__ import annotations

import numpy as np
from typing import Any

try:
    from spatialmath import SE2, SE3, SO2, SO3, Twist3
    import spatialmath.base as smb

    sm = True
except:
    sm = False

from bdsim.components import ContinuousBlock, FunctionBlock, SampledBlock, Clock, deprecated_block

if sm:

    class Pose_postmul(FunctionBlock):
        r"""
        :blockname:`POSE_POSTMUL`

        Post multiply pose.

        :inputs: 1
        :outputs: 1
        :states: 0

        .. list-table::
            :header-rows: 1

            *   - Port type
                - Port number
                - Types
                - Description
            *   - Input
                - 0
                - SEn, SOn
                - :math:`\xi`
            *   - Output
                - 0
                - SEn, SOn
                - :math:`\xi \oplus \xi_c`

        Postmultiply the input pose by a constant pose.

        .. note:: Pose objects must be of the same type.

        :seealso: :class:`Pose_premul`
        """

        nin = 1
        nout = 1

        def __init__(self, pose: SO2 | SO3 | SE2 | SE3 | None = None, **blockargs: Any) -> None:
            """
            :param pose: pose to apply
            :type pose: SO2, SE2, SO3 or SE3
            :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
            :type blockargs: dict
            """
            if not isinstance(pose, (SO2, SO3, SE2, SE3)):
                raise ValueError("pose must be SO2, SE2, SO3 or SE3")

            super().__init__(**blockargs)
            self.pose = pose

        def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
            input = inputs[0]
            return [input * self.pose]

    # ------------------------------------------------------------------------ #

    class Pose_premul(FunctionBlock):
        r"""
        :blockname:`POSE_PREMUL`

        Pre multiply pose.

        :inputs: 1
        :outputs: 1
        :states: 0

        .. list-table::
            :header-rows: 1

            *   - Port type
                - Port number
                - Types
                - Description
            *   - Input
                - 0
                - SEn, SOn
                - :math:`\xi`
            *   - Output
                - 0
                - SEn, SOn
                - :math:`\xi_c \oplus \xi`

        Premultiply the input pose by a constant pose.

        .. note:: Pose objects must be of the same type.

        :seealso: :class:`Pose_postmul`
        """

        nin = 1
        nout = 1

        def __init__(self, pose: SO2 | SO3 | SE2 | SE3 | None = None, **blockargs: Any) -> None:
            """
            :param pose: pose to apply
            :type pose: SO2, SE2, SO3 or SE3
            :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
            :type blockargs: dict
            """
            if not isinstance(pose, (SO2, SO3, SE2, SE3)):
                raise ValueError("pose must be SO2, SE2, SO3 or SE3")

            super().__init__(**blockargs)
            self.pose = pose

        def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
            input = inputs[0]
            return [self.pose * input]

    # ------------------------------------------------------------------------ #

    class Transform_vector(FunctionBlock):
        r"""
        :blockname:`TRANSFORM_VECTOR`

        Transform a vector.

        :inputs: 2
        :outputs: 1
        :states: 0

        .. list-table::
            :header-rows: 1

            *   - Port type
                - Port number
                - Types
                - Description
            *   - Input
                - 0
                - SEn, SOn
                - :math:`\xi`
            *   - Input
                - 1
                - ndarray
                - :math:`v`, Euclidean 2D or 3D
            *   - Output
                - 0
                - ndarray
                - :math:`\xi \bullet v`

        Linearly transform the input vector by the input pose.
        """

        nin = 2
        nout = 1

        def __init__(self, **blockargs: Any) -> None:
            """
            :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
            :type blockargs: dict
            """
            super().__init__(nin=2, **blockargs)

        def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
            pose = inputs[0]
            if not isinstance(pose, (SO2, SO3, SE2, SE3)):
                raise ValueError("pose must be SO2, SE2, SO3 or SE3")
            return [pose * inputs[1]]

    # ------------------------------------------------------------------------ #

    class Pose_inverse(FunctionBlock):
        r"""
        :blockname:`POSE_INVERSE`

        Pose inverse.

        :inputs: 1
        :outputs: 1
        :states: 0

        .. list-table::
            :header-rows: 1

            *   - Port type
                - Port number
                - Types
                - Description
            *   - Input
                - 0
                - SEn, SOn
                - :math:`\xi`
            *   - Output
                - 0
                - SEn, SOn
                - :math:`\ominus \xi`

        Invert the pose on the input port.

        """

        nin = 1
        nout = 1

        def __init__(self, **blockargs: Any) -> None:
            """
            :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
            :type blockargs: dict
            """
            super().__init__(**blockargs)

        def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
            input = inputs[0]
            return [input.inv()]

    # ------------------------------------------------------------------------ #

    class PoseIntegrator(ContinuousBlock):
        r"""
        :blockname:`POSEINTEGRATOR`

        Continuous-time pose integrator

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

        This block integrates spatial velocity over time. The block input is a spatial
        velocity as a 6-vector :math:`(v_x, v_y, v_z, \omega_x, \omega_y, \omega_z)` and the
        output is pose as an ``SE3`` instance.

        .. note:: The state vector is a velocity twist.
        """

        nin = 1
        nout = 1

        def __init__(self, x0: SE3 | Twist3 | None = None, **blockargs: Any) -> None:
            r"""
            :param x0: Initial pose, defaults to null
            :type x0: SE3, Twist3, optional
            :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
            :type blockargs: dict
            """

            if x0 is None:
                _x0 = np.zeros((6,))
            elif isinstance(x0, SE3):
                _x0 = Twist3(x0).A
            elif isinstance(x0, Twist3):
                _x0 = x0.A

            nstates = len(_x0)

            super().__init__(nstates=nstates, **blockargs)

            self._x0 = _x0

        def output(self, t: float, u: list[Any], x: np.ndarray) -> list[SE3]:
            return [Twist3(x).SE3(1)]

        def deriv(self, t: float, u: list[Any], x: np.ndarray) -> Any:
            return u[0]

    # ------------------------------------------------------------------------ #

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
        inlabels = ("\u03bd",)
        outlabels = ("\u03be",)

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
            :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
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

            super().__init__(clock=clock, x0=x0, **blockargs)

        def output(self, t: float, u: list[Any], x: np.ndarray) -> list[SE3]:
            return [Twist3(x).SE3()]

        def next(self, t: float, u: list[Any], x: np.ndarray) -> np.ndarray:
            assert self._clock is not None
            T_delta: SE3 = SE3.Delta(u[0] * self._clock.T)
            pose = Twist3(x).SE3() * T_delta
            return Twist3(pose).A

    # ------------------------------------------------------------------------ #

    @deprecated_block("PoseIntegrator_S")
    class DPoseIntegrator(PoseIntegrator_S):
        r"""Deprecated: use ``PoseIntegrator_S`` instead."""


# ------------------------------------------------------------------------ #

if __name__ == "__main__":  # pragma: no cover
    from pathlib import Path
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[3]
    test_file = root / "tests" / "blocks" / f"test_blocks_{Path(__file__).stem.lower()}.py"

    if not test_file.exists():
        print(f"No module unit tests found for {Path(__file__).name}: {test_file}")
        raise SystemExit(0)

    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", str(test_file)]))
