import bdsim
from pathlib import Path

bd = bdsim.BlockDiagram()
cap = bd.CAMERA(0)
bd.DISPLAY(cap, "Feed")

gray = bd.CVTCOLOR(cap, 'bgr', 'hsv')
bd.DISPLAY(gray, title="Greyscaled")

masked = bd.INRANGE(cap,
    [35, 18, 54],
    [67, 176, 160])
bd.DISPLAY(masked, title="Masked")

blobs = bd.BLOBS(masked, top_k=1)
def biggest_blob_stats(blobs):
    try:
        blob = blobs[0]
        return blob.cx, blob.cy, blob.size
    except IndexError:
        return [None] * 3

picker = bd.FUNCTION(biggest_blob_stats, blobs, nout=3)

blob_scope = bd.SCOPE(nin=3, labels=['cx', 'cy', 'size'], name='Blob vs Time')
bd.connect(picker[0:3], blob_scope)

blob_xy_scope = bd.SCOPEXY(name='Blob Trajectory')
bd.connect(picker[0:2], blob_xy_scope)

bd.compile(eval0=False)
try:
    bd.run_realtime()
finally:
    bd.done()