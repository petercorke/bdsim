import pydoc
import cv2
import bdsim
import numpy as np

bd = bdsim.BlockDiagram()
tuner = bdsim.tuning.tuners.TcpClientTuner()

# setup hsv stream
bgr = bd.CAMERA(0)
bd.DISPLAY(bgr, "BGR", web_stream_host=tuner)

hsv = bd.CVTCOLOR(bgr, cv2.COLOR_BGR2HSV)
bd.DISPLAY(hsv, "HSV", web_stream_host=tuner)

# the bd.param function should be used to create a parameter functionally that can be passed in
# as an argument to one or more block constructors that support a parameter of that type from that keyword
print(pydoc.render_doc(bd.param))  # display docs

# by wrapping param args with bd.param, you are making it editable via GUI controls / over network
# the value you pass to it is its initial value
thresholded = bd.INRANGE(hsv,
                         lower=bd.param(53, 103, 55),
                         upper=bd.param(133, 195, 174))

# you can create your parameters first and share them between blocks later
# n_iterations = bd.param(1)
# shares 'iterations' between erode and dilate
eroded = bd.ERODE(thresholded, tinker=True)
dilated = bd.DILATE(eroded, tinker=True)
eroded2 = bd.ERODE(dilated, tinker=True)
dilated2 = bd.DILATE(eroded2, tinker=True)

# you can also get or set any parameter from a block after its instantiation:
# kernel = eroded.param('kernel')
# dilated.param('kernel', kernel)  # shares 'kernel' between erode and dilate

# you can also pass 'tinker=True' into block constructors to make all of their internal params editable
blobs = bd.BLOBS(dilated2, top_k=1, area=(2000, 999999),
                 inertia_ratio=(0.4, 1), tinker=True)

# draw the blobs found on the screen
blob_vis = bd.DRAWKEYPOINTS(dilated2, blobs)

# host the stream through the tuner app
bd.DISPLAY(blob_vis, "Blobs", show_fps=True, web_stream_host=tuner)


def biggest_blob_stats(blobs):
    try:
        blob = blobs[0]
        return [*(blob.pt), blob.size]
    except IndexError:
        return [None] * 3


# pull out stats to track
picker = bd.FUNCTION(biggest_blob_stats, blobs, nout=3)

# plot biggest blob trajectory over time
# display it through the tuner app
blob_scope = bd.SCOPE(
    picker[0:3],
    nin=3,
    labels=['BlobX', 'BlobY', 'BlobSize'],
    name='Blob vs Time',
    tuner=tuner)


bd.compile()


try:
    bd.run_realtime(tuner=tuner)
finally:
    bd.done()

# plot biggest blob trajectory over pixel space
