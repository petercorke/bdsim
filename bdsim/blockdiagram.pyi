from spatialmath.base.types import *
import numpy as np
import math

class BlockDiagram:


    # bdsim.blocks.functions.Sum
    def SUM(self, signs: str = '++', mode: str = None, **blockargs):
        """
        :param signs: signs associated with input ports, accepted characters: + or -, defaults to "++"
        :type signs: str, optional
        :param mode: controls addition mode, per element, string comprises ``r`` or ``c`` or ``C`` or ``L``, defaults to None
        :type mode: str, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict

        ``mode`` controls how elements of the input vectors are added/subtracted.
        Elements which are angles must be treated specially, and this is indicated by
        the corresponding characters in ``mode``.  The string's length must equal the
        width of the input vectors. The characters of the string can be:

        ==============  ============================================
        mode character  purpose
        ==============  ============================================
        r               real number, don't wrap (default)
        c               angle on circle, wrap to [-π, π)
        C               angle on circle, wrap to [0, 2π)
        L               colatitude angle, wrap to [0, π]
        ==============  ============================================

        For example if ``mode="rc"`` then a 2-element array would have its
        second element wrapped to the range [-π, π).

        
        """
        ...


    # bdsim.blocks.functions.Prod
    def PROD(self, ops: str = '**', matrix: bool = False, **blockargs):
        """
        :param ops: operations associated with input ports, accepted characters: * or /, defaults to '**'
        :type ops: str, optional
        :param inputs: Optional incoming connections
        :type inputs: Block or Plug
        :param matrix: Arguments are matrices, defaults to False
        :type matrix: bool, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict

        
        """
        ...


    # bdsim.blocks.functions.Gain
    def GAIN(self, K: Union[int, float, numpy.ndarray] = 1, premul: bool = False, **blockargs):
        """
        :param K: The gain value, defaults to 1
        :type K: scalar, array_like
        :param premul: premultiply by constant, default is postmultiply, defaults to False
        :type premul: bool, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict

        
        """
        ...


    # bdsim.blocks.functions.Pow
    def POW(self, p: Union[int, float] = 1, matrix: bool = False, **blockargs):
        """
        :param p: The exponent value, defaults to 1
        :type p: scalar
        :param matrix: premultiply by constant, default is postmultiply, defaults to False
        :type matrix: bool, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict

        
        """
        ...


    # bdsim.blocks.functions.Clip
    def CLIP(self, min: Union[numpy.ndarray, int, float, list, tuple] = -inf, max: Union[numpy.ndarray, int, float, list, tuple] = inf, **blockargs):
        """
        :param min: Minimum value, defaults to -math.inf
        :type min: scalar or array_like, optional
        :param max: Maximum value, defaults to math.inf
        :type max: float or array_like, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.functions.Function
    def FUNCTION(self, func: Callable = None, nin: int = 1, nout: int = 1, persistent: bool = False, fargs: list = None, fkwargs: dict = None, **blockargs):
        """
        :param func: function or lambda, or list thereof, defaults to None
        :type func: callable or sequence of callables, optional
        :param nin: number of inputs, defaults to 1
        :type nin: int, optional
        :param nout: number of outputs, defaults to 1
        :type nout: int, optional
        :param persistent: pass in a reference to a dictionary instance to hold persistent state, defaults to False
        :type persistent: bool, optional
        :param fargs: extra positional arguments passed to the function, defaults to []
        :type fargs: list, optional
        :param fkwargs: extra keyword arguments passed to the function, defaults to {}
        :type fkwargs: dict, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict, optional
        
        """
        ...


    # bdsim.blocks.functions.Interpolate
    def INTERPOLATE(self, x: Union[list, tuple, numpy.ndarray] = None, y: Union[list, tuple, numpy.ndarray] = None, xy: numpy.ndarray = None, time: bool = False, kind: str = 'linear', **blockargs):
        """
        :param x: x-values of function, defaults to None
        :type x: array_like, shape (N,) optional
        :param y: y-values of function, defaults to None
        :type y: array_like, optional
        :param xy: combined x- and y-values of function, defaults to None
        :type xy: array_like, optional
        :param time: x new is simulation time, defaults to False
        :type time: bool, optional
        :param kind: interpolation method, defaults to 'linear'
        :type kind: str, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.sources.Constant
    def CONSTANT(self, value=0, **blockargs):
        """
        :param value: the constant, defaults to 0
        :type value: any, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.sources.Time
    def TIME(self, value=None, **blockargs):
        """
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.sources.WaveForm
    def WAVEFORM(self, wave='square', freq=1, unit='Hz', phase=0, amplitude=1, offset=0, min=None, max=None, duty=0.5, **blockargs):
        """
        :param wave: type of waveform to generate, one of: 'sine', 'square' [default], 'triangle'
        :type wave: str, optional
        :param freq: frequency, defaults to 1
        :type freq: float, optional
        :param unit: frequency unit, one of: 'rad/s', 'Hz' [default]
        :type unit: str, optional
        :param amplitude: amplitude, defaults to 1
        :type amplitude: float, optional
        :param offset: signal offset, defaults to 0
        :type offset: float, optional
        :param phase: Initial phase of signal in the range [0,1], defaults to 0
        :type phase: float, optional
        :param min: minimum value, defaults to None
        :type min: float, optional
        :param max: maximum value, defaults to None
        :type max: float, optional
        :param duty: duty cycle for square wave in range [0,1], defaults to 0.5
        :type duty: float, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict

        
        """
        ...


    # bdsim.blocks.sources.Piecewise
    def PIECEWISE(self, *args, seq=None, **blockargs):
        """
        :param seq: sequence of time, value pairs
        :type seq: list of 2-element iterables
        :param blockargs: |BlockOptions|
        :type blockargs: dict

        
        """
        ...


    # bdsim.blocks.sources.Step
    def STEP(self, T=1, off=0, on=1, **blockargs):
        """
        :param T: time of step, defaults to 1
        :type T: float, optional
        :param off: initial value, defaults to 0
        :type off: float, optional
        :param on: final value, defaults to 1
        :type on: float, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.sources.Ramp
    def RAMP(self, T=1, off=0, slope=1, **blockargs):
        """
        :param T: time of ramp start, defaults to 1
        :type T: float, optional
        :param off: initial value, defaults to 0
        :type off: float, optional
        :param slope: gradient of slope, defaults to 1
        :type slope: float, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.sinks.Print
    def PRINT(self, fmt=None, file=None, **blockargs):
        """
        :param fmt: Format string, defaults to None
        :type fmt: str, optional
        :param file: file to write data to, defaults to None
        :type file: file object, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A PRINT block
        :rtype: Print instance
        
        """
        ...


    # bdsim.blocks.sinks.Stop
    def STOP(self, func=None, **blockargs):
        """
        :param func: evaluate stop condition, defaults to None
        :type func: callable, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.sinks.Null
    def NULL(self, nin=1, **blockargs):
        """
        :param nin: number of input ports, defaults to 1
        :type nin: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.sinks.Watch
    def WATCH(self, **blockargs):
        """
        :param nin: number of input ports, defaults to 1
        :type nin: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.transfers.Integrator
    def INTEGRATOR(self, x0=0, gain=1.0, min=None, max=None, enable=None, **blockargs):
        """
        :param x0: Initial state, defaults to 0
        :type x0: array_like, optional
        :param gain: gain or scaling factor, defaults to 1
        :type gain: float
        :param min: Minimum value of state, defaults to None
        :type min: float or array_like, optional
        :param max: Maximum value of state, defaults to None
        :type max: float or array_like, optional
        :param enable: enable or disable integration
        :type enable: callable
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.transfers.PoseIntegrator
    def POSEINTEGRATOR(self, x0=None, **blockargs):
        """
        :param x0: Initial pose, defaults to null
        :type x0: SE3, Twist3, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.transfers.LTI_SS
    def LTI_SS(self, A=None, B=None, C=None, x0=None, **blockargs):
        """
        :param N: numerator coefficients, defaults to 1
        :type N: array_like, optional
        :param D: denominator coefficients, defaults to [1,1]
        :type D: array_like, optional
        :param x0: initial states, defaults to None
        :type x0: array_like, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.transfers.LTI_SISO
    def LTI_SISO(self, N=1, D=[1, 1], x0=None, **blockargs):
        """
        :param N: numerator coefficients, defaults to 1
        :type N: array_like, optional
        :param D: denominator coefficients, defaults to [1,1]
        :type D: array_like, optional
        :param x0: initial states, defaults to None
        :type x0: array_like, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: LTI_SISO block
        :rtype: ``LTI_SISO`` instance
        
        """
        ...


    # bdsim.blocks.connections.SubSystem
    def SUBSYSTEM(self, subsys, nin=1, nout=1, **blockargs):
        """
        :param subsys: Subsystem as either a filename or a ``BlockDiagram`` instance
        :type subsys: str or BlockDiagram
        :param nin: Number of input ports, defaults to 1
        :type nin: int, optional
        :param nout: Number of output ports, defaults to 1
        :type nout: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :raises ImportError: DESCRIPTION
        :raises ValueError: DESCRIPTION
        
        """
        ...


    # bdsim.blocks.transfers.Deriv
    def DERIV(self, alpha, x0=0, y0=None, **blockargs):
        """
        :param alpha: filter pole in units of rad/s
        :type alpha: float
        :param x0: initial states, defaults to 0
        :type x0: array_like, optional
        :param y0: inital outputs
        :type y0: array_like
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.transfers.PID
    def PID(self, type: str = 'PID', P: float = 0.0, D: float = 0.0, I: float = 0.0, D_pole=1, I_limit=None, I_band=0, **blockargs):
        """
        :param type: the controller type, defaults to "PID"
        :type type: str, optional
        :param P: proportional gain, defaults to 0
        :type P: float
        :param D: derivative gain, defaults to 0
        :type D: float
        :param I: integral gain, defaults to 0
        :type I: float
        :param D_pole: filter pole for derivative estimate, defaults to 1 rad/s
        :type D_pole: float
        :param I_limit: integral limit
        :type I_limit: float or 2-tuple
        :param I_band: band within which integral action is active
        :type I_band: float
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.discrete.ZOH
    def ZOH(self, clock, x0=0, **blockargs):
        """
        :param clock: clock source
        :type clock: Clock
        :param x0: Initial value of the hold, defaults to 0
        :type x0: array_like, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.discrete.DIntegrator
    def DINTEGRATOR(self, clock, x0=0, gain=1.0, min=None, max=None, **blockargs):
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
        ...


    # bdsim.blocks.discrete.DPoseIntegrator
    def DPOSEINTEGRATOR(self, clock, x0=None, **blockargs):
        """
        :param clock: clock source
        :type clock: Clock
        :param x0: Initial pose, defaults to null
        :type x0: SE3, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.linalg.Inverse
    def INVERSE(self, pinv=False, **blockargs):
        """
        :param pinv: force pseudo inverse, defaults to False
        :type pinv: bool, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.linalg.Transpose
    def TRANSPOSE(self, **blockargs):
        """
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.linalg.Norm
    def NORM(self, ord=None, axis=None, **blockargs):
        """
        :param axis: specifies the axis along which to compute the vector norms, defaults to None.
        :type axis: int, optional
        :param ord: Order of the norm, default to None.
        :type ord: int or str
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.linalg.Flatten
    def FLATTEN(self, order='C', **blockargs):
        """
        :param order: flattening order, either "C" or "F", defaults to "C"
        :type order: str
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.linalg.Slice2
    def SLICE2(self, rows=None, cols=None, **blockargs):
        """
        :param rows: row selection, defaults to None
        :type rows: tuple(3) or list
        :param cols: column selection, defaults to None
        :type cols: tuple(3) or list
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.linalg.Slice1
    def SLICE1(self, index, **blockargs):
        """
        :param index: slice, defaults to None
        :type index: tuple(3)
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.linalg.Det
    def DET(self, **blockargs):
        """
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.linalg.Cond
    def COND(self, **blockargs):
        """
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.displays.Scope
    def SCOPE(self, nin=1, vector=None, styles=None, stairs=False, scale='auto', labels=None, grid=True, watch=False, title=None, loc='best', **blockargs):
        """
        :param nin: number of inputs, defaults to 1 or if given, the length of
                    style vector
        :type nin: int, optional
        :param vector: vector signal on single input port, defaults to None
        :type vector: int or list, optional
        :param styles: styles for each line to be plotted
        :type styles: str or dict, list of strings or dicts; one per line, optional
        :param stairs: force staircase style plot for all lines, defaults to False
        :type stairs: bool, optional
        :param scale: fixed y-axis scale or defaults to 'auto'
        :type scale: str or array_like(2)
        :param labels: vertical axis labels
        :type labels: sequence of strings
        :param grid: draw a grid, defaults to True. Can be boolean or a tuple of
                     options for grid()
        :type grid: bool or sequence
        :param watch: add these signals to the watchlist, defaults to False
        :type watch: bool, optional
        :param title: title of plot
        :type title: str
        :param loc: location of legend, see :meth:`matplotlib.pyplot.legend`, defaults to "best"
        :type loc: str
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.displays.ScopeXY
    def SCOPEXY(self, style=None, scale='auto', aspect='equal', labels=['X', 'Y'], init=None, nin=2, **blockargs):
        """
        :param style: line style, defaults to None
        :type style: optional str or dict
        :param scale: fixed y-axis scale or defaults to 'auto'
        :type scale: str or array_like(2) or array_like(4)
        :param labels: axis labels (xlabel, ylabel), defaults to ["X","Y"]
        :type labels: 2-element tuple or list
        :param init: function to initialize the graphics, defaults to None
        :type init: callable
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.displays.ScopeXY1
    def SCOPEXY1(self, indices=[0, 1], **blockargs):
        """
        :param indices: indices of elements to select from block input vector, defaults to [0,1]
        :type indices: array_like(2)
        :param style: line style
        :type style: optional str or dict
        :param scale: fixed y-axis scale or defaults to 'auto'
        :type scale: str or array_like(2) or array_like(4)
        :param labels: axis labels (xlabel, ylabel)
        :type labels: 2-element tuple or list
        :param init: function to initialize the graphics, defaults to None
        :type init: callable
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.connections.Item
    def ITEM(self, item, **blockargs):
        """
        :param item: name of dictionary item
        :type item: str
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.connections.Dict
    def DICT(self, keys, **blockargs):
        """
        :param keys: list of dictionary keys
        :type keys: list
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.connections.Mux
    def MUX(self, nin=1, **blockargs):
        """
        :param nin: Number of input ports, defaults to 1
        :type nin: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.connections.DeMux
    def DEMUX(self, nout=1, **blockargs):
        """
        :param nout: number of outputs, defaults to 1
        :type nout: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.connections.Index
    def INDEX(self, index=[], **blockargs):
        """
        Index an iterable signal.

        :param index: elements of input array, defaults to []
        :type index: list, slice or str, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.connections.InPort
    def INPORT(self, nout=1, **blockargs):
        """
        :param nout: Number of output ports, defaults to 1
        :type nout: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.connections.OutPort
    def OUTPORT(self, nin=1, **blockargs):
        """
        :param nin: Number of input ports, defaults to 1
        :type nin: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # bdsim.blocks.spatial.Pose_postmul
    def POSE_POSTMUL(self, pose=None, **blockargs):
        """
            :param pose: pose to apply
            :type pose: SO2, SE2, SO3 or SE3
            :param blockargs: |BlockOptions|
            :type blockargs: dict
            
        """
        ...


    # bdsim.blocks.spatial.Pose_premul
    def POSE_PREMUL(self, pose=None, **blockargs):
        """
            :param pose: pose to apply
            :type pose: SO2, SE2, SO3 or SE3
            :param blockargs: |BlockOptions|
            :type blockargs: dict
            
        """
        ...


    # bdsim.blocks.spatial.Transform_vector
    def TRANSFORM_VECTOR(self, **blockargs):
        """
            :param blockargs: |BlockOptions|
            :type blockargs: dict
            
        """
        ...


    # bdsim.blocks.spatial.Pose_inverse
    def POSE_INVERSE(self, **blockargs):
        """
            :param blockargs: |BlockOptions|
            :type blockargs: dict
            
        """
        ...


    # bdsim.blocks.io.DOUT
    def DOUT(self, pin=0, **blockargs):
        """
        Constant value.

        :param value: the constant, defaults to 0
        :type value: any, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a CONSTANT block
        :rtype: Constant instance

        This block has only one output port, but the value can be any
        Python type, for example float, list or Numpy ndarray.
        
        """
        ...


    # roboticstoolbox.blocks.arm.FKine
    def FKINE(self, robot=None, args={}, **blockargs):
        """
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param robot: Robot model, defaults to None
        :type robot: Robot subclass, optional
        :param args: Options for fkine, defaults to {}
        :type args: dict, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.arm.IKine
    def IKINE(self, robot=None, q0=None, useprevious=True, ik=None, args={}, seed=None, **blockargs):
        """
        :param robot: Robot model, defaults to None
        :type robot: Robot subclass, optional
        :param q0: Initial joint angles, defaults to None
        :type q0: array_like(n), optional
        :param useprevious: Use previous IK solution as q0, defaults to True
        :type useprevious: bool, optional
        :param ik: Specify an IK function, defaults to "LM"
        :type ik: str
        :param args: Options passed to IK function
        :type args: dict
        :param seed: random seed for solution
        :type seed: int
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.arm.Jacobian
    def JACOBIAN(self, robot, frame='0', representation=None, inverse=False, pinv=False, damping=None, transpose=False, **blockargs):
        """
        :param robot: Robot model
        :type robot: Robot subclass
        :param frame: Frame to compute Jacobian for, one of: "0" [default], "e"
        :type frame: str, optional
        :param representation: representation for analytical Jacobian
        :type representation: str, optional
        :param inverse: output inverse of Jacobian, defaults to False
        :type inverse: bool, optional
        :param pinv: output pseudo-inverse of Jacobian, defaults to False
        :type pinv: bool, optional
        :param damping: damping term for inverse, defaults to None
        :type damping: float or array_like(N)
        :param transpose: output transpose of Jacobian, defaults to False
        :type transpose: bool, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict

        If an inverse is requested and ``damping`` is not None it is added to the
        diagonal of the Jacobian prior to the inversion.  If a scalar is provided it is
        added to each element of the diagonal, otherwise an N-vector is assumed.

        .. note::
            - Only one of ``inverse`` or ``pinv`` can be True
            - ``inverse`` or ``pinv`` can be used in conjunction with ``transpose``
            - ``inverse`` requires that the Jacobian is square
            - If ``inverse`` is True and the Jacobian is singular a runtime
              error will occur.
        
        """
        ...


    # roboticstoolbox.blocks.arm.ArmPlot
    def ARMPLOT(self, robot=None, q0=None, backend=None, **blockargs):
        """
        :param robot: Robot model
        :type robot: Robot subclass
        :param q0: initial joint angles, defaults to None
        :type q0: ndarray(N)
        :param backend: RTB backend name, defaults to 'pyplot'
        :type backend: str, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.arm.JTraj
    def JTRAJ(self, q0, qf, qd0=None, qdf=None, T=None, **blockargs):
        """

        :param q0: initial joint coordinate
        :type q0: array_like(n)
        :param qf: final joint coordinate
        :type qf: array_like(n)
        :param T: time vector or number of steps, defaults to None
        :type T: array_like or int, optional
        :param qd0: initial velocity, defaults to None
        :type qd0: array_like(n), optional
        :param qdf: final velocity, defaults to None
        :type qdf: array_like(n), optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.arm.CTraj
    def CTRAJ(self, T1, T2, T, trapezoidal=True, **blockargs):
        """
        :param T1: initial pose
        :type T1: SE3
        :param T2: final pose
        :type T2: SE3
        :param T: motion time
        :type T: float
        :param trapezoidal: Use LSPB motion profile along the path
        :type trapezoidal: bool
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.arm.CirclePath
    def CIRCLEPATH(self, radius=1, centre=(0, 0, 0), pose=None, frequency=1, unit='rps', phase=0, **blockargs):
        """
        :param radius: radius of circle, defaults to 1
        :type radius: float
        :param centre: center of circle, defaults to [0,0,0]
        :type centre: array_like(3)
        :param pose: SE3 pose of output, defaults to None
        :type pose: SE3
        :param frequency: rotational frequency, defaults to 1
        :type frequency: float
        :param unit: unit for frequency, one of: 'rps' [default], 'rad'
        :type unit: str
        :param phase: phase
        :type phase: float
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.arm.Trapezoidal
    def TRAPEZOIDAL(self, q0, qf, V=None, T=None, **blockargs):
        """
        Compute a joint-space trajectory

        :param q0: initial joint coordinate
        :type q0: float
        :param qf: final joint coordinate
        :type qf: float
        :param T: maximum time, defaults to None
        :type T: float, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict

        If ``T`` is given the value ``qf`` is reached at this time.  This can be
        less or greater than the simulation time.
        
        """
        ...


    # roboticstoolbox.blocks.arm.Traj
    def TRAJ(self, y0=0, yf=1, T=None, time=False, traj='trapezoidal', **blockargs):
        """
        :param y0: initial value, defaults to 0
        :type y0: array_like(m), optional
        :param yf: final value, defaults to 1
        :type yf: array_like(m), optional
        :param T: maximum time, defaults to None
        :type T: float, optional
        :param time: x is simulation time, defaults to False
        :type time: bool, optional
        :param traj: trajectory type, one of: 'trapezoidal' [default], 'quintic'
        :type traj: str, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.arm.IDyn
    def IDYN(self, robot, gravity=None, **blockargs):
        """
        :param robot: Robot model
        :type robot: Robot subclass
        :param gravity: gravitational acceleration
        :type gravity: float
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.arm.Gravload
    def GRAVLOAD(self, robot, gravity=None, **blockargs):
        """
        :param robot: Robot model
        :type robot: Robot subclass
        :param gravity: gravitational acceleration
        :type gravity: float
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.arm.Gravload_X
    def GRAVLOAD_X(self, robot, representation='rpy/xyz', gravity=None, **blockargs):
        """
        :param robot: Robot model
        :type robot: Robot subclass
        :param representation: task-space representation, defaults to "rpy/xyz"
        :type representation: str
        :param gravity: gravitational acceleration
        :type gravity: float
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.arm.Inertia
    def INERTIA(self, robot, **blockargs):
        """
        :param robot: Robot model
        :type robot: Robot subclass
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.arm.Inertia_X
    def INERTIA_X(self, robot, representation='rpy/xyz', pinv=False, **blockargs):
        """
        :param robot: Robot model
        :type robot: Robot subclass
        :param representation: task-space representation, defaults to "rpy/xyz"
        :type representation: str
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.arm.FDyn
    def FDYN(self, robot, q0=None, **blockargs):
        """
        :param robot: Robot model
        :type robot: Robot subclass
        :param q0: Initial joint configuration
        :type q0: array_like(n)
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.arm.FDyn_X
    def FDYN_X(self, robot, q0=None, gravcomp=False, velcomp=False, representation='rpy/xyz', **blockargs):
        """
        :param robot: Robot model
        :type robot: Robot subclass
        :param q0: Initial joint configuration
        :type q0: array_like(n)
        :param gravcomp: perform gravity compensation
        :type gravcomp: bool
        :param velcomp: perform velocity term compensation
        :type velcomp: bool
        :param representation: task-space representation, defaults to "rpy/xyz"
        :type representation: str
    
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.mobile.Bicycle
    def BICYCLE(self, L=1, speed_max=inf, accel_max=inf, steer_max=1.413716694115407, x0=None, **blockargs):
        """
        :param L: Wheelbase, defaults to 1
        :type L: float, optional
        :param speed_max: Velocity limit, defaults to math.inf
        :type speed_max: float, optional
        :param accel_max: maximum acceleration, defaults to math.inf
        :type accel_max: float, optional
        :param steer_max: maximum steered wheel angle, defaults to math.pi*0.45
        :type steer_max: float, optional
        :param x0: Initial state, defaults to [0,0,0]
        :type x0: array_like(3), optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.mobile.Unicycle
    def UNICYCLE(self, w=1, speed_max=inf, accel_max=inf, steer_max=inf, x0=None, **blockargs):
        """

        :param w: vehicle width, defaults to 1
        :type w: float, optional
        :param speed_max: Velocity limit, defaults to math.inf
        :type speed_max: float, optional
        :param accel_max: maximum acceleration, defaults to math.inf
        :type accel_max: float, optional
        :param steer_max: maximum turn rate :math:`\omega`, defaults to math.inf
        :type steer_max: float, optional
        :param x0: Inital state, defaults to [0,0,0]
        :type x0: array_like(3), optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.mobile.DiffSteer
    def DIFFSTEER(self, w=1, R=1, speed_max=inf, accel_max=inf, steer_max=None, a=0, x0=None, **blockargs):
        """
        :param w: vehicle width, defaults to 1
        :type w: float, optional
        :param R: Wheel radius, defaults to 1
        :type R: float, optional
        :param speed_max: Velocity limit, defaults to 1
        :type speed_max: float, optional
        :param accel_max: maximum acceleration, defaults to math.inf
        :type accel_max: float, optional
        :param steer_max: maximum steering rate, defaults to 1
        :type steer_max: float, optional
        :param x0: Inital state, defaults to None
        :type x0: array_like, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.mobile.VehiclePlot
    def VEHICLEPLOT(self, animation=None, path=None, labels=['X', 'Y'], square=True, init=None, scale='auto', polyargs={}, **blockargs):
        """
        :param animation: Graphical animation of vehicle, defaults to None
        :type animation: VehicleAnimation subclass, optional
        :param path: linestyle to plot path taken by vehicle, defaults to None
        :type path: str or dict, optional
        :param labels: axis labels (xlabel, ylabel), defaults to ["X","Y"]
        :type labels: array_like(2) or list
        :param square: Set aspect ratio to 1, defaults to True
        :type square: bool, optional
        :param init: function to initialize graphics, defaults to None
        :type init: callable, optional
        :param scale: scale of plot, defaults to "auto"
        :type scale: list or str, optional
        :param polyargs: arguments passed to :meth:`Animation.Polygon`
        :type polyargs: dict
        :param blockargs: |BlockOptions|
        :type blockargs: dict

        .. note::

            - The ``init`` function is called after the axes are initialized
              and can be used to draw application specific detail on the
              plot. In the example below, this is the dot and star.
            - A dynamic trail, showing path to date can be animated if
              the option ``path`` is set to a linestyle.
        
        """
        ...


    # roboticstoolbox.blocks.uav.MultiRotor
    def MULTIROTOR(self, model, groundcheck=True, speedcheck=True, x0=None, **blockargs):
        """
        Create a multi-rotor dynamic model block.

        :param model: A dictionary of vehicle geometric and inertial properties
        :type model: dict
        :param groundcheck: Prevent vehicle moving below ground :math:`z>0`, defaults to True
        :type groundcheck: bool
        :param speedcheck: Check for non-positive rotor speed, defaults to True
        :type speedcheck: bool
        :param x0: Initial state, defaults to None
        :type x0: array_like(6) or array_like(12), optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.uav.MultiRotorMixer
    def MULTIROTORMIXER(self, model=None, wmax=1000, wmin=5, **blockargs):
        """
        :param model: A dictionary of vehicle geometric and inertial properties
        :type model: dict
        :param maxw: maximum rotor speed in rad/s, defaults to 1000
        :type maxw: float
        :param minw: minimum rotor speed in rad/s, defaults to 5
        :type minw: float
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.uav.MultiRotorPlot
    def MULTIROTORPLOT(self, model, scale=[-2, 2, -2, 2, 10], flapscale=1, projection='ortho', **blockargs):
        """
        :param model: A dictionary of vehicle geometric and inertial properties
        :type model: dict
        :param scale: dimensions of workspace: xmin, xmax, ymin, ymax, zmin, zmax, defaults to [-2,2,-2,2,10]
        :type scale: array_like, optional
        :param flapscale: exagerate flapping angle by this factor, defaults to 1
        :type flapscale: float
        :param projection: 3D projection, one of: 'ortho' [default], 'perspective'
        :type projection: str
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.spatial.Tr2Delta
    def TR2DELTA(self, **blockargs):
        """
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.spatial.Delta2Tr
    def DELTA2TR(self, **blockargs):
        """
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # roboticstoolbox.blocks.spatial.Point2Tr
    def POINT2TR(self, T=None, **blockargs):
        """
        :param T: the transform
        :type T: SE3
        :param blockargs: |BlockOptions|
        :type blockargs: dict

        If ``T`` is None then it defaults to the identity matrix.
        
        """
        ...


    # roboticstoolbox.blocks.spatial.TR2T
    def TR2T(self, **blockargs):
        """
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        
        """
        ...


    # machinevisiontoolbox.blocks.camera.Camera
    def CAMERA(self, camera=None, args={}, **blockargs):
        """
        :param camera: Camera model, defaults to None
        :type camera: Camera subclass, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a CAMERA block
        :rtype: Camera instance

        Camera projection model.

        **Block ports**

            :input pose: Camera pose as an SE3 object.
            :input P: world points as ndarray(3,N)

            :output p: image plane points as ndarray(2,N)
        
        """
        ...


    # machinevisiontoolbox.blocks.camera.Visjac_p
    def VISJAC_P(self, camera, depth=1, depthest=False, **blockargs):
        """
        :param camera: Camera model, defaults to None
        :type camera: Camera subclass, optional
        :param depth: Point depth
        :type depth: float or ndarray
        :param depthest: Use depth estimation, defaults to True
        :type depthest: bool, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a VISJAC_P block
        :rtype: Visjac_p instance

        If the Jacobian


        
        """
        ...


    # machinevisiontoolbox.blocks.camera.EstPose_p
    def ESTPOSE_P(self, camera, P, frame='world', method='iterative', **blockargs):
        """
        :param camera: Camera model, defaults to None
        :type camera: Camera subclass, optional
        :param P: World point coordinates
        :type P: ndarray(2,N)
        :param frame: return pose of points with respect to reference frame which is one of: 'world' [default] or 'camera'
        :type frame: str, optional
        :param method: pose estimation algorithm one of: 'iterative' [default], 'epnp', 'p3p', 'ap3p', 'ippe', 'ippe-square'
        :type method: str, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a ESTPOSE_P block
        :rtype: EstPose_p instance

        
        """
        ...


    # machinevisiontoolbox.blocks.camera.ImagePlane
    def IMAGEPLANE(self, camera, style=None, labels=None, grid=True, retain=False, watch=False, init=None, **blockargs):
        """
        Create a block that plots image plane coordinates.

        :param camera: a camera model
        :type camera: Camera instance
        :param style: styles for each point to be plotted
        :type style: str or dict, list of strings or dicts; one per line, optional
        :param grid: draw a grid, defaults to True. Can be boolean or a tuple of
                     options for grid()
        :type grid: bool or sequence
        :param retain: keep previous image plane points, defaults to False
        :type retain: bool, optional
        :param watch: add these signals to the watchlist, defaults to False
        :type watch: bool, optional
        :param init: function to initialize the graphics, defaults to None
        :type init: callable, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: An IMAGEPLANE block
        :rtype: ImagePlane instance

        Create a block that plots points on a camera object's virtual image plane.

        Examples::

            SCOPE()
            SCOPE(nin=2)
            SCOPE(nin=2, scale=[-1,2])
            SCOPE(styles='k--')
            SCOPE(styles=[{'color': 'blue'}, {'color': 'red', 'linestyle': '--'}])
            SCOPE(styles=['k', 'r--'])


        .. figure:: ../../figs/Figure_1.png
           :width: 500px
           :alt: example of generated graphic

           Example of scope display.
        
        """
        ...
