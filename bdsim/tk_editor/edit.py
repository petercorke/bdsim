import tkinter as tk
import numpy as np
import re
from itertools import tee, pairwise
from PIL import Image, ImageTk

# from sklearn import tree

verbose_events = True

blockdict = {}
wirelist = []


class Block:
    blockWidth = 50  # block width
    blockHeight = 100  # block height
    a = 20  # distance from top/bottom
    b = 5  # half width of output
    portSize = 10  # size of port square
    portSep = 15
    blocknum = 0  # block index: 1, 2, ...

    def __init__(self, pos, nin, nout):
        self.nin = nin  # number of input ports
        self.nout = nout  # number of output ports
        self.pos = pos  # position of top-left corner on canvas
        self.tag = None
        self.inpos = []
        self.outpos = []
        self.item_id = None  # canvas item id
        self.flipped = False
        Block.blocknum += 1
        self.name = f"block{Block.blocknum}"

    def port_y(self, i, n):
        if n == 0:
            return None
        else:
            return self.pos[1] + self.blockHeight / 2 - ((n - 1) / 2 - i) * self.portSep


class Wire:
    wirenum = 0

    def __init__(self, start: tuple[Block, int], end: tuple[Block, int]):
        self.start = start
        self.end = end
        self.item_id = None  # canvas item id
        Wire.wirenum += 1

    def start_coord(self):
        block, port = self.start
        return block.outpos[port]

    def end_coord(self):
        block, port = self.end
        return block.inpos[port]


class Editor(tk.Canvas):
    """
    Represents a graphical block element for a block diagram editor.

    The GBlock class is responsible for creating and managing the visual representation
    of a block with configurable input and output ports. The block is drawn as a polygon
    on a canvas, with triangles on the right side for outputs and squares on the left side for inputs.
    The positions of input and output ports are calculated and stored for later use.

    Attributes:
        W (int): Width of the block.
        H (int): Height of the block.
        a (int): Vertical margin from the top and bottom edges.
        b (int): Half-width of the output triangle and input square.
        _inpos (list): List of input port positions relative to the block.
        _outpos (list): List of output port positions relative to the block.
        outline (list): List of points defining the block's outline polygon.
        id (int): Canvas object ID for the block polygon.

    Args:
        nin (int): Number of input ports.
        nout (int): Number of output ports.
        pos (tuple): (x, y) position of the block's top-left corner on the canvas.
        fill (str, optional): Fill color for the block. Defaults to "red".
        **kwargs: Additional keyword arguments passed to the canvas.create_polygon method.

    Methods:
        flip():
            Flips the block horizontally on the canvas.

        inpos(i):
            Returns the absolute position of the i-th input port.

        outpos(i):
            Returns the absolute position of the i-th output port.
    """

    _inpos = []
    _outpos = []
    _iports = []
    _oports = []

    active_output = None

    def event_print(self, event_name, event):
        if verbose_events:
            print(f"!! {event_name}, {event}, ({self.itemcget(tk.CURRENT, 'tags')})")

    def gridlines(canvas, line_distance):
        canvas.root.update()
        print(canvas.winfo_width())
        canvas_width = 1000
        canvas_height = 500
        # vertical lines at an interval of "line_distance" pixel
        for x in range(line_distance, canvas_width, line_distance):
            canvas.create_line(x, 0, x, canvas_height, fill="#f0f0f0")
        # horizontal lines at an interval of "line_distance" pixel
        for y in range(line_distance, canvas_height, line_distance):
            canvas.create_line(0, y, canvas_width, y, fill="#f0f0f0")

    def get_active_block(self):
        return self.blockdict[self.gettags(tk.CURRENT)[0]]

    def ortho_line(
        self, start: tuple[int, int], end: tuple[int, int], tag=[], **kwargs
    ) -> tuple[tuple[float, float], ...]:
        if start[0] < end[0]:
            if start[1] == end[1]:
                return (start, end)
            else:
                xmid = (start[0] + end[0]) // 2
                return (
                    start,
                    (xmid, start[1]),
                    (xmid, end[1]),
                    end,
                )
        else:
            # line has to go backwards
            L = 20
            H = 100
            if end[1] < start[1]:
                # new block above
                y = end[1] - H
            else:
                y = end[1] + H
            return (
                start,
                (start[0] + L, start[1]),
                (start[0] + L, y),
                (end[0] - L, y),
                (end[0] - L, end[1]),
                end,
            )

    def draw_ortho_line(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        width: int = 2,
        tag=[],
        **kwargs,
    ) -> None:
        coords = self.ortho_line(start, end)

        l = self.create_line(
            *[coord for point in coords for coord in point],
            arrow=tk.LAST,
            tags=tag,
            width=width,
            **kwargs,
        )
        print("ortholine", self.gettags(l))
        print("line id", l)
        re_wire = re.compile(r"(block\d+).out(\d+)\>(block\d+).in(\d+)")

    re_wire = re.compile(r"(block\d+).out(\d+)\>(block\d+).in(\d+)")

    def parse_io(self, s):
        m = self.re_wire.match(s)
        from_block = m.group(1)
        from_port = int(m.group(2))
        to_block = m.group(3)
        to_port = int(m.group(4))
        print(from_block, from_port, to_block, to_port)
        return from_block, from_port, to_block, to_port

    def redraw_wires(self, obj_id):
        # pass
        print("redraw_wires", obj_id)
        print("redraw_wires", self.gettags(obj_id))
        block = self.gettags(obj_id)[0]
        ids = self.find_withtag(f"wire&&{block}")
        print("wires to redraw:", ids)
        re_wire = re.compile(r"(block\d+).out(\d+)\>(block\d+).in(\d+)")
        for id in ids:
            tags = self.gettags(id)
            print("wire tags:", tags)
            m = re_wire.match(tags[3])
            from_block = m.group(1)
            from_port = int(m.group(2))
            to_block = m.group(3)
            to_port = int(m.group(4))
            print(from_block, from_port, to_block, to_port)
            self.delete(id)

            self.draw_ortho_line(
                self.blockdict[from_block].outpos[from_port],
                self.blockdict[to_block].inpos[to_port],
                tag=tags,
            )

    def add_block(
        self,
        nin: int,
        nout: int,
        pos: tuple[int, int],
        image_path: str = None,
        fill: str = "white",
        outline: str = "black",
        **kwargs,
    ) -> None:
        """
        Initialize a block object with specified input/output ports and position.

        Args:
            nin (int): Number of input ports.
            nout (int): Number of output ports.
            pos (tuple): (x, y) position of the block on the canvas.
            image_path (str, optional): Path to PNG image to display in block.
            fill (str, optional): Fill color for the block. Defaults to "red".
            **kwargs: Additional keyword arguments passed to the canvas.create_polygon method.
        """

        block = Block(pos, nin, nout)
        blockdict[block.name] = block

        # draw the block
        block.item_id = self.create_rectangle(
            pos[0],
            pos[1],
            pos[0] + block.blockWidth,
            pos[1] + block.blockHeight,
            fill=fill,
            outline=outline,
            tags=(block.name, "block"),
            **kwargs,
        )

        # Add image if provided
        if image_path:
            try:
                # Load and resize image to fit inside block
                img = Image.open(image_path)
                img_width = block.blockWidth - 10  # 5px margin on each side
                img = img.resize(
                    (img_width, img.height * img_width // img.width),
                    Image.Resampling.BICUBIC,
                )
                photo = ImageTk.PhotoImage(img)

                # Create image centered in block
                img_id = self.create_image(
                    pos[0] + block.blockWidth // 2,
                    pos[1] + block.blockHeight // 2,
                    image=photo,
                    anchor=tk.CENTER,
                    tags=(block.name, "block", "image"),
                )

                # Keep reference to prevent garbage collection
                self._images.append(photo)
                block.image_id = img_id

            except Exception as e:
                print(f"Error loading image {image_path}: {e}")

        # draw the input ports
        for i in range(nin):
            x = block.pos[0]
            y = block.port_y(i, block.nin)
            item = self.create_rectangle(
                x,
                y - block.portSize / 2,
                x - block.portSize / 2,
                y + block.portSize / 2,
                fill="blue",
                tags=(block.name, f"{block.name}.in{i}", "inport", "moveable"),
            )
            block.inpos.append((x - block.portSize / 2, y))

        # draw the output ports
        for i in range(nout):
            x = block.pos[0] + block.blockWidth
            y = block.port_y(i, block.nout)
            item = self.create_polygon(
                x,
                y - block.portSize / 2,
                x,
                y + block.portSize / 2,
                x + block.portSize,
                y,
                fill="black",
                tags=(block.name, f"{block.name}.out{i}", "outport", "moveable"),
            )
            block.outpos.append((x + block.portSize, y))

        # draw the block name
        self.create_text(
            pos[0] + block.blockWidth / 2,
            pos[1] + block.blockHeight * 1.1,
            text=block.name,
            tags=(block.name, "label"),
        )
        return block

    def flip(self):
        # Flip the block horizontally by reflecting its coordinates
        for i, port in enumerate(self._iports):
            coords = canvas.coords(port)
            x0, y0, x1, y1, x2, y2 = coords
            x0 = self.blockWidth - x0
            x1 = self.blockWidth - x1
            x2 = self.blockWidth - x2
            canvas.coords(port, x0, y0, x1, y1, x2, y2)
            self._inpos[i] = (x2, y0)

        for i, port in enumerate(self._oports):
            coords = canvas.coords(port)
            x0, y0, x1, y1, x2, y2 = coords
            x0 = self.blockWidth - x0
            x1 = self.blockWidth - x1
            x2 = self.blockWidth - x2
            canvas.coords(port, x0, y0, x1, y1, x2, y2)
            self._outpos[i] = (x2, y0)

    def add_wire(self, from_name, to_name):
        print(
            "Connect",
            from_name,
            "to",
            to_name,
        )

        re_block = re.compile(r"(block\d+)\.(?:in|out)(\d+)")
        m = re_block.match(from_name)
        from_block = m.group(1)
        from_port = int(m.group(2))

        m = re_block.match(to_name)
        to_block = m.group(1)
        to_port = int(m.group(2))
        print(from_block, from_port, to_block, to_port)

        b1 = blockdict[from_block]
        b2 = blockdict[to_block]

        # ortho_line(b1.outpos(0), b2.inpos(0))
        print(b1.outpos[from_port])
        print(b2.inpos[to_port])
        self.draw_ortho_line(
            b1.outpos[from_port],
            b2.inpos[to_port],
            tag=[
                "wire",
                from_block,
                to_block,
                f"{from_name}>{to_name}",
            ],
        )

    def inpos(self, i):
        # Return the absolute position of the i-th input port
        coords = canvas.coords(self.tag)
        return (self._inpos[i][0] + coords[0], self._inpos[i][1] + coords[1])

    def outpos(self, i):
        # Return the absolute position of the i-th output port
        coords = canvas.coords(self.tag)
        return (self._outpos[i][0] + coords[0], self._outpos[i][1] + coords[1])

    # see http://www.bitflipper.ca/Documentation/dnd_barebones.txt

    def current_item_id(self) -> int:
        # return the id of the current item
        id = self.find_withtag("current")[0]
        return id

    def current_item_tag(self) -> str:
        # return the first tag of the current item
        id = self.find_withtag("current")[0]
        tag = self.gettags(id)[0]
        return tag

    # ------------ block body events -----------------

    # mouse button down, start drag
    def block_down(self, event):
        self.event_print("block_down", event)

        self.loc = 1
        self.dragged = 0
        widget = event.widget
        self.x, self.y = widget.canvasx(event.x), widget.canvasy(event.y)
        if "image" in self.gettags(tk.CURRENT):
            self.color = None
        else:
            self.color = widget.itemcget(tk.CURRENT, "fill")
        event.widget.bind("<Motion>", self.block_motion)
        self.dx = 0
        self.dy = 0

    # mouse is dragging
    def block_motion(self, event):
        self.root.config(cursor="fleur")
        widget = event.widget
        widget.itemconfigure(tk.CURRENT, fill="white", outline="grey", dash=(5, 5))
        x, y = widget.canvasx(event.x), widget.canvasy(event.y)
        dx = x - self.x
        dy = y - self.y
        self.x = x
        self.y = y
        self.dx += dx
        self.dy += dy
        if verbose_events:
            print(self.active_block)
        # move all elements tagged with this block's tag
        event.widget.move(self.active_block, dx, dy)

    # mouse button released
    def block_up(self, event):
        self.event_print("block_up", event)

        self.root.config(cursor="")
        widget = event.widget
        widget.unbind("<Motion>")
        if self.color:
            self.itemconfigure(tk.CURRENT, fill=self.color, dash=())
        # if self.loc:  # is button released in same widget as pressed?
        #     self.block_up(event)
        # else:
        #     self.dragged = event.time

        block = blockdict[self.gettags(tk.CURRENT)[0]]
        for i in range(block.nin):
            block.inpos[i] = (
                block.inpos[i][0] + self.dx,
                block.inpos[i][1] + self.dy,
            )
        for i in range(block.nout):
            block.outpos[i] = (
                block.outpos[i][0] + self.dx,
                block.outpos[i][1] + self.dy,
            )
        self.redraw_wires(self.current_item_id())

    def block_enter(self, event):
        self.event_print("block_enter", event)
        block_name = self.current_item_tag()

        # need the id of the block, not the image
        id = blockdict[block_name].item_id
        # print("  block enter", block_name)
        self.itemconfigure(id, outline="blue", width=2)
        self.loc = 1
        self.active_id = id  # item id of the block rectangle
        self.active_block_name = block_name
        if self.dragged == event.time:
            self.up(event)
        self.focus_set()

    def block_leave(self, event):
        self.event_print("block_leave", event)
        self.itemconfigure(self.active_id, outline="black", width=1)
        self.loc = 0

    # ------------ output port events -----------------
    def outport_down(self, event):
        selected = self.current_item_id()
        if self.active_output == selected:
            # cancelation of selection
            self.itemconfig(selected, fill="black", outline="")
            self.active_output = None
        elif self.active_output is not None:
            # change selection
            self.itemconfig(self.active_output, fill="black", outline="")
            self.itemconfig(selected, fill="yellow", outline="black", width=1)
            self.active_output = selected
        else:
            # new selection
            self.active_output = selected
            self.itemconfig(selected, fill="yellow", outline="black", width=1)

        if verbose_events:
            print("outport down", selected, self.active_output)

    def outport_up(self, event):
        pass
        # self.itemconfig(tk.CURRENT, fill="black", outline="")

    def outport_enter(self, event):
        selected = self.current_item_id()
        if verbose_events:
            print("outport enter", selected, self.active_output)
        self.itemconfig(tk.CURRENT, outline="red", width=2)

    def outport_leave(self, event):
        if verbose_events:
            print("outport leave", self.current_item_id(), self.active_output)
        if self.current_item_id() != self.active_output:
            self.itemconfig(tk.CURRENT, outline="")

    # ------------ input port events -----------------
    def inport_down(self, event):
        # create a wire if an output port is active
        if self.active_output:
            self.itemconfig(self.active_output, fill="black", outline="")
            from_block = self.gettags(self.active_output)
            to_block = self.gettags(self.current_item_id())
            if verbose_events:
                print("inport down", from_block, to_block)
            self.active_output = None

            self.add_wire(from_block[1], to_block[1])

    def inport_up(self, event):
        pass
        # self.itemconfig(tk.CURRENT, fill="black", outline="")

    def inport_enter(self, event):
        self.itemconfig(tk.CURRENT, outline="red", width=2)

    def inport_leave(self, event):
        self.itemconfig(tk.CURRENT, outline="")

    # ------------ wire events -----------------
    def wire_motion(self, event):
        self.event_print("wire_motion", event)

        self.root.config(cursor="fleur")
        widget = event.widget
        # widget.itemconfigure(tk.CURRENT, fill="white", outline="grey", dash=(5, 5))
        x, y = widget.canvasx(event.x), widget.canvasy(event.y)

        id = self.current_item_id()
        print("wire id:", id)
        # idx=0, x1, y1
        # x0, y0, x1 y1, x2 y2
        coords = self.coords(id)
        print("old coords:", coords)
        print(self.idx, self.isvertical)
        if self.isvertical:
            # change x coordinates
            coords[2 * self.idx] = x
            coords[2 * self.idx + 2] = x
        else:
            # change y coordinates
            coords[2 * self.idx + 1] = y
            coords[2 * self.idx + 3] = y
        print("new coords:", coords)
        self.coords(id, *coords)
        # self.x = x
        # self.y = y
        # self.dx += dx
        # self.dy += dy
        # if verbose_events:
        #     print(self.active)
        # event.widget.move(self.active, dx, dy)

    def wire_down(self, event):
        self.event_print("wire_down", event)

        for tag in self.gettags(tk.CURRENT):
            if ">" in tag:
                wiretag = tag
                blocks = tag.split(">")
                print("wire tag:", blocks[0], "-->", blocks[1])

        from_block, from_port, to_block, to_port = self.parse_io(wiretag)
        coords = self.ortho_line(
            blockdict[from_block].outpos[from_port],
            blockdict[to_block].inpos[to_port],
        )
        print(event.x, event.y)
        print(coords)

        if len(coords) == 2:
            # straight line
            pass
        elif len(coords) == 3:
            # dogleg forward line
            pass
        else:
            # backward line
            for i, (start, end) in enumerate(pairwise(coords[1:-1])):
                if is_close_numpy((event.x, event.y), start, end, tolerance=5):
                    print("close to segment", start, end)

                    self.dragged = 0
                    widget = event.widget
                    self.x, self.y = widget.canvasx(event.x), widget.canvasy(event.y)
                    # self.color = widget.itemcget(tk.CURRENT, "fill")
                    event.widget.bind("<Motion>", self.wire_motion)
                    self.dx = 0
                    self.dy = 0
                    self.idx = i + 1
                    self.isvertical = (i & 1) == 0  # is vertical segment

            pass

    def wire_up(self, event):
        self.event_print("wire_up", event)
        self.root.config(cursor="")
        widget = event.widget
        widget.unbind("<Motion>")

    def wire_enter(self, event):
        self.event_print("wire_enter", event)
        self.itemconfig(tk.CURRENT, width=3)

    def wire_leave(self, event):
        self.event_print("wire_leave", event)
        self.itemconfig(tk.CURRENT, width=1)

    def wire_delete(self, event):
        self.event_print("wire delete", event)
        self.delete(self.current_item_id())

    # ------------ UI events -----------------
    def new_block(event):
        self.event_print("new block", event)
        tree = getattr(event, "data", None)
        block = getattr(tree, "_last_activated_block", None)
        if block:
            print("Activated block:", block)

    # ------------ keyboard events -----------------

    # "x" to list all items
    def list_items(self, event):
        print("list items")
        for item in self.find_withtag("block"):
            print(
                "item",
                item,
                self.gettags(item),
                self.coords(item),
            )
        for item in self.find_withtag("wire"):
            print(
                "item",
                item,
                self.gettags(item),
                self.coords(item),
            )

    # "q" to quit
    def quit(self, event):
        self.list_items(event)
        self.root.quit()

    def flip(self, event):
        print("flip")
        b4.flip()

    def __init__(self, parent, **kwargs):
        # Initialize the Canvas
        super().__init__(
            parent,
            **kwargs,
        )

        self._images = []  # keep references to icon images
        self.root = self.winfo_toplevel()

        self.gridlines(20)
        self.pack()

        self.loc = self.dragged = 0

        self.tag_bind("block", "<ButtonPress-1>", self.block_down)
        self.tag_bind("block", "<ButtonRelease-1>", self.block_up)
        self.tag_bind("block", "<Enter>", self.block_enter)
        self.tag_bind("block", "<Leave>", self.block_leave)
        self.bind("<Key-f>", self.flip)

        self.tag_bind("image", "<ButtonPress-1>", self.block_down)
        self.tag_bind("image", "<ButtonRelease-1>", self.block_up)
        self.tag_bind("image", "<Enter>", self.block_enter)
        self.tag_bind("image", "<Leave>", self.block_leave)
        self.bind("<Key-f>", self.flip)

        self.tag_bind("outport", "<ButtonPress-1>", self.outport_down)
        self.tag_bind("outport", "<ButtonRelease-1>", self.outport_up)
        self.tag_bind("outport", "<Enter>", self.outport_enter)
        self.tag_bind("outport", "<Leave>", self.outport_leave)

        self.tag_bind("inport", "<ButtonPress-1>", self.inport_down)
        self.tag_bind("inport", "<ButtonRelease-1>", self.inport_up)
        self.tag_bind("inport", "<Enter>", self.inport_enter)
        self.tag_bind("inport", "<Leave>", self.inport_leave)

        self.tag_bind("wire", "<ButtonPress-1>", self.wire_down)
        self.tag_bind("wire", "<ButtonRelease-1>", self.wire_up)
        self.tag_bind("wire", "<Delete>", self.wire_delete)
        self.tag_bind("wire", "<Enter>", self.wire_enter)
        self.tag_bind("wire", "<Leave>", self.wire_leave)

        self.bind("<<NewBlockActivated>>", self.new_block)

        self.bind("x", self.list_items)
        self.bind("q", self.quit)


def is_close_numpy(point, start, end, tolerance):
    p = np.array(point)
    a = np.array(start)
    b = np.array(end)

    # Vector AB
    ab = b - a

    # Squared length of AB
    len_sq = np.sum(ab**2)

    if len_sq == 0:
        return np.linalg.norm(p - a) <= tolerance

    # Project point onto line, clamped between 0 and 1
    t = np.dot(p - a, ab) / len_sq
    t = np.clip(t, 0, 1)

    # Find closest point on segment
    closest = a + t * ab

    # Check distance
    return np.linalg.norm(p - closest) <= tolerance
