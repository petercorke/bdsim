# Notebooks

These notebooks run locally (Jupyter, JupyterLab, VS Code), on Google Colab and in the browser with
JupyterLite. Locally, install bdsim first, `pip install bdsim`, and Jupyter or the VS Code Jupyter extension.
`index.ipynb` is the list of them and the entry point for Colab (below).

## How the environment is set up

Google Colab fetches only the single `.ipynb` it is opened from, so each notebook carries its own copy of the
code that installs bdsim. That copy is the cell whose first line starts with `# BDSIM_BOOTSTRAP_CELL`, the
second cell of a notebook, folded by default. It prints one line saying where it is running and which version of
bdsim it found.

* `_bdsim_nb_bootstrap.py` is the single source of truth for that cell. It is bdsim's copy of the template
  shared by RTB, MVTB and bdsim, [`notebooks/bootstrap_template.py` in
  rvc-ecosystem](https://github.com/petercorke/rvc-ecosystem/blob/main/notebooks/bootstrap_template.py), with only
  its repo-specific constants changed. The explanation of what it does in each environment is in
  [notebooks.md](https://github.com/petercorke/rvc-ecosystem/blob/main/notebooks.md) there.
* The cell is generated into every notebook by `sync_bootstrap.py` (also from rvc-ecosystem). **Never edit the
  cell in a notebook**: edit `_bdsim_nb_bootstrap.py` and let the hook regenerate it.
* A notebook that needs more says so in its own metadata, not in the cell:

  ```json
  "metadata": {"bdsim_bootstrap": {"extras": ["control"], "min_version": "1.5.0"}}
  ```

  `extras` are extras of bdsim (`control` is python-control, which installs in the browser too); `packages` are
  other packages, such as another toolbox; `min_version` is the oldest bdsim the notebook works with.

### Colab and the development version

On Colab a notebook comes from `main` but bdsim from PyPI, so a notebook can use what the next release will have
(`linearization` and `cart-pole` use `functions()`, `linearize()` and `STATE`). With `min_version` set, the cell
installs the development version from GitHub if the release on PyPI is older, and says so. Once the release
catches up the fallback is never used. In JupyterLite there is nothing to check: the site's bdsim is built from
the same commit as the notebooks.

## Editing a notebook

Edit it in VS Code or anywhere and commit it. Install the hooks once, in a clone or worktree:

    pip install pre-commit
    pre-commit install

and every commit that includes a notebook is tidied first: no outputs or execution counts, the same kernel and
language in the metadata (an editor writes the name of your own Python environment there, which is noise in every
diff), the file written as Jupyter writes it, the bootstrap cell current, and the first cell checked. `pre-commit
run --all-files` does the same by hand, and the `lint` job of CI runs it, so CI tells you if you forgot.

The hooks are [`.pre-commit-config.yaml`](../../.pre-commit-config.yaml) at the top of the repo, pinned to a commit
of rvc-ecosystem. They only touch notebooks in this folder.

## The first cell

The first cell is ordinary markdown written by hand: the logo and the title, the copyright line and a description.
The logo is an absolute GitHub URL, since Colab fetches only the one `.ipynb` and cannot see `docs/figs/`, and it
has a `width`, a `height` and `style="height:auto"`: Colab needs the height to keep the aspect ratio, but a viewer
that limits an image to the width of its cell (a narrow notebook pane) shrinks the width and leaves the height, so
without the style the logo is squashed. The `notebooks-first-cell` hook checks this. Figures in the notebooks are
linked by absolute URL for the same reason.

## Colab

A `colab.research.google.com/github/petercorke/bdsim/blob/main/docs/notebooks/index.ipynb` link opens `index.ipynb`
there, and its relative links to the other notebooks work (Colab lists this folder through the GitHub API). Two
things to remember: a `+` in a file name is read as a space, so a link to `discrete-time+hybrid.ipynb` fails, and
the listing is limited to the first 100 entries, so keep this folder well under that.
