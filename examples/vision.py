import cv2
import bdsim

bd = bdsim.BlockDiagram()
p = bd.param  # alias for brevity
cap = bd.CAMERA(0)

hsv = bd.CVTCOLOR(cap, cv2.COLOR_BGR2HSV)

thresholded = bd.INRANGE(hsv, tinker=True)
bd.DISPLAY(thresholded, "HSV")

opened = bd.OPENMASK(thresholded, kernel=p(("ellipse", 3, 3)))
# p = opened.parameter(“kernel”)
# p = opened.parameter(“kernel”, “thing1”, minval=0, maxval=7)
# opened.__dict__[“kernel”]
# opened.getattr(“kernel”)

blobs = bd.BLOBS(opened, top_k=1, tinker=True)

blob_vis = bd.DRAWKEYPOINTS(opened, blobs)
bd.DISPLAY(blob_vis, "Blobs")

# def biggest_blob_stats(blobs):
#     try:
#         blob = blobs[0]
#         return blob.cx, blob.cy, blob.size
#     except IndexError:
#         return [None] * 3

# picker = bd.FUNCTION(biggest_blob_stats, blobs, nout=3)

# blob_scope = bd.SCOPE(
#     picker[0:3],
#     nin=3,
#     labels=['BlobX', 'BlobY', 'BlobSize'],
#     name='Blob vs Time')

# blob_xy_scope = bd.SCOPEXY(
#     picker[0:2],
#     name='Blob Trajectory')

bd.compile()

try:
    bd.run_realtime(tuner=True)
finally:
    bd.done()
