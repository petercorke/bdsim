"""
Transfer blocks:

- have inputs and outputs
- have state variables
- are a subclass of ``TransferBlock`` |rarr| ``Block``

"""

import numpy as np
import scipy.signal
import math
from math import sin, cos, atan2, sqrt, pi
import matplotlib.pyplot as plt
from spatialmath import base

from bdsim.components import TransferBlock, SubsystemBlock


class Integrator(TransferBlock):
    r"""
    :blockname:`INTEGRATOR`

    Continuous-time integrator.

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
            - any
            - :math:`y`

    Output is the time integral of the input :math:`y(t) = \int_0^T x(t) dt`.

    The state can be a scalar or a vector. The initial state, and type, is given by
    ``x0``.  The shape of the input signal must match ``x0``.

    The minimum and maximum values can be:

        - a scalar, in which case the same value applies to every element of
          the state vector, or
        - a vector, of the same shape as ``x0`` that applies elementwise to
          the state.

    .. note:: The minimum and maximum prevent integration outside the limits,
        but assume that the initial state is within the limits.

    :seealso: :class:`Deriv`
    """

    nin = 1
    nout = 1

    def __init__(self, x0=0, gain=1.0, min=None, max=None, **blockargs):
        """
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
        super().__init__(**blockargs)

        if isinstance(x0, (int, float)):
            x0 = np.r_[x0]

        elif isinstance(x0, np.ndarray):
            if x0.ndim > 1:
                raise ValueError("state must be a 1D vector")
        else:
            x0 = base.getvector(x0)

        self.nstates = x0.shape[0]

        if min is not None:
            min = base.getvector(min, self.nstates)
        if max is not None:
            max = base.getvector(max, self.nstates)

        self._x0 = x0
        self.min = min
        self.max = max
        self.gain = gain

        self._x0 = x0
        self.min = min
        self.max = max
        # print("nstates", self.nstates)

    def output(self, t, u, x):
        return [x]

    def deriv(self, t, u, x):
        xd = base.getvector(u[0])
        if self.min is not None:
            xd[x < self.min] = 0
        if self.max is not None:
            xd[x > self.max] = 0

        return self.gain * xd


class PoseIntegrator(TransferBlock):
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

    def __init__(self, x0=None, **blockargs):
        r"""
        :param x0: Initial pose, defaults to null
        :type x0: SE3, Twist3, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(**blockargs)

        if x0 is None:
            x0 = np.zeros((6,))

        self.nstates = len(x0)

        self._x0 = x0

    def output(self, t, u, x):
        return [Twist3(x).SE3(1)]

    def deriv(self, t, u, x):
        return u[0]


# ------------------------------------------------------------------------ #


class LTI_SS(TransferBlock):
    r"""
    :blockname:`LTI_SS`

    Continuous-time state-space LTI dynamics

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
            - :math:`u`
        *   - Output
            - 0
            - float, ndarray
            - :math:`y`

    Implements the dynamics of a multi-input multi-output (MIMO) linear
    time invariant (LTI) system described in statespace form.  The dynamics are given by

    .. math::

        \dot{x} &= A x + B u

        y &= C x

    The order of the states in ``x0`` is consistent with controller canonical
    form.  A direct passthrough component, typically :math:`D`, is not allowed in order
    to avoid algebraic loops.

    Examples::

        lti = bd.LTI_SS(A=-2, B=1, C=-1)

    is the system :math:`\dot{x}=-2x+u, y=-x`.
    """

    nin = 1
    nout = 1

    def __init__(self, A=None, B=None, C=None, x0=None, **blockargs):
        r"""
        :param N: numerator coefficients, defaults to 1
        :type N: array_like, optional
        :param D: denominator coefficients, defaults to [1,1]
        :type D: array_like, optional
        :param x0: initial states, defaults to None
        :type x0: array_like, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        # print('in SS constructor')
        assert A.shape[0] == A.shape[1], "A must be square"
        n = A.shape[0]
        if len(B.shape) == 1:
            nin = 1
            B = B.reshape((n, 1))
        else:
            nin = B.shape[1]
        assert B.shape[0] == n, "B must have same number of rows as A"

        if len(C.shape) == 1:
            nout = 1
            assert C.shape[0] == n, "C must have same number of columns as A"
            C = C.reshape((1, n))
        else:
            nout = C.shape[0]
            assert C.shape[1] == n, "C must have same number of columns as A"

        super().__init__(**blockargs)

        self.A = A
        self.B = B
        self.C = C

        self.nstates = A.shape[0]

        if x0 is None:
            self._x0 = np.zeros((self.nstates,))
        else:
            self._x0 = x0

    def output(self, t, u, x):
        return list(self.C @ x)

    def deriv(self, t, u, x):
        xd = self.A @ x + self.B @ np.array(u)
        return xd.flatten()


# ------------------------------------------------------------------------ #


class LTI_SISO(LTI_SS):
    r"""
    :blockname:`LTI_SISO`

    Continuous-time SISO LTI dynamics.

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
            - float
            - :math:`u`
        *   - Output
            - 0
            - float
            - :math:`y`

    Implements the dynamics of a single-input single-output (SISO) linear
    time invariant (LTI) system described by numerator and denominator
    polynomial coefficients.  The dynamics are given by

    .. math::

        \frac{Y(s)}{U(s)} = \frac{N(s)}{D(s)}

    Coefficients are given in the order from highest order to zeroth
    order, ie. :math:`2s^2 - 4s +3` is ``[2, -4, 3]``.

    Only proper transfer functions, where order of numerator is less
    than denominator are allowed.

    The order of the states in ``x0`` is consistent with controller canonical
    form.

    Examples::

        lti = bd.LTI_SISO(N=[1, 2], D=[2, 3, -4])

    is the transfer function :math:`\frac{s+2}{2s^2+3s-4}`.
    """

    nin = 1
    nout = 1

    def __init__(self, N=1, D=[1, 1], x0=None, **blockargs):
        r"""
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
        # print('in SISO constscutor')

        if not isinstance(N, list):
            N = [N]
        if not isinstance(D, list):
            D = [D]
        self.N = N
        self.D = N
        n = len(D) - 1
        nn = len(N)
        if x0 is None:
            x0 = np.zeros((n,))
        assert nn <= n, "direct pass through is not supported"

        # convert to numpy arrays
        # N = np.r_[np.zeros((len(D) - len(N),)), np.array(N)]
        N = np.array(N)

        D = np.array(D)

        # normalize the coefficients to obtain
        #
        #   b_0 s^n + b_1 s^(n-1) + ... + b_n
        #   ---------------------------------
        #   a_0 s^n + a_1 s^(n-1) + ....+ a_n

        # normalize so leading coefficient of denominator is one
        # D0 = D[0]
        # D = D / D0
        # N = N / D0

        # A = np.eye(len(D) - 1, k=1)  # control canonic (companion matrix) form
        # A[-1, :] = -D[1:]

        # B = np.zeros((n, 1))
        # B[-1] = 1

        # C = (N[1:] - N[0] * D[1:]).reshape((1, n))

        A, B, C, D = scipy.signal.tf2ss(N, D)

        self.num = N
        self.den = D

        if len(np.flatnonzero(D)) > 0:
            raise ValueError("D matrix is not zero")

        super().__init__(A=A, B=B, C=C, x0=x0, **blockargs)

        if self.verbose:
            print("A=", A)
            print("B=", B)
            print("C=", C)

        def change_param(self, param, newvalue):
            if param == "num":
                self.num = newvalue
            elif param == "den":
                self.den = newvalue
            self.A, self.B, self.C, self.D = scipy.signal.tf2ss(self.num, self.den)

        self.add_param("num", change_param)
        self.add_param("den", change_param)


# ------------------------------------------------------------------------ #

from bdsim.blocks.connections import SubSystem


class Deriv(SubsystemBlock):
    r"""
    :blockname:`DERIV`

    Continuous-time derivative.

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
            - float
            - :math:`x`
        *   - Output
            - 0
            - float
            - :math:`y`

    Implements the dynamics of a derivative filter, but to be causal it has a single
    pole given by ``alpha``.  The dynamics is

    .. math:: \frac{s}{\frac{s}{\alpha} + 1}

    It is implemented as a subsystem with an integrator and a feedback loop.  The
    initial state of the integrator is ``x0``.

    :seealso: :class:`Integrator`
    """

    nin = 1
    nout = 1

    def __init__(self, alpha, x0=0, **blockargs):
        r"""
        :param alpha: filter pole
        :type alpha: float
        :param x0: initial states, defaults to 0
        :type x0: float, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(**blockargs)
        self.type = "subsystem"

        bd = self.bd.runtime.blockdiagram()

        integrator = bd.INTEGRATOR(x0=x0)
        inp = bd.INPORT(1)
        outp = bd.OUTPORT(1)
        sum = bd.SUM("+-")
        gain = bd.GAIN(1.0 / alpha)
        bd.connect(inp, sum[0])
        bd.connect(sum[0], gain)
        bd.connect(gain, outp, integrator)
        bd.connect(integrator, sum[1])

        # get references to the input and output port blocks
        self.inport = inp
        self.outport = outp
        self.subsystem = bd

        self.ssname = "derivative"


class PID(SubSystem):
    r"""
    :blockname:`PID`

    Continuous-time PID control.

    :inputs: 2
    :outputs: 1
    :states: 2

    .. list-table::
        :header-rows: 1

        *   - Port type
            - Port number
            - Types
            - Description
        *   - Input
            - 0
            - float
            - :math:`x`, plant output
        *   - Input
            - 1
            - float
            - :math:`x^*`, demanded output
        *   - Output
            - 0
            - any
            - :math:`u`, control to plant

    Implements the dynamics of a PID controller:

    .. math::

        e &= x^* - x

        u &= Pe + D \frac{d}{dt} e + I \int e dt

    To reduce noise the derivative is computed by a first-order system

    .. math::

        \frac{s}{s/a + 1}

    where the pole :math:`a=` ``D_filt`` can be positioned appropriately.

    If ``I_limit`` is provided it specifies the limits of the integrator
    state, before multiplication by ``I``.  If ``I_limit`` is:

    * a scalar :math:`a` the integrator state is clipped to the interval :math:`[-a, a]`
    * a 2-tuple :math:`(a,b)` the integrator state is clipped to the interval :math:`[a, b]`

    If ``I_band`` is provided the integrator is reset to zero whenever the
    error :math:`e` is outside the band given by ``I_band`` which is:

    * a scalar :math:`s` the band is the interval :math:`[-s, s]`
    * a 2-tuple :math:`(a,b)` the band is the interval :math:`[a, b]`


    Examples::

        pid = bd.PID(P=3, D=2, I=1)

    :seealso: :class:`Deriv`
    """

    class _ID(LTI_SS):
        def __init__(
            self,
            D: float = 0.0,
            I: float = 0.0,
            D_pole=1,
            I_limit=None,
            I_band=0,
            **blockargs,
        ):

            self.D = D
            self.I = I
            self.D_pole = D_pole
            self.I_limit = I_limit
            self.I_band = I_band

            A = np.zeros((2, 2))
            B = np.zeros((2, 1))
            C = np.zeros((1, 2))

            super().__init__(A=A, B=B, C=C, **blockargs)

            if self.verbose:
                print("A=", A)
                print("B=", B)
                print("C=", C)

        def output(self, t, u, x):
            e = u[1] - u[0]
            return list(self.C @ x)

        def deriv(self, t, u, x):
            return self.A @ x + self.B @ np.array(u)

    nin = 1
    nout = 1

    def __init__(
        self,
        P: float = 0.0,
        D: float = 0.0,
        I: float = 0.0,
        D_pole=1,
        I_limit=None,
        I_band=0,
        name="PID",
        **blockargs,
    ):
        r"""
        :param P: proportional gain, defaults to 0
        :type P: float
        :param D: derivative gain, defaults to 0
        :type D: float
        :param I: integral gain, defaults to 0
        :type I: float
        :param D_pole: filter pole for derivative estimate, defaults to 1 rad/s
        :type D_pole: float
        :param I_limit: integral limit
        :type I_limit: float
        :param I_band: band within which integral action is active
        :type I_band: float
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """

        subsystem = self.bd.runtime.blockdiagram()

        bd = blockargs["bd"]
        blockargs.pop("bd")
        Pblock = subsystem.GAIN(P)
        IDblock = self._ID(
            D=D,
            I=I,
            D_pole=D_pole,
            I_limit=I_limit,
            I_band=I_band,
            bd=subsystem,
            **blockargs,
        )
        sum = subsystem.SUM("++")
        Input = subsystem.INPORT(1)
        Output = subsystem.OUTPORT(1)

        subsystem.connect(Input, Pblock, IDblock)
        subsystem.connect(Pblock, sum[0])
        subsystem.connect(IDblock, sum[1])
        subsystem.connect(sum, Output)

        subsystem.report()
        super().__init__(subsystem, name=name, bd=bd)


if __name__ == "__main__":

    from bdsim import BDSim

    sim = BDSim(hold=False)
    bd = sim.blockdiagram()
    deriv = bd.DERIV(alpha=0.1, verbose=True)

    c = bd.WAVEFORM(wave="sine", freq=1)
    s = bd.SCOPE(2)
    bd.connect(c, deriv, s[0])
    bd.connect(deriv, s[1])

    bd.compile()
    bd.report_summary()
    out = sim.run(bd, 10, dt=0.02)

    import matplotlib.pyplot as plt

    plt.plot(out.t, out.x)
    sim.done(bd, block=True)

    # sim = BDSim()
    # bd = sim.blockdiagram()
    # pid = bd.PID(P=2, D=0.01, verbose=True)

    # c = bd.CONSTANT(1)
    # s = bd.SCOPE()
    # bd.connect(c, pid)
    # bd.connect(pid, s)

    # bd.compile(report=True)
    # bd.report()

    # from pathlib import Path

    # exec(
    #     open(Path(__file__).parent.parent.parent / "tests" / "test_transfers.py").read()
    # )
