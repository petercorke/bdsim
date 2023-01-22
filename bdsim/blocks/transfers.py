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

from bdsim.components import TransferBlock


class Integrator(TransferBlock):
    """
    :blockname:`INTEGRATOR`

    .. table::
       :align: left

       +------------+---------+---------+
       | inputs     | outputs |  states |
       +------------+---------+---------+
       | 1          | 1       | N       |
       +------------+---------+---------+
       | float,     | float,  |         |
       | A(N,)      | A(N,)   |         |
       +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, x0=0, gain=1.0, min=None, max=None, **blockargs):
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
        :return: an INTEGRATOR block
        :rtype: Integrator instance

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
        print("nstates", self.nstates)

    def output(self, t=None):
        return [self._x]

    def deriv(self):
        xd = base.getvector(self.inputs[0])
        if self.min is not None:
            xd[self._x < self.min] = 0
        if self.max is not None:
            xd[self._x > self.max] = 0

        return self.gain * xd


class PoseIntegrator(TransferBlock):
    """
    :blockname:`POSEINTEGRATOR`

    .. table::
       :align: left

       +------------+---------+---------+
       | inputs     | outputs |  states |
       +------------+---------+---------+
       | 1          | 1       | N       |
       +------------+---------+---------+
       | A(N,)      | A(N,)   |         |
       +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, x0=None, **blockargs):
        r"""
        Pose integrator

        :param x0: Initial pose, defaults to null
        :type x0: SE3, Twist3, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: an POSEINTEGRATOR block
        :rtype: PoseIntegrator instance

        This block integrates spatial velocity over time.
        The block input is a spatial velocity as a 6-vector
        :math:`(v_x, v_y, v_z, \omega_x, \omega_y, \omega_z)` and the output
        is pose as an ``SE3`` instance.

        .. note:: State is a velocity twist.

        .. warning:: NOT WORKING YET
        """
        super().__init__(**blockargs)

        if x0 is None:
            x0 = np.zeros((6,))

        self.nstates = len(x0)

        self._x0 = x0

    def output(self, t=None):
        return [Twist3(self._x).SE3(1)]

    def deriv(self):

        return self.inputs[0]


# ------------------------------------------------------------------------ #


class LTI_SS(TransferBlock):
    """
    :blockname:`LTI_SS`

    .. table::
       :align: left

       +------------+---------+---------+
       | inputs     | outputs |  states |
       +------------+---------+---------+
       | 1          | 1       | nc      |
       +------------+---------+---------+
       | float,     | float,  |         |
       | A(nb,)     | A(nc,)  |         |
       +------------+---------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, A=None, B=None, C=None, x0=None, **blockargs):
        r"""
        State-space LTI dynamics.

        :param N: numerator coefficients, defaults to 1
        :type N: array_like, optional
        :param D: denominator coefficients, defaults to [1,1]
        :type D: array_like, optional
        :param x0: initial states, defaults to None
        :type x0: array_like, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A SCOPE block
        :rtype: LTI_SISO instance

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

            LTI_SISO(N=[1,2], D=[2, 3, -4])

        is the transfer function :math:`\frac{s+2}{2s^2+3s-4}`.
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

    def output(self, t=None):
        return list(self.C @ self._x)

    def deriv(self):
        return self.A @ self._x + self.B @ np.array(self.inputs)


# ------------------------------------------------------------------------ #


class LTI_SISO(LTI_SS):
    """
    :blockname:`LTI_SISO`

    .. table::
       :align: left

       +------------+---------+---------+
       | inputs     | outputs |  states |
       +------------+---------+---------+
       | 1          | 1       | n       |
       +------------+---------+---------+
       | float      | float   |         |
       +------------+---------+---------+

    """

    nin = 1
    nout = 1

    def __init__(self, N=1, D=[1, 1], x0=None, **blockargs):
        r"""
        SISO LTI dynamics.

        :param N: numerator coefficients, defaults to 1
        :type N: array_like, optional
        :param D: denominator coefficients, defaults to [1,1]
        :type D: array_like, optional
        :param x0: initial states, defaults to None
        :type x0: array_like, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: A SCOPE block
        :rtype: LTI_SISO instance

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
        N = np.r_[np.zeros((len(D) - len(N),)), np.array(N)]
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


if __name__ == "__main__":

    from pathlib import Path

    exec(
        open(Path(__file__).parent.parent.parent / "tests" / "test_transfers.py").read()
    )
