**********************
Notebooks & examples
**********************

Jupyter notebooks
==================

Jupyter notebooks are a great way to learn how to use `bdsim`, and to explore its
various features and capabilities.

The notebooks are provided in the folder ``docs/notebooks`` and there are a number of different ways to
run a Jupyter notebook.

Running a notebook
---------------------

Locally from the command line
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You need to load some packages first.  You can do this at install time, and no harm in installing again.

.. code-block:: bash

    pip install bdsim[jupyter]

or just pull the packages you need for the notebooks

.. code-block:: bash

    pip install jupyter ipympl ipywidgets

Then run Jupyter

.. code-block:: bash

    jupyter notebook yourfile.ipynb

which will start a server and open a new browser tab with the Jupyter GUI.  The UI is a bit clunky, but it works.  

JupyterLab is a more modern interface to Jupyter notebooks, and it is available as an
option when you install Jupyter.  It has a more modern interface and better support for
multiple notebooks. You would:

.. code-block:: bash

    pip install jupyterlab
    jupyter lab yourfile.ipynb

.. note:: 
    A powerful feature of Jupyter is that the server can run on a different machine
    than your browser interface.  This allows you to run the notebooks on a more powerful
    computer on your network -- that machine must have the Toolbox and Jupyter
    installed and have the notebooks available in its filesystem.  To do this, you would start a
    Jupyter server on the remote machine ``$ jupyter server``, note the URL it is serving
    on, and connect to it from your local browser.

Locally using Visual Studio Code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a very convenient way to work and highly recommended -- the interface is rather
more polished than the standard Jupyter interface.  You need to install
some packages first.  You can do this at install time, and no harm in installing again.

.. code-block:: bash

    pip install bdsim[jupyter]

or

.. code-block:: bash

    pip install jupyter ipympl ipywidgets

Then install the [Jupyter extension for Visual Studio Code](https://marketplace.visualstudio.com/items?itemName=ms-toolsai.jupyter). This will allow you to open
and run the notebooks directly in Visual Studio Code -- just open the file from the file explorer view.
This provides a much nicer interface, supports multiple notebooks, and is great for debugging.

.. note:: 
    You can also use the Visual Studio Code interface to run the notebooks in a Jupyter
    server running on your local machine or on a remote machine.  If you are running the
    notebooks on a remote machine then you will need to set up a Jupyter server on that
    machine ``$ jupyter server``, note the URL it is serving on, and connect to it from 
    Visual Studio Code.  This is a bit more work to set up, but it allows you to run 
    the notebooks on a more powerful machine than your local laptop -- that machine 
    must have the Toolbox and Jupyter installed and the notebooks available on its filesystem.

In the browser using Jupyter lite
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Jupyter lite is a version of Jupyter that runs entirely in the browser, without the need
for a server.  The environment supports NumPy and Matplotlib all compiled for the web.
It is a great option for quickly trying out the notebooks without
installing anything on your local machine.  To use it, just click the "Launch in Jupyter
Lite" button at the top of each notebook page, and it will open the notebook in a new
browser tab running Jupyter lite.


In the cloud using Google Colab
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. |colab_image| image:: https://colab.research.google.com/img/colab_favicon_256px.png
   :height: 30px
   :alt: Open In Colab

.. |jupyterlite_image| image:: https://img.shields.io/badge/Jupyter-Lite-orange?logo=jupyter
   :height: 20px
   :alt: Open In JupyterLite


Just click the |colab_image| buttons below to open the notebooks in Colab.  Colab will
pull the notebook from GitHub, and allow you to interact with it in a browser tab. If
you modify the notebook you have the option of saving it in your own GitHub account, or
on Google Drive.

While this is theoretically a convenient approach with zero install on your computer, it is unfortunate that each notebook is quite slow to startup because the toolboxes need to be installed into the Colab environment, and they are only cached there for a short amount of time.


Provided notebooks 
------------------



.. csv-table::
   :header-rows: 1
   :widths: 28, 16, 16, 40

   "Notebook", "|jupyterlite_image|", "|colab_image|", "Description"
   "`Introduction <https://github.com/petercorke/bdsim/blob/main/docs/lite/files/getting-started.ipynb>`_", "`open <https://petercorke.github.io/bdsim/lite/lab/index.html?path=getting-started.ipynb>`_", "`open <https://colab.research.google.com/github/petercorke/bdsim/blob/main/docs/lite/files/getting-started.ipynb>`_", "A quick introduction to the package."
   "`Discrete & hybrid systems <https://github.com/petercorke/bdsim/blob/main/docs/lite/files/discrete-time+hybrid.ipynb>`_", "`open <https://petercorke.github.io/bdsim/lite/lab/index.html?path=discrete-time%2Bhybrid.ipynb>`_", "`open <https://colab.research.google.com/github/petercorke/bdsim/blob/main/docs/lite/files/discrete-time+hybrid.ipynb>`_", "Simulating discrete-time and mixed discrete-/continuous-time systems."
   "`Event-based systems <https://github.com/petercorke/bdsim/blob/main/docs/lite/files/bouncing-ball.ipynb>`_", "`open <https://petercorke.github.io/bdsim/lite/lab/index.html?path=bouncing-ball.ipynb>`_", "`open <https://colab.research.google.com/github/petercorke/bdsim/blob/main/docs/lite/files/bouncing-ball.ipynb>`_", "The classic bouncing ball example."
   "`Advanced topics <https://github.com/petercorke/bdsim/blob/main/docs/lite/files/advanced-topics.ipynb>`_", "`open <https://petercorke.github.io/bdsim/lite/lab/index.html?path=advanced-topics.ipynb>`_", "`open <https://colab.research.google.com/github/petercorke/bdsim/blob/main/docs/lite/files/advanced-topics.ipynb>`_", "Advanced options: options, movies, animation, block loading."


Obtaining the notebooks
-----------------------

If you want to run the notebooks locally, you will need to obtain them from the GitHub repository.  
You can download all the notebooks `directly from the GitHub web interface as a zip file <https://petercorke.github.io/bdsim/bdsim_notebooks.zip>`_, and extract the notebooks from the zip file.

Alternatively, you can clone the repository

.. code-block:: shell

    git clone https://github.com/petercorke/bdsim.git

The notebooks are located in the ``docs/notebooks`` folder.  
You can also navigate to `that folder on GitHub <https://github.com/petercorke/machinevision-toolbox-python/tree/main/docs/notebooks>`_ and download the notebooks individually.



Other Jupyter notebook tools
----------------------------

* ``jupyter nbconvert``  executes a notebook and saves the result in HTML, PDF, Markdown, LaTeX, or other formats. It can also turn the notebook into a Python script, with the documentation cells as comment blocks.
*  ``papermill`` allows parameterizing and executing Jupyter Notebooks programmatically. This is useful for running the same notebook with different parameters, for example to run a training notebook with different hyperparameters.  It can also be used to execute a notebook and save the result in a new notebook file, which is useful for keeping a record of the executed notebook with the results.


Examples
=========

`bdsim` ships with a number of example scripts that demonstrate how to use the library
to build and simulate block diagrams.  These are located in the ``examples`` folder.
You can run these examples from the command line.

You can download all the examples `directly from the GitHub web interface as a zip file <https://petercorke.github.io/bdsim/bdsim_examples.zip>`_, and extract the Python files from the zip file.

Alternatively, you can clone the repository

.. code-block:: shell

    git clone https://github.com/petercorke/bdsim.git

The examples are located in the ``examples`` folder.  
You can also navigate to `that folder on GitHub <https://github.com/petercorke/bdsim/tree/main/examples>`_ and download the examples individually.
