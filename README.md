# bdsim: Block Diagram Simulation for Python


<div align="center">
  <img src="https://raw.githubusercontent.com/petercorke/bdsim/master/figs/BDSimLogo_NoBackgnd@2x.png" width="500" alt="bdsim logo">
  <br>
  <strong>A Pythonic block-diagram environment for the simulation and analysis of dynamic systems.</strong>
  <br><br>


[![JupyterLite](https://img.shields.io/badge/Try_it_Now-JupyterLite-orange?style=for-the-badge&logo=jupyter)](https://petercorke.github.io/bdsim/lite/lab?path=index.ipynb)
  [![PyPI version](https://img.shields.io/pypi/v/machinevision-toolbox-python?style=for-the-badge&color=blue)](https://pypi.org/project/bdsim/)
  [![Documentation](https://img.shields.io/badge/Docs-View_Online-blue?style=for-the-badge)](https://petercorke.github.io/bdsim/)

  <p>
    <a href="https://github.com/petercorke/bdsim">GitHub</a> •
    <a href="https://github.com/petercorke/bdsim/wiki">Wiki</a> •
    <a href="https://github.com/petercorke/bdsim/blob/main/CHANGELOG.md">Changelog</a> •
    <a href="#installation">Installation</a>
  </p>
</div>


---
### Status & Ecosystem
[![A Python Robotics Package](https://raw.githubusercontent.com/petercorke/robotics-toolbox-python/master/.github/svg/py_collection.min.svg)](https://github.com/petercorke/robotics-toolbox-python)
[![QUT Centre for Robotics Open Source](https://github.com/qcr/qcr.github.io/raw/master/misc/badge.svg)](https://qcr.github.io)
[![Build Status](https://github.com/petercorke/bdsim/actions/workflows/ci.yml/badge.svg)](https://github.com/petercorke/bdsim/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/petercorke/bdsim/branch/main/graph/badge.svg)](https://codecov.io/gh/petercorke/machinevision-toolbox-python)
![Python Version](https://img.shields.io/pypi/pyversions/bdsim.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI - Downloads](https://img.shields.io/pypi/dw/bdsim)](https://pypistats.org/packages/bdsim)

### Powered by
[![Powered by Spatial Maths](https://raw.githubusercontent.com/petercorke/spatialmath-python/master/.github/svg/sm_powered.min.svg)](https://github.com/petercorke/spatialmath-python)
[![Powered by NumPy](https://img.shields.io/badge/powered_by-NumPy-013243?logo=numpy&logoColor=white)](https://numpy.org)


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
To include the graphical editor (bdedit) and its dependencies:

Bash
pip install bdsim[editor]
```

Install locally with help from the [detailed installation guide](https://petercorke.github.io/machinevision-toolbox-python/installation.html#installing-the-toolbox).

Or skip setup and run the [browser-based JupyterLite examples](https://petercorke.github.io/machinevision-toolbox-python/lite/lab/index.html?path=files/index.ipynb).

## Example

The power of bdsim lies in its conciseness. The step response of a simple first-order system can be defined and simulated in just a few lines of code:

```python
Python
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

* Seamless Integration: Incorporate SciPy solvers, PyTorch models, or custom computer vision pipelines directly into your simulation loops.

* Scalability: Programmatically generate massive block diagrams or run large-scale batch simulations on headless servers.

## 📚 Documentation
Full Documentation: https://petercorke.github.io/bdsim/

Wiki: Access the community wiki for deep dives into specific block behaviours and tutorials.