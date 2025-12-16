#!/usr/bin/env python3
import sys
import os
import string
import time
import tkinter as tk
from screeninfo import get_monitors
from tkinter import ttk

from edit import Editor
import bdsim

# eventually from a config file
appearance = {
    "block:width": 100,
    "block:height": 60,
    "block:bg": "white",
    "block:outline": "black",
    "block:font": ("Helvetica", 12),
}


def center_on_monitor(window, monitor_index, width, height):
    """
    Centers a Tkinter window on a specific monitor.

    Args:
        window: The Tkinter instance (root or Toplevel).
        monitor_index: Index of the monitor (0 = Primary).
        width: Desired width of the window.
        height: Desired height of the window.
    """
    try:
        monitors = get_monitors()

        # Safety check: if index is too high, default to primary (0)
        if monitor_index >= len(monitors):
            monitor_index = 0

        target_monitor = monitors[monitor_index]

        # 1. Calculate the center position relative to the monitor
        # (Monitor Width - Window Width) / 2
        x_offset = (target_monitor.width - width) // 2
        y_offset = (target_monitor.height - height) // 2

        # 2. Add the monitor's absolute global position
        final_x = target_monitor.x + x_offset
        final_y = target_monitor.y - y_offset

        # 3. Apply geometry: "WidthxHeight+X+Y"
        window.geometry(f"{width}x{height}+{final_x}+{final_y}")

    except Exception as e:
        print(f"Error centering window: {e}")
        # Fallback: just set size and let OS decide position
        window.geometry(f"{width}x{height}")


# def pairwise(iterable):
#     "s -> (s0,s1), (s1,s2), (s2, s3), ..."
#     a, b = tee(iterable)
#     next(b, None)
#     return zip(a, b)


def init_diagram(editor):
    b1 = editor.add_block(1, 1, (100, 100), image_path="Icons/integrator.png")
    b2 = editor.add_block(0, 1, (200, 100))
    b3 = editor.add_block(3, 1, (300, 100))
    b4 = editor.add_block(2, 3, (400, 100))
    editor.add_wire("block4.out0", "block3.in0")

    # print(ed.coords(b4.item))
    # print(ed.bbox(b4.item))
    # print(canvas.bbox(b4.id))
    # canvas.create_rectangle(canvas.bbox(b4.id), outline="black", fill="")


def create_ui(root, blockmenu):
    center_on_monitor(
        root, 1, 1200, 600
    )  # set geometry to 800x600 centered on monitor 1

    root.title("bdsim editor")

    # Mac-specific app name setting
    try:
        root.tk.call("tk", "appname", "BDSim Editor")
    except:
        try:
            root.wm_class("BDSim Editor", "BDSim Editor")
        except:
            pass  # Not supported

    # ---------------------------------------------------------------------
    # App task bar

    menubar = tk.Menu(root)
    root.config(menu=menubar)

    # File menu
    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(
        label="New", accelerator="Cmd+N", command=lambda: print("New")
    )
    file_menu.add_command(
        label="Open...", accelerator="Cmd+O", command=lambda: print("Open")
    )
    file_menu.add_separator()
    file_menu.add_command(
        label="Save", accelerator="Cmd+S", command=lambda: print("Save")
    )
    file_menu.add_command(
        label="Save As...", accelerator="Shift+Cmd+S", command=lambda: print("Save As")
    )
    file_menu.add_separator()
    file_menu.add_command(
        label="Close", accelerator="Cmd+W", command=lambda: root.quit()
    )

    # Edit menu
    edit_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Edit", menu=edit_menu)
    edit_menu.add_command(
        label="Undo", accelerator="Cmd+Z", command=lambda: print("Undo")
    )
    edit_menu.add_command(
        label="Redo", accelerator="Shift+Cmd+Z", command=lambda: print("Redo")
    )
    edit_menu.add_separator()
    edit_menu.add_command(
        label="Cut", accelerator="Cmd+X", command=lambda: print("Cut")
    )
    edit_menu.add_command(
        label="Copy", accelerator="Cmd+C", command=lambda: print("Copy")
    )
    edit_menu.add_command(
        label="Paste", accelerator="Cmd+V", command=lambda: print("Paste")
    )
    edit_menu.add_separator()
    edit_menu.add_command(
        label="Select All", accelerator="Cmd+A", command=lambda: print("Select All")
    )

    # Block menu
    block_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Block", menu=block_menu)
    block_menu.add_command(label="Add Block", command=lambda: print("Add Block"))
    block_menu.add_command(label="Delete Block", command=lambda: print("Delete Block"))
    block_menu.add_separator()
    block_menu.add_command(label="Connect Blocks", command=lambda: print("Connect"))

    # View menu
    view_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="View", menu=view_menu)
    view_menu.add_command(
        label="Zoom In", accelerator="Cmd+=", command=lambda: print("Zoom In")
    )
    view_menu.add_command(
        label="Zoom Out", accelerator="Cmd+-", command=lambda: print("Zoom Out")
    )
    view_menu.add_command(
        label="Actual Size", accelerator="Cmd+0", command=lambda: print("Actual Size")
    )
    view_menu.add_separator()
    view_menu.add_command(label="Show Grid", command=lambda: print("Toggle Grid"))

    # Help menu
    help_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Help", menu=help_menu)
    help_menu.add_command(label="About BDSim Editor", command=lambda: print("About"))
    help_menu.add_command(label="Documentation", command=lambda: print("Docs"))

    # ---------------------------------------------------------------------
    # Top toolbar across the window

    toolbar = ttk.Frame(root, padding=(4, 2))
    toolbar.pack(side=tk.TOP, fill=tk.X)

    btn_new = ttk.Button(toolbar, text="New", command=lambda: print("New"))
    btn_open = ttk.Button(toolbar, text="Open", command=lambda: print("Open"))
    btn_save = ttk.Button(toolbar, text="Save", command=lambda: print("Save"))
    btn_add = ttk.Button(toolbar, text="Add Block", command=lambda: print("Add block"))
    btn_zoom_in = ttk.Button(toolbar, text="Zoom +", command=lambda: print("Zoom in"))
    btn_zoom_out = ttk.Button(toolbar, text="Zoom -", command=lambda: print("Zoom out"))

    btn_new.pack(side=tk.LEFT, padx=2)
    btn_open.pack(side=tk.LEFT, padx=2)
    btn_save.pack(side=tk.LEFT, padx=2)
    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
    btn_add.pack(side=tk.LEFT, padx=2)
    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
    btn_zoom_in.pack(side=tk.LEFT, padx=2)
    btn_zoom_out.pack(side=tk.LEFT, padx=2)

    # ---------------------------------------------------------------------
    # Main PanedWindow with left Treeview and right Editor canvas

    panes = ttk.Panedwindow(root, orient=tk.HORIZONTAL)
    panes.pack(fill="both", expand=True)

    left = ttk.Frame(panes, width=100)
    right = ttk.Frame(panes)

    panes.add(left, weight=0)
    panes.add(right, weight=4)

    # --------------- Treeview in left pane
    tree_frame = ttk.Frame(left)
    tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

    tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical")
    tree = ttk.Treeview(tree_frame, yscrollcommand=tree_scroll.set, show="tree")
    tree_scroll.config(command=tree.yview)
    tree_scroll.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=False)

    # populate the tree from blockmenu
    if blockmenu:
        for cat, items in blockmenu.items():
            parent = tree.insert("", "end", text=cat, open=True)
            for it in items:
                tree.insert(parent, "end", text=it)
                # collapse tree categories at startup
                for iid in tree.get_children():
                    tree.item(iid, open=False)

    # Convenience helpers
    def get_selected_block():
        sel = tree.selection()
        if not sel:
            return None
        iid = sel[0]
        # return block name only for leaf items
        if tree.parent(iid):
            return tree.item(iid, "text")
        return None

    # --------------- Canvas in right pane
    canvas = Editor(
        right,
        bg="white",
        height=500,
        width=1000,
        relief=tk.RIDGE,
        background="white",
        borderwidth=1,
    )
    canvas.pack(fill="both", expand=True, padx=5, pady=5)

    # Double-click on tree item to add block to canvas
    def tree_click(event):
        print("Tree double-click")
        block = get_selected_block()
        if block:  # is a leaf item
            tree._last_activated_block = block
            canvas.event_generate("<<NewBlockActivated>>", when="tail", data=tree)

    tree.bind("<Double-1>", tree_click)

    return canvas


def get_blocks():
    sim = bdsim.BDSim()  # create simulator

    blockmenu = {}
    for block, info in sim._blocklibrary.items():
        cls = info["blockclass"].capitalize()
        if cls in blockmenu:
            blockmenu[cls].append(block)
        else:
            blockmenu[cls] = [block]

    return blockmenu


if __name__ == "__main__":
    root = tk.Tk()
    # block_menu = get_blocks()
    block_menu = None
    canvas = create_ui(root, block_menu)
    init_diagram(canvas)
    root.mainloop()
