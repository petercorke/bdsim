import math
import importlib.util
import sys

try:
    import pulp
except ImportError:
    print("Error: The MILP approach requires the 'pulp' library.")
    print("Please run: pip install pulp[cbc]")
    sys.exit(1)


def optimize_placement(bd):
    """
    Optimizes bdsim block placement using a Mixed Integer Linear Program (MILP).
    Employs topology-aware cost functions to force left-to-right flow,
    pull sources/sinks to the edges, penalize reverse routing, and
    allow source->sink reference signals to stretch freely.
    """
    blocks = bd.blocklist
    wires = bd.wirelist
    n = len(blocks)

    if n == 0:
        return

    # 1. Grid Sizing
    # N + 2 gives enough slack for sinks to pull away from the main cluster
    grid_dim = n + 2

    # Big-M constant for linearization
    M = grid_dim * 2

    # 2. Create the Problem
    prob = pulp.LpProblem("Bdsim_Layout_Optimization", pulp.LpMinimize)

    # 3. Decision Variables
    x_vars = {}
    y_vars = {}
    f_vars = {}

    for b in blocks:
        x_vars[b] = prob.add_variable(
            f"x_{id(b)}", lowBound=0, upBound=grid_dim, cat=pulp.LpInteger
        )
        y_vars[b] = prob.add_variable(
            f"y_{id(b)}", lowBound=0, upBound=grid_dim, cat=pulp.LpInteger
        )

        # Only allow flipping if the block is neither a pure source nor a pure sink
        if b.nin > 0 and b.nout > 0:
            f_vars[b] = prob.add_variable(f"f_{id(b)}", cat=pulp.LpBinary)
        else:
            f_vars[b] = 0

    cost_terms = []

    # 4. Objective Function: Topology-Aware Routing Costs
    for idx, wire in enumerate(wires):
        sb = wire.start.block
        eb = wire.end.block

        if not sb or not eb:
            continue

        sb_out_x = x_vars[sb] + 1 - f_vars[sb]
        sb_out_y = y_vars[sb]

        eb_in_x = x_vars[eb] + f_vars[eb]
        eb_in_y = y_vars[eb]

        # Separate X distance into Forward and Reverse components
        fwd = prob.add_variable(f"fwd_{idx}", lowBound=0, upBound=M, cat=pulp.LpInteger)
        rev = prob.add_variable(f"rev_{idx}", lowBound=0, upBound=M, cat=pulp.LpInteger)
        dy = prob.add_variable(f"dy_{idx}", lowBound=0, upBound=M, cat=pulp.LpInteger)

        prob += fwd >= eb_in_x - sb_out_x
        prob += rev >= sb_out_x - eb_in_x
        prob += dy >= eb_in_y - sb_out_y
        prob += dy >= sb_out_y - eb_in_y

        # Default Cost Weights
        fwd_weight = 1.0
        rev_weight = 10.0
        dy_weight = 2.0

        # Semantic adjustment: Source -> Sink (Reference signals)
        # We drop the forward and vertical penalty so the solver isn't penalized
        # for stretching a reference wire across the entire diagram.
        if sb.nin == 0 and eb.nout == 0:
            fwd_weight = 0.1
            dy_weight = 0.1

        cost_terms.append(fwd_weight * fwd + rev_weight * rev + dy_weight * dy)

    # 5. Objective Function: Block Gravity & Orientation
    for b in blocks:
        # Gravity: Gently pull Sources left and Sinks right
        if b.nin == 0:
            cost_terms.append(2.0 * x_vars[b])
        if b.nout == 0:
            cost_terms.append(2.0 * (grid_dim - x_vars[b]))

        # Flip Penalty: Massive cost. Only flip if it saves multiple reverse-flow wires.
        if isinstance(f_vars[b], pulp.LpVariable):
            cost_terms.append(20.0 * f_vars[b])

    prob += pulp.lpSum(cost_terms)

    # 6. Non-Overlap Constraints
    for i in range(n):
        for j in range(i + 1, n):
            b1 = blocks[i]
            b2 = blocks[j]

            b_up = prob.add_variable(f"up_{i}_{j}", cat=pulp.LpBinary)
            b_dn = prob.add_variable(f"dn_{i}_{j}", cat=pulp.LpBinary)
            b_lf = prob.add_variable(f"lf_{i}_{j}", cat=pulp.LpBinary)
            b_rg = prob.add_variable(f"rg_{i}_{j}", cat=pulp.LpBinary)

            prob += b_up + b_dn + b_lf + b_rg >= 1

            prob += y_vars[b1] - y_vars[b2] >= 1 - M * (1 - b_up)
            prob += y_vars[b2] - y_vars[b1] >= 1 - M * (1 - b_dn)
            prob += x_vars[b1] - x_vars[b2] >= 1 - M * (1 - b_lf)
            prob += x_vars[b2] - x_vars[b1] >= 1 - M * (1 - b_rg)

    # 7. Solve
    status = prob.solve()

    if not status:
        print("Warning: MILP solver did not find an optimal solution.")

    # 8. Extract Results and Normalize Coordinates
    min_x = min(int(round(pulp.value(x_vars[b]))) for b in blocks)
    min_y = min(int(round(pulp.value(y_vars[b]))) for b in blocks)

    for b in blocks:
        b.x = int(round(pulp.value(x_vars[b]))) - min_x
        b.y = int(round(pulp.value(y_vars[b]))) - min_y
        if isinstance(f_vars[b], pulp.LpVariable):
            b.flip = bool(round(pulp.value(f_vars[b])))
        else:
            b.flip = False


def visualize_layout(bd):
    """
    Renders the layout grid and blocks with simple straight lines for visibility.
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches

    fig, ax = plt.subplots(figsize=(10, 8))

    max_x = max((b.x for b in bd.blocklist), default=1)
    max_y = max((b.y for b in bd.blocklist), default=1)

    ax.set_xlim(-1, max_x + 2)
    ax.set_ylim(-1, max_y + 2)
    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.set_xticks(range(-1, max_x + 3))
    ax.set_yticks(range(-1, max_y + 3))
    ax.grid(True, linestyle=":", alpha=0.4)

    # Draw Wires
    for wire in bd.wirelist:
        if not wire.start.block or not wire.end.block:
            continue

        sx, sy = wire.start.block.x, wire.start.block.y
        ex, ey = wire.end.block.x, wire.end.block.y
        sflip = getattr(wire.start.block, "flip", False)
        eflip = getattr(wire.end.block, "flip", False)

        px1 = sx + (-0.4 if sflip else 0.4)
        py1 = sy
        px2 = ex + (0.4 if eflip else -0.4)
        py2 = ey

        ax.plot([px1, px2], [py1, py2], color="gray", linewidth=2, alpha=0.6, zorder=1)
        ax.plot(px2, py2, marker=">", color="gray", markersize=6, zorder=2)

    # Draw Blocks
    for b in bd.blocklist:
        is_flipped = getattr(b, "flip", False)
        color = "#FFA07A" if is_flipped else "#ADD8E6"

        rect = patches.Rectangle(
            (b.x - 0.4, b.y - 0.4),
            0.8,
            0.8,
            linewidth=1.5,
            edgecolor="#333333",
            facecolor=color,
            zorder=3,
        )
        ax.add_patch(rect)

        name = b.name if b.name else b.__class__.__name__
        if len(name) > 10:
            name = name[:8] + ".."

        ax.text(
            b.x,
            b.y,
            name,
            ha="center",
            va="center",
            fontsize=9,
            fontweight="bold",
            zorder=4,
        )

    plt.title("bdsim Block Placement Optimization (MILP)")
    plt.show(block=True)


if __name__ == "__main__":
    import pathlib

    filename = sys.argv[1] if len(sys.argv) > 1 else "examples/eg1.py"

    print(f"Loading {filename}...")
    file_path = pathlib.Path(filename)
    if not file_path.exists():
        print(f"Error: Could not find {file_path}. Run from the bdsim root directory.")
        sys.exit(1)

    import traceback

    import matplotlib.pyplot as plt

    plt.ion()

    # Import the user's script as a module named after its file, so that
    # any name it defines (here: bd) is an attribute of the module.
    spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
    if spec is None or spec.loader is None:
        print(f"Error: cannot import {file_path} as a Python module.")
        sys.exit(1)
    module = importlib.util.module_from_spec(spec)

    # Let the script import siblings that live next to it
    sys.path.insert(0, str(file_path.resolve().parent))

    # The script's own argument parsing (bdsim.BDSim) reads sys.argv, so
    # give it the arguments we want, and restore ours afterwards.
    original_argv = sys.argv.copy()
    sys.argv = [str(file_path), "--no-graphics"]
    try:
        spec.loader.exec_module(module)
    except Exception:
        # Do not swallow the error: it is the reason bd may be missing.
        traceback.print_exc()
    finally:
        sys.argv = original_argv
        sys.path.pop(0)

    if not hasattr(module, "bd"):
        print(f"Error: {file_path} did not define a variable called 'bd'.")
        sys.exit(1)
    bd = module.bd
    print(
        f"\nLoaded diagram with {len(bd.blocklist)} blocks and {len(bd.wirelist)} wires."
    )

    print("Running layout optimizer (MILP Exact Solver)...")
    optimize_placement(bd)

    print("Visualizing optimized layout...")
    plt.ioff()
    visualize_layout(bd)
