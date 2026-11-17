# Auto-layout experiments

Two ways to place the blocks of a block diagram on a grid, for (1) giving a diagram that
has no positions a layout when the web editor (bdweb) opens it, and (3) a drawing exporter.
Not part of the package; this branch is for trying things.

| File | Approach | Needs |
|---|---|---|
| `annealing.py` | simulated annealing, random start | nothing |
| `milp.py` | mixed-integer linear program, topology-aware cost | `pip install pulp[cbc]` |

Both take a `BlockDiagram` and call `optimize_placement(bd)`.  Run from the repo root:
`python experiments/layout/annealing.py examples/eg1.py`.

Next: run both over the diagrams in `examples/` and compare wire length, crossings,
right-to-left wires and run time; then move the winner to `src/bdsim/layout.py` as a function
that returns positions and does not change the diagram (a clean PR to `main`).  The MILP
would be an optional extra, with `pulp` imported lazily.
