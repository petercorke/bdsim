[![A Python Robotics Package](https://raw.githubusercontent.com/petercorke/robotics-toolbox-python/master/.github/svg/py_collection.min.svg)](https://github.com/petercorke/robotics-toolbox-python)
[![QUT Centre for Robotics Open Source](https://github.com/qcr/qcr.github.io/raw/master/misc/badge.svg)](https://qcr.github.io)

[![PyPI version](https://badge.fury.io/py/bdsim.svg)](https://badge.fury.io/py/bdsim)
![Python Version](https://img.shields.io/pypi/pyversions/bdsim.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[![Build Status](https://github.com/petercorke/bdsim/workflows/build/badge.svg?branch=master)](https://github.com/petercorke/bdsim/actions?query=workflow%3Abuild)
[![Coverage](https://codecov.io/gh/petercorke/bdsim/branch/master/graph/badge.svg)](https://codecov.io/gh/petercorke/bdsim)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/bdsim)](https://pypistats.org/packages/bdsim)
[![GitHub stars](https://img.shields.io/github/stars/petercorke/bdsim.svg?style=social&label=Star)](https://GitHub.com/petercorke/bdsim/stargazers/)

<table style="border:0px">
<tr style="border:0px">
<td style="border:0px">
<img src="https://github.com/petercorke/bdsim/raw/master/figs/BDSimLogo_NoBackgnd@2x.png" width="300"></td>
<td style="border:0px">
A Python block diagram simulation package</a>
<ul>
<li><a href="https://github.com/petercorke/bdsim">GitHub repository </a></li>
<li><a href="https://petercorke.github.io/bdsim">Documentation</a></li>
<li><a href="https://github.com/petercorke/bdsim/wiki">Wiki (examples and details)</a></li>
<li><a href="installation#">Installation</a></li>
<li>Dependencies: numpy, scipy, matplotlib, <a href="https://github.com/petercorke/ansitable">ansitable</a>, ffmpeg (if rendering animations as a movie)</li>
</ul>
</td>
</tr>
</table>

`bdsim` is Python 3 package that enables modelling and simulation of continuous-time, discrete-time or hybrid dynamic systems.  Systems are conceptualized in block diagram form, but represented in terms of Python objects. 

  <table>
  <tr>
  <td>
  <img width=450 src="https://github.com/petercorke/bdsim/raw/master/figs/bd1-sketch.png">
  </td>
  <td style="padding-left: 20px;">
  <pre style="font-size:10px;">
  # define the blocks
  demand = bd.STEP(T=1, name='demand')
  sum = bd.SUM('+-')
  gain = bd.GAIN(10)
  plant = bd.LTI_SISO(0.5, [2, 1])
  scope = bd.SCOPE(styles=['k', 'r--'])
  # connect the blocks
  bd.connect(demand, sum[0], scope[1])
  bd.connect(plant, sum[1])
  bd.connect(sum, gain)
  bd.connect(gain, plant)
  bd.connect(plant, scope[0])
  </pre>
  </td>
  </tr>
  </table>

Key features include:

* The block diagram can be created easily using Python code, rather than drawing boxes and wires. This enables use of your favourite IDE, standard version control tools and development workflows.
* Wires can communicate *any* Python type such as scalars, lists, dicts, NumPy arrays, objects, and functions. For robotics and vision applications using the [Spatial Maths Toolbox for Python](https://github.com/petercorke/spatialmath-python) wires could send values such as `SE3`, `UnitQuaternion` or `Twist3` objects.
* Over 70 blocks for linear, nonlinear functions, display blocks, as well as continuous- and discrete-time dynamics
  * Easy to add your own block, it's simply a class
  * Subsystems are supported, and a subsystem can be independently instantiated multiple times in a system.  Subsystems can also be nested.
  * Blocks from other toolboxes are automatically discovered and included. There are blocks for some functions in the  [Robotics Toolbox for Python](https://github.com/petercorke/robotics-toolbox-python) (such as arm, ground and aerial robots) and [Machine Vision Toolbox for Python](https://github.com/petercorke/machinevision-toolbox-python) (such as cameras). These are defined in the `blocks` folder of those toolboxes.
* The diagram can be executed in a headless configuration, particularly useful on an embedded computer like a RaspberryPi.
* A [python-based graphical editor](bdedit-the-graphical-editing-tool)
  * allows graphical creation of block diagrams
  * the diagram is stored in a human readable/editable JSON file with extension `.bd`
  * creates good-quality graphics for inclusion in publications
  * can launch `bdsim` to import and execute the model
  * automatically discovers all bsdim and toolbbox blocks and adds them to the block library menu
  * icons can be easily created using any image creation tool or a LaTeX expression 

# Getting started

We first sketch the dynamic system we want to simulate as a block diagram, for example this simple first-order system

![block diagram](https://github.com/petercorke/bdsim/raw/master/figs/bd1-sketch.png)

which we can express concisely with `bdsim` as (see [`bdsim/examples/eg1.py`](https://github.com/petercorke/bdsim/blob/master/examples/eg1.py))

```python
     1  #!/usr/bin/env python3
     2  import bdsim	
     4  sim = bdsim.BDSim()  # create simulator
     5  bd = sim.blockdiagram()  # create an empty block diagram
     6	
     7	# define the blocks
     8	demand = bd.STEP(T=1, name='demand')
     9	sum = bd.SUM('+-')
    10	gain = bd.GAIN(10)
    11	plant = bd.LTI_SISO(0.5, [2, 1], name='plant')
    12	scope = bd.SCOPE(styles=['k', 'r--'])
    13	
    14	# connect the blocks
    15	bd.connect(demand, sum[0], scope[1])
    17	bd.connect(sum, gain)
    18	bd.connect(gain, plant)
    19	bd.connect(plant, sum[1], scope[0])
    20	
    21	bd.compile()   # check the diagram
    22	bd.report()    # list all blocks and wires
    23
    24  out = sim.run(bd, 5)   # simulate for 5s
    25  sim.savefig(scope, 'scope0')
    26  sim.done(bd, block=True)
```
which is just 16 lines of executable code.

The red block annotations on the hand-drawn diagram are used as the names of the variables holding references to the block instance. The blocks can also have user-assigned names, see lines 8 and 11, which are used in diagnostics and as labels in plots.

After the blocks are created their input and output ports need to be connected. In `bdsim` all wires are point to point, a *one-to-many* connection is implemented by *many* wires,
for example
```
bd.connect(source, dest1, dest2, ...)
```
creates individual wires from `source` -> `dest1`, `source` -> `dest2` and so on.
Ports are designated using Python indexing notation, for example `block[2]` is port 2 (the third port) of `block`.  Whether it is an input or output port depends on context.
In the example above an index on the first argument refers to an output port, while on the second (or subsequent) arguments it refers to an input port.  If a block has only a single input or output port then no index is required, 0 is assumed.

A group of ports can be denoted using slice notation, for example 
```
bd.connect(source[2:5], dest[3:6)
```
will connect `source[2]` -> `dest[3]`, `source[3]` -> `dest[4]`, `source[4]` -> `dest[5]`.
The number of wires in each slice must be consistent.  You could even do a cross over by connecting `source[2:5]` to `dest[6:3:-1]`.

Line 21 assembles all the blocks and wires, instantiates subsystems, checks connectivity to create a flat wire list, and then builds the dataflow execution plan.

Line 22 generates a report, in tabular form, showing a summary of the block diagram:

```
Blocks::

┌───┬─────────┬─────┬──────┬────────┬─────────┬───────┐
│id │    name │ nin │ nout │ nstate │ ndstate │ type  │
├───┼─────────┼─────┼──────┼────────┼─────────┼───────┤
│ 0 │  demand │   0 │    1 │      0 │       0 │ step  │
│ 1 │   sum.0 │   2 │    1 │      0 │       0 │ sum   │
│ 2 │  gain.0 │   1 │    1 │      0 │       0 │ gain  │
│ 3 │   plant │   1 │    1 │      1 │       0 │ LTI   │
│ 4 │ scope.0 │   2 │    0 │      0 │       0 │ scope │
└───┴─────────┴─────┴──────┴────────┴─────────┴───────┘

Wires::

┌───┬──────┬──────┬──────────────────────────┬─────────┐
│id │ from │  to  │       description        │  type   │
├───┼──────┼──────┼──────────────────────────┼─────────┤
│ 0 │ 0[0] │ 1[0] │ demand[0] --> sum.0[0]   │ int     │
│ 1 │ 0[0] │ 4[1] │ demand[0] --> scope.0[1] │ int     │
│ 2 │ 3[0] │ 1[1] │ plant[0] --> sum.0[1]    │ float64 │
│ 3 │ 1[0] │ 2[0] │ sum.0[0] --> gain.0[0]   │ float64 │
│ 4 │ 2[0] │ 3[0] │ gain.0[0] --> plant[0]   │ float64 │
│ 5 │ 3[0] │ 4[0] │ plant[0] --> scope.0[0]  │ float64 │
└───┴──────┴──────┴──────────────────────────┴─────────┘

Continuous state variables:   1
Discrete state variables:     0
initial state  x0 =  [0.]
```
In the first table we can see key information about each block, its `id` (used internally), name, the number of input and output ports, the number of
continuous- and discrete-time states, and the type which is the block class.  Note that the name is auto-generated based on the type, except if it has
been set explicitly as for the blocks `demand` and `plant`.

The second table shows all wires in point-to-point form, showing the start and end block and port (the block is represented here by its `id`) and the type of the object sent along the wire.

Finally, there is a summary of the number of states for the complete system: the number of continuous states, the number
of discrete states, and the initial value of the continuous state vector.

Line 24 runs the simulation for 5 seconds 
using the default variable-step RK45 solver and saves output values at least every 0.1s.  The scope block pops up a graph

![bdsim output](https://github.com/petercorke/bdsim/raw/master/figs/Figure_1.png)

The simulation results are in a container object
```
>>> out
results:
t           | ndarray (67,)
x           | ndarray (67, 1)
xnames      | list              
```
which contains an array of time values, an array of state values, and a list of the names of the state variables.

Line 25 saves the content of the scope to be saved in the file called `scope0.pdf`.

Line 26 blocks the script until all figure windows are closed, or the script is killed with SIGINT.

The result `out` is effectively a structure with elements

```
>>> out
results:
t           | ndarray (67,)
x           | ndarray (67, 1)
xnames      | list        
y0          | ndarray (67,)
y1          | ndarray (67,)
ynames      | list   
```
where

- `t` the time vector: ndarray, shape=(M,)
- `x` is the state vector: ndarray, shape=(M,N), one row per timestep
- `xnames` is a list of the names of the states corresponding to columns of `x`, eg. "plant.x0"

The `watch` argument is a list of outputs to log, in this case `plant` defaults
to output port 0.  This information is saved in additional variables `y0`, `y1`
etc.  `ynames` is a list of the names of the watched variables.

Line 29 saves the scope graphics as a PDF file.

Line 30 blocks until the last figure is dismissed.

More details on this Wiki about:

- [Adding blocks](Adding-blocks)
- [Connecting blocks](Connecting-blocks)
- [Running the simulation](Running)


## Other examples

In the folder `bdsim/examples` you can find a few other runnable examples:

- [`eg1.py`](https://github.com/petercorke/bdsim/blob/master/examples/eg1.py) the example given above
- [`waveform.py`](https://github.com/petercorke/bdsim/blob/master/examples/waveform.py) two signal generators connected to two scopes

Examples from Chapter four of _Robotics, Vision & Control (2017)_:

- [`rvc4_2.py`](https://github.com/petercorke/bdsim/blob/master/examples/rvc4_2.py) Fig 4.2 - a car-like vehicle with bicycle kinematics driven by a rectangular pulse steering signal
- [`rvc4_4.py`](https://github.com/petercorke/bdsim/blob/master/examples/rvc4_4.py) Fig 4.4 - a car-like vehicle driving to a point

![RVC Figure 4.4](https://github.com/petercorke/bdsim/raw/master/figs/rvc4_4.gif)

- [`rvc4_6.py`](https://github.com/petercorke/bdsim/blob/master/examples/rvc4_6.py) Fig 4.6 - a car-like vehicle driving to/along a line

![RVC Figure 4.6](https://github.com/petercorke/bdsim/raw/master/figs/rvc4_6.gif)

- [`rvc4_8.py`](https://github.com/petercorke/bdsim/blob/master/examples/rvc4_8.py) Fig 4.8 - a car-like vehicle using pure-pursuit trajectory following

![RVC Figure 4.6](https://github.com/petercorke/bdsim/raw/master/figs/rvc4_8.gif)

- [`rvc4_11.py`](https://github.com/petercorke/bdsim/blob/master/examples/rvc4_11.py) Fig 4.11 a car-like vehicle driving to a pose

![RVC Figure 4.11](https://github.com/petercorke/bdsim/raw/master/figs/rvc4_11.gif)

Figs 4.8 (pure pursuit) and Fig 4.21 (quadrotor control) are yet to be done.

# A more concise way

Wiring, and some simple arithmetic blocks like `GAIN`, `SUM` and `PROD` can be implicitly generated by overloaded Python operators.  This strikes a nice balance between block diagram coding and Pythonic programming.

```
     1  #!/usr/bin/env python3
     2
     3  import bdsim
     4
     5  sim = bdsim.BDSim()  # create simulator
     6  bd = sim.blockdiagram()  # create an empty block diagram
     7
     8  # define the blocks
     9  demand = bd.STEP(T=1, name='demand')
    10  plant = bd.LTI_SISO(0.5, [2, 1], name='plant')
    11  scope = bd.SCOPE(styles=['k', 'r--'], movie='eg1.mp4')
    12
    13  # connect the blocks using Python syntax
    14  scope[0] = plant
    15  scope[1] = demand
    16  plant[0] = 10 * (demand - plant)
    17
    18  bd.compile()   # check the diagram
    19  bd.report()    # list all blocks and wires
    20
    21  sim.set_options(animation=True)
    22  out = sim.run(bd, 5, watch=[plant,])  # simulate for 5s
```
This requires fewer lines of code and the code is more readable. Importantly, it results in in *exactly the same* block diagram in terms of blocks and wires
```
Wires::

┌───┬──────┬──────┬──────────────────────────────┬─────────┐
│id │ from │  to  │         description          │  type   │
├───┼──────┼──────┼──────────────────────────────┼─────────┤
│ 0 │ 1[0] │ 2[0] │ plant[0] --> scope.0[0]      │ float64 │
│ 1 │ 0[0] │ 2[1] │ demand[0] --> scope.0[1]     │ int     │
│ 2 │ 0[0] │ 3[0] │ demand[0] --> _sum.0[0]      │ int     │
│ 3 │ 1[0] │ 3[1] │ plant[0] --> _sum.0[1]       │ float64 │
│ 4 │ 3[0] │ 4[0] │ _sum.0[0] --> _gain.0(10)[0] │ float64 │
│ 5 │ 4[0] │ 1[0] │ _gain.0(10)[0] --> plant[0]  │ float64 │
└───┴──────┴──────┴──────────────────────────────┴─────────┘
```
The implicitly created blocks have names prefixed with an underscore.

# bdedit: the graphical editing tool

![block diagram](https://github.com/petercorke/bdsim/raw/master/figs/eg1-bdedit.png)

`bdedit` is a multi-platform PyQt5-based graphical tool to create, edit, render and execute block diagram models.

From the examples folder
```
% bdedit eg1.bd
```
will create a display like that shown above.  Pushing the run button, top left (triangle in circle) will spawn `bdrun` as a subprocess which will:

* parse the JSON file
* instantiate all blocks and wires
* compile and run the diagram

# Article

I published [this article on LinkedIn](https://www.linkedin.com/in/petercorke/recent-activity/shares/), which describes the thouhgt process behind bdsim.

# Limitations

There are lots!  The biggest is that `bdsim` is based on a very standard variable-step integrator from the scipy library.  For discontinuous inputs (step, square wave, triangle wave, piecewise constant) the transitions get missed.  This also makes it inaccurate to simulate hybrid discrete-continuous time systems.  We really need a better integrator, perhaps [`odedc`](https://help.scilab.org/docs/6.1.0/en_US/odedc.html) from SciLab could be integrated.


