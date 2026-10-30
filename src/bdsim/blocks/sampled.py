r"""
Sampled-time blocks:

- have inputs and outputs
- have discrete-time state variables that are sampled/updated at the times
  specified by the associated clock
- are a subclass of ``SampledBlock`` |rarr| ``Block``
"""

from __future__ import annotations

import numpy as np
import spatialmath.base as smb  # type: ignore[import-not-found]

from typing import Any, Callable

from bdsim.components import SampledBlock, Clock, SubsystemBlock, deprecated_block
from bdsim.blocks.continuous import (
    _NO_D,
    _NO_I,
    _conform_D,
    _integral_limits,
    _old_tf_names,
    _tf2ss,
    _TFParams,
)

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
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(clock=clock, nin=1, nout=1, x0=x0, **blockargs)
        self.add_param("clock", when="never")
        self.add_param("x0", when="setup")

        # print('nstates', self.nstates)

    def output(self, t: float, inputs: list[Any], x: np.ndarray) -> list[Any]:
        # print('* output, x is ', self._x)
        if x.size == 1:
            return [x.item()]
        return [x]

    def next(self, t: float, inputs: list[Any], x: np.ndarray) -> np.ndarray:
        u = smb.getvector(inputs[0])
        return u  # must be an ndarray


# ------------------------------------------------------------------------ #


def _check_enable(value: Any) -> None:
    """Validator for ``enable``, a function or ``None``."""
    if value is not None and not callable(value):
        raise ValueError("enable must be callable")


def _band_enable(I_band: float | None) -> Callable[..., bool] | None:
    """The ``enable`` function of an integrator that only integrates when the error is in a band."""
    if I_band is None:
        return None

    def ifunc(t: float, u: list[Any], x: Any) -> bool:
        return bool(abs(u[0]) < I_band)

    return ifunc


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
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        super().__init__(clock=clock, x0=x0, **blockargs)

        self.min = min
        self.max = max
        self.gain: float = gain
        self.T = clock.T

        self.enable = enable
        if enable is not None and not callable(enable):
            raise ValueError("enable must be callable")
        self.add_param("clock", when="never")
        self.add_param("gain")
        self.add_param("min", coerce=False)
        self.add_param("max", coerce=False)
        self.add_param("enable", coerce=False, validate=_check_enable)
        self.add_param("x0", when="setup")

    @property
    def min(self) -> np.ndarray | None:
        """Lower limit of each state, or ``None`` for no limit."""
        return self._min

    @min.setter
    def min(self, value: Any) -> None:
        self._min = None if value is None else smb.getvector(value, len(self._x0))

    @property
    def max(self) -> np.ndarray | None:
        """Upper limit of each state, or ``None`` for no limit."""
        return self._max

    @max.setter
    def max(self, value: Any) -> None:
        self._max = None if value is None else smb.getvector(value, len(self._x0))

    def output(self, t: float, u: list[Any], x: np.ndarray) -> list[Any]:
        result = x
        if isinstance(result, np.ndarray) and result.ndim == 1 and result.size == 1:
            result = result.item()
        return [result]

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
        :param kwargs: :meth:`common block options <bdsim.Block.__init__>`
        :type kwargs: dict
        """
        super().__init__(clock=clock, x0=x0, feedthrough=True, **blockargs)
        self.gain = gain
        self.add_param("clock", when="never")
        self.add_param("gain")
        self.add_param("x0", when="setup")

    def output(self, t: float, u: list[Any], x: np.ndarray) -> list[Any]:
        result = self.gain * (u[0] - x) / self.T
        if isinstance(result, np.ndarray) and result.ndim == 1 and result.size == 1:
            result = result.item()
        return [result]

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
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """
        # check dimensions of A, B, C, D conform
        #  B, C, D can be 1D or 2D, but must conform to A dimensions and are reshaped as required.
        if A.shape[0] != A.shape[1]:
            raise ValueError("A must be square")
        n = A.shape[0]
        if len(B.shape) == 1:
            # 1D array, assume it's a column vector and reshape to (n,1)
            nin = 1
            B = B.reshape((n, 1))
        else:
            nin = B.shape[1]
        if B.shape[0] != n:
            raise ValueError("B must have same number of rows as A")

        if len(C.shape) == 1:
            # 1D array, assume it's a row vector and reshape to (1,n)
            nout = 1
            if C.shape[0] != n:
                raise ValueError("C must have same number of columns as A")
            C = C.reshape((1, n))
        else:
            nout = C.shape[0]
            if C.shape[1] != n:
                raise ValueError("C must have same number of columns as A")

        if D is None:
            D = np.zeros((nout, nin))
        elif len(D.shape) == 1:
            if len(D) != nin * nout:
                raise ValueError("D must conform to B and C dimensions")
            D = D.reshape((nout, nin))
        else:
            if D.shape != (nout, nin):
                raise ValueError("D must conform to B and C dimensions")

        self.A = A
        self.B = B
        self.C = C

        # if D is nonzero then we have feedthrough, which may create an algebraic loop, so flag this to the base class
        if np.any(D != 0):
            # flag we have feedthrough, which may create an algebraic loop
            self._D: np.ndarray | None = D
            feedthrough = True
        else:
            self._D = None
            feedthrough = False

        super().__init__(
            clock=clock,
            ndstates=n,
            nin=nin,
            nout=nout,
            x0=x0,
            feedthrough=feedthrough,
            **blockargs,
        )
        self.add_param("clock", when="never")
        self.add_param("A")
        self.add_param("B")
        self.add_param("C")
        self.add_param("D")
        self.add_param("x0", when="setup")

    @property
    def D(self) -> np.ndarray | None:
        """The feedthrough matrix, ``None`` if it is zero."""
        return self._D

    @D.setter
    def D(self, value: Any) -> None:
        self._D = _conform_D(self, value)

    def output(self, t: float, u: list[Any], x: np.ndarray) -> list[Any]:
        y = self.C @ x
        if self._D is not None:
            y = y + self._D @ np.array(u)
        if y.size == 1:
            return [y.item()]
        return [y]

    def next(self, t: float, u: list[Any], x: np.ndarray) -> np.ndarray:
        # Reshape u and x to (N,1), i.e. column vectors, so
        # no problems with broadcasting between A@x and B@u
        x = x.reshape(-1, 1)
        u_arr = np.array(u).reshape(-1, 1)
        xnext = self.A @ x + self.B @ u_arr
        return xnext.flatten()


# ------------------------------------------------------------------------ #


class LTI_SISO_S(_TFParams, LTI_SS_S):
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

        lti = bd.LTI_SISO_S(clock, num=[1, 2], den=[2, 3, -4])

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
        num: Vector1D = 1,
        den: Vector1D = [1, 1],
        x0: np.ndarray | None = None,
        form: str = "ccf",
        order: str = "backward",
        verbose: bool = False,
        **blockargs: Any,
    ) -> None:
        r"""
        :param clock: clock source
        :type clock: Clock
        :param num: Numerator coefficients in descending powers of :math:`z`.
        :type num: array_like
        :param den: Denominator coefficients in descending powers of :math:`z`.
            Does not have to be normalized.
        :type den: array_like
        :param form: The canonical form of the realization, defaults to 'ccf'.
        :type form: str, optional
        :param order: The state ordering convention
        :type order: str, optional
        :param verbose: If True, print the state-space matrices, defaults to False
        :type verbose: bool, optional
        :return: LTI_SISO_S block
        :rtype: ``LTI_SISO_S`` instance

        Coefficients ``num`` and ``den`` can be specified in the form of an array of
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
            - The transfer function is assumed to be strictly proper (:math:`deg(num) < deg(den)`).
            - The default ``form='ccf', order='backward'`` corresponds to the state-space realization returned by ``scipy.signal.tf2ss`` and MATLAB's ``tf2ss``.
            - ``num`` and ``den`` are attributes holding the numerator and denominator coefficients (expanded
              if they were given as factors), and can be changed after the block is created (they are
              parameters).  The state-space matrices are rebuilt from them.  The order of the system, the
              length of ``den`` minus one, cannot change.
            - The state-space matrices are available in the ``A``, ``B``, ``C``, and ``D`` attributes of the block.
            - If the numerator degree is less than the denominator degree, the block has no feedthrough and ``D`` is None.
              The ``_feedthrough`` attribute of the block is set to True otherwise. It is used
              by the scheduler to ensure correct block evaluation order.

        .. versionchanged:: next
            The arguments ``N`` and ``D`` are renamed ``num`` and ``den``, because ``D`` is also the feedthrough
            matrix of the state-space realization.  The old keywords still work, with a ``DeprecationWarning``,
            and will be removed in a later release.
        """

        num, den = _old_tf_names(num, den, blockargs)
        A, B, C, _D = _tf2ss(num, den, form=form, order=order, verbose=verbose)

        n = A.shape[0]
        if x0 is None:
            x0 = np.zeros((n,))

        super().__init__(clock=clock, A=A, B=B, C=C, D=_D, x0=x0, **blockargs)
        self._init_tf(num, den, form, order, verbose)
        self.add_param("num", coerce=False)  # a polynomial may change length
        self.add_param("den", coerce=False)
        self.add_param("clock", when="never")
        self.add_param("form", when="never")
        self.add_param("order", when="never")
        self.add_param("verbose", when="never")
        self.add_param("x0", when="setup")


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
        :param blockargs: :meth:`common block options <bdsim.Block.__init__>`
        :type blockargs: dict
        """

        bd = blockargs["bd"]
        subsystem = bd.runtime.blockdiagram(name="PID")

        Pblock = subsystem.GAIN(P)  # proportional gain block
        type = "P"

        if I != 0:
            # if the I term is required, create the block
            type += "I"
            lo, hi = _integral_limits(I_limit)

            Iblock = subsystem.INTEGRATOR_S(
                clock,
                gain=I,
                name="I",
                min=lo,
                max=hi,
                enable=_band_enable(I_band),
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
        self._Iblock = Iblock if "I" in type else None
        self._I_band = I_band
        self.add_param("P", forward=(Pblock, "K"))
        if "I" in type:
            self.add_param("I", forward=(Iblock, "gain"))
            self.add_param("I_limit", coerce=False)
            self.add_param("I_band", coerce=False)
        else:
            for name in ("I", "I_limit", "I_band"):
                self.add_param(name, unavailable=_NO_I)
        if "D" in type:
            self.add_param("D", forward=(Dblock, "gain"))
        else:
            self.add_param("D", unavailable=_NO_D)
        self.add_param("clock", when="never")
        self.add_param("structure", when="never")

    @property
    def I_limit(self) -> float | tuple[float | None, float | None] | None:
        """
        Limit on the integral term: ``None`` for none, a number for the limit
        :math:`\\pm` that number, or a (lower, upper) pair.
        """
        if self._Iblock is None:
            return None
        lo, hi = self._Iblock.min, self._Iblock.max
        lo = None if lo is None else float(lo[0])
        hi = None if hi is None else float(hi[0])
        if lo is None and hi is None:
            return None
        if lo is not None and hi is not None and lo == -hi:
            return hi
        return lo, hi

    @I_limit.setter
    def I_limit(self, value: Any) -> None:
        if self._Iblock is None:
            raise ValueError(_NO_I)
        lo, hi = _integral_limits(value)
        self._Iblock.set_param("min", lo)
        self._Iblock.set_param("max", hi)

    @property
    def I_band(self) -> float | None:
        """The integral term only integrates while the error is smaller than this, or ``None``."""
        return self._I_band

    @I_band.setter
    def I_band(self, value: float | None) -> None:
        if self._Iblock is None:
            raise ValueError(_NO_I)
        if value is not None and not value > 0:
            raise ValueError("I_band must be positive")
        self._Iblock.set_param("enable", _band_enable(value))
        self._I_band = value


# ---------------------------------------------------------------------------
# Compatibility shims


@deprecated_block("Integrator_S")
class DIntegrator(Integrator_S):
    r"""Deprecated: use ``Integrator_S`` instead."""


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
