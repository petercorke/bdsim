![PyPI - Downloads](https://img.shields.io/pypi/dm/bdsim)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/bdsim)](https://pypi.python.org/pypi/bdsim/)
[![PyPI version fury.io](https://badge.fury.io/py/bdsim.svg)](https://pypi.python.org/pypi/bdsim/)
[![PyPI status](https://img.shields.io/pypi/status/ansicolortags.svg)](https://pypi.python.org/pypi/bdsim/)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/petercorke/bdsim/graphs/commit-activity)
[![GitHub license](https://img.shields.io/github/license/Naereen/StrapDown.js.svg)](https://github.com/petercorke/bdsim/blob/master/LICENSE)

- GitHub repository: [https://github.com/petercorke/bdsim](https://github.com/petercorke/bdsim)
- Examples and details: [https://github.com/petercorke/bdsim/wiki](https://github.com/petercorke/bdsim/wiki)
- Documentation: [https://petercorke.github.io/bdsim](https://petercorke.github.io/bdsim)
- Dependencies: `numpy`, `scipy`, `matplotlib`, `spatialmath`, `ffmpeg` (if rendering animations as a movie)

# Block diagram simulation

This Python package enables modelling and simulation of dynamic systems conceptualized in block diagram form, but represented in terms of Python class and method calls.  Unlike Simulink or LabView we write Python code rather than drawing boxes and wires.  Wires can communicate any Python type such as scalars, lists, numpy arrays, other objects, and even functions.

We first sketch the dynamic system we want to simulate as a block diagram, for example this simple first-order system

![block diagram](https://github.com/petercorke/bdsim/raw/master/figs/bd1-sketch.png)

which we can express concisely with `bdsim` as (see [`bdsim/examples/eg1.py`](https://github.com/petercorke/bdsim/blob/master/examples/eg1.py)

```python
     1	#!/usr/bin/env python3
     2	
     3	import bdsim.simulation as sim
     4	
     5	bd = sim.Simulation()
     6	
     7	# define the blocks
     8	demand = bd.STEP(T=1, pos=(0,0), name='demand')
     9	sum = bd.SUM('+-', pos=(1,0))
    10	gain = bd.GAIN(10, pos=(1.5,0))
    11	plant = bd.LTI_SISO(0.5, [2, 1], name='plant', pos=(3,0))
    12	scope = bd.SCOPE(styles=['k', 'r--'], pos=(4,0))
    13	
    14	# connect the blocks
    15	bd.connect(demand, sum[0], scope[1])
    16	bd.connect(plant, sum[1])
    17	bd.connect(sum, gain)
    18	bd.connect(gain, plant)
    19	bd.connect(plant, scope[0])
    20	
    21	bd.compile()   # check the diagram
    22	bd.report()    # list all blocks and wires
    23	
    24	bd.run(5)  # simulate for 5s
    25	
    26	bd.dotfile('bd1.dot')  # output a graphviz dot file
    27	bd.savefig('pdf')      # save all figures as pdf
    28	
    29	bd.done()
```
which is just 18 lines of code.

The red block annotations in the diagram are the names of blocks, and have become names of instances of object that represent those blocks.  The blocks can also have names which are used in diagnostics and as labels in plots.

In `bdsim` all wires are point to point, a *one-to-many* connection is implemented by *many* wires.

Ports are designated using Python indexing and slicing notation, for example `sum[0]`.  Whether it is an input or output port depends on context.  Blocks are connected by `connect(from, to_1, to_2, ...)` so an index on the first argument refers to an output port, while on the second (or subsequent) arguments refers to an input port.  If a port has only a single port then no index is required.

A bundle of wires can be denoted using slice notation, for example `block[2:4]` refers to ports 2 and 3.  When connecting slices of ports the number of wires in each slice must be consistent.  You could even do a cross over by connecting `block1[2:4]` to `block2[5:2:-1]`.

Line 22 shows a report, in tabular form, showing all the blocks and wires in the diagram.

```python
Blocks::

  id  name                  nin    nout    nstate  
----  ------------------  -----  ------  --------  
0     source.step.demand  0      1       0         
1     function.sum.b1     2      1       0         
2     function.gain.b2    1      1       0         
3     transfer.LTI.plant  1      1       1         
4     sink.scope.b4       2      0       0         

Wires::

  id  from    to      description                     type     
----  ------  ------  ------------------------------  -------  
0       0[0]    1[0]  step.demand[0] --> sum.b1[0]    int      
1       0[0]    4[1]  step.demand[0] --> scope.b4[1]  int      
2       3[0]    1[1]  LTI.plant[0] --> sum.b1[1]      float64  
3       1[0]    2[0]  sum.b1[0] --> gain.b2[0]        float64  
4       2[0]    3[0]  gain.b2[0] --> LTI.plant[0]     float64  
5       3[0]    4[0]  LTI.plant[0] --> scope.b4[0]    float64  
```

Line 24 runs the simulation for 5 seconds 

```python
s.run(5)
```
using the default variable-step RK45 solver and saves output values at least every 0.1s.  The scope block pops up a graph

![bdsim output](https://github.com/petercorke/bdsim/raw/master/figs/Figure_1.png)

Line 27 causes the graphs in all displayed figures to be saved in the specified format, in this case the file would be called `scope.b4.pdf`.

Line 28 blocks the script until all figure windows are closed, or the script is killed with SIGINT.

To save the results is achieved by

```python
out = s.run(5, dt=0.1)
```

The result `out` is effectively a structure with elements

- `t` the time vector: ndarray, shape=(M,)
- `x` is the state vector: ndarray, shape=(M,N)
- `xnames` is a list of the names of the states corresponding to columns of `x`, eg. "plant.x0"

Line 26 attempts to produce something like a real block diagram by generating produce a [Graphviz](https://www.graphviz.org) .dot file.  Using `dot`
we can generate a graphic

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


# Other examples

In the folder `bdsim/examples` you can find a couple of runnable examples:

- [`eg1.py`](https://github.com/petercorke/bdsim/blob/master/examples/eg1.py) the example given above
- [`waveform.py`](https://github.com/petercorke/bdsim/blob/master/examples/waveform.py) two signal generators connected to two scopes

Examples from Chapter four of _Robotics, Vision & Control (2017)_:

- [`rvc4_2.py`](https://github.com/petercorke/bdsim/blob/master/examples/rvc4_2.py) Fig 4.2 - a car-like vehicle with bicycle kinematics driven by a rectangular pulse steering signal
- [`rvc4_4.py`](https://github.com/petercorke/bdsim/blob/master/examples/rvc4_4.py) Fig 4.4 - a car-like vehicle driving to a point

![RVC Figure 4.4](https://github.com/petercorke/bdsim/raw/master/figs/rvc4_4.gif)

- [`rvc4_6.py`](https://github.com/petercorke/bdsim/blob/master/examples/rvc4_6.py) Fig 4.6 - a car-like vehicle driving to/along a line

![RVC Figure 4.6](https://github.com/petercorke/bdsim/raw/master/figs/rvc4_6.gif)

- [`rvc4_11.py`](https://github.com/petercorke/bdsim/blob/master/examples/rvc4_11.py) Fig 4.11 a car-like vehicle driving to a pose

![RVC Figure 4.11](https://github.com/petercorke/bdsim/raw/master/figs/rvc4_11.gif)

Figs 4.8 (pure pursuit) and Fig 4.21 (quadrotor control) are yet to be done.

# Limitations

There are lots!  The biggest is that `bdsim` is based on a very standard variable-step integrator from the scipy library.  For discontinuous inputs (step, square wave, triangle wave, piecewise constant) the transitions get missed.  This also makes it inaccurate to simulate hybrid discrete-continuous time systems.  We really need a better integrator, perhaps [`odedc`](https://help.scilab.org/docs/6.1.0/en_US/odedc.html) from SciLab could be integrated.


