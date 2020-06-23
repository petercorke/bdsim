"""
Define transfer blocks for use in block diagrams.  These are blocks that:

- have inputs and outputs
- have state variables
- are a subclass of ``TransferBlock``

Each class MyClass in this module becomes a method MYCLASS() of the Simulation object.
"""

import numpy as np
import math
from math import sin, cos, atan2, sqrt, pi

import matplotlib.pyplot as plt
import inspect

from bdsim.components import TransferBlock, block

# ------------------------------------------------------------------------ #

# @block
# class SpatialIntegrator(TransferBlock):
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.type = 'spatialintegrator'
        
#     def output(self, t=None):
#         pass
    
#     def deriv(self):
#         return xd

# ------------------------------------------------------------------------ #

@block
class MultiRotor(TransferBlock):
    """
    Flyer2dynamics lovingly coded by Paul Pounds, first coded 12/4/04
    A simulation of idealised X-4 Flyer II flight dynamics.
    version 2.0 2005 modified to be compatible with latest version of Matlab
    version 3.0 2006 fixed rotation matrix problem
    version 4.0 4/2/10, fixed rotor flapping rotation matrix bug, mirroring
    version 5.0 8/8/11, simplified and restructured
    version 6.0 25/10/13, fixed rotation matrix/inverse wronskian definitions, flapping cross-product bug

    New in version 2:
      - Generalised rotor thrust model
      - Rotor flapping model
      - Frame aerodynamic drag model
      - Frame aerodynamic surfaces model
      - Internal motor model
      - Much coolage
    
    Version 1.3
      - Rigid body dynamic model
      - Rotor gyroscopic model
      - External motor model
    
    ARGUMENTS
      u       Reference inputs                1x4
      tele    Enable telemetry (1 or 0)       1x1
      crash   Enable crash detection (1 or 0) 1x1
      init    Initial conditions              1x12
    
    INPUTS
      u = [N S E W]
      NSEW motor commands                     1x4
    
    CONTINUOUS STATES
      z      Position                         3x1   (x,y,z)
      v      Velocity                         3x1   (xd,yd,zd)
      n      Attitude                         3x1   (Y,P,R)
      o      Angular velocity                 3x1   (wx,wy,wz)
      w      Rotor angular velocity           4x1
    
    Notes: z-axis downward so altitude is -z(3)
    
    CONTINUOUS STATE MATRIX MAPPING
      x = [z1 z2 z3 n1 n2 n3 z1 z2 z3 o1 o2 o3 w1 w2 w3 w4]
    

    CONTINUOUS STATE EQUATIONS
      z` = v
      v` = g*e3 - (1/m)*T*R*e3
      I*o` = -o X I*o + G + torq
      R = f(n)
      n` = inv(W)*o
    """
    
    def __init__(self, model, groundcheck=True, speedcheck=True, x0=None):
        """
        
        :param model: A dictionary of vehicle geometric and inertial parameters
        :type model: dict
        :param groundcheck: Prevent vehicle moving below ground , defaults to True
        :type groundcheck: bool
        :param speedcheck: Check for zero rotor speed, defaults to True
        :type speedcheck: bool
        :param x0: Initial state, defaults to all zeros
        :type x0: TYPE, optional
        :return: DESCRIPTION
        :rtype: TYPE

        """
        super().__init__(**kwargs)
        self.type = 'quadrotor'
    
        self.nin = 1   # vector of 4 rotor speeds
        self.nout = 1  # it's a dict
        
        try:
            nrotors = model['nrotors']
        except KeyError:
            raise RuntimeError('vehicle model does not contain nrotors')
        assert self.nrotors % 2 == 0, 'Must have an even number of rotors'
        
        self.nstates = 12
        if x0 is not None:
            assert len(x0) == self.nstates, "x0 is the wrong length"
        else:
            x0 = np.zeros((self.nstates,))
        self._x0 = x0
        
        self.nrotors = nrotors
        self.model = model
        
        self.groundcheck = groundcheck
        self.speedcheck = speedcheck

        self.D = np.zeros((3,self.nrotors))
        for i in range(0, self.nrotors):
            theta = i / self.nrotors * 2 * pi
            #  Di      Rotor hub displacements (1x3)
            # first rotor is on the x-axis, clockwise order looking down from above
            self.D[:,i] = np.r_[ model['d'] * cos(theta), model['d'] * sin(theta), model['h']]
            
        self.a1s = np.zeros((self.nrotors,))
        self.b1s = np.zeros((self.nrotors,))
    
    def output(self, t=None):
        
        model = self.model    
        
        # compute output vector as a function of state vector
        #   z      Position                         3x1   (x,y,z)
        #   v      Velocity                         3x1   (xd,yd,zd)
        #   n      Attitude                         3x1   (Y,P,R)
        #   o      Angular velocity                 3x1   (Yd,Pd,Rd)
        
        n = self._x[3:6]   # RPY angles
        phi = n[0]         # yaw
        the = n[1]         # pitch
        psi = n[2]         # roll
        
        # rotz(phi)*roty(the)*rotx(psi)
        #  BBF > Inertial rotation matrix
        R = np.array([
                [cos(the) * cos(phi), sin(psi) * sin(the) * cos(phi) - cos(psi) * sin(phi), cos(psi) * sin(the) * cos(phi) + sin(psi) * sin(phi)],
                [cos(the) * sin(phi), sin(psi) * sin(the) * sin(phi) + cos(psi) * cos(phi), cos(psi) * sin(the) * sin(phi) - sin(psi) * cos(phi)],
                [-sin(the),           sin(psi) * cos(the),                                  cos(psi) * cos(the)]
            ])
        
        #inverted Wronskian
        iW = np.array([
                    [0,        sin(psi),             cos(psi)],             
                    [0,        cos(psi) * cos(the), -sin(psi) * cos(the)],
                    [cos(the), sin(psi) * sin(the),  cos(psi) * sin(the)]
                ]) / cos(the)
        
        # return velocity in the body frame
        out = {}
        out['x'] = self._x[0:6]
        out['vb'] = np.linalg.inv(R) @ self._x[6:9]   # translational velocity mapped to body frame
        out['pqr'] = iW @ self._x[9:12]               # RPY rates mapped to body frame
        out['a1s'] = self.a1s
        out['b1s'] = self.b1s
    
        return [out]
    
    def deriv(self):
    
        model = self.model
        
        # Body-fixed frame references
        #   ei      Body fixed frame references 3x1
        e3 = np.r_[0, 0, 1]
        
        # process inputs
        w = self.inputs[0]
        if len(w) != self.nrotors:
            raise RuntimeError('input vector wrong size')
    
        if self.speedcheck and np.any(w == 0):
            # might need to fix this, preculudes aerobatics :(
            # mu becomes NaN due to 0/0
            raise RuntimeError('quadrotor_dynamics: not defined for zero rotor speed');
        
        # EXTRACT STATES FROM X
        z = self._x[0:3]   # position in {W}
        n = self._x[3:6]   # RPY angles {W}
        v = self._x[6:9]   # velocity in {W}
        o = self._x[9:12]  # angular velocity in {W}
        
        # PREPROCESS ROTATION AND WRONSKIAN MATRICIES
        phi = n[0]    # yaw
        the = n[1]    # pitch
        psi = n[2]    # roll
        
        # rotz(phi)*roty(the)*rotx(psi)
        # BBF > Inertial rotation matrix
        R = np.array([
            [cos(the)*cos(phi), sin(psi)*sin(the)*cos(phi)-cos(psi)*sin(phi), cos(psi)*sin(the)*cos(phi)+sin(psi)*sin(phi)],
            [cos(the)*sin(phi), sin(psi)*sin(the)*sin(phi)+cos(psi)*cos(phi), cos(psi)*sin(the)*sin(phi)-sin(psi)*cos(phi)],
            [-sin(the),         sin(psi)*cos(the),                            cos(psi)*cos(the)]
            ])
        
        # Manual Construction
        #     Q3 = [cos(phi) -sin(phi) 0;sin(phi) cos(phi) 0;0 0 1];   % RZ %Rotation mappings
        #     Q2 = [cos(the) 0 sin(the);0 1 0;-sin(the) 0 cos(the)];   % RY
        #     Q1 = [1 0 0;0 cos(psi) -sin(psi);0 sin(psi) cos(psi)];   % RX
        #     R = Q3*Q2*Q1    %Rotation matrix
        #
        #    RZ * RY * RX
        # inverted Wronskian
        iW = np.array([
                    [0,        sin(psi),          cos(psi)],            
                    [0,        cos(psi)*cos(the), -sin(psi)*cos(the)],
                    [cos(the), sin(psi)*sin(the), cos(psi)*sin(the)]
                ]) / cos(the)
    
        # ROTOR MODEL
        T = np.zeros((3,4))
        Q = np.zeros((3,4))
        tau = np.zeros((3,4))
    
        a1s = self.a1s
        b1s = self.b1s
    
        for i in range(0, self.nrotors):  # for each rotor
    
            # Relative motion
            Vr = np.cross(o, self.D[:,i]) + v
            mu = sqrt(np.sum(Vr[0:2]**2)) / (abs(w[i]) * model['r'])  # Magnitude of mu, planar components
            lc = Vr[2] / (abs(w[i]) * model['r'])                     # Non-dimensionalised normal inflow
            li = mu                                                  # Non-dimensionalised induced velocity approximation
            alphas = atan2(lc, mu)
            j = atan2(Vr[1], Vr[0])                                  # Sideslip azimuth relative to e1 (zero over nose)
            J = np.array([
                    [cos(j), -sin(j)],
                    [sin(j),  cos(j)]
                ])                                                   # BBF > mu sideslip rotation matrix
            
            # Flapping
            beta = np.array([
                    [((8/3*model['theta0'] + 2 * model['theta1']) * mu - 2 * lc * mu) / (1 - mu**2 / 2)], # Longitudinal flapping
                    [0]                                                              # Lattitudinal flapping (note sign)
                ])
    
                # sign(w) * (4/3)*((Ct/sigma)*(2*mu*gamma/3/a)/(1+3*e/2/r) + li)/(1+mu^2/2)]; 
    
            beta = J.T @ beta;                                    # Rotate the beta flapping angles to longitudinal and lateral coordinates.
            a1s[i] = beta[0] - 16 / model['gamma'] / abs(w[i]) * o[1]
            b1s[i] = beta[1] - 16 / model['gamma'] / abs(w[i]) * o[0]
            
            # Forces and torques
    
            # Rotor thrust, linearised angle approximations
    
            T[:,i] = model['Ct'] * model['rho'] * model['A'] * model['r']**2 * w[i]**2 * \
                np.r_[-cos(b1s[i]) * sin(a1s[i]), sin(b1s[i]), -cos(a1s[i])*cos(b1s[i])] 
    
            # Rotor drag torque - note that this preserves w[i] direction sign
    
            Q[:,i] = -model['Cq'] * model['rho'] * model['A'] * model['r']**3 * w[i] * abs(w[i])* e3  
    
            tau[:,i] = np.cross(T[:,i], self.D[:,i])    # Torque due to rotor thrust
    
        # RIGID BODY DYNAMIC MODEL
        dz = v
        dn = iW @ o
        
        dv = model['g'] * e3 + R @ np.sum(T, axis=1) / model['M']
        
        # vehicle can't fall below ground, remember z is down
        if self.groundcheck and z[2] > 0:
            z[0] = 0
            dz[0] = 0
    
        do = np.linalg.inv(model['J']) @ (np.cross(-o, model['J'] @ o) + np.sum(tau, axis=1) + np.sum(Q, axis=1)) # row sum of torques
    
        # stash the flapping information for plotting
        self.a1s = a1s
        self.b1s = b1s
        
        return np.r_[dz, dn, dv, do]  # This is the state derivative vector

# ------------------------------------------------------------------------ #

@block
class Integrator(TransferBlock):
    def __init__(self, x0=0, min=None, max=None, **kwargs):
        super().__init__(**kwargs)
        
        self.nin = 1
        self.nout = 1
        if isinstance(x0, np.ndarray):
            assert len(x0.shape) == 1, 'state must be a vector'
            self.nstates = x0.shape[0]
            if min is None:
                min = [-math.inf] * self.nstates
            else:
                assert len(min) == self.nstates, 'minimum bound length must match x0'
                
            if max is None:
                max = [math.inf] * self.nstates
            else:
                assert len(max) == self.nstates, 'mmaximum bound length must match x0'
        elif isinstance(x0, (int, float)):
            self.nstates = 1
            if min is None:
                min = -math.inf
            if max is None:
                max = math.inf
        self._x0 = np.r_[x0]
        self.min = np.r_[min]
        self.max = np.r_[max]
        
    def output(self, t=None):
        return list(self._x)
    
    def deriv(self):
        xd = np.array(self.inputs)
        for i in range(0, self.nstates):
            if self._x[i] < self.min[i] or self._x[i] > self.max[i]:
                xd[i] = 0
        return xd

# ------------------------------------------------------------------------ #

@block
class LTI_SS(TransferBlock):
    def __init__(self, A=None, B=None, C=None, x0=None, verbose=False, **kwargs):
        r"""
        Create a state-space LTI block.
        
        :param N: numerator coefficients, defaults to 1
        :type N: array_like, optional
        :param D: denominator coefficients, defaults to [1, 1]
        :type D: array_like, optional
        :param x0: initial states, defaults to zero
        :type x0: array_like, optional
        :param ``**kwargs``: common Block options
        :return: A SCOPE block
        :rtype: _LTI_SISO
        
        Describes the dynamics of a single-input single-output (SISO) linear
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
        print('in SS constructor')

        super().__init__(**kwargs)

        self.type = 'LTI SS'

        assert A.shape[0] == A.shape[1], 'A must be square'
        n = A.shape[0]
        if len(B.shape) == 1:
            self.nin = 1
            B = B.reshape((n, 1))
        else:
            self.nin = B.shape[1]
        assert B.shape[0] == n, 'B must have same number of rows as A'
        
        if len(C.shape) == 1:
            self.nout = 1
            assert C.shape[0] == n, 'C must have same number of columns as A'
            C = C.reshape((1,n))
        else:
            self.nout = C.shape[0]
            assert C.shape[1] == n, 'C must have same number of columns as A'
        
        self.A = A
        self.B = B
        self.C = C
        
        self.nstates = A.shape[0]
        
        if x0 is None:
            self._x0 = np.zeros((self.nstates,))
        else:
            self._x0 = x0
        
    def output(self, t=None):
        return list(self.C@self._x)
    
    def deriv(self):
        return self.A@self._x + self.B@np.array(self.inputs)
# ------------------------------------------------------------------------ #

@block
class LTI_SISO(LTI_SS):
    def __init__(self, N=1, D=[1, 1], x0=None, verbose=False, **kwargs):
        r"""
        Create a SISO LTI block.
        
        :param N: numerator coefficients, defaults to 1
        :type N: array_like, optional
        :param D: denominator coefficients, defaults to [1, 1]
        :type D: array_like, optional
        :param x0: initial states, defaults to zero
        :type x0: array_like, optional
        :param ``**kwargs``: common Block options
        :return: A SCOPE block
        :rtype: _LTI_SISO
        
        Describes the dynamics of a single-input single-output (SISO) linear
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
        super(LTI_SS, self).__init__(**kwargs)
        if not isinstance(N, list):
            N = [N]
        if not isinstance(D, list):
            D = [D]
        self.N = N
        self.D = N
        n = len(D) - 1
        nn = len(N)
        if x0 is None:
            self._x0 = np.zeros((n,))
        else:
            self._x0 = x0
        assert nn <= n, 'direct pass through is not supported'
        self.type = 'LTI'
        
        self.nin = 1
        self.nout = 1
        self.nstates = n
        
        # convert to numpy arrays
        N = np.r_[np.zeros((len(D)-len(N),)), np.array(N)]
        D = np.array(D)
        
        # normalize the coefficients to obtain
        #
        #   b_0 s^n + b_1 s^(n-1) + ... + b_n
        #   ---------------------------------
        #   a_0 s^n + a_1 s^(n-1) + ....+ a_n
        

        # normalize so leading coefficient of denominator is one
        D0 = D[0]
        D = D / D0
        N = N / D0
        
        self.A = np.eye(len(D)-1, k=1)  # control canonic (companion matrix) form
        self.A[-1,:] = -D[1:]
        
        self.B = np.zeros((n,1))
        self.B[-1] = 1
        
        self.C = (N[1:] - N[0] * D[1:]).reshape((1,n))
        
        if verbose:
            print('A=', self.A)
            print('B=', self.B)
            print('C=', self.C)


if __name__ == "__main__":

    import pathlib
    import os.path

    exec(open(os.path.join(pathlib.Path(__file__).parent.absolute(), "test_transfers.py")).read())
