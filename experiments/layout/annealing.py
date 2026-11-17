import random
import math
import importlib.util
import sys


def optimize_placement(bd, steps=30000, initial_temp=100.0, final_temp=0.01):
    blocks = bd.blocklist
    wires = bd.wirelist
    n = len(blocks)

    if n == 0:
        return

    grid_dim = math.ceil(math.sqrt(n * 2))
    state = {}
    occupied = set()

    # Helper: Only blocks with BOTH inputs and outputs can be flipped
    def is_flippable(block):
        return block.nin > 0 and block.nout > 0

    # 1. Random Initialization
    for b in blocks:
        while True:
            x = random.randint(0, grid_dim - 1)
            y = random.randint(0, grid_dim - 1)
            if (x, y) not in occupied:
                break

        flip = random.choice([True, False]) if is_flippable(b) else False
        state[b] = [x, y, flip]
        occupied.add((x, y))

    # 2. Cost Function
    def get_cost(current_state):
        cost = 0
        for wire in wires:
            start_block = wire.start.block
            end_block = wire.end.block

            if not start_block or not end_block:
                continue

            sx, sy, sflip = current_state[start_block]
            ex, ey, eflip = current_state[end_block]

            # Port geometry natively enforces left-to-right preference
            port_out_x = sx + (0 if sflip else 1)
            port_out_y = sy

            port_in_x = ex + (1 if eflip else 0)
            port_in_y = ey

            dx = abs(port_in_x - port_out_x)
            dy = abs(port_in_y - port_out_y)

            # Multiply Y distance by 1.5 to encourage horizontal flattening
            cost += dx + (dy * 1.5)

        # Flip penalty: a flip must save >3 units of wire distance to be accepted
        flips = sum(1 for b, v in current_state.items() if v[2])
        cost += flips * 3.0

        return cost

    # 3. Annealing Loop
    current_cost = get_cost(state)
    temp = initial_temp
    cooling_rate = (final_temp / initial_temp) ** (1.0 / steps)

    for step in range(steps):
        b = random.choice(blocks)
        cx, cy, cflip = state[b]

        new_x, new_y, new_flip = cx, cy, cflip
        swap_block = None

        mutation = random.random()
        if mutation < 0.3:
            if is_flippable(b):
                new_flip = not cflip
        elif mutation < 0.6:
            while True:
                nx = random.randint(0, grid_dim - 1)
                ny = random.randint(0, grid_dim - 1)
                if (nx, ny) not in occupied:
                    new_x, new_y = nx, ny
                    break
        else:
            swap_block = random.choice(blocks)
            if swap_block != b:
                new_x, new_y = state[swap_block][0], state[swap_block][1]

        # Apply tentatively
        old_b_state = list(state[b])
        if swap_block and swap_block != b:
            old_swap_state = list(state[swap_block])
            state[b] = [new_x, new_y, new_flip]
            state[swap_block][0], state[swap_block][1] = cx, cy
        else:
            state[b] = [new_x, new_y, new_flip]

        new_cost = get_cost(state)
        delta = new_cost - current_cost

        if delta < 0 or random.random() < math.exp(-delta / temp):
            current_cost = new_cost
            if not swap_block and (new_x, new_y) != (cx, cy):
                occupied.remove((cx, cy))
                occupied.add((new_x, new_y))
        else:
            state[b] = old_b_state
            if swap_block and swap_block != b:
                state[swap_block] = old_swap_state

        temp *= cooling_rate

    # 4. Write states back
    min_x = min(s[0] for s in state.values())
    min_y = min(s[1] for s in state.values())

    for b, (x, y, flip) in state.items():
        b.x = x - min_x
        b.y = y - min_y
        b.flip = flip


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

    # 1. Draw Wires (Simple straight translucent lines between ports)
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

        # Draw straight line
        ax.plot([px1, px2], [py1, py2], color="gray", linewidth=2, alpha=0.6, zorder=1)
        # Arrow head at the destination
        ax.plot(px2, py2, marker=">", color="gray", markersize=6, zorder=2)

    # 2. Draw Blocks
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

    plt.title("bdsim Block Placement Optimization")
    plt.show(block=True)


if __name__ == "__main__":
    import pathlib

    print("Loading examples/eg1.py...")
    eg1_path = pathlib.Path("examples/eg1.py")
    if not eg1_path.exists():
        print(f"Error: Could not find {eg1_path}. Run from the bdsim root directory.")
        sys.exit(1)

    spec = importlib.util.spec_from_file_location("eg1", eg1_path)
    eg1 = importlib.util.module_from_spec(spec)

    import matplotlib.pyplot as plt

    plt.ion()

    try:
        spec.loader.exec_module(eg1)
    except Exception as e:
        pass

    bd = eg1.bd
    print(
        f"\nLoaded diagram with {len(bd.blocklist)} blocks and {len(bd.wirelist)} wires."
    )

    print("Running layout optimizer (Simulated Annealing)...")
    optimize_placement(bd)

    print("Visualizing optimized layout...")
    plt.ioff()
    visualize_layout(bd)
