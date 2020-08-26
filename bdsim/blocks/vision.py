import logging
import numpy as np
from ..components import SourceBlock, SinkBlock, FunctionBlock, block
import time

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
            self.is_livestream = isinstance(source, int)
            if not (self.is_livestream or isinstance(source, str)):
                # coerce it into str, good if it's something like a pathlib.Path
                source = str(source)
            self.video_capture = cv2.VideoCapture(source, *cv2_args)
            assert self.video_capture.isOpened(), f"VideoCapture at {source} could not be opened. Please check the filepath / if another process is using the camera"
        
        def start(self):
            super().start()
            if not self.is_livestream:
                # restart the video if it is
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        

        def output(self, t=None):
            # set the frame if we're using a video
            if t != None and not self.is_livestream:
                fps = self.video_capture.get(cv2.CAP_PROP_FPS)
                frame_n = int(round(t * fps))
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_n)
            
            _, frame = self.video_capture.read()
            return [frame]

    @block
    class CvtColor(FunctionBlock):

        type = "cvtcolor"
        
        # TODO: automate 'from_', when unit system is implemented ('rgb img' will be a unit)
        def __init__(self, input_, from_, to, **kwargs):
            super().__init__(inputs=[input_], nin=1, nout=1, **kwargs)
            self.from_ = from_
            self.to = to
        
        def output(self, t=None):
            [input_] = self.inputs
            converted = cv2.cvtColor(input_, getattr(cv2, f'COLOR_{self.from_.upper()}2{self.to.upper()}'))
            return [converted]

    @block
    class InRange(FunctionBlock):

        type = "inrange"
        
        def __init__(self, input_, lower, upper, retain_color=False, **kwargs):
            super().__init__(inputs=[input_], nin=1, nout=1, **kwargs)
            self.lower = np.array(lower)
            self.upper = np.array(upper)
            self.retain_color = retain_color

        def output(self, t=None):
            [input_] = self.inputs
            mask = cv2.inRange(input_, self.lower, self.upper)
            if self.retain_color:
                masked = cv2.bitwise_and(
                    input_, input_, mask=mask)
                return [masked]
            else:
                return [mask]
    
    @block
    class Threshold(FunctionBlock):

        type = "threshold"
        available_methods = ["binary", "binary_inv", "trunc", "tozero", "tozero_inv", "mask"]
        # TODO support "otsu" & "triangle"

        # lower 
        def __init__(self, input_, lower, upper, method="binary", **kwargs):
            super().__init__(inputs=[input_], nin=1, nout=1, **kwargs)
            assert method in self.available_methods, \
                f"Thresholding method {method} unsupported. Please select from methods in Threshold.available_methods list"

            self.lower = lower
            self.upper = upper

            self.method = getattr(cv2, f'THRESH_{method.upper()}')


        def output(self, t=None):
            [input_] = self.inputs
            _, output = cv2.threshold(input_, self.lower, self.upper, self.method)
            return [output]

    @block
    class Blobs(FunctionBlock):
        """[summary]

        :param Block: [description]
        :type Block: [type]

        grayscale_threshold: only useful if input is grayscale
            (min, max, step) TODO describe this better
            https://github.com/opencv/opencv/blob/e5e767abc1314f918a848e0b912dc9574c19bfaf/modules/features2d/src/blobdetector.cpp#L324
        
        Would be nice to represent this as a subsystem block rather than a single function block,
        ie if/when a gui is developed (for education purposes), but it would be (slightly) less efficient,

        some SimpleBlobDetector features, such as color filtering, don't make sense (always 255/0 for binary image), so was omitted.
        See: https://github.com/opencv/opencv/blob/e5e767abc1314f918a848e0b912dc9574c19bfaf/modules/features2d/src/blobdetector.cpp#L275
        """

        type = "blobs"

        def __init__(self, input_, top_k=None, min_dist_between_blobs=10, area=None, circularity=None, inertia_ratio=None, convexivity=None, grayscale_threshold=(100, 100, 0), **kwargs):
            super().__init__(inputs=[input_], nin=1, nout=1, **kwargs)
            params = cv2.SimpleBlobDetector_Params()
            params.minDistBetweenBlobs = min_dist_between_blobs
            params.minThreshold, params.maxThreshold, params.thresholdStep = grayscale_threshold
            if area:
                params.filterByArea = True
                params.minArea, params.maxArea = area
            if circularity:
                params.filterByCircularity = True
                params.minCircularity, params.maxCircularity = circularity
            if inertia_ratio:
                params.filterByInertia = True
                params.minInertiaRatio, params.maxInertiaRatio = inertia_ratio

            self.detector = cv2.SimpleBlobDetector_create(params)
            self.top_k = top_k


        def output(self, t=None):
            [input_] = self.inputs
            keypoints = self.detector.detect(input_)
            return [keypoints[:self.top_k] if self.top_k else keypoints]


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

        def __init__(self, input_, title="Display", **kwargs):
            super().__init__(inputs=[input_], nin=1, **kwargs)
            self.title = title


        def step(self):
            input_ = self.inputs[0]
            try:
                cv2.imshow(self.title, input_)
                cv2.waitKey(1) # cv2 needs this to actually show, apparently
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
