# bdsim
# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
#sys.path.insert(0, os.path.abspath('.'))
# defined relative to configuration directory which is where this file conf.py lives
sys.path.append(os.path.abspath('exts'))


# -- Project information -----------------------------------------------------

project = 'Block diagram simulation'
copyright = '2020, Peter Corke'
author = 'Peter Corke'

# The full version, including alpha/beta/rc tags
release = '0.7'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
 'sphinx.ext.autodoc',
 'sphinx.ext.todo',
 'sphinx.ext.viewcode',
 'sphinx.ext.mathjax',
 'sphinx.ext.coverage',
 'sphinx.ext.inheritance_diagram',
 'blockname'
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['test_*']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'
html_show_sourcelink = True

html_theme = 'sphinx_rtd_theme'
#html_theme = 'alabaster'
#html_theme = 'pyramid'
#html_theme = 'sphinxdoc'

github_url = 'https://github.com/petercorke/bdsim'

html_theme_options = {
    "github_host": "gitlab.com",
    'github_user': 'petercorke',
    'github_repo': 'bdsim',
    "display_github": True,
    'github_version': 'HEAD',
    #'logo_name': False,
    'logo_only': False,
    #'description': 'Spatial maths and geometry for Python',
    'display_version': True,
    'prev_next_buttons_location': 'both',
    'analytics_id': 'G-11Q6WJM565',

    }
html_favicon = 'favicon.ico'

html_logo = '../../figs/BDSimLogo_NoBackgnd@2x.png'
html_last_updated_fmt = '%d-%b-%Y'
autoclass_content = "class"
html_show_sourcelink = True

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']

rst_epilog = """
.. role:: raw-html(raw)
   :format: html
.. |BlockOptions| replace:: :raw-html:`<a href="https://petercorke.github.io/bdsim/internals.html?highlight=block%20__init__#bdsim.Block.__init__">common Block options</a>`
"""