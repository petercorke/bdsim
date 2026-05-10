******************
Installing `bdsim`
******************

To install the latest stable release from PyPI, simply run:

.. code-block:: bash

	$ pip install bdsim

This will install the `bdsim` package as well as any dependencies required for its functionality.

You can also install the latest development version from GitHub using:

.. code-block:: bash

	$ pip install git+https://github.com/machinevision-toolbox/bdsim.git

.. warning:: The GitHub version may be unstable and is not recommended for production use. It may contain bugs or incomplete features. Use it at your own risk.


Installation environment
==========================

It is highly recommend that you use Miniconda and create an environment for your
simulation work. This will allow you to manage dependencies and avoid conflicts with
other code. You can use tools such as ``venv`` or ``conda`` to create and manage your
environment. For example, with conda you could run:

.. code-block:: bash
        :linenos:

        $ conda create -n bdsim python=3.12
        $ conda activate bdsim
        $ pip install bdsim

Line 2 activates the environment you just created, and typically this will
modify your shell prompt to indicate the active environment. Line 3 installs
`bdsim` and its dependencies into that environment. You can then use this
environment for your projects.


Installation extras
====================

``pip`` also supports installing optional dependencies, known as "extras". These are
additional packages that provide extra functionality but are not required for the core
functionality of the toolbox. You can specify which extras you want to install by
including them in square brackets after the package name.

.. code-block:: bash

	$ pip install machinevision-toolbox-python[extra]


The available extras are:

+--------------+-------------------------------------------+
| Extra        | Purpose                                   |
+==============+===========================================+
| ``dev``      | Development and test tools                |
+--------------+-------------------------------------------+
| ``docs``     | Documentation build toolchain             |
+--------------+-------------------------------------------+
| ``jupyter``  | Jupyter notebook widgets and plotting     |
|              | support                                   |
+--------------+-------------------------------------------+
| ``bdedit``   | PySide6 graphic editor support            |
+--------------+-------------------------------------------+
| ``all``      | All of the above                          |
+--------------+-------------------------------------------+

For example, to install the jupyter support extras, you would run:


.. code-block:: bash

        $ pip install bdsim[jupyter]

.. warning::
        Many shells, including ``bash`` and ``zsh`` interpret the square brackets as a glob pattern. 
        You must escape the square brackets, for example any of the following will work:

        .. code-block:: bash

                $ pip install bdsim\[jupyter\]
                $ pip install 'bdsim[jupyter]'
                $ pip install bdsim'[jupyter]'