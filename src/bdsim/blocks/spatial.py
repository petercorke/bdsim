try:
    from spatialmath import SE2, SE3, SO2, SO3

    sm = True
except:
    sm = False

from bdsim.components import FunctionBlock

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

        def __init__(self, pose=None, **blockargs):
            """
            :param pose: pose to apply
            :type pose: SO2, SE2, SO3 or SE3
            :param blockargs: |BlockOptions|
            :type blockargs: dict
            """
            if not isinstance(pose, (SO2, SO3, SE2, SE3)):
                raise ValueError("pose must be SO2, SE2, SO3 or SE3")

            super().__init__(**blockargs)
            self.pose = pose

        def output(self, t, inports, x):
            input = inports[0]
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

        def __init__(self, pose=None, **blockargs):
            """
            :param pose: pose to apply
            :type pose: SO2, SE2, SO3 or SE3
            :param blockargs: |BlockOptions|
            :type blockargs: dict
            """
            if not isinstance(pose, (SO2, SO3, SE2, SE3)):
                raise ValueError("pose must be SO2, SE2, SO3 or SE3")

            super().__init__(**blockargs)
            self.pose = pose

        def output(self, t, inports, x):
            input = inports[0]
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

        def __init__(self, **blockargs):
            """
            :param blockargs: |BlockOptions|
            :type blockargs: dict
            """
            super().__init__(nin=2, **blockargs)

        def output(self, t, inports, x):
            pose = inports[0]
            if not isinstance(pose, (SO2, SO3, SE2, SE3)):
                raise ValueError("pose must be SO2, SE2, SO3 or SE3")
            return [pose * inports[1]]

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

        def __init__(self, **blockargs):
            """
            :param blockargs: |BlockOptions|
            :type blockargs: dict
            """
            super().__init__(**blockargs)

        def output(self, t, inports, x):
            input = inports[0]
            return [input.inv()]


# ------------------------------------------------------------------------ #

if __name__ == "__main__":  # pragma: no cover

    from pathlib import Path

    exec(open(Path(__file__).parent.parent.parent / "tests" / "test_spatial.py").read())
