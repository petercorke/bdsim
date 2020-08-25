import unittest
from bdsim.blocks.vision import *
from pathlib import Path
import numpy.testing as nt


class VideoBlocksTest(unittest.TestCase):

    def test_videocapture_mp4(self):
        filepath = Path(__file__).parent / "test_video.mp4"
        block = VideoCapture(filepath)
        
        # don't hold the resource unless the graph is executing
        frame = block.output()
        self.assertIsNone(frame)

        # starting opens the file at frame 0, and the frame should read
        block.start()
        frame = block.output()
        self.assertEqual(frame.shape, (360, 480, 3))
    

    def test_videocapture_camera(self):
        # Probably can't run this test on eg; a CI server.
        block = VideoCapture(0)

        # don't hold the resource unless the graph is executing
        frame = block.output()
        self.assertIsNone(frame)

        # starting holds the camera, and the frame should read
        block.start()
        frame = block.output()
        self.assertIsInstance(frame, np.ndarray)


if __name__ == "__main__":
    unittest.main()