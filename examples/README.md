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

Examples provided in this folder include:

- `eg1.py` the example given above
- `waveform.py` two signal generators connected to two scopes
-  `vanderpol.py` a classic non-linear oscillator
- `sine+sampler.py` a sine wave generator connected to a scope via a ZOH

- `RVC2` is a folder holding some examples from Chapter four of [_Robotics, Vision & Control (2017)_](https://petercorke.com/rvc/home):

  - `rvc4_2.py` Fig 4.2 - a car-like vehicle with bicycle kinematics driven by a rectangular pulse steering signal
  - `rvc4_4.py` Fig 4.4 - a car-like vehicle driving to a point

  - `rvc4_6.py` Fig 4.6 - a car-like vehicle driving to/along a line


  - `rvc4_11.py` Fig 4.11 a car-like vehicle driving to a pose

All `bdsim` programs support a number of [command line switches](https://github.com/petercorke/bdsim/wiki/Runtime-options).

More examples can be found in the [support package for the book _Robotics, Vision & Control (2023) 3e_](https://github.com/petercorke/RVC3-python/tree/main/RVC3/models).