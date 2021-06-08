import tkinter as tk

# init tk
root = tk.Tk()
root.title('bdsim')

# create  widget
canvas = tk.Canvas(root, bg="white", height=500, width=1000)
canvas.pack()

# draw arcs
coord = 10, 10, 300, 300
# arc = canvas.create_arc(coord, start=0, extent=150, fill="red")
# arv2 = canvas.create_arc(coord, start=150, extent=215, fill="green")


def grid(canvas, line_distance):
   root.update()
   print(canvas.winfo_width())
   canvas_width = 1000
   canvas_height = 500
   # vertical lines at an interval of "line_distance" pixel
   for x in range(line_distance,canvas_width,line_distance):
      canvas.create_line(x, 0, x, canvas_height, fill="#f0f0f0")
   # horizontal lines at an interval of "line_distance" pixel
   for y in range(line_distance,canvas_height,line_distance):
      canvas.create_line(0, y, canvas_width, y, fill="#f0f0f0")

grid(canvas, 20)



def draw_block(nin, nout, pos):
    W = 50
    H = 100
    a = 20 # distance from top/bottm
    b = 5  # half width of output

    D = H - 2 * a

    # draw top edge
    p = [(0,0), (W,0)]

    # draw right side with triangles
    if nout == 1:
        y = H / 2
        p.extend([(W,y-b), (W+b,y), (W,y+b)])
    else:
        d = D / (nout - 1)
        for k in range(0, nout):
            y = a + k * d
            p.extend([(W,y-b), (W+b,y), (W,y+b)])

    # draw bottom edge
    p.extend([(W,H), (0,H)])

    # draw left side with squares
    if nout == 1:
        y = H / 2
        p.extend([(0,y+b), (-b,y+b), (-b,y-b), (0,y-b)])
    else:
        d = D / (nout - 1)
        for k in range(0, nout):
            y = a + k * d
            p.extend([(0,y+b), (-b,y+b), (-b,y-b), (0,y-b)])
    print(p)

    x0 = 100
    y0 = 200
    pp = [ (x[0]+pos[0], x[1]+pos[1]) for x in p]
    b1 = canvas.create_polygon(pp, fill="red", tags="box")

draw_block(1, 1, (100,100))
draw_block(0, 1, (200,100))
draw_block(3, 1, (300,100))
draw_block(2, 3, (400,100))

# add to window and show

root.mainloop()