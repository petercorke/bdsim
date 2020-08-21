import _penguin_pi_drivers as drivers
from ...components import block, SourceBlock, SinkBlock


@block
class PenguinPiDiffSteer(SinkBlock):
    """
    :blockname:`PenguinPiDiffSteer`
    
    .. table::
       :align: left
    
       +------------+---------+---------+
       | inputs     | outputs |  states |
       +------------+---------+---------+
       | 2          | 0       | 0       |
       +------------+---------+---------+
       | float      | 0       |         | 
       +------------+---------+---------+
    """

    PENGUINPI_STANDARD_WHEEL_RADIUS = 0.013 # 1.3 cm
    PENGUINPI_STANDARD_WHEEL_SEPARATION = 0.06 # 6 cm


    def __init__(self, *inputs,
        R=PENGUINPI_STANDARD_WHEEL_RADIUS, W=PENGUINPI_STANDARD_WHEEL_SEPARATION,
        **kwargs):

        r"""
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param R: Wheel radius, defaults to :py:const:`PENGUINPI_STANDARD_WHEEL_RADIUS`
        :type R: float, optional
        :param W: Wheel separation in lateral direction, defaults to :py:const:`PENGUINPI_STANDARD_WHEEL_SEPARATION`
        :type R: float, optional
        :param ``**kwargs``: common Block options
        :return: a DIFFDRIVE block
        :rtype: DifSteer instance
        
        Create an interface to PenguinPi motors. API mirrors theoretical DiffSteer model
        block defined by :py:class:`~bdsim.blocks.robots.DiffSteer`

        The block has two input ports:
            
            1. Left-wheel angular velocity (radians/sec).
            2. Right-wheel angular velocity (radians/sec).
        
        And no output ports, as it is a :py:class:`SinkBlock`.

        Note:
            - wheel velocity is defined such that if both are positive the PenguinPi
              moves forward.
        """
        SinkBlock.__init__(self)
        self.left_motor = drivers.Motor(drivers.AD_MOTOR_A)
        self.right_motor = drivers.Motor(drivers.AD_MOTOR_B)
    
    
    def step(self):
        self.left_motor.set_power(self.inputs[0])
        self.right_motor.set_power(self.inputs[1])


@block
class PenguinPiCamera(SourceBlock):
    """
    :blockname:`PenguinPiCamera`
    
    .. table::
       :align: left
    
       +------------+---------+---------+
       | inputs     | outputs |  states |
       +------------+---------+---------+
       | 2          | 0       | 0       |
       +------------+---------+---------+
       | float      | 0       |         | 
       +------------+---------+---------+
    """

    def __init__(self):
        