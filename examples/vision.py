import cv2
import bdsim
import pydoc
import math
import cProfile

bd = bdsim.BlockDiagram()

# setup hsv stream
cap = bd.CAMERA(0)
hsv = bd.CVTCOLOR(cap, cv2.COLOR_BGR2HSV)
# bd.DISPLAY(hsv, "HSV", show_fps=True)

# the bd.param function should be used to create a parameter functionally that can be passed in
# as an argument to one or more block constructors that support a parameter of that type from that keyword
print(pydoc.render_doc(bd.param))  # display docs

# by wrapping param args with bd.param, you are making it editable via GUI controls / over network
# the value you pass to it is its initial value
thresholded = bd.INRANGE(hsv,
                         lower=bd.param(53, 103, 55),
                         upper=bd.param(133, 195, 174))

# you can create your parameters first and share them between blocks later
n_iterations = bd.param(1)
# shares 'iterations' between erode and dilate
dilated = bd.DILATE(thresholded, iterations=n_iterations)
eroded = bd.ERODE(dilated, iterations=n_iterations)

# you can also get or set any parameter from a block after its instantiation:
kernel = eroded.param('kernel')
dilated.param('kernel', kernel)  # shares 'kernel' between erode and dilate

# you can also pass 'tinker=True' into block constructors to make all of their internal params editable
blobs = bd.BLOBS(eroded, top_k=1, area=(2000, 999999),
                 inertia_ratio=(0.4, 1), tinker=True)

# draw the blobs found on the screen
blob_vis = bd.DRAWKEYPOINTS(dilated, blobs)
bd.DISPLAY(blob_vis, "Blobs", show_fps=True, web_stream=True)


# def biggest_blob_stats(blobs):
#     try:
#         blob = blobs[0]
#         return [*(blob.pt), blob.size]
#     except IndexError:
#         return [None] * 3


# # pull out stats to track
# picker = bd.FUNCTION(biggest_blob_stats, blobs, nout=3)


# TODO: increase plotting performance - these reduce framerate to 7fps
# # plot biggest blob trajectory over time
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
    bd.run_realtime(tuner=bdsim.tuning.tuners.TcpClientTuner())
finally:
    bd.done()

# plot biggest blob trajectory over pixel space
