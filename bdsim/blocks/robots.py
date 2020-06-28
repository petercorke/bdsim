"""
Define robotic blocks for use in block diagrams, such as kinematic, dynamic and graphical display.
These are blocks that may be:

- subclass of ``FunctionBlock`` for kinematics
- subclass of ``TransferBlock`` for dynamics
- subclass of``SinkBlockGraphics`` for graphical display

Each class MyClass in this module becomes a method MYCLASS() of the Simulation object.
"""

# TODO: quadrotor dyanmics and display

import numpy as np
from math import sin, cos, atan2, sqrt, pi

import matplotlib.pyplot as plt
import time

from bdsim.components import TransferBlock, block

# ------------------------------------------------------------------------ #
@block
class Bicycle(TransferBlock):
    def __init__(self, *inputs, x0=None, L=1, vlim=1, slim=1, **kwargs):
        r"""
        Create a vehicle model with Bicycle kinematics.
        
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param x0: Inital state, defaults to 0
        :type x0: array_like, optional
        :param L: Wheelbase, defaults to 1
        :type L: float, optional
        :param vlim: Velocity limit, defaults to 1
        :type vlim: float, optional
        :param slim: Steering limit, defaults to 1
        :type slim: float, optional
        :param ``**kwargs``: common Block options
        :return: a BICYCLE block
        :rtype: Bicycle instance
        
        Bicycle kinematic model with state :math:``[x, y, \theta]``.  
        
        The block has two input ports:
            
            1. Vehicle speed (meters/sec).  The velocity limit ``vlim`` is
               applied to the magnitude of this input.
            2. Steering wheel angle (radians).  The steering limit ``slime``
               is applied to the magnitude of this input.
            
        and three output ports:
            
            1. x position in the world frame (metres)
            2. y positon in the world frame (meters)
            3. heading angle with respect to the world frame (radians)
            

        """
        super().__init__(nin=2, nout=3, inputs=inputs, **kwargs)

        self.nstates = 3
        self.vlim = vlim
        self.slim = slim
        self.type = 'bicycle'

        self.L = L
        if x0 is None:
            self._x0 = np.zeros((self.nstates,))
        else:
            assert len(x0) == self.nstates, "x0 is {:d} long, should be {:d}".format(len(x0), self.nstates)
            self._x0 = x0
            
        self.inport_names(('v', '$\gamma$'))
        self.outport_names(('x', 'y', r'$\theta$'))
        self.state_names(('x', 'y', r'$\theta$'))
        
    def output(self, t):
        return list(self._x)
    
    def deriv(self):
        theta = self._x[2]
        
        # get inputs and clip them
        v = self.inputs[0]
        v = min(self.vlim, max(v, -self.vlim))
        gamma = self.inputs[1]
        gamma = min(self.slim, max(gamma, -self.slim))
        
        xd = np.r_[v*math.cos(theta), v*math.sin(theta), v*math.tan(gamma)/self.L ]
        return xd
    
# ------------------------------------------------------------------------ #
@block
class Unicycle(TransferBlock):
    def __init__(self, *inputs, x0=None, **kwargs):
        r"""
        Create a vehicle model with Unicycle kinematics.
        
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param x0: Inital state, defaults to 0
        :type x0: array_like, optional
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param ``**kwargs``: common Block options
        :return: a UNICYCLE block
        :rtype: Unicycle instance
        
        Unicycle kinematic model with state :math:``[x, y, \theta]``.
        
        The block has two input ports:
            
            1. Vehicle speed (meters/sec).
            2. Angular velocity (radians/sec).
            
        and three output ports:
            
            1. x position in the world frame (metres)
            2. y positon in the world frame (meters)
            3. heading angle with respect to the world frame (radians)

        """
        super().__init__(nin=2, nout=3, inputs=inputs, **kwargs)
        self.nstates = 3
        self.type = 'unicycle'
        
        if x0 is None:
            self._x0 = np.zeros((slef.nstates,))
        else:
            assert len(x0) == self.nstates, "x0 is {:d} long, should be {:d}".format(len(x0), self.nstates)
            self._x0 = x0
        
    def output(self, t):
        return list(self._x)
    
    def deriv(self):
        theta = self._x[2]
        v = self.inputs[0]
        omega = self.inputs[1]
        xd = np.r_[v * math.cos(theta), v * math.sin(theta), omega]
        return xd
    
# ------------------------------------------------------------------------ #
@block
class DiffSteer(TransferBlock):
    def __init__(self, *inputs, R=1, W=1, x0=None, **kwargs):
        r"""
        Create a differential steer vehicle model with Unicycle kinematics.
        
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param x0: Inital state, defaults to 0
        :type x0: array_like, optional
        :param R: Wheel radius, defaults to 1
        :type R: float, optional
        :param W: Wheel separation in lateral direction, defaults to 1
        :type R: float, optional
        :param ``**kwargs``: common Block options
        :return: a DIFFSTEER block
        :rtype: DifSteer instance
        
        Bicycle kinematic model with state :math:``[x, y, \theta]``.

        The block has two input ports:
            
            1. Left-wheel angular velocity (radians/sec).
            2. Right-wheel angular velocity (radians/sec).
            
        and three output ports:
            
            1. x position in the world frame (metres)
            2. y positon in the world frame (meters)
            3. heading angle with respect to the world frame (radians)

        """
        super().__init__(nin=2, nout=3, inputs=inputs, **kwargs)
        self.nstates = 3
        self.type = 'diffsteer'
        self.R = R
        self.W = W
        
        if x0 is None:
            self._x0 = np.zeros((slef.nstates,))
        else:
            assert len(x0) == self.nstates, "x0 is {:d} long, should be {:d}".format(len(x0), self.nstates)
            self._x0 = x0
        
    def output(self, t):
        return list(self._x)
    
    def deriv(self):
        theta = self._x[2]
        v = self.R * (self.inputs[0] + self.inputs[1]) / 2
        omega = (self.inputs[1] + self.inputs[0]) / self.W
    
        xd = np.r_[v * math.cos(theta), v * math.sin(theta), omega]
        return xd
    
    # seriallink
    # RNE
    # fkine
    # robot plot
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
    
    def __init__(self, model, *inputs, groundcheck=True, speedcheck=True, x0=None, **kwargs):
        r"""
        Createa a multi-rotor dynamic model block.
        
        :param ``*inputs``: Optional incoming connections
        :type ``*inputs``: Block or Plug
        :param model: A dictionary of vehicle geometric and inertial parameters
        :param groundcheck: Prevent vehicle moving below ground , defaults to True
        :type groundcheck: bool
        :param speedcheck: Check for zero rotor speed, defaults to True
        :type speedcheck: bool
        :param x0: Initial state, defaults to all zeros
        :type x0: TYPE, optional
        :param ``**kwargs``: common Block options
        :return: a DIFFSTEER block
        :rtype: MultiRotor instance
        
        The block has one input port which is a vector of input rotor speeds
        in (radians/sec).  These are, looking down, clockwise from the front rotor
        which lies on the x-axis.
        
        The block has one output port which is a dictionary signal with the
        following items:
            
            - ``x`` pose in the world frame as :math:``[x, y, z, \theta_Y, \theta_P, \theta_R]``
            - ``vb`` translational velocity in the world frame (metres/sec)
            - ``w`` angular rates in the world frame as yaw-pitch-roll rates (radians/second)
            - ``a1s`` longitudinal flapping angles (radians)
            - ``b1s`` lateral flapping angles (radians)
            
        Based on MATLAB code developed by Pauline Pounds 2004.

        """
        super().__init__(nin=1, nout=1, inputs=inputs, **kwargs)
        self.type = 'quadrotor'
    

        
        try:
            nrotors = model['nrotors']
        except KeyError:
            raise RuntimeError('vehicle model does not contain nrotors')
        assert nrotors % 2 == 0, 'Must have an even number of rotors'
        
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
        out['w'] = iW @ self._x[9:12]               # RPY rates mapped to body frame
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



if __name__ == "__main__":

    import pathlib
    import os.path

    exec(open(os.path.join(pathlib.Path(__file__).parent.absolute(), "test_robots.py")).read())
