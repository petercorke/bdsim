import bdsim
from pathlib import Path

bd = bdsim.BlockDiagram()
cap = bd.CAMERA(Path(bdsim.__file__).parent / "blocks/test_video.mp4")
display = bd.DISPLAY(cap)

bd.compile()
try:
    bd.run_realtime()
except KeyboardInterrupt:
    bd.done()