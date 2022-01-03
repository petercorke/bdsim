try:
    from spatialmath import SE2, SE3
    sm = True
except:
    sm = False

from bdsim.components import FunctionBlock

if sm:

    class Pose_postmul(FunctionBlock):
        """
        :blockname:`POSE_POSTMUL`
        
        .. table::
        :align: left
        
        +------------+---------+---------+
        | inputs     | outputs |  states |
        +------------+---------+---------+
        | 1          | 1       | 0       |
        +------------+---------+---------+
        | SE3        | SE3     |         | 
        +------------+---------+---------+
        """

        nin = 1
        nout = 1

        def __init__(self, pose=None, **blockargs):
            """
            Post multiply pose.

            :param pose: The pose
            :type pose: SE3 or SE2
            :param blockargs: |BlockOptions|
            :type blockargs: dict
            :return: A POSE_POSTMUL block
            :rtype: Pose_postmul instance
            
            Transform the pose on the input signal by post multiplication.

            For example::

                gain = bd.POSE_POSTMUL(SE3())
            """
            if not isinstance(pose, (SE2, SE3)):
                raise ValueError('post must be SE2 or SE3')

            super().__init__(**blockargs)
            self.pose  = pose
            
        def output(self, t=None):
            return [self.inputs[0] * self.pose]
        
# ------------------------------------------------------------------------ #


    class Pose_premul(FunctionBlock):
        """
        :blockname:`POSE_PREMUL`
        
        .. table::
        :align: left
        
        +------------+---------+---------+
        | inputs     | outputs |  states |
        +------------+---------+---------+
        | 1          | 1       | 0       |
        +------------+---------+---------+
        | SE3        | SE3     |         | 
        +------------+---------+---------+
        """

        nin = 1
        nout = 1

        def __init__(self, pose=None, **blockargs):
            """
            Pre multiply pose.

            :param pose: The gain value
            :type pose: SE3 or SE2
            :param blockargs: |BlockOptions|
            :type blockargs: dict
            :return: A POSE_PREMUL block
            :rtype: Pose_premul instance
            
            Transform the pose on the input signal by premultiplication.

            For example::

                gain = bd.POSE_POSTMUL(SE3())
            """
            if not isinstance(pose, (SE2, SE3)):
                raise ValueError('post must be SE2 or SE3')

            super().__init__(**blockargs)
            self.pose  = pose
            
        def output(self, t=None):            
            return [self.pose * self.inputs[0]]

# ------------------------------------------------------------------------ #


    class Transform_vector(FunctionBlock):
        """
        :blockname:`TRANSFORM_VECTOR`
        
        .. table::
        :align: left
        
        +------------+---------+---------+
        | inputs     | outputs |  states |
        +------------+---------+---------+
        | 1          | 1       | 0       |
        +------------+---------+---------+
        | SE3        | SE3     |         | 
        +------------+---------+---------+
        """

        nin = 2
        nout = 1

        def __init__(self, **blockargs):
            """
            Pre multiply pose.

            :param blockargs: |BlockOptions|
            :type blockargs: dict
            :return: A TRANSFORM_VECTOR block
            :rtype: Transform_vector instance
            
            Transform the vector on the input signal by the pose.

            For example::

                gain = bd.POSE_POSTMUL(SE3())
            """
            if not isinstance(pose, (SE2, SE3)):
                raise ValueError('post must be SE2 or SE3')

            super().__init__(nin=2, **blockargs)
            
        def output(self, t=None):            
            return [self.inputs[0] * self.inputs[1]]
        
# ------------------------------------------------------------------------ #


    class Pose_inverse(FunctionBlock):
        """
        :blockname:`POSE_INVERSE`
        
        .. table::
        :align: left
        
        +------------+---------+---------+
        | inputs     | outputs |  states |
        +------------+---------+---------+
        | 1          | 1       | 0       |
        +------------+---------+---------+
        | SE3        | SE3     |         | 
        +------------+---------+---------+
        """

        nin = 1
        nout = 1

        def __init__(self, **blockargs):
            """
            Pose inverse.

            :param blockargs: |BlockOptions|
            :type blockargs: dict
            :return: A POSE_INVERSE block
            :rtype: Pose_inverse instance
            
            Transform the pose on the input signal.

            For example::

                gain = bd.POSE_POSTMUL(SE3())
            """
            super().__init__(**blockargs)
            
        def output(self, t=None):            
            return [self.inputs[0].inv()]
        
# ------------------------------------------------------------------------ #