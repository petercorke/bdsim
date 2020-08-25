import logging
import numpy as np
from ..components import SourceBlock, SinkBlock, block

try:
    import cv2

    @block
    class Camera(SourceBlock):
        """
        :blockname:`CAMERA`
        
        .. table::
        :align: left
        
        +--------+---------+---------+
        | inputs | outputs |  states |
        +--------+---------+---------+
        | 0      | 1       | 0       |
        +--------+---------+---------+
        |        | float,  |         | 
        |        | A(N,)   |         |
        +--------+---------+---------+
        """
        type = "camera"


        def __init__(self, source, *cv2_args, **kwargs):
            """
            :param source: the source of the video stream. A local camera device index or a path/url.
                If a video file is specified, will play the file (works in simulation mode).
            :type source: Union[int, string]
            :param `*cv2_args`: Optional arguments to pass into `cv2's VideoCapture constructor`
            <https://docs.opencv.org/4.1.0/d8/dfe/classcv_1_1VideoCapture.html#ac4107fb146a762454a8a87715d9b7c96>
            :param ``**kwargs``: common Block options
            :return: a VIDEOCAPTURE block
            :rtype: VideoCapture instance
            
            Creates a VideoCapture block. 

            Examples::
                TODO

            See `the OpenCV4.1 docs`
            <https://docs.opencv.org/4.1.0/d8/dfe/classcv_1_1VideoCapture.html>
            for further detail.
            """
            super().__init__(nout=1, **kwargs)
            if (not source is str) or (not source is int):
                # coerce it into str, good if it's something like a pathlib.Path
                source = str(source)
            self.video_capture = cv2.VideoCapture(source, *cv2_args)
            assert self.video_capture.isOpened(), (
                f"Camera at {source} could not be opened. "
                "Please check the filepath / resource availability."
            )
        

        def output(self, t):
            if t != "realtime":
                fps = self.video_capture.get(cv2.CAP_PROP_FPS)
                # if fps attr is zero, we're using a camera
                # TODO: check if this holds for IP cams
                assert fps > 0, (
                    "Cannot set timestamp of live camera feed. "
                    "Please run in realtime mode instead."
                )
                frame_n = int(round(t * fps))
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_n)
            
            _, frame = self.video_capture.read()
            return [frame]

    # @block
    # class CvtColor(Block):
        
    #     def __init__(self):

    # @block
    # class Threshold(Block):
    #     pass

    # @block
    # class SimpleBlobDetector(Block):
    #     pass

    # This probably doesn't need the opencv dependency - I think opencv just uses matplotlib anyway
    # TODO: don't require opencv for display block
    @block
    class Display(SinkBlock):
        """
        :blockname:`DISPLAY`
        
        .. table::
        :align: left
        
        +-------------+---------+---------+
        | inputs      | outputs |  states |
        +-------------+---------+---------+
        | 1           | 0       | 0       |
        +-------------+---------+---------+
        | A(H, W, C)  |         |         | 
        +-------------+---------+---------+
        """
        type = "display"

        def __init__(self, *inputs, title="Display", **kwargs):
            super().__init__(inputs=inputs, nin=1, **kwargs)
            self.title = title


        def step(self):
            input_ = self.inputs[0]
            try:
                cv2.imshow(self.title, input_)
                print('waiting')
                cv2.waitKey(1) # cv2 needs this to actually show, apparently
                print('done')
            except Exception as e:
                raise Exception(
                    f"Expected input to be an HxW[xC] ndarray, got {input_}"
                    f"\nOpenCV error: {e}"
                )


        def stop(self):
            # TODO: Check if overkill to ensure that self.title never changes?
            cv2.destroyWindow(self.title)

except ModuleNotFoundError:
    logging.warn("OpenCV not installed. Vision blocks will not be available")