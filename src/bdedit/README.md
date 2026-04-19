
![block diagram](https://github.com/petercorke/bdsim/raw/master/figs/eg1-bdedit.png)

`bdedit` is a multi-platform PySide6-based graphical tool to create, edit, render and execute block diagram models.

Key features include:

* Graphical creation of block diagrams
* Diagrams stored as human-readable/editable JSON with extension `.bd`
* High-quality export for publications — **vector PDF**, **vector SVG**, and high-resolution **PNG**
* Launch `bdsim` to simulate the model directly from the editor
* Automatically discovers all bdsim and toolbox blocks and adds them to the block library panel
* Icons can be any PNG image or a LaTeX expression
* Undo/redo history
* Grouping boxes and free-text annotations
* Open Recent file list (persisted across sessions)

**PySide6 is licensed under LGPL.**

# Installation

```
pip install bdsim[edit]
```

## macOS — named app bundle

To have the menu bar show **bdedit** instead of **Python**, and to enable
double-click / drag-drop file opening, build a `.app` bundle:

```
make app          # builds bdedit.app and registers it with Launch Services
```

or equivalently:

```
python src/bdsim/bdedit/make_app.py
```

Then drag `bdedit.app` to `/Applications` or keep it in the repo root and
launch with `open bdedit.app`.  After building, `open -a bdedit file.bd` will
open the file directly.

## Windows — file association

To associate `.bd` files with bdedit so they open on double-click:

```
bdedit-associate-windows          # installed as a console script by pip
# or:
python src/bdsim/bdedit/associate_bd_windows.py
```

Run once after installation (no admin rights needed — writes to HKCU).
To remove: `bdedit-associate-windows --uninstall`

# Getting started

Open a diagram:
```
bdedit examples/eg1.bd
```

Run an existing `.bd` file without the GUI:
```
bdrun eg1.bd
bdrun +g -a eg1.bd    # enable graphics, disable animation
```

## Command-line options

| Option | Description |
|---|---|
| `file` | `.bd` file to open on launch |
| `-p [file]`, `--print [file]` | Export diagram to file and exit; defaults to same name as model (PDF) |
| `-f png\|pdf`, `--format` | Override export format when using `--print` |
| `-b white\|grey`, `--background` | Background colour (default: grey) |
| `-s N`, `--fontsize N` | Block name font size (default: 12) |
| `-d`, `--debug` | Enable debug output |

Examples:
```
bdedit -p examples/eg1.bd          # saves eg1.pdf
bdedit -p out.pdf examples/eg1.bd  # saves out.pdf (vector)
bdedit -p out.png -f png examples/eg1.bd
```

# Keyboard shortcuts

| Key | Action |
|---|---|
| `V` | Fit diagram to canvas |
| `F` | Flip selected block(s) |
| `Ctrl+Z` / `Ctrl+Y` | Undo / Redo |
| `Del` / `Backspace` | Delete selected items |
| `Ctrl+S` | Save |
| `Ctrl+O` | Open |

# Exporting diagrams

**File → Export As** offers three formats:

| Format | Output |
|---|---|
| PDF | Vector — lines, curves, and text are fully scalable |
| SVG | Vector — ideal for web or Inkscape editing |
| PNG | High-resolution raster (3× oversampling, ~288 dpi) |

The background and grid are automatically suppressed during export so you always
get a clean white-background image regardless of the current display mode.

The save dialog shows the full filename including extension so you always see
what you will get.

# Adding a block

Click a block from the library panel on the left-hand side.  Each category is
initially closed; click it to reveal the blocks within.

All blocks are added to the centre of the canvas.

The key elements of a block are:

* **Input ports** — small blue boxes
* **Output ports** — small red triangles / arrow heads
* **Icon** — centre of the block (a 250×250 PNG image)
* **Block label** — beneath the block, must be unique in the diagram
* **Block class** — shown on hover
* **Port labels** — small text inside the box at input/output ports
* **Parameters** — set by right-clicking the block

Blocks can be flipped by typing `F` while selected.

# Wiring blocks together

* Click one port then click another, or
* Click and drag from one port to another.

An output port can connect to any number of input ports.

# Selecting and moving elements

All selected elements have an orange highlight.  Drag a region to select
everything within it.

Selected items can be moved by clicking and dragging.  Blocks cannot be resized.

Selected wire segments can be adjusted:
* Horizontal segments can be dragged up/down
* Vertical segments can be dragged left/right

# Connectors

The wire routing is sometimes hard to control. Add a **Connector** from the
_Canvas Items_ category: run a wire into its input and one or more wires from
its output.  A wire can have an arbitrary number of connectors.

# Block parameters

Right-clicking a block opens a parameter panel on the right.  Parameters are
initialised from default values in the block's docstring.

* **Update parameters** — validates types and applies changes
* **View documentation** — opens the GitHub docs page for the block class

Parameter values can be:

* A constant: `3.14`
* A Python expression (prefix with `=`): `=[x**2 for x in range(10)]`
* Runtime values via a **Main** block — point it at a Python script that sets
  up the simulation environment, for example:

  ```python
  from bdsim import bdload, BDSim

  sim = BDSim()
  bd = sim.blockdiagram()

  lmbda = 0.08
  bd = bdload(bd, "model.bd", globals=globals())
  bd.compile()
  out = sim.run(bd, 100)
  ```

# Grouping boxes

Transparent coloured boxes drawn below all other items.  Use them to add
visual structure to large diagrams.

# Free text

Click **Canvas Items → Text Item** to place a text annotation.  Select it to
edit.  Multi-line text with left/right/centred alignment is supported.

# Further details

More detail about the internal data structures is in the
[technical report](TechReport.md) (note: the visual appearance has evolved
since that was written).
