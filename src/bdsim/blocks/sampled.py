r"""
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

from typing import Any, Callable

from bdsim.components import SampledBlock, Clock, SubsystemBlock, deprecated_block
from bdsim.blocks.continuous import _tf2ss

Vector1D = int | float | tuple[float, ...] | list[float] | np.ndarray

# ------------------------------------------------------------------------


class ZOH(SampledBlock):
    r"""
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

    def __init__(self, clock: Clock, x0: Vector1D = 0, **blockargs: Any) -> None:
        r"""
        :param clock: clock source
        :type clock: Clock
        :param x0: Initial value of the hold, defaults to 0
        :type x0: array_like, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(clock=clock, nin=1, nout=1, x0=x0, **blockargs)

        # print('nstates', self.nstates)

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        # print('* output, x is ', self._x)
        return [x]

    def next(self, t: float, inputs: list[Any], x: np.ndarray) -> np.ndarray:
        u = smb.getvector(inputs[0])
        return u  # must be an ndarray


# ------------------------------------------------------------------------ #


class Integrator_S(SampledBlock):
    r"""
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

    This block implements the dynamics of a discrete-time integrator with gain :math:`k`, which is given by

    .. math::

        \begin{aligned}
        x_{k+1} &= x_k + k \cdot u_k \cdot T \\
        y_k &= x_k
        \end{aligned}

    The state can be a scalar or a vector. The initial state, and type, is given by
    ``x0``.  The shape of the input signal must match ``x0``.

    The minimum and maximum output values can be:

        - a scalar, in which case the same value applies to every element of
          the state vector, or
        - a vector, of the same shape as ``x0`` that applies elementwise to
          the state.

    .. note:: The minimum and maximum prevent integration outside the limits,
        but assume that the initial state is within the limits.

    Integration can be controlled by an ``enable`` function::

        enable(t, u, x): bool

    where the arguments are current time, a list of inputs to the integrator block and the state
    as an ndarray.  If the function returns False then the integrator's state is set
    to zero.
    """

    nin = 1
    nout = 1

    def __init__(
        self,
        clock: Clock,
        x0: Vector1D = 0,
        gain: float = 1.0,
        min: Vector1D | None = None,
        max: Vector1D | None = None,
        enable: Callable[[float, list[Any], np.ndarray], bool] | None = None,
        **blockargs: Any,
    ) -> None:
        r"""
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
        :param enable: function to enable or disable integration
        :type enable: callable
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        super().__init__(clock=clock, x0=x0, **blockargs)

        if min is not None:
            min = smb.getvector(min, len(self._x0))
        if max is not None:
            max = smb.getvector(max, len(self._x0))

        self.min = min
        self.max = max
        self.gain: float = gain
        self.T = clock.T

        self.enable = enable
        if enable is not None and not callable(enable):
            raise ValueError("enable must be callable")

    def output(self, t: float, u: list[Any], x: np.ndarray) -> list[Any]:
        return [x]

    def next(self, t: float, u: list[Any], x: np.ndarray) -> np.ndarray:
        # compute next state
        xnext = x + self.gain * self.T * np.array(u[0])

        # apply enable function if it exists
        if self.enable is not None and not self.enable(t, u, x):
            # if enable function returns False then integrator output is jammed at zero
            return np.zeros(x.shape)

        # apply limits if they exist
        if self.min is not None or self.max is not None:
            xnext = np.clip(xnext, self.min, self.max)
        return xnext


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

        super().__init__(clock=clock, x0=x0, **blockargs)

        # print("nstates", self.nstates, x0)

    def output(self, t: float, u: list[Any], x: np.ndarray) -> list[SE3]:
        return [Twist3(x).SE3()]

    def next(self, t: float, u: list[Any], x: np.ndarray) -> np.ndarray:
        assert self._clock is not None
        T_delta: SE3 = SE3.Delta(u[0] * self._clock.T)
        pose = Twist3(x).SE3() * T_delta
        return Twist3(pose).A


# ------------------------------------------------------------------------ #


class Deriv_S(SampledBlock):
    r"""
    :blockname:`DERIV_S`

    Discrete-time derivative.

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

    Implements the dynamics of a derivative filter, but to be causal (proper) it includes a first-order
    low-pass filter.  The dynamics are

    .. math:: \frac{1 - z^{-1}}{T}

    where :math:`T` is the sampling time.

    Unlike the continuous-time derivative blocks, this one includes no smoothing filter.

    The initial output of the derivative block is given by the initial state ``x0``.

    .. versionadded:: 1.2.0

    :seealso: :class:`Integrator`
    """

    nin = 1
    nout = 1

    def __init__(
        self,
        clock: Clock,
        x0: Vector1D = 0,
        gain: float = 1.0,
        **blockargs: Any,
    ) -> None:
        r"""
        :param clock: clock source
        :type clock: Clock
        :param x0: initial states, defaults to 0
        :type x0: array_like, optional
        :param gain: gain or scaling factor, defaults to 1
        :type gain: float
        :param kwargs: |BlockOptions|
        :type kwargs: dict
        """
        super().__init__(clock=clock, x0=x0, feedthrough=True, **blockargs)
        self.gain = gain

    def output(self, t: float, u: list[Any], x: np.ndarray) -> list[Any]:
        return [
            self.gain * (u[0] - x) / self.T
        ]  # output is current input minus previous input (state)

    def next(self, t: float, u: list[Any], x: np.ndarray) -> np.ndarray:
        # next state is current input, so output is difference between current and previous input
        return np.array(u[0])


# ------------------------------------------------------------------------ #


class LTI_SS_S(SampledBlock):
    r"""
    :blockname:`LTI_SS_S`

    Discrete-time state-space LTI dynamics

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

    Implements the dynamics of a discrete-time multi-input multi-output (MIMO) linear
    time invariant (LTI) system described in statespace form.  The dynamics are given by

    .. math::

        \begin{aligned}
        x_{k+1} &= A x_k + B u_k \\
        y_k &= C x_k
        \end{aligned}

    A direct passthrough component, typically :math:`D`, is not allowed in order
    to avoid algebraic loops.

    Examples::

        lti = bd.LTI_SS_S(A=-2, B=1, C=-1)

    is the system :math:`x_{k+1}=-2x_k+u_k, y_k=-x_k`.

    .. versionadded:: 1.2.0
    """

    nin = 1
    nout = 1

    def __init__(
        self,
        clock: Clock,
        A: np.ndarray,
        B: np.ndarray,
        C: np.ndarray,
        D: np.ndarray | None = None,
        x0: np.ndarray | None = None,
        **blockargs: Any,
    ) -> None:
        r"""
        :param clock: clock source
        :type clock: Clock
        :param A: system matrix, defaults to [1,1]
        :type A: array_like, optional
        :param B: input matrix, defaults to [1]
        :type B: array_like, optional
        :param C: output matrix, defaults to [1]
        :type C: array_like, optional
        :param D: feedthrough matrix, defaults to None
        :type D: array_like, optional
        :param x0: initial states, defaults to None
        :type x0: array_like, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """
        # check dimensions of A, B, C, D conform
        #  B, C, D can be 1D or 2D, but must conform to A dimensions and are reshaped as required.
        assert A.shape[0] == A.shape[1], "A must be square"
        n = A.shape[0]
        if len(B.shape) == 1:
            # 1D array, assume it's a column vector and reshape to (n,1)
            nin = 1
            B = B.reshape((n, 1))
        else:
            nin = B.shape[1]
        assert B.shape[0] == n, "B must have same number of rows as A"

        if len(C.shape) == 1:
            # 1D array, assume it's a row vector and reshape to (1,n)
            nout = 1
            assert C.shape[0] == n, "C must have same number of columns as A"
            C = C.reshape((1, n))
        else:
            nout = C.shape[0]
            assert C.shape[1] == n, "C must have same number of columns as A"

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
            self.D: np.ndarray | None = D
            feedthrough = True
        else:
            self.D = None
            feedthrough = False

        super().__init__(clock=clock, x0=x0, feedthrough=feedthrough, **blockargs)

    def output(self, t: float, u: list[Any], x: np.ndarray) -> list[Any]:
        if self.D is not None:
            return list(self.C @ x + self.D @ u)
        else:
            return list(self.C @ x)

    def next(self, t: float, u: list[Any], x: np.ndarray) -> np.ndarray:
        # Reshape u and x to (N,1), i.e. column vectors, so
        # no problems with broadcasting between A@x and B@u
        x = x.reshape(-1, 1)
        u_arr = np.array(u).reshape(-1, 1)
        xnext = self.A @ x + self.B @ u_arr
        return xnext.flatten()


# ------------------------------------------------------------------------ #


class LTI_SISO_S(LTI_SS_S):
    r"""
    :blockname:`LTI_SISO_S`

    Discrete-time SISO LTI dynamics.

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

    Implements the dynamics of a discrete-time single-input single-output (SISO) linear
    time invariant (LTI) system described by numerator and denominator
    polynomial coefficients.  The dynamics are given by

    .. math::

        \frac{Y(z)}{U(z)} = \frac{N(z)}{D(z)}

    Coefficients are given in the order from highest to lowest
    order, ie. :math:`2z^2 - 4z +3` is ``[2, -4, 3]``, :math:`1 - z^{-1} + 2 z^{-2}` is ``[1, -1, 2]``.

    The state-space form can be either controller canonical form or observer canonical
    form, as specified by the ``form`` argument. For either

    Examples::

        lti = bd.LTI_SISO(N=[1, 2], D=[2, 3, -4])

    is the transfer function :math:`\frac{s+2}{2s^2+3s-4}`.

    .. note::
      * The state-space realization is not unique. The controller canonical form is more common
        in control design, while the observer canonical form is more common in estimation.
        The state ordering convention (the direction of the integrator chain) can be
        specified by the ``order`` argument, and results in either 1s on the super-diagonal
        or sub-diagonal of the A matrix for the controller canonical form.

    .. versionadded:: 1.2.0
    """

    nin = 1
    nout = 1

    def __init__(
        self,
        clock: Clock,
        N: Vector1D = 1,
        D: Vector1D = [1, 1],
        x0: np.ndarray | None = None,
        form: str = "ccf",
        order: str = "backward",
        verbose: bool = False,
        **blockargs: Any,
    ) -> None:
        r"""
        :param clock: clock source
        :type clock: Clock
        :param N: Numerator coefficients in descending powers of :math:`s`.
        :type N: array_like
        :param D: Denominator coefficients in descending powers of :math:`s`.
            Does not have to be normalized.
        :type D: array_like
        :param form: The canonical form of the realization, defaults to 'ccf'.
        :type form: str, optional
        :param order: The state ordering convention
        :type order: str, optional
        :param verbose: If True, print the state-space matrices, defaults to False
        :type verbose: bool, optional
        :return: LTI_SISO_S block
        :rtype: ``LTI_SISO_S`` instance

        Coefficients ``N`` and ``D``can be specified in the form of an array of
        coefficients, or an array of factors. The coefficients and factors are arrays of
        coefficients in decreasing powers of :math:`z`, this could be :math:`z^2 + 0.8z
        + 0.15` or :math:`1 + 0.8z^{-1} + 0.15z^{-2}`, both represented as ``[1, 0.8, 0.15]``.
        For example:

            * ``[1, 0.8]`` is the polynomial :math:`z+0.8`,
            * ``[[1, 0.3], [1, 0.5]]`` is the factors :math:`(z+0.3)(z+0.5)` which are convolved to obtain the coefficients of :math:`z^2 + 0.8z + 0.15`.
            * ``[2,[1,0.3], [1,0.5]]`` is the factors :math:`2(z+0.3)(z+0.5)` which are convolved to obtain the coefficients of :math:`2z^2 + 1.6z + 0.3`

        The ``form`` of the realization can be one of:

                        * ``'ccf'`` : Controller Canonical Form. The characteristic equation
                            coefficients appear in a row of **A**. Useful for control design.

                        * ``'ocf'`` : Observer Canonical Form. The characteristic equation
                            coefficients appear in a column of **A**. Useful for estimation.

        The ``order`` of the integrator chain can be one of:

                        * ``'forward'`` : :math:`x_0` is the output of the first integrator,
                            :math:`x_n-1` is the last. Results in 1s on the super-diagonal for ``'ccf'``.

                        * ``'backward'``: :math:`x_n-1` is the output of the first integrator,
                            :math:`x_0` is the last. Results in 1s on the sub-diagonal for ``'ccf'``.

        .. note::

            **Representation Perspectives:**

            1. **Control Perspective (z-domain):**
            If coefficients represent descending powers of :math:`z`, the states 
            represent forward shifts. 
            
            Example: :math:`G(z) = \\frac{b_1 z + b_2}{z^2 + a_1 z + a_2}`

            2. **DSP Perspective (z⁻¹-domain):**
            If coefficients represent ascending powers of :math:`z^{-1}`, the 
            states represent physical unit delays. 
            
            Example: :math:`H(z^{-1}) = \\frac{b_0 + b_1 z^{-1}}{1 + a_1 z^{-1} + a_2 z^{-2}}`

            In both cases, this function treats the input arrays as ordered 
            coefficients. 

            .. math::
                x[k+1] = A x[k] + B u[k] \\\\
                y[k] = C x[k] + D u[k]

            If ``form='ccf'`` and ``order='forward'``, the state :math:`x_i[k]` 
            corresponds to the output of the :math:`i`-th delay element in a 
            tapped delay line.
  

        .. note::
            - The transfer function is assumed to be strictly proper (:math:`deg(N) < deg(D)`).
            - The default ``form='ccf', order='backward'`` corresponds to the state-space realization returned by ``scipy.signal.tf2ss`` and MATLAB's ``tf2ss``.
            - The state-space matrices are available in the ``A``, ``B``, ``C``, and ``D`` attributes of the block.
            - If D is zero, then the block has no feedthrough and the D matrix is set to None. If D is nonzero, then the block has feedthrough and the D matrix is stored in the D attribute.
            - The ``_feedthrough`` attribute of the block is set to True if D is nonzero. This can be used to check for feedthrough without having to check the D matrix directly, and is used
              by the scheduler to ensure correct block evaluation order.
        """

        A, B, C, _D = _tf2ss(N, D, form=form, order=order, verbose=verbose)

        n = A.shape[0]
        if x0 is None:
            x0 = np.zeros((n,))

        super().__init__(clock=clock, A=A, B=B, C=C, D=_D, x0=x0, **blockargs)

        # TODO: parameters
        # def change_param(self, param: str, newvalue: np.ndarray) -> None:
        #     if param == "num":
        #         self.num = newvalue
        #     elif param == "den":
        #         self.den = newvalue
        #     self.A, self.B, self.C, self.D = scipy.signal.tf2ss(self.num, self.den)

        # self.add_param("num", change_param)
        # self.add_param("den", change_param)


# ------------------------------------------------------------------------ #


class PID_S(SubsystemBlock):
    r"""
    :blockname:`PID_S`

    Discrete-time PID control.

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

    Implements the dynamics of a discrete-timePID controller as a ``bdsim`` subsystem.
    There are three possible structures:

    * Parallel structure::

              ┌───────> P ─────────┐
              │                    │
              │                    ▼
        e ────┼───> D(z-1)/Tz ──> SUM ───> y
              │                    ▲
              │                    │
              └───> IT/(z-1) ──────┘

    .. math::

            \begin{aligned}
            e &= x^* - x \\
            \frac{Y(z)}{E(z)} &= P + I\frac{T}{z-1} + D\frac{z-1}{Tz}
            \end{aligned}


    * Ideal or standard structure. Described by ANSI/ISA-S75::

                    ┌────────────────────┐
                    │                    │
                    │                    ▼
        e ────> P ──┼───> D(z-1)/Tz ──> SUM ───> y
                    │                    ▲
                    │                    │
                    └───> IT/(z-1) ──────┘

    .. math::

        \begin{aligned}
        e &= x^* - x \\
        \frac{Y(z)}{E(z)} &= P \left(1 + I\frac{T}{z-1} + D\frac{z-1}{Tz}\right)
        \end{aligned}


    * Series structure. Archaic form, essentially a PI controller followed by a PD controller::

                    ┌───────────────────┐    ┌────────────────────┐
                    │                   │    │                    │
                    │                   ▼    │                    ▼
        e ────> P ──┴──> IT/(z-1) ───> SUM ──┴──>  D(z-1)/Tz ──> SUM ───> y


    .. math::

        \begin{aligned}
        e &= x^* - x \\
        \frac{Y(z)}{E(z)} &= P \left(1 + I\frac{T}{z-1} + D\frac{z-1}{Tz}\right)
        \end{aligned}

    Sometimes the gains are written in terms of time constants :math:`T_i = 1/I` and :math:`Td = D`.

    The PID controller is a subsytem comprising a number of blocks. If the I or D gains are
    zero then a PD or PI controller will be created with fewer blocks.

    The gain equivalence between the three structures is given by

    .. list-table::
        :header-rows: 1
        :align: center

        *   - structure
            - :math:`P`
            - :math:`I`
            - :math:`D`
        *   - parallel
            - :math:`P_p`
            - :math:`I_p`
            - :math:`D_p`
        *   - ideal
            - :math:`P_i`
            - :math:`P_i I_i`
            - :math:`P_i D_i`
        *   - series
            - :math:`P_s (1 + D_s I_s)`
            - :math:`P_s I_s`
            - :math:`P_s D_s`


    The derivate is computed by a ``DERIV_S`` block which is a simple first-order difference,
    which will exacerbate any noise on its input signal.

    The integration is performed by an ``INTEGRATOR_S`` block, which has some options to limit the integrator state and to enable/disable integration based on the error signal.

    If ``I_limit`` is provided it specifies the limits of the integrator state, before
    multiplication by ``I``.  If ``I_limit`` is:

    * a scalar :math:`a` the integrator state is clipped to the interval :math:`[-a, a]`
    * a 2-tuple :math:`(a,b)` the integrator state is clipped to the interval :math:`[a,
      b]`

    If ``I_limit`` is provided it specifies the limits of the integrator output.  The
    integrator state is clipped to these limits, which can be used to prevent integrator
    windup.  The limits can be specified as:

    * a scalar :math:`s` the band is the interval :math:`[-s, s]`
    * a 2-tuple :math:`(a,b)` the band is the interval :math:`[a, b]`

    If ``I_band`` is provided the integrator is reset to zero whenever the error
    :math:`e` is outside the band given by ``I_band`` which is:

    * a scalar :math:`s` the band is the interval :math:`[-s, s]`
    * a 2-tuple :math:`(a,b)` the band is the interval :math:`[a, b]`

    Examples::

        pid = bd.PID_S(P=3, D=2, I=1)

    .. warning::
        This block has a direct feedthrough term (by definition), and depending on how it is used
        in a system it may introduce an an algebraic loop which will be flagged at
        ``compile`` time.

    .. versionadded:: 1.2.0

    :seealso: :class:`Deriv_S` :class:`Integrator_S`
    """

    nin = 2
    nout = 1

    def __init__(
        self,
        clock: Clock,
        P: float = 0.0,
        I: float = 0.0,
        D: float = 0.0,
        I_limit: float | tuple[float, ...] | list[float] | None = None,
        I_band: float | None = None,
        structure: str = "parallel",
        **blockargs: Any,
    ) -> None:
        r"""
        :param clock: clock source
        :type clock: Clock
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
        :param structure: the structure of the PID implementation, "parallel" (default), "series", "standard|ideal"
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """

        bd = blockargs["bd"]
        subsystem = bd.runtime.blockdiagram(name="PID")

        Pblock = subsystem.GAIN(P)  # proportional gain block
        type = "P"

        if I != 0:
            # if the I term is required, create the block
            type += "I"
            integ_args: dict[str, Any] = {}
            if isinstance(I_limit, float):
                integ_args["min"] = -I_limit
                integ_args["max"] = I_limit
            elif isinstance(I_limit, tuple) and len(I_limit) == 2:
                integ_args["min"] = I_limit[0]
                integ_args["max"] = I_limit[1]

            if I_band is not None:

                def ifunc(t: float, u: list[Any], x: Any) -> bool:
                    return abs(u[0]) < I_band

                integ_args["enable"] = ifunc

            Iblock = subsystem.INTEGRATOR_S(
                clock, gain=I, name="I", **integ_args
            )  # integral block with gain I

        if D != 0:
            type += "D"
            # if the D term is required, create the blocks
            Dblock = subsystem.DERIV_S(clock, gain=D)  # derivative block

        error_sum = subsystem.SUM("-+", name="errsum")  # error summing junction
        inp = subsystem.INPORT(2)  # PID block inputs
        outp = subsystem.OUTPORT(1)  # PID block output

        subsystem.connect(inp, error_sum)

        # for each case sum the various terms
        if structure == "parallel":
            if type == "PID":
                out_sum = subsystem.SUM("+++", name="SUM")
                subsystem.connect(error_sum, Pblock, Dblock, Iblock)
                subsystem.connect(Pblock, out_sum[0])
                subsystem.connect(Iblock, out_sum[1])
                subsystem.connect(Dblock, out_sum[2])
            elif type == "PI":
                out_sum = subsystem.SUM("++", name="SUM")
                subsystem.connect(error_sum, Pblock, Iblock)
                subsystem.connect(Pblock, out_sum[0])
                subsystem.connect(Iblock, out_sum[1])
            elif type == "PD":
                out_sum = subsystem.SUM("++", name="SUM")
                subsystem.connect(error_sum, Pblock, Dblock)
                subsystem.connect(Pblock, out_sum[0])
                subsystem.connect(Dblock, out_sum[1])

            subsystem.connect(out_sum, outp)

        elif structure == "series":
            # cascade of P, I and D blocks with summing junctions between them

            subsystem.connect(error_sum, Pblock)

            if "I" in type:
                sum1 = subsystem.SUM("++", name="SUM_I")

                subsystem.connect(Pblock, Iblock, sum1[1])
                subsystem.connect(Iblock, sum1[0])
                I_out = sum1
            else:
                I_out = Pblock

            if "D" in type:
                sum2 = subsystem.SUM("++", name="SUM_D")
                subsystem.connect(I_out, Dblock, sum2[1])
                subsystem.connect(Dblock, sum2[0])
                D_out = sum2
            else:
                D_out = I_out

            subsystem.connect(D_out, outp)

        elif structure in ("standard", "ideal"):
            # P in series with parallel D and I
            if type == "PID":
                out_sum = subsystem.SUM("+++", name="SUM")
                subsystem.connect(error_sum, Pblock)
                subsystem.connect(Pblock, out_sum[0], Iblock, Dblock)
                subsystem.connect(Iblock, out_sum[1])
                subsystem.connect(Dblock, out_sum[2])
            elif type == "PI":
                out_sum = subsystem.SUM("++", name="SUM")
                subsystem.connect(error_sum, Pblock)
                subsystem.connect(Pblock, out_sum[0], Iblock)
                subsystem.connect(Iblock, out_sum[1])
            elif type == "PD":
                out_sum = subsystem.SUM("++", name="SUM")
                subsystem.connect(error_sum, Pblock)
                subsystem.connect(Pblock, out_sum[0], Dblock)
                subsystem.connect(Dblock, out_sum[1])

            subsystem.connect(out_sum, outp)

        super().__init__(subsystem=subsystem, **blockargs)


# ---------------------------------------------------------------------------
# Compatibility shims


@deprecated_block("Integrator_S")
class DIntegrator(Integrator_S):
    r"""Deprecated: use ``Integrator_S`` instead."""


@deprecated_block("PoseIntegrator_S")
class DPoseIntegrator(PoseIntegrator_S):
    r"""Deprecated: use ``PoseIntegrator_S`` instead."""


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
