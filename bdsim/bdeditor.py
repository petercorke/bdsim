#!/usr/bin/env python3
import sys
import os
import string
import time
import tkinter as tk

from itertools import tee

def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)

# A Python example of drag and drop functionality within a single Tk widget.
# The trick is in the bindings and event handler functions.
# Tom Vrankar twv at ici.net

# empirical events between dropee and target, as determined from Tk 8.0
# down.
# leave.
# up, leave, enter.
def ortho_line(start, end, width=2, **kwargs):
  if start[0] < end[0]:
    if start[1] == end[1]:
      canvas.create_line( start, end, arrow=tk.LAST, tag="wire", **kwargs)
    else:
      xmid = (start[0] + end[0]) / 2.0
      canvas.create_line( start, (xmid, start[1]), (xmid, end[1]), end, arrow=tk.LAST, tag="wire", width=width, **kwargs)
  else:
    # line has to go backwards
    L = 20
    H = 100
    if end[1] < start[1]:
      # new block above
      y = end[1] - H
    else:
      y = end[1] + H
    canvas.create_line( start, (start[0]+L, start[1]), (start[0]+L, y), (end[0]-L, y), (end[0]-L, end[1]), end, arrow=tk.LAST, tag="wire", **kwargs)

def redraw_wires():
  canvas.delete("wire")
  ortho_line( b3.outpos(0), b4.inpos(0))

class CanvasDnD (tk.Frame):
# see http://www.bitflipper.ca/Documentation/dnd_barebones.txt
  def __init__(self, master, canvas):
    self.master = master
    self.loc = self.dragged = 0
    tk.Frame.__init__(self, master)

    canvas.tag_bind("DnD", "<ButtonPress-1>", self.down)
    canvas.tag_bind("DnD", "<ButtonRelease-1>", self.chkup)
    canvas.tag_bind("DnD", "<Enter>", self.enter)
    canvas.tag_bind("DnD", "<Leave>", self.leave)
    canvas.bind("<Key-f>", self.flip)

  # mouse button down, start drag
  def down(self, event):
    self.loc = 1
    self.dragged = 0
    cnv = event.widget
    self.x, self.y = cnv.canvasx(event.x), cnv.canvasy(event.y)
    self.color = cnv.itemcget(tk.CURRENT, "fill")
    event.widget.bind("<Motion>", self.motion)

  # mouse is dragging
  def motion(self, event):
    root.config(cursor="exchange")
    cnv = event.widget
    cnv.itemconfigure(tk.CURRENT, fill="white", outline="grey", dash=(5,5))
    x, y = cnv.canvasx(event.x), cnv.canvasy(event.y)
    dx = x - self.x
    dy = y - self.y
    self.x = x
    self.y = y
    #got = event.widget.coords(tk.CURRENT, x, y)
    event.widget.move(tk.CURRENT, dx, dy)

  def leave(self, event):
    print('leave')
    canvas.itemconfigure(tk.CURRENT, outline="")
    self.loc = 0

  def enter(self, event):
    print('enter', event)
    canvas.itemconfigure(tk.CURRENT, outline="darkred", width=2)
    self.loc = 1
    if self.dragged == event.time:
      self.up(event)
    canvas.focus_set()

  # mouse button released
  def chkup(self, event):
    event.widget.unbind("<Motion>")
    root.config(cursor="")
    self.target = event.widget.find_withtag(tk.CURRENT)
    event.widget.itemconfigure(tk.CURRENT, fill=self.color, dash=())
    if self.loc:  # is button released in same widget as pressed?
      self.up(event)
    else:
      self.dragged = event.time
    redraw_wires()

  def up(self, event):
    event.widget.unbind("<Motion>")
    if (self.target == event.widget.find_withtag(tk.CURRENT)):
      pass
      #print("Select %s" % event.widget.itemcget(tk.CURRENT, "text"))
    else:
      event.widget.itemconfigure(tk.CURRENT, fill="blue")
      self.master.update()
      time.sleep(.1)
      # print("%s Drag-N-Dropped onto %s"
      #       % (event.widget.itemcget(self.target, "text"),
      #          event.widget.itemcget(tk.CURRENT, "text")))
      event.widget.itemconfigure(tk.CURRENT, fill=self.defaultcolor)

  def flip(self, event):
    print("flip")
    b4.flip()

root = tk.Tk()
root.title("bdsim editor")

# create  widget
canvas = tk.Canvas(root, bg="white", height=500, width=1000, relief=tk.RIDGE, background="white", borderwidth=1)
canvas.pack()

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

class GBlock:
  W = 50
  H = 100
  a = 20 # distance from top/bottm
  b = 5  # half width of output

  def __init__(self, nin, nout, pos, fill="red", **kwargs):



      D = self.H - 2 * self.a

      inpos = []
      outpos = []

      # draw top edge
      p = [(0, 0), (self.W, 0)]

      # draw right side with triangles
      if nout == 1:
          y = self.H / 2
          p.extend([(self.W, y-self.b), (self.W+self.b, y), (self.W, y+self.b)])
          outpos.append((self.W+self.b, y))
      else:
          d = D / (nout - 1)
          for k in range(0, nout):
              y = self.a + k * d
              p.extend([(self.W, y-self.b), (self.W+self.b, y), (self.W, y+self.b)])
              outpos.append((self.W+self.b, y))

      # draw bottom edge
      p.extend([(self.W, self.H), (0, self.H)])

      # draw left side with squares
      if nout == 1:
          y = self.H / 2
          p.extend([(0, y+self.b), (-self.b, y+self.b), (-self.b, y-self.b), (0, y-self.b)])
          inpos.append((-self.b, y))
      else:
          d = D / (nout - 1)
          for k in range(0, nout):
              y = self.H - self.a - k * d
              p.extend([(0, y+self.b), (-self.b, y+self.b), (-self.b, y-self.b), (0, y-self.b)])
              inpos.append((-self.b, y))

      self._inpos = inpos
      self._outpos = outpos

      self.outline = p
      pp = [ (x[0]+pos[0], x[1]+pos[1]) for x in p]
      self.id = canvas.create_polygon(pp, fill=fill, tags="DnD", **kwargs)

  def flip(self):
    outline = canvas.coords(self.id)
    print(outline)
    A = 2 * (outline[0] + 25)
    flipped = []
    for i in range(0, len(outline), 2):
      flipped.extend([A-outline[i], outline[i+1]])
    print(flipped)
    canvas.coords(self.id, flipped)


  def inpos(self, i):
      pos = canvas.coords(self.id)
      return (pos[0]+self._inpos[i][0], pos[1]+self._inpos[i][1])

  def outpos(self, i):
    pos = canvas.coords(self.id)
    return (pos[0]+self._outpos[i][0], pos[1]+self._outpos[i][1])

GBlock(1, 1, (100,100))
GBlock(0, 1, (200,100))
b3 = GBlock(3, 1, (300,100))
b4 = GBlock(2, 3, (400,100))

#print(canvas.bbox(b4.id))
#canvas.create_rectangle(canvas.bbox(b4.id), outline="black", fill="")

print(canvas.coords(b4.id))
print(canvas.bbox(b4.id))


CanvasDnD(root, canvas)
root.mainloop()
