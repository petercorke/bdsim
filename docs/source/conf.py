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
import warnings

# Keep docs builds focused on bdsim itself; avoid external toolbox discovery
# side effects (extra warnings from third-party docstrings during scanning).
os.environ.setdefault("BDSIM_NO_TOOLBOXES", "1")

# Reduce non-actionable warning noise during docs builds.
warnings.filterwarnings(
    "ignore", message=r"invalid escape sequence", category=SyntaxWarning
)
warnings.filterwarnings(
    "ignore",
    message=r".*subclasses TransferBlock which is deprecated.*",
    category=FutureWarning,
)

# sys.path.insert(0, os.path.abspath('.'))
# defined relative to configuration directory which is where this file conf.py lives
sys.path.append(os.path.abspath("exts"))


# -- Project information -----------------------------------------------------

project = "Block diagram simulation"
copyright = "2020-, Peter Corke."
author = "Peter Corke"

try:
    import bdsim

    version = bdsim.__version__
except AttributeError:
    import re

    with open("../../pyproject.toml", "r") as f:
        m = re.compile(r'version\s*=\s*"([0-9\.]+)"').search(f.read())
        version = m[1]

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx.ext.mathjax",
    "matplotlib.sphinxext.plot_directive",
    "sphinx.ext.coverage",
    "sphinx.ext.intersphinx",
    "sphinx.ext.inheritance_diagram",
    "sphinx_autodoc_typehints",
    "sphinx_favicon",
    "blockname",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["test_*", "modules.rst"]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "alabaster"
html_show_sourcelink = True

html_theme = "sphinx_rtd_theme"
# html_theme = 'alabaster'
# html_theme = 'pyramid'
# html_theme = 'sphinxdoc'

github_url = "https://github.com/petercorke/bdsim"

html_theme_options = {
    "logo_only": False,
    "prev_next_buttons_location": "both",
    "collapse_navigation": False,
    "navigation_depth": 4,
    "titles_only": False,
}

html_logo = "../figs/bdsim_logo.png"
html_last_updated_fmt = "%d-%b-%Y"
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
# -------- RVC maths notation -------------------------------------------------------#

# see https://stackoverflow.com/questions/9728292/creating-latex-math-macros-within-sphinx
mathjax3_config = {
    "tex": {
        "macros": {
            # RVC Math notation
            #  - not possible to do the if/then/else approach
            #  - subset only
            "presup": [r"\,{}^{\scriptscriptstyle #1}\!", 1],
            # groups
            "SE": [r"\mathbf{SE}(#1)", 1],
            "SO": [r"\mathbf{SO}(#1)", 1],
            "se": [r"\mathbf{se}(#1)", 1],
            "so": [r"\mathbf{so}(#1)", 1],
            # vectors
            "vec": [r"\boldsymbol{#1}", 1],
            "dvec": [r"\dot{\boldsymbol{#1}}", 1],
            "ddvec": [r"\ddot{\boldsymbol{#1}}", 1],
            "fvec": [r"\presup{#1}\boldsymbol{#2}", 2],
            "fdvec": [r"\presup{#1}\dot{\boldsymbol{#2}}", 2],
            "fddvec": [r"\presup{#1}\ddot{\boldsymbol{#2}}", 2],
            "norm": [r"\Vert #1 \Vert", 1],
            # matrices
            "mat": [r"\mathbf{#1}", 1],
            "dmat": [r"\dot{\mathbf{#1}}", 1],
            "fmat": [r"\presup{#1}\mathbf{#2}", 2],
            # skew matrices
            "sk": [r"\left[#1\right]", 1],
            "skx": [r"\left[#1\right]_{\times}", 1],
            "vex": [r"\vee\left( #1\right)", 1],
            "vexx": [r"\vee_{\times}\left( #1\right)", 1],
            # quaternions
            "q": r"\mathring{q}",
            "fq": [r"\presup{#1}\mathring{q}", 1],
        }
    }
}

# -------- Options favicon -------------------------------------------------------#

html_static_path = ["_static"]
# create favicons online using https://favicon.io/favicon-converter/
favicons = [
    {
        "rel": "icon",
        "sizes": "16x16",
        "static-file": "favicon-16x16.png",
        "type": "image/png",
    },
    {
        "rel": "icon",
        "sizes": "32x32",
        "static-file": "favicon-32x32.png",
        "type": "image/png",
    },
    {
        "rel": "apple-touch-icon",
        "sizes": "180x180",
        "static-file": "apple-touch-icon.png",
        "type": "image/png",
    },
    {
        "rel": "android-chrome",
        "sizes": "192x192",
        "static-file": "android-chrome-192x192.png ",
        "type": "image/png",
    },
    {
        "rel": "android-chrome",
        "sizes": "512x512",
        "static-file": "android-chrome-512x512.png ",
        "type": "image/png",
    },
]

# -------- Options inheritance-diagram -----------------------------------------------#

inheritance_graph_attrs = dict(rankdir="TB")

# -------- Options InterSphinx -------------------------------------------------------#

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/", None),
    "matplotlib": ("https://matplotlib.org/stable/", None),
    "smtb": ("https://spatialmath-python.rai-inst.com/", None),
    "ansitable": ("https://petercorke.github.io/ansitable/", None),
}
