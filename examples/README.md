# Running the examples

From the command line:

```
% pip install bdsim
```

Then you can run the examples from the command line, for example

```
% ./eg1.py
```

which will display a graph in a new figure window.  Close the figure to allow the program to exit.

# Supplied example files

Continuous time systems:

* `eg1.py` closed-loop first-order plant
* `eg1a.py` same as `eg1.py` but expressed using Python operators and assignments
* `pid.py` same as `eg1.py` but with PI rather than P controller
* `subsys.py` demonstration of subsystems
* `bouncing-ball.py` bouncing ball demonstration with event detection and block state updating
* `vanderpol.py` Van der Pol oscillator

* `deriv.py` sine-wave response of derivative
* `test_deriv1.py` ramp response of derivative with 1st order smoothing
* `test_deriv2.py` ramp response of derivative with 2nd order smoothing
* `test_integrator.py` integrator response to step
* `test_lti_tf.py` example from Franlin, Powell, Workman 2nd ed.
* `test_pid.py` comparison of 3 different PID structures


Discrete-time systems:

* `multi-clock.py` system with two clocks sampling sine wave
* `test_deriv_s.py` ramp response of derivative
* `test_integrator_s.py` integrator response to step
* `test_lti_tf_s.py` example from Franlin, Powell, Workman 2nd ed.
* `test_pid_s.py` comparison of 3 different PID structures

Hybrid continuous-/discrete-time:

* `eg1_zoh.py` same as `eg1.py` but with ZOH between controller and plant

System with no states:

* `waveform.py` waveform generator connected to a scope, no system dynamics

RVC2 is a folder holding some examples from Chapter four of [_Robotics, Vision & Control (2017)_](https://petercorke.com/rvc/home):

* `rvc4_2.py` Fig 4.2 - a car-like vehicle with bicycle kinematics driven by a rectangular pulse steering signal
* `rvc4_4.py` Fig 4.4 - a car-like vehicle driving to a point

* `rvc4_6.py` Fig 4.6 - a car-like vehicle driving to/along a line

* `rvc4_11.py` Fig 4.11 a car-like vehicle driving to a pose

All `bdsim` programs support a number of [command line switches](https://github.com/petercorke/bdsim/wiki/Runtime-options).

# Robotics, Vision & Control 3rd edition in Python (2022)

More examples can be found in the [support package for the book _Robotics, Vision & Control (2023) 3e_](https://github.com/petercorke/RVC3-python/tree/main/RVC3/models).


