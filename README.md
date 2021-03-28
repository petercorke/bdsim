[![PyPI - Downloads](https://img.shields.io/pypi/dm/bdsim)](https://pypistats.org/packages/bdsim)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/bdsim)](https://pypi.python.org/pypi/bdsim/)
[![PyPI version fury.io](https://badge.fury.io/py/bdsim.svg)](https://pypi.python.org/pypi/bdsim/)
[![PyPI status](https://img.shields.io/pypi/status/ansicolortags.svg)](https://pypi.python.org/pypi/bdsim/)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/petercorke/bdsim/graphs/commit-activity)
[![GitHub license](https://img.shields.io/github/license/Naereen/StrapDown.js.svg)](https://github.com/petercorke/bdsim/blob/master/LICENSE)


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
<li>Dependencies: `numpy`, `scipy`, `matplotlib`, `spatialmath`, `ansitable`, `colored`, `ffmpeg` (if rendering animations as a movie)</li>
</ul>
</td>
</tr>
</table>


# Block diagram simulation

This Python package enables modelling and simulation of dynamic systems conceptualized in block diagram form, but represented in terms of Python class and method calls.  Unlike Simulink or LabView we write Python code rather than drawing boxes and wires.  Wires can communicate any Python type such as scalars, lists, numpy arrays, other objects, and even functions.

We first sketch the dynamic system we want to simulate as a block diagram, for example this simple first-order system

![block diagram](https://github.com/petercorke/bdsim/raw/master/figs/bd1-sketch.png)

which we can express concisely with `bdsim` as (see [`bdsim/examples/eg1.py`](https://github.com/petercorke/bdsim/blob/master/examples/eg1.py)

```python
     1  #!/usr/bin/env python3
     2
     3  import bdsim
     4
     5
     6  sim = bdsim.BDSim(animation=True)  # create simulator
     7  print(sim)
     8  bd = sim.blockdiagram()  # create an empty block diagram
     9
    10  # define the blocks
    11  demand = bd.STEP(T=1, pos=(0,0), name='demand')
    12  sum = bd.SUM('+-', pos=(1,0))
    13  gain = bd.GAIN(10, pos=(1.5,0))
    14  plant = bd.LTI_SISO(0.5, [2, 1], name='plant', pos=(3,0))
    15  scope = bd.SCOPE(styles=['k', 'r--'], pos=(4,0))
    16
    17  # connect the blocks
    18  bd.connect(demand, sum[0], scope[1])
    19  bd.connect(plant, sum[1])
    20  bd.connect(sum, gain)
    21  bd.connect(gain, plant)
    22  bd.connect(plant, scope[0])
    23
    24  bd.compile()   # check the diagram
    25  bd.report()    # list all blocks and wires
    26
    27  out = sim.run(bd, 5, watch=[plant, demand])  # simulate for 5s
    28
    29  sim.savefig(scope, 'scope0')
    30  sim.done(bd, block=True)
```
which is just 20 lines actual of code.

The red block annotations in the diagram are the names of blocks, and have become names of instances of object that represent those blocks.  The blocks can also have names which are used in diagnostics and as labels in plots.

In `bdsim` all wires are point to point, a *one-to-many* connection is implemented by *many* wires.

Ports are designated using Python indexing and slicing notation, for example `sum[0]`.  Whether it is an input or output port depends on context.  Blocks are connected by `connect(from, to_1, to_2, ...)` so an index on the first argument refers to an output port, while on the second (or subsequent) arguments refers to an input port.  If a port has only a single port then no index is required.

A bundle of wires can be denoted using slice notation, for example `block[2:4]` refers to ports 2 and 3.  When connecting slices of ports the number of wires in each slice must be consistent.  You could even do a cross over by connecting `block1[2:4]` to `block2[5:2:-1]`.

Line 25 generates a report, in tabular form, showing all the blocks and wires in the diagram.

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
```

where `nstate` is the number of continuous states and `ndstate` is the number
of discrete states.

Line 27 runs the simulation for 5 seconds 
using the default variable-step RK45 solver and saves output values at least every 0.1s.  The scope block pops up a graph

![bdsim output](https://github.com/petercorke/bdsim/raw/master/figs/Figure_1.png)

Line 29 saves the content causes the graphs in all displayed figures to be saved in the specified format, in this case the file would be called `scope.b4.pdf`.

Line 28 blocks the script until all figure windows are closed, or the script is killed with SIGINT.

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

A [Graphviz](https://www.graphviz.org) .dot file can be generated by

```python
bd.dotfile('demo.dot')
```

which you can compile and display

```shell
% dot -Tpng -o demo.png demo.dot 
```
or `neato`

```shell
% neato -Tpng -o demo.png demo.dot
```

![output of neato](https://github.com/petercorke/bdsim/raw/master/figs/bd1.png)

While this is topologically correct, it's not quite the way we would expect the diagram to be drawn.  `dot` ignores the `pos` options on the blocks while `neato` respects them, but is prone to drawing all the lines on top of each other.

Sources are shown as 3D boxes, sinks as folders, functions as boxes (apart from gains which are triangles and summing junctions which are points), and transfer functions as connectors (look's like a gate).  To create a decent looking plot you need to manually place the blocks using the `pos` argument to place them. Unit spacing in the x- and y-directions is generally sufficient. 

The `sim` object can do these operations in a convenient shorthand
```python
sim.showgraph(bd)
```
and display the result via your webbrowser.

# Other examples

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

# Limitations

There are lots!  The biggest is that `bdsim` is based on a very standard variable-step integrator from the scipy library.  For discontinuous inputs (step, square wave, triangle wave, piecewise constant) the transitions get missed.  This also makes it inaccurate to simulate hybrid discrete-continuous time systems.  We really need a better integrator, perhaps [`odedc`](https://help.scilab.org/docs/6.1.0/en_US/odedc.html) from SciLab could be integrated.


