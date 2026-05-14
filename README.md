# bdsim: Block Diagram Simulation for Python


<div align="center">
  <img src="https://raw.githubusercontent.com/petercorke/bdsim/main/docs/figs/bdsim_logo.png" width="500" alt="bdsim logo">
  <br>
  <strong>A Pythonic block-diagram environment for the simulation and analysis of dynamic systems.</strong>
  <br><br>

<p style="font-size: 1.5em;"><em>Block diagram thinking → Python coding</em></p>


[![JupyterLite](https://img.shields.io/badge/Try_it_Now-JupyterLite-orange?style=for-the-badge&logo=jupyter)](https://petercorke.github.io/bdsim/lite/lab?path=notebooks/index.ipynb)
  [![PyPI version](https://img.shields.io/pypi/v/bdsim?style=for-the-badge&color=blue)](https://pypi.org/project/bdsim/)
  [![Documentation](https://img.shields.io/badge/Docs-View_Online-blue?style=for-the-badge)](https://petercorke.github.io/bdsim/)

  <p>
    <a href="https://github.com/petercorke/bdsim">GitHub</a> •
    <a href="https://github.com/petercorke/bdsim/wiki">Wiki</a> •
    <a href="https://github.com/petercorke/bdsim/blob/main/CHANGELOG.md">Changelog</a> •
    <a href="https://petercorke.github.io/bdsim/installation.html">Installation</a>
  </p>
</div>

---
### Status & Project Health
[![Build Status](https://github.com/petercorke/bdsim/actions/workflows/ci.yml/badge.svg)](https://github.com/petercorke/bdsim/actions/workflows/ci.yml)
[![Downloads](https://static.pepy.tech/badge/bdsim/month)](https://pepy.tech/projects/bdsim)
![Python Version](https://img.shields.io/pypi/pyversions/bdsim.svg)
[![Coverage](https://codecov.io/gh/petercorke/bdsim/branch/main/graph/badge.svg)](https://codecov.io/gh/petercorke/bdsim)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)



### Ecosystem & Dependencies
[![A Python Robotics Package](https://raw.githubusercontent.com/petercorke/robotics-toolbox-python/master/.github/svg/py_collection.min.svg)](https://github.com/petercorke/robotics-toolbox-python)
[![QUT Centre for Robotics Open Source](https://github.com/qcr/qcr.github.io/raw/master/misc/badge.svg)](https://qcr.github.io)

[![powered by NumPy](https://img.shields.io/badge/powered_by-NumPy-013243?logo=numpy&logoColor=white)](https://numpy.org)
[![powered by SciPy](https://img.shields.io/badge/powered_by-SciPy-0054a6?logo=scipy&logoColor=white)](https://scipy.org)
[![powered by Matplotlib](https://img.shields.io/badge/powered_by-Matplotlib-11557c?logo=matplotlib&logoColor=white)](https://matplotlib.org)
[![Powered by Spatial Maths](https://raw.githubusercontent.com/petercorke/spatialmath-python/master/.github/svg/sm_powered.min.svg)](https://github.com/petercorke/spatialmath-python)

## Synopsis

**bdsim** bridges the gap between mathematical block diagrams and executable Python code. Unlike traditional graphical-only tools, it treats modelling as code, allowing you to define, simulate, and analyze continuous-time, discrete-time, or hybrid systems within a modern software engineering workflow. Wires in bdsim aren't limited to scalars; they pass NumPy arrays, dictionaries, or even SpatialMath objects seamlessly through your system, integrating directly with the Robotics and Machine Vision toolboxes.

## 🚀 Key Features

* **Python-First Workflow**: Define your systems in pure Python code. Use your preferred IDE (like VS Code), manage versions with Git, and integrate with standard unit-testing frameworks.
* **Rich Data Types**: Wires in `bdsim` aren't limited to scalars. Seamlessly pass NumPy arrays, dictionaries, or complex objects like `SE3` and `SO3` from the `spatialmath-python` library.
* **Modular & Extensible**: Adding new functionality is straightforward. Create custom blocks by simply subclassing the `Block` class.
* **Hybrid Ecosystem**: Native integration with the **Robotics Toolbox** and **Machine Vision Toolbox** for Python.
* **Powerful Editor**: Includes `bdedit`, a PySide-based graphical editor for visual system design and discovery.
* **Publication Ready**: Export diagrams or simulation data to to high-quality formats such as PDF or SVG for use in publications.

## 💻  Quick start

You can install `bdsim` directly from PyPI:

```bash
pip install bdsim
```

To include the graphical editor (bdedit) and its dependencies:

```bash
pip install bdsim[editor]
```

Install locally with help from the [detailed installation guide](https://petercorke.github.io/bdsim/installation.html).

Or skip setup and run the [browser-based JupyterLite examples](https://petercorke.github.io/bdsim/lite/lab/index.html?path=notebooks/index.ipynb).

## Example

The power of bdsim lies in its conciseness. The step response of a simple first-order system can be defined and simulated in just a few lines of code:

```python
import bdsim

sim = bdsim.BDSim()
bd = sim.blockdiagram()

# Define blocks
step = bd.STEP(T=1, pos=1)
plant = bd.LTI_SISO(1, [1, 1]) # 1/(s+1)
scope = bd.SCOPE()

# Connect blocks
bd.connect(step, plant)
bd.connect(plant, scope)

bd.compile()
out = sim.run(bd, T=5)
```

## 🔍 Why bdsim?

In contrast to traditional graphical simulation tools, bdsim treats modelling as code. This ensures:

* Better Version Control: No more opaque binary blobs. Your models are searchable, diffable text.

* Seamless Integration: Incorporate SciPy solvers, PyTorch models, or custom robotic vision pipelines directly into your simulation loops.

* Scalability: Programmatically generate massive block diagrams or run large-scale batch simulations on headless servers.

## Startup and Tooling Metadata

Block discovery supports two metadata modes:

* `block_metadata="minimal"`: faster startup for runtime/realtime use; skips help-oriented metadata such as parsed docstrings and documentation URLs.
* `block_metadata="full"`: richer metadata for tooling such as `bdedit`, menus, and help screens.

Example:

```python
import bdsim

sim = bdsim.BDSim(block_metadata="minimal")
```

The realtime entry point defaults to minimal metadata, while editor-style tooling should request full metadata explicitly.

For realtime applications, prefer the dedicated import path:

```python
from bdsim.realtime import BDRealTime
```

## 📚 Documentation
Full Documentation: https://petercorke.github.io/bdsim/

Wiki: Access the community wiki for deep dives into specific block behaviours and tutorials.