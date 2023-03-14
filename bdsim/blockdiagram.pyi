from spatialmath.base.types import *
import numpy as np
import math

class BlockDiagram:


    # bdsim.blocks.functions.Sum
    def SUM(self, signs: str = '++', mode: str = None, **blockargs):
        """
        :param signs: signs associated with input ports, accepted characters: + or -, defaults to '++'
        :type signs: str, optional
        :param mode: controls addition mode, per element, string comprises ``r`` or ``c`` or ``C`` or ``L``, defaults to None
        :type mode: str, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: SUM block
        :rtype: ``Sum`` instance

        Add or subtract input signals according to the `signs` string.  The
        number of input ports is the length of this string.

        For example::

            sum = bd.SUM('+-+')

        is a 3-input summing junction which computes port0 - port1 + port2.

        :note: The signals must be compatible, all scalars, or all arrays
        of the same shape.

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
        :return: PROD block
        :rtype: ``Prod`` instance

        Multiply or divide input signals according to the `ops` string.  The
        number of input ports is the length of this string.

        For example::

            prod = PROD('*/*')

        is a 3-input product junction which computes port0 / port 1 * port2.

        :note: By default the ``*`` and ``/`` operators are used which perform element-wise
            operations.

        :note: The option ``matrix`` will instead use ``@`` and ``@ np.linalg.inv()``. The
            shapes of matrices must conform.  A matrix on a ``/`` input must be square and
            non-singular.
        
        """
        ...


    # bdsim.blocks.functions.Gain
    def GAIN(self, K: Union[int, float, numpy.ndarray] = 1, premul: bool = False, **blockargs):
        """
        Gain block.

        :param K: The gain value, defaults to 1
        :type K: scalar, array_like
        :param premul: premultiply by constant, default is postmultiply, defaults to False
        :type premul: bool, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: GAIN block
        :rtype: ``Gain`` instance

        Scale the input signal. If the input is :math:`u` the output is :math:`u K`.

        Either or both the input and gain can be Numpy arrays and Numpy will
        compute the appropriate product :math:`u K`.

        If :math:`u` and ``K`` are both NumPy arrays the ``@`` operator is used
        and :math:`u` is postmultiplied by the gain. To premultiply by the gain,
        to compute :math:`K u` use the ``premul`` option.

        For example::

            gain = bd.GAIN(constant)
        
        """
        ...


    # bdsim.blocks.functions.Clip
    def CLIP(self, min: Union[numpy.ndarray, int, float, list, tuple] = -inf, max: Union[numpy.ndarray, int, float, list, tuple] = inf, **blockargs):
        """
        Signal clipping.

        :param min: Minimum value, defaults to -math.inf
        :type min: scalar or array_like, optional
        :param max: Maximum value, defaults to math.inf
        :type max: float or array_like, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: CLIP block
        :rtype: ``Clip`` instance

        The input signal is clipped to the range from ``minimum`` to ``maximum`` inclusive.

        The signal can be a 1D-array in which case each element is clipped.  The
        minimum and maximum values can be:

            - a scalar, in which case the same value applies to every element of
              the input vector , or
            - a 1D-array, of the same shape as the input vector that applies elementwise to
              the input vector.

        For example::

            clip = bd.CLIP()

        
        """
        ...


    # bdsim.blocks.functions.Function
    def FUNCTION(self, func: Callable = None, nin: int = 1, nout: int = 1, persistent: bool = False, fargs: list = None, fkwargs: dict = None, **blockargs):
        """
        Python function.

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
        :return: FUNCTION block
        :rtype: ``Function`` instance

        Inputs to the block are passed as separate arguments to the function.
        Programmatic ositional or keyword arguments can also be passed to the function.

        A block with one output port that sums its two input ports is::

            FUNCTION(lambda u1, u2: u1+u2, nin=2)

        A block with a function that takes two inputs and has two additional arguments::

            def myfun(u1, u2, param1, param2):
                pass

            FUNCTION(myfun, nin=2, args=(p1,p2))

        If we need access to persistent (static) data, to keep some state::

            def myfun(u1, u2, param1, param2, state):
                pass

            FUNCTION(myfun, nin=2, args=(p1,p2), persistent=True)

        where a dictionary is passed in as the last argument and which is kept from call to call.

        A block with a function that takes two inputs and additional keyword arguments::

            def myfun(u1, u2, param1=1, param2=2, param3=3, param4=4):
                pass

            FUNCTION(myfun, nin=2, kwargs=dict(param2=7, param3=8))

        A block with two inputs and two outputs, the outputs are defined by two lambda
        functions with the same inputs::

            FUNCTION( [ lambda x, y: x_t, lambda x, y: x* y])

        A block with two inputs and two outputs, the outputs are defined by a
        single function which returns a list::

            def myfun(u1, u2):
                return [ u1+u2, u1*u2 ]

            FUNCTION( myfun, nin=2, nout=2)

        For example::

            func = bd.FUNCTION(myfun, args)

        If inputs are specified then connections are automatically made and
        are assigned to sequential input ports::

            func = bd.FUNCTION(myfun, block1, block2, args)

        is equivalent to::

            func = bd.FUNCTION(myfun, args)
            bd.connect(block1, func[0])
            bd.connect(block2, func[1])
        
        """
        ...


    # bdsim.blocks.functions.Interpolate
    def INTERPOLATE(self, x: Union[list, tuple, numpy.ndarray] = None, y: Union[list, tuple, numpy.ndarray] = None, xy: numpy.ndarray = None, time: bool = False, kind: str = 'linear', **blockargs):
        """
        Interpolate signal.

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
        :return: INTERPOLATE block
        :rtype: ``Interpolate`` instance

        Interpolate the input signal using to a piecewise function.

        A simple triangle function with domain [0,10] and range [0,1] can be
        defined by::

            INTERPOLATE(x=(0,5,10), y=(0,1,0))

        We might also express this as a list of 2D-coordinats::

            INTERPOLATE(xy=[(0,0), (5,1), (10,0)])

        The data can also be expressed as Numpy arrays.  If that is the case,
        the interpolation function can be vector valued. ``x`` has a shape of
        (N,1) and ``y`` has a shape of (N,M).  Alternatively ``xy`` has a shape
        of (N,M+1) and the first column is the x-data.

        The input to the interpolator comes from:

        - Input port 0
        - Simulation time, if ``time=True``.  In this case the block has no
          input ports and is a ``Source`` not a ``Function``.
        
        """
        ...


    # bdsim.blocks.sources.Constant
    def CONSTANT(self, value=0, **blockargs):
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


    # bdsim.blocks.sources.Time
    def TIME(self, value=None, **blockargs):
        """
        Simulation time.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a TIME block
        :rtype: Time instance

        The block has only one output port which is the current simulation time.

        
        """
        ...


    # bdsim.blocks.sources.WaveForm
    def WAVEFORM(self, wave='square', freq=1, unit='Hz', phase=0, amplitude=1, offset=0, min=None, max=None, duty=0.5, **blockargs):
        """
        Waveform as function of time.

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
        :return: a WAVEFORM block
        :rtype: WaveForm instance

        Create a waveform generator block.

        Examples::

            WAVEFORM(wave='sine', freq=2)   # 2Hz sine wave varying from -1 to 1
            WAVEFORM(wave='square', freq=2, unit='rad/s') # 2rad/s square wave varying from -1 to 1

        The minimum and maximum values of the waveform are given by default in
        terms of amplitude and offset. The signals are symmetric about the offset
        value. For example::

            WAVEFORM(wave='sine') varies between -1 and +1
            WAVEFORM(wave='sine', amplitude=2) varies between -2 and +2
            WAVEFORM(wave='sine', offset=1) varies between 0 and +2
            WAVEFORM(wave='sine', amplitude=2, offset=1) varies between -1 and +3

        Alternatively we can specify the minimum and maximum values which override
        amplitude and offset::

            WAVEFORM(wave='triangle', min=0, max=5) varies between 0 and +5

        At time 0 the sine and triangle wave are zero and increasing, and the
        square wave has its first rise.  We can specify a phase shift with
        a number in the range [0,1] where 1 corresponds to one cycle.

        .. note:: For discontinuous signals (square, triangle) the block declares
            events for every discontinuity.

        :seealso :meth:`declare_events`
        
        """
        ...


    # bdsim.blocks.sources.Piecewise
    def PIECEWISE(self, *seq, **blockargs):
        """
        Piecewise constant signal.

        :param seq: sequence of time, value pairs
        :type seq: list of 2-tuples
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a PIECEWISE block
        :rtype: Piecewise instance

        Outputs a piecewise constant function of time.  This is described as
        a series of 2-tuples (time, value).  The output value is taken from the
        active tuple, that is, the latest one in the list whose time is no greater
        than simulation time.

        .. note::
            - The tuples must be order by monotonically increasing time.
            - There is no default initial value, the list should contain
              a tuple with time zero otherwise the output will be undefined.

        .. note:: The block declares an event for the start of each segment.

        :seealso: :meth:`declare_events`
        
        """
        ...


    # bdsim.blocks.sources.Step
    def STEP(self, T=1, off=0, on=1, **blockargs):
        """
        Step signal.

        :param T: time of step, defaults to 1
        :type T: float, optional
        :param off: initial value, defaults to 0
        :type off: float, optional
        :param on: final value, defaults to 1
        :type on: float, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a STEP block
        :rtype: Step

        Output a step signal that transitions from the value ``off`` to ``on``
        when time equals ``T``.

        .. note:: The block declares an event for the step time.

        :seealso: :meth:`declare_events`
        
        """
        ...


    # bdsim.blocks.sources.Ramp
    def RAMP(self, T=1, off=0, slope=1, **blockargs):
        """
        Ramp signal.

        :param T: time of ramp start, defaults to 1
        :type T: float, optional
        :param off: initial value, defaults to 0
        :type off: float, optional
        :param slope: gradient of slope, defaults to 1
        :type slope: float, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a RAMP block
        :rtype: Ramp

        Output a ramp signal that starts increasing from the value ``off``
        when time equals ``T`` linearly with time, with a gradient of ``slope``.

        .. note:: The block declares an event for the ramp start time.

        :seealso: :method:`declare_event`
        
        """
        ...


    # bdsim.blocks.sinks.Print
    def PRINT(self, fmt=None, file=None, **blockargs):
        """
        Print signal.

        :param fmt: Format string, defaults to None
        :type fmt: str, optional
        :param file: file to write data to, defaults to None
        :type file: file object, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A PRINT block
        :rtype: Print instance

        Creates a console print block which displays the value of a signal
        at each simulation time step. The display format is like::

            PRINT(print.0 @ t=0.100) [-1.0 0.2]

        and includes the block name, time, and the formatted value.

        The numerical formatting of the signal is controlled by ``fmt``:

        - if not provided, ``str()`` is used to format the signal
        - if provided:
            - a scalar is formatted by the ``fmt.format()``
            - a NumPy array is formatted by ``fmt.format()`` applied to every
              element

        Examples::

            pr = bd.PRINT()     # create PRINT block
            bd.connect(x, inputs=pr)   # its input comes from x

            bd.PRINT(x)         # create PRINT block with input from x

            bd.PRINT(x, name='X')  # block name appears in the printed text

            bd.PRINT(x, fmt="{:.1f}") # print with explicit format

        .. note::
            - By default writes to stdout
            - The output is cleaner if progress bar printing is disabled.

        
        """
        ...


    # bdsim.blocks.sinks.Stop
    def STOP(self, func=None, **blockargs):
        """
        Conditional simulation stop.

        :param func: evaluate stop condition, defaults to None
        :type func: callable, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A STOP block
        :rtype: Stop instance

        Conditionally stop the simulation if the input is:

        - bool type and True
        - numeric type and > 0

        If ``func`` is provided, then it is applied to the block input
        and if it returns True the simulation is stopped.
        
        """
        ...


    # bdsim.blocks.sinks.Null
    def NULL(self, nin=1, **blockargs):
        """
        Discard signal.

        :param nin: number of input ports, defaults to 1
        :type nin: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A NULL block
        :rtype: Null instance

        Create a sink block with arbitrary number of input ports that discards
        all data.  Useful for testing.

        
        """
        ...


    # bdsim.blocks.sinks.Watch
    def WATCH(self, **blockargs):
        """
        Watch a signal.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A NULL block
        :rtype: Null instance

        Causes the input signal to be logged during the
        simulation run.  Equivalent to adding it as the ``watch=`` argument
        to ``bdsim.run``.

        :seealso: :method:`BDSim.run`
        
        """
        ...


    # bdsim.blocks.transfers.Integrator
    def INTEGRATOR(self, x0=0, gain=1.0, min=None, max=None, **blockargs):
        """
        Integrator.

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
        :return: INTEGRATOR block
        :rtype: ``Integrator`` instance

        Output is the time integral of the input.  The state can be a scalar or a
        vector. The initial state, and type, is given by ``x0``.  The shape of
        the input signal must match ``x0``.

        The minimum and maximum values can be:

            - a scalar, in which case the same value applies to every element of
              the state vector, or
            - a vector, of the same shape as ``x0`` that applies elementwise to
              the state.

        .. note:: The minimum and maximum prevent integration outside the limits,
            but assume that the initial state is within the limits.
        
        """
        ...


    # bdsim.blocks.transfers.PoseIntegrator
    def POSEINTEGRATOR(self, x0=None, **blockargs):
        """
        Pose integrator

        :param x0: Initial pose, defaults to null
        :type x0: SE3, Twist3, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: POSEINTEGRATOR block
        :rtype: ``PoseIntegrator`` instance

        This block integrates spatial velocity over time.
        The block input is a spatial velocity as a 6-vector
        :math:`(v_x, v_y, v_z, \omega_x, \omega_y, \omega_z)` and the output
        is pose as an ``SE3`` instance.

        .. note:: State is a velocity twist.
        
        """
        ...


    # bdsim.blocks.transfers.LTI_SS
    def LTI_SS(self, A=None, B=None, C=None, x0=None, **blockargs):
        """
        State-space LTI dynamics.

        :param N: numerator coefficients, defaults to 1
        :type N: array_like, optional
        :param D: denominator coefficients, defaults to [1,1]
        :type D: array_like, optional
        :param x0: initial states, defaults to None
        :type x0: array_like, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: LTI_SS block
        :rtype: ``LTI_SS`` instance

        Implements the dynamics of a single-input single-output (SISO) linear
        time invariant (LTI) system described by numerator and denominator
        polynomial coefficients.

        Coefficients are given in the order from highest order to zeroth
        order, ie. :math:`2s^2 - 4s +3` is ``[2, -4, 3]``.

        Only proper transfer functions, where order of numerator is less
        than denominator are allowed.

        The order of the states in ``x0`` is consistent with controller canonical
        form.

        Examples::

            LTI_SS(N=[1,2], D=[2, 3, -4])

        is the transfer function :math:`\frac{s+2}{2s^2+3s-4}`.
        
        """
        ...


    # bdsim.blocks.transfers.LTI_SISO
    def LTI_SISO(self, N=1, D=[1, 1], x0=None, **blockargs):
        """
        SISO LTI dynamics.

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

        Implements the dynamics of a single-input single-output (SISO) linear
        time invariant (LTI) system described by numerator and denominator
        polynomial coefficients.

        Coefficients are given in the order from highest order to zeroth
        order, ie. :math:`2s^2 - 4s +3` is ``[2, -4, 3]``.

        Only proper transfer functions, where order of numerator is less
        than denominator are allowed.

        The order of the states in ``x0`` is consistent with controller canonical
        form.

        Examples::

            LTI_SISO(N=[1, 2], D=[2, 3, -4])

        is the transfer function :math:`\frac{s+2}{2s^2+3s-4}`.
        
        """
        ...


    # bdsim.blocks.connections.SubSystem
    def SUBSYSTEM(self, subsys, nin=1, nout=1, **blockargs):
        """
        Instantiate a subsystem.

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
        :return: A SUBSYSTEM block
        :rtype: SubSystem instance

        This block represents a subsystem in a block diagram.  The definition
        of the subsystem can be:

            - the name of a module which is imported and must contain only
              only ``BlockDiagram`` instance, or
            - a ``BlockDiagram`` instance

        The referenced block diagram must contain one or both of:

            - one ``InPort`` block, which has outputs but no inputs. These
              outputs are connected to the inputs to the enclosing ``SubSystem`` block.
            - one ``OutPort`` block, which has inputs but no outputs. These
              inputs are connected to the outputs to the enclosing ``SubSystem`` block.

        .. note::

        - The referenced block diagram is treated like a macro and copied into
          the parent block diagram at compile time. The ``SubSystem``, ``InPort`` and
          ``OutPort`` blocks are eliminated, that is, all hierarchical structure is
          lost.
        - The same subsystem can be used multiple times, its blocks and wires
           will be cloned.  Subsystems can also include subsystems.
        - The number of input and output ports is not specified, they are computed
          from the number of ports on the ``InPort`` and ``OutPort`` blocks within the
          subsystem.
        
        """
        ...


    # bdsim.blocks.transfers.Deriv
    def DERIV(self, alpha, **blockargs):
        """None
        """
        ...


    # bdsim.blocks.transfers.PID
    def PID(self, P: float = 0.0, D: float = 0.0, I: float = 0.0, D_pole=1, I_limit=None, I_band=0, name='PID', **blockargs):
        """
        PID controller.

        :param P: proportional gain, defaults to 0
        :param D: derivative gain, defaults to 0
        :param I: integral gain, defaults to 0
        :param D_pole: filter pole for derivative estimate, defaults to 1 rad/s
        :param I_limit: integral limit
        :param I_band: band within which integral action is active
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A PID block
        :rtype: PID instance

        Implements the dynamics of a PID controller:

        .. math::

            e &= x^* - x

            x &= Pe + D \frac{d}{dt} e + I \int e dt

        To reduce noise the derivative is computed by a first-order system

        .. math::

            \frac{s}{s/a + 1}

        where the pole :math:`a=` ``D_filt`` can be positioned appropriately.

        If ``I_limit`` is provided it specifies the limits of the integrator
        state, before multiplication by ``I``.  If ``I_limit`` is:

        * a scalar :math:`s` the integrator state is clipped to the interval :math:`[-s, s]`
        * a 2-tuple :math:`(a,b)` the integrator state is clipped to the interval :math:`[a, b]`

        If ``I_band`` is provided the integrator is reset to zero whenever the
        error :math:`e` is outside the band given by ``I_band`` which is:

        * a scalar :math:`s` the band is the interval :math:`[-s, s]`
        * a 2-tuple :math:`(a,b)` the band is the interval :math:`[a, b]`


        Examples::

            PID(P=3, D=2, I=1)

        
        """
        ...


    # bdsim.blocks.discrete.ZOH
    def ZOH(self, clock, x0=0, **blockargs):
        """
        Zero-order hold.

        :param clock: clock source
        :type clock: Clock
        :param x0: Initial value of the hold, defaults to 0
        :type x0: array_like, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a ZOH block
        :rtype: Integrator instance

        Output is the input at the previous clock time.  The state can be a scalar or a
        vector, this is given by the type of ``x0``.

        .. note:: If input is not a scalar, ``x0`` must have the shape of the
            input signal.
        
        """
        ...


    # bdsim.blocks.discrete.DIntegrator
    def DINTEGRATOR(self, clock, x0=0, gain=1.0, min=None, max=None, **blockargs):
        """
        Discrete-time integrator.

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
        :return: an INTEGRATOR block
        :rtype: Integrator instance

        Create a discrete-time integrator block.

        Output is the time integral of the input.  The state can be a scalar or a
        vector, this is given by the type of ``x0``.

        The minimum and maximum values can be:

            - a scalar, in which case the same value applies to every element of
              the state vector, or
            - a vector, of the same shape as ``x0`` that applies elementwise to
              the state.
        
        """
        ...


    # bdsim.blocks.discrete.DPoseIntegrator
    def DPOSEINTEGRATOR(self, clock, x0=None, **blockargs):
        """
        Discrete-time spatial velocity integrator.

        :param clock: clock source
        :type clock: Clock
        :param x0: Initial pose, defaults to null
        :type x0: SE3, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: an DPOSEINTEGRATOR block
        :rtype: Integrator instance

        This block integrates spatial velocity over time.
        The block input is a spatial velocity as a 6-vector
        :math:`(v_x, v_y, v_z, \omega_x, \omega_y, \omega_z)` and the output
        is pose as an ``SE3`` instance.

        .. note:: State is a velocity twist.

        
        """
        ...


    # bdsim.blocks.linalg.Inverse
    def INVERSE(self, pinv=False, **blockargs):
        """
        Matrix inverse.

        :param pinv: force pseudo inverse, defaults to False
        :type pinv: bool, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: An INVERSE block
        :rtype: Inverse instance

        Compute inverse of the 2D-array input signal.  If the matrix is square
        the inverse is computed unless the ``pinv`` flag is True.  For a
        non-square matrix the pseudo-inverse is used.  The condition number is
        output on the second port.

        :seealso: `numpy.linalg.inv <https://numpy.org/doc/stable/reference/generated/numpy.linalg.inv.html>`_,
            `numpy.linalg.pinv <https://numpy.org/doc/stable/reference/generated/numpy.linalg.pinv.html>`_,
            `numpy.linalg.cond <https://numpy.org/doc/stable/reference/generated/numpy.linalg.cond.html>`_
        
        """
        ...


    # bdsim.blocks.linalg.Transpose
    def TRANSPOSE(self, **blockargs):
        """
        Matrix transpose.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A TRANSPOSE block
        :rtype: Transpose instance

        Compute transpose of the 2D-array input signal.

        .. note::
            - An input 1D-array of shape (N,) is turned into a 2D-array column vector
              with shape (N,1).
            - An input 2D-array column vector of shape (N,1) becomes a 2D-array
             row vector with shape (1,N).

        :seealso: `numpy.linalg.transpose <https://numpy.org/doc/stable/reference/generated/numpy.linalg.transpose.html>`_
        
        """
        ...


    # bdsim.blocks.linalg.Norm
    def NORM(self, ord=None, axis=None, **blockargs):
        """
        Array norm.

        :param axis: specifies the axis along which to compute the vector norms, defaults to None.
        :type axis: int, optional
        :param ord: Order of the norm, default to None.
        :type ord: int or str
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A NORM block
        :rtype: Norm instance

        Computes the specified norm for a 1D- or 2D-array.

        :seealso: `numpy.linalg.norm <https://numpy.org/doc/stable/reference/generated/numpy.linalg.norm.html>`_
        
        """
        ...


    # bdsim.blocks.linalg.Flatten
    def FLATTEN(self, order='C', **blockargs):
        """
        Flatten a multi-dimensional array.

        :param order: flattening order, either "C" or "F", defaults to "C"
        :type order: str
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A FLATTEN block
        :rtype: Flatten instance

        Flattens the incoming array in either row major ('C') or column major ('F') order.

        :seealso: `numpy.flatten <https://numpy.org/doc/stable/reference/generated/numpy.flatten.html>`_
        
        """
        ...


    # bdsim.blocks.linalg.Slice2
    def SLICE2(self, rows=None, cols=None, **blockargs):
        """
        Slice out subarray of 2D-array.

        :param rows: row selection, defaults to None
        :type rows: tuple(3) or list
        :param cols: column selection, defaults to None
        :type cols: tuple(3) or list
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A SLICE2 block
        :rtype: Slice2 instance

        Compute a 2D slice of input 2D array.

        If ``rows`` or ``cols`` is ``None`` it means all rows or columns
        respectively.

        If ``rows`` or ``cols`` is a list, perform NumPy fancy indexing, returning
        the specified rows or columns

        Example::

            SLICE2(rows=[2,3])  # return rows 2 and 3, all columns
            SLICE2(cols=[4,1])  # return columns 4 and 1, all rows
            SLICE2(rows=[2,3], cols=[4,1]) # return elements [2,4] and [3,1] as a 1D array

        If a single row or column is selected, the result will be a 1D array

        If ``rows`` or ``cols`` is a tuple, it must have three elements.  It
        describes a Python slice ``(start, stop, step)`` where any element can be ``None``

            * ``start=None`` means start at first element
            * ``stop=None`` means finish at last element
            * ``step=None`` means step by one

        ``rows=None`` is equivalent to ``rows=(None, None, None)``.

        Example::

            SLICE2(rows=(None,None,2))  # return every second row
            SLICE2(cols=(None,None,-1)) # reverse the columns

        The list and tuple notation can be mixed, for example, one for rows
        and one for columns.

        :seealso: :class:`Slice1` :class:`Index`
        
        """
        ...


    # bdsim.blocks.linalg.Slice1
    def SLICE1(self, index, **blockargs):
        """
        Slice out subarray of 1D-array.

        :param index: slice, defaults to None
        :type index: tuple(3)
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A SLICE1 block
        :rtype: Slice1 instance

        Compute a 1D slice of input 1D array.

        If ``index`` is ``None`` it means all elements.

        If ``index`` is a list, perform NumPy fancy indexing, returning
        the specified elements

        Example::

            SLICE1(index=[2,3]) # return elements 2 and 3 as a 1D array
            SLICE1(index=[2])   # return element 2 as a 1D array
            SLICE1(index=2)     # return element 2 as a NumPy scalar

        If ``index`` is a tuple, it must have three elements.  It
        describes a Python slice ``(start, stop, step)`` where any element can be ``None``

            * ``start=None`` means start at first element
            * ``stop=None`` means finish at last element
            * ``step=None`` means step by one

        ``rows=None`` is equivalent to ``rows=(None, None, None)``.

        Example::

            SLICE1(index=(None,None,2))  # return every second element
            SLICE1(index=(None,None,-1)) # reverse the elements

        :seealso: :class:`Slice1`
        
        """
        ...


    # bdsim.blocks.linalg.Det
    def DET(self, **blockargs):
        """
        Matrix determinant

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A DET block
        :rtype: Det instance

        Compute the matrix determinant.

        :seealso: `numpy.linalg.det <https://numpy.org/doc/stable/reference/generated/numpy.linalg.det.html>`_
        
        """
        ...


    # bdsim.blocks.linalg.Cond
    def COND(self, **blockargs):
        """
        Compute the matrix condition number.

        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A COND block
        :rtype: Cond instance

        :seealso: `numpy.linalg.cond <https://numpy.org/doc/stable/reference/generated/numpy.linalg.cond.html>`_
        
        """
        ...


    # bdsim.blocks.displays.Scope
    def SCOPE(self, nin=None, vector=None, styles=None, stairs=False, scale='auto', labels=None, grid=True, watch=False, title=None, **blockargs):
        """
        Plots input signals against time.

        :param nin: number of inputs, defaults to 1 or if given, the length of
                    style vector
        :type nin: int, optional
        :param vector: vector signal on single input port, defaults to None
        :type vector: int or list, optional
        :param styles: styles for each line to be plotted
        :type styles: str or dict, list of strings or dicts; one per line, optional
        :param stairs: force staircase style plot, defaults to False
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
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A SCOPE block
        :rtype: Scope instance

        Create a block that plots:

        * scalar input ports against time, ``vector=None``
        * selected elements of a NumPy array on a single input port. If ``vector`` is an
          int this is the expected width of the array. If ``vector`` is a list of ints these
          are the indices of the array to display.

        Each line can have its own color or style which is specified by:

            - a dict of options for `Line2D <https://matplotlib.org/3.2.2/api/_as_gen/matplotlib.lines.Line2D.html#matplotlib.lines.Line2D>`_ or
            - a  MATLAB-style linestyle like 'k--'

        The number of lines to plot will be inferred from:
        * the length of the ``labels`` list if specified
        * the length of the ``styles`` list if specified
        * ``nin`` if specified
        * ``vector`` if specified

        If multiple lines are plotted then a heterogeneous list of styles, dicts or strings,
        one per line must be given.

        The vertical scale factor defaults to auto-scaling but can be fixed by
        providing a 2-tuple [ymin, ymax]. All lines are plotted against the
        same vertical scale.

        Examples::

            SCOPE()
            SCOPE(nin=2)
            SCOPE(nin=2, scale=[-1,2])
            SCOPE(styles='k--')
            SCOPE(styles=[{'color': 'blue'}, {'color': 'red', 'linestyle': '--'}])
            SCOPE(styles=['k', 'r--'])
            SCOPE(vector=[0,1,2]) # display elements 0, 1, 2 of array on port 0


        .. figure:: ../../figs/Figure_1.png
           :width: 500px
           :alt: example of generated graphic

           Example of scope display.
        
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
        :return: A SCOPEXY block
        :rtype: ScopeXY instance

        Create an XY scope.

        This block has two inputs which are plotted against each other. Port 0
        is the horizontal axis, and port 1 is the vertical axis.

        The line style is given by either:

            - a dict of options for ``plot``, or
            - as a simple MATLAB-style linestyle like ``'k--'``.

        The scale factor defaults to auto-scaling but can be fixed by
        providing either:

            - a 2-tuple [min, max] which is used for the x- and y-axes
            - a 4-tuple [xmin, xmax, ymin, ymax]

        :input x: signal plotted on horizontal axis
        :input y: signal plotted on vertical axis
        
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
        :return: A SCOPEXY block
        :rtype: ScopeXY instance

        Create an XY scope with vector input

        This block has one vector input and two elemetns are plotted against each other. The first
        selected element is the horizontal axis, and second is the vertical axis.

        The line style is given by either:

            - a dict of options for ``plot``, or
            - as a simple MATLAB-style linestyle like ``'k--'``.

        The scale factor defaults to auto-scaling but can be fixed by
        providing either:

            - a 2-tuple [min, max] which is used for the x- and y-axes
            - a 4-tuple [xmin, xmax, ymin, ymax]
        
        """
        ...


    # bdsim.blocks.connections.Item
    def ITEM(self, item, **blockargs):
        """
        Selector item from a dictionary signal.

        :param item: name of dictionary item
        :type item: str
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: An ITEM block
        :rtype: Item instance

        For a dictionary type input signal, select one item as the output signal.
        For example::

            ITEM('xd')

        selects the ``xd`` item from the dictionary signal input to the block.

        A dictionary signal can serve a similar purpose to a "bus" in Simulink(R).

        This is somewhat like a demultiplexer :class:`DeMux` but allows for
        named heterogeneous data.

        :seealso: :class:`Dict`
        
        """
        ...


    # bdsim.blocks.connections.Dict
    def DICT(self, item, **blockargs):
        """
        Create a dictionary signal.

        :param keys: list of dictionary keys
        :type keys: list
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A DICT block
        :rtype: Dict instance

        Inputs are assigned to a dictionary signal, using the corresponding
        names from ``keys``.
        For example::

            DICT(['x', 'xd', 'xdd'])

        expects three inputs and assigns them to dictionary items ``x``, ``xd``, ``xdd`` of
        the output dictionary respectively.

        A dictionary signal can serve a similar purpose to a "bus" in Simulink(R).

        This is somewhat like a multiplexer :class:`Mux` but allows for
        named heterogeneous data.

        :seealso: :class:`Item` :class:`Mux`
        
        """
        ...


    # bdsim.blocks.connections.Mux
    def MUX(self, nin=1, **blockargs):
        """
        Multiplex signals.

        :param nin: Number of input ports, defaults to 1
        :type nin: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A MUX block
        :rtype: Mux instance

        This block takes a number of scalar or 1D-array signals and concatenates
        them into a single 1-D array signal.  For example::

            MUX(2, inputs=(func1[2], sum3))

        multiplexes the outputs of blocks ``func1`` (port 2) and ``sum3`` into a
        single output vector as a 1D-array.

        :seealso: :class:`Dict`
        
        """
        ...


    # bdsim.blocks.connections.DeMux
    def DEMUX(self, nout=1, **blockargs):
        """
        Demultiplex signals.

        :param nout: number of outputs, defaults to 1
        :type nout: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A DEMUX block
        :rtype: DeMux instance

        This block has a single input port and ``nout`` output ports.  A 1D-array
        input signal (with ``nout`` elements) is routed element-wise to individual
        scalar output ports.

        
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
        :return: An INDEX block
        :rtype: Index instance

        The specified element(s) of the input iterable (list, string, etc.)
        are output.  The index can be an integer, sequence of integers, a Python slice
        object, or a string with Python slice notation, eg. ``"::-1"``.

        :seealso: :class:`Slice1` :class:`Slice2`
        
        """
        ...


    # bdsim.blocks.connections.InPort
    def INPORT(self, nout=1, **blockargs):
        """
        Input ports for a subsystem.

        :param nout: Number of output ports, defaults to 1
        :type nout: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: An INPORT block
        :rtype: InPort instance

        This block connects a subsystem to a parent block diagram.  Inputs to the
        parent-level ``SubSystem`` block appear as the outputs of this block.

        .. note:: Only one ``INPORT`` block can appear in a block diagram but it
            can have multiple ports.  This is different to Simulink(R) which
            would require multiple single-port input blocks.
        
        """
        ...


    # bdsim.blocks.connections.OutPort
    def OUTPORT(self, nin=1, **blockargs):
        """
        Output ports for a subsystem.

        :param nin: Number of input ports, defaults to 1
        :type nin: int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A OUTPORT block
        :rtype: OutPort instance

        This block connects a subsystem to a parent block diagram.  The the
        inputs of this block become the outputs of the parent-level ``SubSystem``
        block.

        .. note:: Only one ``OUTPORT`` block can appear in a block diagram but it
            can have multiple ports.  This is different to Simulink(R) which
            would require multiple single-port output blocks.
        
        """
        ...


    # bdsim.blocks.spatial.Pose_postmul
    def POSE_POSTMUL(self, pose=None, **blockargs):
        """
            Post multiply pose.

            :param pose: pose to apply
            :type pose: SO2, SE2, SO3 or SE3
            :param blockargs: |BlockOptions|
            :type blockargs: dict
            :return: A POSE_POSTMUL block
            :rtype: Pose_postmul instance

            Transform the pose on the input signal by post multiplication.

            For example::

                pose_mul = bd.POSE_POSTMUL(SE3())
            
        """
        ...


    # bdsim.blocks.spatial.Pose_premul
    def POSE_PREMUL(self, pose=None, **blockargs):
        """
            Pre multiply pose.

            :param pose: pose to apply
            :type pose: SO2, SE2, SO3 or SE3
            :param blockargs: |BlockOptions|
            :type blockargs: dict
            :return: A POSE_PREMUL block
            :rtype: Pose_premul instance

            Transform the pose on the input signal by premultiplication.

            For example::

                pose_mul = bd.POSE_PREMUL(SE3())
            
        """
        ...


    # bdsim.blocks.spatial.Transform_vector
    def TRANSFORM_VECTOR(self, **blockargs):
        """
            Transform a vector.

            :param blockargs: |BlockOptions|
            :type blockargs: dict
            :return: A TRANSFORM_VECTOR block
            :rtype: Transform_vector instance

            Transform the vector on the input signal by the pose.

            For example::

                vec_xform = bd.TRANSFORM_VECTOR()
            
        """
        ...


    # bdsim.blocks.spatial.Pose_inverse
    def POSE_INVERSE(self, **blockargs):
        """
            Pose inverse.

            :param blockargs: |BlockOptions|
            :type blockargs: dict
            :return: A POSE_INVERSE block
            :rtype: Pose_inverse instance

            Invert the pose on the input signal.

            For example::

                gain = bd.POSE_INVERSE()
            
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
        :return: a FORWARD_KINEMATICS block
        :rtype: Foward_Kinematics instance

        Robot arm forward kinematic model.

        **Block ports**

            :input q: Joint configuration vector as an ndarray.

            :output T: End-effector pose as an SE(3) object
        
        """
        ...


    # roboticstoolbox.blocks.arm.IKine
    def IKINE(self, robot=None, q0=None, useprevious=True, ik=None, seed=None, **blockargs):
        """
        :param robot: Robot model, defaults to None
        :type robot: Robot subclass, optional
        :param q0: Initial joint angles, defaults to None
        :type q0: array_like(n), optional
        :param useprevious: Use previous IK solution as q0, defaults to True
        :type useprevious: bool, optional
        :param ik: Specify an IK function, defaults to 'ikine_LM'
        :type ik: callable f(T)
        :param seed: random seed for solution
        :type seed: int
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: an INVERSE_KINEMATICS block
        :rtype: Inverse_Kinematics instance

        Robot arm inverse kinematic model.

        The block has one input port:

            1. End-effector pose as an SE(3) object

        and one output port:

            1. Joint configuration vector as an ndarray.


        
        """
        ...


    # roboticstoolbox.blocks.arm.Jacobian
    def JACOBIAN(self, robot, frame='0', inverse=False, pinv=False, transpose=False, **blockargs):
        """
        :param robot: Robot model
        :type robot: Robot subclass
        :param frame: Frame to compute Jacobian for, one of: '0' [default], 'e'
        :type frame: str, optional
        :param inverse: output inverse of Jacobian, defaults to False
        :type inverse: bool, optional
        :param pinv: output pseudo-inverse of Jacobian, defaults to False
        :type pinv: bool, optional
        :param transpose: output transpose of Jacobian, defaults to False
        :type transpose: bool, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a JACOBIAN block
        :rtype: Jacobian instance

        Robot arm Jacobian.

        The block has one input port:

            1. Joint configuration vector as an ndarray.

        and one output port:

            1. Jacobian matrix as an ndarray(6,n)

        .. notes::
            - Only one of ``inverse`` or ``pinv`` can be True
            - ``inverse`` or ``pinv`` can be used in conjunction with ``transpose``
            - ``inverse`` requires that the Jacobian is square
            - If ``inverse`` is True and the Jacobian is singular a runtime
              error will occur.
        
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
        :return: a FORWARD_DYNAMICS block
        :rtype: Foward_Dynamics instance

        Robot arm forward dynamics model.

        The block has one input port:

            1. Joint force/torque as an ndarray.

        and three output ports:

            1. joint configuration
            2. joint velocity
            3. joint acceleration


        
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
        :return: an INVERSE_DYNAMICS block
        :rtype: Inverse_Dynamics instance

        Robot arm forward dynamics model.

        The block has three input port:

            1. Joint configuration vector as an ndarray.
            2. Joint velocity vector as an ndarray.
            3. Joint acceleration vector as an ndarray.

        and one output port:

            1. joint torque/force

        .. TODO:: end-effector wrench input, base wrench output, payload input
        
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
        :return: a GRAVLOAD block
        :rtype: Gravload instance

        Robot arm gravity torque.

        The block has one input port:

            1. Joint configuration vector as an ndarray.

        and one output port:

            1. joint torque/force due to gravity

        
        """
        ...


    # roboticstoolbox.blocks.arm.Gravload_X
    def GRAVLOAD_X(self, robot, representation='rpy/xyz', gravity=None, **blockargs):
        """

        :param robot: Robot model
        :type robot: Robot subclass
        :param gravity: gravitational acceleration
        :type gravity: float
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a GRAVLOAD block
        :rtype: Gravload instance

        Robot arm gravity torque.

        The block has one input port:

            1. Joint configuration vector as an ndarray.

        and one output port:

            1. joint torque/force due to gravity

        
        """
        ...


    # roboticstoolbox.blocks.arm.Inertia
    def INERTIA(self, robot, **blockargs):
        """

        :param robot: Robot model
        :type robot: Robot subclass
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: an INERTIA block
        :rtype: Inertia instance

        Robot arm inertia matrix.

        The block has one input port:

            1. Joint configuration vector as an ndarray.

        and one output port:

            1. Joint-space inertia matrix :math:`\mat{M}(q)`

        
        """
        ...


    # roboticstoolbox.blocks.arm.Inertia_X
    def INERTIA_X(self, robot, representation='rpy/xyz', pinv=False, **blockargs):
        """

        :param robot: Robot model
        :type robot: Robot subclass
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: an INERTIA_X block
        :rtype: Inertia_X instance

        Robot arm task-space inertia matrix.

        The block has one input port:

            1. Joint configuration vector as an ndarray.

        and one output port:

            1. Task-space inertia matrix :math:`\mat{M}_x(q)`

        
        """
        ...


    # roboticstoolbox.blocks.arm.FDyn_X
    def FDYN_X(self, robot, q0=None, gravcomp=False, velcomp=False, representation='rpy/xyz', **blockargs):
        """
        :param robot: Robot model
        :type robot: Robot subclass
        :param end: Link to compute pose of, defaults to end-effector
        :type end: Link or str
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a FDYN_X block
        :rtype: FDyn_X instance

        Robot arm forward dynamics model.

        The block has one input port:

            1. Applied end-effector wrench as an ndarray.

        and three output ports:

            1. task space pose
            2. task space velocity
            3. task space acceleration


        
        """
        ...


    # roboticstoolbox.blocks.arm.ArmPlot
    def ARMPLOT(self, robot=None, q0=None, backend=None, **blockargs):
        """
        :param robot: Robot model
        :type robot: Robot subclass
        :param backend: RTB backend name, defaults to 'pyplot'
        :type backend: str, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: An ARMPLOT block
        :rtype: ArmPlot instance


        Create a robot animation.

        Notes:

            - Uses RTB ``plot`` method

           Example of vehicle display (animated).  The label at the top is the
           block name.
        
        """
        ...


    # roboticstoolbox.blocks.mobile.Bicycle
    def BICYCLE(self, L=1, speed_max=inf, accel_max=inf, steer_max=1.413716694115407, x0=None, **blockargs):
        """
        Create a vehicle model with Bicycle kinematics.

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
        :return: a BICYCLE block
        :rtype: Bicycle instance


        Bicycle kinematic model with state/configuration :math:`[x, y, \theta]`.

        **Block ports**

            :input v: Vehicle speed (metres/sec).  The velocity limit ``speed_max``
                and acceleration limit ``accel_max`` is
                applied to this input.
            :input γ: Steered wheel angle (radians).  The steering limit ``steer_max``
                is applied to this input.

            :output q: configuration (x, y, θ)

        :seealso: :class:`roboticstoolbox.mobile.Bicycle` :class:`Unicycle` :class:`DiffSteer`
        
        """
        ...


    # roboticstoolbox.blocks.mobile.Unicycle
    def UNICYCLE(self, w=1, speed_max=inf, accel_max=inf, steer_max=inf, a=0, x0=None, **blockargs):
        """
        Create a vehicle model with Unicycle kinematics.

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
        :return: a UNICYCLE block
        :rtype: Unicycle instance

        Unicycle kinematic model with state/configuration :math:`[x, y, \theta]`.

        **Block ports**

            :input v: Vehicle speed (metres/sec).  The velocity limit ``speed_max`` and
                acceleration limit ``accel_max`` is
                applied to this input.
            :input ω: Angular velocity (radians/sec).  The steering limit ``steer_max``
                is applied to this input.

            :output q: configuration (x, y, θ)

        :seealso: :class:`roboticstoolbox.mobile.Unicycle` :class:`Bicycle` :class:`DiffSteer`
        
        """
        ...


    # roboticstoolbox.blocks.mobile.DiffSteer
    def DIFFSTEER(self, w=1, R=1, speed_max=inf, accel_max=inf, steer_max=None, a=0, x0=None, **blockargs):
        """
        Create a differential steer vehicle model

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
        :return: a DIFFSTEER block
        :rtype: DiffSteer instance

        Unicycle kinematic model with state :math:`[x, y, \theta]`, with
        inputs given as wheel angular velocity.

        **Block ports**

            :input ωL: Left-wheel angular velocity (radians/sec).
            :input ωR: Right-wheel angular velocity (radians/sec).

            :output q: configuration (x, y, θ)

        The resulting forward velocity and turning rate from ωL and ωR have
        the velocity limit ``speed_max`` and acceleration limit ``accel_max``
        applied, as well as the turning rate limit ``steer_max``.

        .. note:: Wheel velocity is defined such that if both are positive the vehicle
              moves forward.

        :seealso: :class:`roboticstoolbox.mobile.Unicycle` :class:`Bicycle` :class:`Unicycle`
        
        """
        ...


    # roboticstoolbox.blocks.mobile.VehiclePlot
    def VEHICLEPLOT(self, animation=None, path=None, labels=['X', 'Y'], square=True, init=None, scale='auto', **blockargs):
        """
        Create a vehicle animation

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
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A VEHICLEPLOT block
        :rtype: VehiclePlot instance

        Create a vehicle animation similar to the figure below.

        **Block ports**

            :input q: configuration (x, y, θ)

        Notes:

            - The ``init`` function is called after the axes are initialized
              and can be used to draw application specific detail on the
              plot. In the example below, this is the dot and star.
            - A dynamic trail, showing path to date can be animated if
              the option ``path`` is set to a linestyle.

        .. figure:: ../../figs/rvc4_4.gif
           :width: 500px
           :alt: example of generated graphic

           Example of vehicle display (animated).  The label at the top is the
           block name.
        
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
        :return: a MULTIROTOR block
        :rtype: MultiRotor instance

        Dynamic model of a multi-rotor flying robot, includes rotor flapping.

        **Block ports**

            :input ω: a vector of input rotor speeds in (radians/sec).  These are,
                looking down, clockwise from the front rotor which lies on the x-axis.

            :output x: a dictionary signal with the following items:

                - ``x`` pose in the world frame as :math:`[x, y, z, \theta_Y, \theta_P, \theta_R]`
                - ``vb`` translational velocity in the world frame (metres/sec)
                - ``w`` angular rates in the world frame as yaw-pitch-roll rates (radians/second)
                - ``a1s`` longitudinal flapping angles (radians)
                - ``b1s`` lateral flapping angles (radians)

        **Model parameters**

        The dynamic model is a dict with the following key/value pairs.

        ===========   ==========================================
        key           description
        ===========   ==========================================
        ``nrotors``   Number of rotors (even integer)
        ``J``         Flyer rotational inertia matrix (3x3)
        ``h``         Height of rotors above CoG
        ``d``         Length of flyer arms
        ``nb``        Number of blades per rotor
        ``r``         Rotor radius
        ``c``         Blade chord
        ``e``         Flapping hinge offset
        ``Mb``        Rotor blade mass
        ``Mc``        Estimated hub clamp mass
        ``ec``        Blade root clamp displacement
        ``Ib``        Rotor blade rotational inertia
        ``Ic``        Estimated root clamp inertia
        ``mb``        Static blade moment
        ``Ir``        Total rotor inertia
        ``Ct``        Non-dim. thrust coefficient
        ``Cq``        Non-dim. torque coefficient
        ``sigma``     Rotor solidity ratio
        ``thetat``    Blade tip angle
        ``theta0``    Blade root angle
        ``theta1``    Blade twist angle
        ``theta75``   3/4 blade angle
        ``thetai``    Blade ideal root approximation
        ``a``         Lift slope gradient
        ``A``         Rotor disc area
        ``gamma``     Lock number
        ===========   ==========================================

        .. note::
            - SI units are used.
            - Based on MATLAB code developed by Pauline Pounds 2004.

        :References:
            - Design, Construction and Control of a Large Quadrotor micro air vehicle.
              P.Pounds, `PhD thesis <https://openresearch-repository.anu.edu.au/handle/1885/146543>`_
              Australian National University, 2007.

        :seealso: :class:`MultiRotorMixer` :class:`MultiRotorPlot`
        
        """
        ...


    # roboticstoolbox.blocks.uav.MultiRotorMixer
    def MULTIROTORMIXER(self, model=None, wmax=1000, wmin=5, **blockargs):
        """
        Create a speed mixer block for a multi-rotor flying vehicle.

        :param model: A dictionary of vehicle geometric and inertial properties
        :type model: dict
        :param maxw: maximum rotor speed in rad/s, defaults to 1000
        :type maxw: float
        :param minw: minimum rotor speed in rad/s, defaults to 5
        :type minw: float
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a MULTIROTORMIXER block
        :rtype: MultiRotorMixer instance

        This block converts airframe moments and total thrust into a 1D
        array of rotor speeds which can be input to the MULTIROTOR block.

        **Block ports**

            :input 𝛕r: roll torque
            :input 𝛕p: pitch torque
            :input 𝛕y: yaw torque
            :input T: total thrust

            :output ω: 1D array of rotor speeds

        **Model parameters**

        The model is a dict with the following key/value pairs.

        ===========   ==========================================
        key           description
        ===========   ==========================================
        ``nrotors``   Number of rotors (even integer)
        ``h``         Height of rotors above CoG
        ``d``         Length of flyer arms
        ``r``         Rotor radius
        ===========   ==========================================

        .. note::
            - Based on MATLAB code developed by Pauline Pounds 2004.

        :seealso: :class:`MultiRotor` :class:`MultiRotorPlot`
        
        """
        ...


    # roboticstoolbox.blocks.uav.MultiRotorPlot
    def MULTIROTORPLOT(self, model, scale=[-2, 2, -2, 2, 10], flapscale=1, projection='ortho', **blockargs):
        """
        Create a block that displays/animates a multi-rotor flying vehicle.

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
        :return: a MULTIROTORPLOT block
        :rtype: MultiRotorPlot instance

        Animate a multi-rotor flying vehicle using Matplotlib graphics.  The
        rotors are shown as circles and their orientation includes rotor
        flapping which can be exagerated by ``flapscale``.

        .. figure:: ../../figs/multirotorplot.png
           :width: 500px
           :alt: example of generated graphic

           Example of quad-rotor display.

        **Block ports**

            :input x: a dictionary signal that includes the item:

                - ``x`` pose in the world frame as :math:`[x, y, z, 	heta_Y, 	heta_P, 	heta_R]`
                - ``a1s`` rotor flap angle
                - ``b1s`` rotor flap angle

        **Model parameters**

        The model is a dict with the following key/value pairs.

        ===========   ==========================================
        key           description
        ===========   ==========================================
        ``nrotors``   Number of rotors (even integer)
        ``h``         Height of rotors above CoG
        ``d``         Length of flyer arms
        ``r``         Rotor radius
        ===========   ==========================================

        .. note::
            - Based on MATLAB code developed by Pauline Pounds 2004.

        :seealso: :class:`MultiRotor` :class:`MultiRotorMixer`
        
        """
        ...


    # roboticstoolbox.blocks.spatial.Tr2Delta
    def TR2DELTA(self, **blockargs):
        """
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a TR2DELTA block
        :rtype: Tr2Delta instance

        Difference between T1 and T2 as a 6-vector

        The block has two input port:

            1. T1 as an SE3.
            2. T2 as an SE3.

        and one output port:

            1. delta as an ndarray(6,n)

        :seealso: :func:`spatialmath.base.tr2delta`
        
        """
        ...


    # roboticstoolbox.blocks.spatial.Delta2Tr
    def DELTA2TR(self, **blockargs):
        """
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a DELTA2TR block
        :rtype: Delta2Tr instance

        Delta to SE(3)

        The block has one input port:

            1. delta as an ndarray(6,n)

        and one output port:

            1. T as an SE3

        :seealso: :func:`spatialmath.base.delta2tr`
        
        """
        ...


    # roboticstoolbox.blocks.spatial.Point2Tr
    def POINT2TR(self, T, **blockargs):
        """
        :param T: the transform
        :type T: SE3
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a POINT2TR block
        :rtype: Point2Tr instance

        The block has one input port:

            1. a 3D point as an ndarray(3)

        and one output port:

            1. T as an SE3 with its position part replaced by the input

        :seealso: :func:`spatialmath.base.delta2tr`
        
        """
        ...


    # roboticstoolbox.blocks.spatial.TR2T
    def TR2T(self, **blockargs):
        """
        :param T: the transform
        :type T: SE3
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a POINT2TR block
        :rtype: Point2Tr instance

        The block has one input port:

            1. a 3D point as an ndarray(3)

        and one output port:

            1. T as an SE3 with its position part replaced by the input

        :seealso: :func:`spatialmath.base.delta2tr`
        
        """
        ...


    # roboticstoolbox.blocks.spatial.Traj
    def TRAJ(self, y0=0, yf=1, T=None, time=False, traj='trapezoidal', **blockargs):
        """

        :param y0: initial value, defaults to 0
        :type y0: array_like(m), optional
        :param yf: final value, defaults to 1
        :type yf: array_like(m), optional
        :param T: time vector or number of steps, defaults to None
        :type T: array_like or int, optional
        :param time: x is simulation time, defaults to False
        :type time: bool, optional
        :param traj: trajectory type, one of: 'trapezoidal' [default], 'quintic'
        :type traj: str, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: TRAJ block
        :rtype: Traj instance

        Create a trajectory block.

        A block that generates a trajectory using a trapezoidal or quintic
        polynomial profile.

        
        """
        ...


    # roboticstoolbox.blocks.spatial.JTraj
    def JTRAJ(self, q0, qf, qd0=None, qdf=None, T=None, **blockargs):
        """
        Compute a joint-space trajectory

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
        :return: TRAJ block
        :rtype: Traj instance

        - ``tg = jtraj(q0, qf, N)`` is a joint space trajectory where the joint
        coordinates vary from ``q0`` (M) to ``qf`` (M).  A quintic (5th order)
        polynomial is used with default zero boundary conditions for velocity and
        acceleration.  Time is assumed to vary from 0 to 1 in ``N`` steps.

        - ``tg = jtraj(q0, qf, t)`` as above but ``t`` is a uniformly-spaced time
        vector

        The return value is an object that contains position, velocity and
        acceleration data.

        Notes:

        - The time vector, if given, scales the velocity and acceleration outputs
        assuming that the time vector starts at zero and increases
        linearly.

        :seealso: :func:`ctraj`, :func:`qplot`, :func:`~SerialLink.jtraj`
        
        """
        ...


    # roboticstoolbox.blocks.spatial.LSPB
    def LSPB(self, q0, qf, V=None, T=None, **blockargs):
        """
        Compute a joint-space trajectory

        :param q0: initial joint coordinate
        :type q0: array_like(n)
        :param qf: final joint coordinate
        :type qf: array_like(n)
        :param T: time vector or number of steps, defaults to None
        :type T: array_like or int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: LSPB block
        :rtype: LSPB instance

        - ``tg = jtraj(q0, qf, N)`` is a joint space trajectory where the joint
        coordinates vary from ``q0`` (M) to ``qf`` (M).  A quintic (5th order)
        polynomial is used with default zero boundary conditions for velocity and
        acceleration.  Time is assumed to vary from 0 to 1 in ``N`` steps.

        - ``tg = jtraj(q0, qf, t)`` as above but ``t`` is a uniformly-spaced time
        vector

        The return value is an object that contains position, velocity and
        acceleration data.

        Notes:

        - The time vector, if given, scales the velocity and acceleration outputs
        assuming that the time vector starts at zero and increases
        linearly.

        :seealso: :func:`ctraj`, :func:`qplot`, :func:`~SerialLink.jtraj`
        
        """
        ...


    # roboticstoolbox.blocks.spatial.CTraj
    def CTRAJ(self, T1, T2, T, trapezoidal=True, **blockargs):
        """
        [summary]

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
        :return: CTRAJ block
        :rtype: CTraj instance

        Create a Cartesian motion block.

        The block outputs a pose that varies smoothly from ``T1`` to ``T2`` over
        the course of ``T`` seconds.

        If ``T`` is not given it defaults to the simulation time.

        If ``trapezoidal`` is True then a trapezoidal motion profile is used along the path
        to provide initial acceleration and final deceleration.  Otherwise,
        motion is at constant velocity.

        :seealso: :method:`SE3.interp`

        
        """
        ...


    # roboticstoolbox.blocks.spatial.CirclePath
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
        :return: TRAJ block
        :rtype: Traj instance

        Create a circular motion block.

        The block outputs the coordinates of a point moving in a circle of
        radius ``r`` centred at ``centre`` and parallel to the xy-plane.

        By default the output is a 3-vector :math:`(x, y, z)` but if
        ``pose`` is an ``SE3`` instance the output is a copy of that pose with
        its translation set to the coordinate of the moving point.  This is the
        motion of a frame with fixed orientation following a circular path.

        
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
