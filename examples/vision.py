import bdsim
from pathlib import Path

bd = bdsim.BlockDiagram()
cap = bd.CAMERA(0)
masked = bd.THRESHOLD(cap, 0, 255, method="binary")

bd.DISPLAY(cap, "Feed")
bd.DISPLAY(masked, "Threshold")
blobs = bd.BLOBS(masked)

bd.compile()
try:
    bd.run_realtime()
finally:
    bd.done()