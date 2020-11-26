import logging
import random
from threading import Thread, Lock

import numpy as np
import flask

from bdsim.components import SourceBlock, SinkBlock, FunctionBlock, SubsystemBlock, block
from bdsim.tuning.tuners import Tuner
from bdsim.tuning.tunable_block import TunableBlock
from bdsim.tuning.parameter import HyperParam, RangeParam

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
            assert (
                self.video_capture.isOpened()
            ), "VideoCapture at {source} could not be opened." \
                "Please check the filepath / if another process is using the camera" \
                .format(source=source)

        def start(self, **kwargs):
            super().start(**kwargs)
            if not self.is_livestream:
                # restart the video if it is
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)

        def output(self, t=None):
            # set the frame index if we're using a video file
            if t is not None and not self.is_livestream:
                fps = self.video_capture.get(cv2.CAP_PROP_FPS)
                frame_n = int(round(t * fps))
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_n)

            _, frame = self.video_capture.read()
            assert frame is not None, "An unknown error occured in OpenCV: camera disconnected or video file ended"
            return [frame]

    @block
    class CvtColor(FunctionBlock, TunableBlock):

        type = "cvtcolor"

        # TODO: automate 'from_', when unit system is implemented ('rgb pixel' will be a unit)

        def __init__(self, input, cvt_code, **kwargs):
            super().__init__(inputs=[input], nin=1, nout=1, **kwargs)

            self.cvt_code = cvt_code
            # TODO: turn cvt_code into a param:
            # self.cvt_code = self._param('cvt_code', cvt_code, oneof=[getattr(
            #     cv2, code) for code in dir(cv2) if code.startswith('COLOR_')])

        def output(self, _t=None):
            [input] = self.inputs
            try:
                converted = cv2.cvtColor(input, self.cvt_code)
            except AttributeError as e:
                raise Exception(
                    "Available methods are: {methods}".format(
                        methods=', '.join(
                            attr for attr in dir(cv2)
                            if attr.startswith('COLOR_'))
                    )
                ) from e
            return [converted]

    @block
    class InRange(FunctionBlock, TunableBlock):

        type = "inrange"

        def __init__(self, input, lower=(0, 0, 0), upper=(255, 255, 255), **kwargs):
            super().__init__(inputs=[input], nin=1, nout=1, **kwargs)

            self.lower = self._param('lower', lower,
                                     min=(0, 0, 0), max=(255, 255, 255), step=1)
            self.upper = self._param('upper', upper,
                                     min=(0, 0, 0), max=(255, 255, 255), step=1)

        def output(self, _t=None):
            [input] = self.inputs
            mask = cv2.inRange(input, self.lower, self.upper)
            return [mask]

    @ block
    class Mask(FunctionBlock):
        type = "mask"

        def __init__(self, input, **kwargs):
            super().__init__(inputs=[input], nin=2, nout=1, **kwargs)

        def output(self, _t=None):
            [input, mask] = self.inputs
            masked = cv2.bitwise_and(input, input, mask=mask)
            return [masked]

    @ block
    class Threshold(FunctionBlock):

        type = "threshold"
        available_methods = [
            "binary",
            "binary_inv",
            "trunc",
            "tozero",
            "tozero_inv",
            "mask",
        ]
        # TODO support "otsu" & "triangle"

        def __init__(self, input, lower, upper, method="binary", **kwargs):
            super().__init__(inputs=[input], nin=1, nout=1, **kwargs)
            assert (
                method in self.available_methods
            ), "Thresholding method {method} unsupported. Please select from methods in Threshold.available_methods list" \
                .format(method=method)

            for l, u in zip(lower, upper):
                assert l <= u, "all lower vals must be less than corresponding upper"

            self.lower = lower
            self.upper = upper
            self.method = getattr(
                cv2, "THRESH_{method}".format(method=method.upper()))

        def output(self, _t=None):
            [input] = self.inputs
            _, output = cv2.threshold(
                input, self.lower, self.upper, self.method)
            return [output]

    class KernelParam2D(HyperParam):

        available_types = ["ellipse", "rect", "cross"]

        def __init__(self, spec=("ellipse", 3, 3), **kwargs):
            super().__init__(spec, **kwargs)

            type, width, height = spec if isinstance(spec, tuple) else \
                ("custom", *spec.shape) if isinstance(spec, np.ndarray) else \
                (None, None, None)

            # self.array = self.param('array', self.val if type == 'custom' else None)
            self.type = self.param(
                'type', type, oneof=self.available_types)
            self.width = self.param('width', width, min=3, max=12, step=1)
            self.height = self.param('height', height, min=3, max=12, step=1)
            self.update()

        def update(self, _=None):
            # TODO: allow for custom kernel with matrix editor (see commented out code)
            # if type == "custom":
            #     # self.show(self.array)
            #     self.hide(self.width, self.height)
            # else:
            assert (
                self.type in self.available_types
            ), "Morphological Kernel type {type} unsupported. Please select from {types}" \
                .format(type=self.type, types=self.available_types)

            # self.show('width', 'height')
            # self.hide(self.array)

            # self.array.set_val(cv2.getStructuringElement(
            #         getattr(cv2, "MORPH_%s" % type.upper()),
            #         (self.width.val, self.height.val)
            #     ), exclude_cb=self.setup_kernel)

            # self.val = self.array.val
            self.val = cv2.getStructuringElement(
                getattr(cv2, "MORPH_%s" % self.type.upper()),
                (self.width, self.height)
            )

    class _Morphological(FunctionBlock, TunableBlock):
        type = "morphological"

        def __init__(self, input, diadic_func, kernel, iterations, **kwargs):
            super().__init__(inputs=[input]
                             if input else [], nin=1, nout=1, **kwargs)

            self.diadic_func = diadic_func
            self.kernel = self._param('kernel', KernelParam2D(kernel))
            self.iterations = self._param(
                'iterations', iterations, min=1, max=10, step=1)

        def output(self, _t=None):
            [input] = self.inputs
            output = self.diadic_func(input, self.kernel, self.iterations)
            return [output]

    @block
    class Erode(_Morphological):

        type = "erode"

        def __init__(self, input, iterations=1, kernel=("ellipse", 3, 3), **kwargs):
            super().__init__(
                input,
                diadic_func=cv2.erode,
                kernel=kernel,
                iterations=iterations,
                **kwargs,
            )

    @block
    class Dilate(_Morphological):

        type = "dilate"

        def __init__(self, input, iterations=1, kernel=("ellipse", 3, 3), **kwargs):
            super().__init__(
                input,
                diadic_func=cv2.dilate,
                kernel=kernel,
                iterations=iterations,
                **kwargs,
            )

    @block
    class OpenMask(SubsystemBlock, TunableBlock):

        type = "openmask"

        def __init__(self, input, iterations=1, kernel=("ellipse", 3, 3), **kwargs):
            super().__init__(
                inputs=[input],
                nin=1,
                nout=1,
                **kwargs
            )

            morphblock_kwargs = dict(input=None,
                                     kernel=self._param(
                                         'kernel', KernelParam2D(kernel), ret_param=True),
                                     iterations=self._param(
                                         'iterations', iterations, ret_param=True),
                                     bd=self.bd, is_subblock=True)

            # I would expect cv2.morphologyEx() to be faster than an cv2.erode -> cv2.dilate
            # but preliminary benchmarks show this isn't the case.
            self.dilate = Dilate(**morphblock_kwargs)
            self.erode = Erode(**morphblock_kwargs)

        def output(self, _t=None):
            self.erode.inputs = self.inputs
            eroded = self.erode.output()
            self.dilate.inputs = eroded
            return self.dilate.output()

    @block
    class CloseMask(SubsystemBlock, TunableBlock):

        type = "closemask"

        def __init__(self, input, iterations=1, kernel=("ellipse", 3, 3), **kwargs):
            # TODO Propagate name in some way to aid debugging
            super().__init__(
                inputs=[input],
                nin=1,
                nout=1,
                **kwargs
            )
            args = dict(input=None, tinker=kwargs['tinker'],
                        kernel=self._param('kernel', kernel),
                        iterations=self._param(
                            'iterations', iterations, min=1, max=10, step=1),
                        bd=self.bd, is_subblock=True)

            self.dilate = Dilate(**args)
            self.erode = Erode(**args)

        def output(self, _t=None):
            self.dilate.inputs = self.inputs
            dilated = self.dilate.output()
            self.erode.inputs = dilated
            return self.erode.output()

    @block
    class Blobs(FunctionBlock, TunableBlock):
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

        def __init__(
            self,
            input,
            top_k=None,
            min_dist_between_blobs=10,
            area=None,
            circularity=None,
            inertia_ratio=None,
            convexivity=None,
            # TODO: come up with better defaults
            grayscale_threshold=(253, 255, 1),
            **kwargs
        ):
            super().__init__(inputs=[input], nin=1, nout=1, **kwargs)

            self.top_k = self._param(
                'top_k', top_k, min=1, max=10, default=1, step=1)

            self.blob_color = self._param(
                'blob_color', 255, oneof=(0, 255), on_change=self._setup_sbd)
            self.min_dist_between_blobs = self._param('min_dist_between_blobs',
                                                      min_dist_between_blobs, min=1, max=1e3, log_scale=True, on_change=self._setup_sbd)
            self.area = self._param('area', RangeParam(
                area, min=1, max=2**21, default=(50, 2**21), log_scale=True), on_change=self._setup_sbd)
            self.circularity = self._param('circularity', RangeParam(
                circularity, min=0, max=1, default=(0.5, 1), step=0.01), on_change=self._setup_sbd)
            self.inertia_ratio = self._param('inertia_ratio', RangeParam(
                inertia_ratio, min=0, max=1, default=(0.5, 1), step=0.01), on_change=self._setup_sbd)
            self.convexivity = self._param('convexivity', RangeParam(
                convexivity, min=0, max=1, default=(0.5, 1), step=0.01), on_change=self._setup_sbd)
            self.grayscale_threshold = self._param(
                'grayscale_threshold', grayscale_threshold, min=(0, 0, 1), max=(255, 255, 255), step=1, on_change=self._setup_sbd)

            self._setup_sbd()

        def _setup_sbd(self, _=None):  # unused param to work with on_change
            params = cv2.SimpleBlobDetector_Params()
            params.blobColor = self.blob_color
            params.minDistBetweenBlobs = self.min_dist_between_blobs
            (
                params.minThreshold,
                params.maxThreshold,
                params.thresholdStep,
            ) = self.grayscale_threshold

            if self.area:
                params.minArea, params.maxArea = self.area
            params.filterByArea = bool(self.area)

            if self.circularity:
                params.minCircularity, params.maxCircularity = self.circularity
            params.filterByCircularity = bool(self.circularity)

            if self.inertia_ratio:
                params.minInertiaRatio, params.maxInertiaRatio = self.inertia_ratio
            params.filterByInertia = bool(self.inertia_ratio)

            self.detector = cv2.SimpleBlobDetector_create(params)

        def output(self, _t=None):
            [input] = self.inputs
            keypoints = self.detector.detect(input)
            return [keypoints[:self.top_k] if self.top_k else keypoints]

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

        FPS_AV_FACTOR = 1 / 15  # smaller number averages over more frames
        FPS_AV_FACTOR_INV = 1 - FPS_AV_FACTOR
        FPS_COLOR = (0, 255, 255)  # yellow

        def __init__(self, input, name="Display", show_fps=False, web_stream_host=None, **kwargs):
            super().__init__(inputs=[input], nin=1, name=name, **kwargs)
            self.show_fps = show_fps
            self.web_stream_host = web_stream_host

            if web_stream_host:
                self.new_frame = None
                # maintain a lock for each mjpeg http stream. Can't think of a better way to do this
                self.new_frame_locks = []

            if self.show_fps:
                self.fps = 30  # seems a decent init value
                self.last_t = None

        def start(self):
            # TODO: web-stream via HTTP stream over raw sockets so it'll work in micropython
            # OR/AND, do so over websockets without jpeg encoding
            if self.web_stream_host is not None:
                app = flask.Flask('dirtywebstream')

                @app.route("/")
                def video_feed():
                    def poll_frames():
                        # maintain a lock for the lifetime of this generator - cleanup when client d/c's
                        new_frame_lock = Lock()
                        self.new_frame_locks.append(new_frame_lock)
                        try:
                            while True:
                                new_frame_lock.acquire()
                                yield(b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' +
                                      bytearray(self.new_frame) + b'\r\n')
                        except GeneratorExit:
                            self.new_frame_locks.remove(new_frame_lock)

                    return flask.Response(poll_frames(),
                                          mimetype="multipart/x-mixed-replace; boundary=frame")

                def host_web_stream():
                    if isinstance(self.web_stream_host, Tuner):
                        self.web_stream_host.register_video_stream(video_feed, name=self.name)
                        
                    else:
                        # start web stream and let bdsim choose the address
                        if self.web_stream_host is True:
                            # TODO: review this default host - localhost is the typical standard but I find that annoying
                            host, port = '0.0.0.0', 7645
                            # keep trying 0.0.0.0 ports - counting up
                            while True:
                                try:
                                    app.run(host, port)
                                except OSError as e:
                                    if 'Address already in use' in str(e):
                                        port += 1
                                    else:
                                        raise Exception('unexpected error', e)
                        else:
                            host, port = self.web_stream_host
                            app.run(host, port)

                Thread(target=host_web_stream, daemon=True).start()

        def step(self):
            [input] = self.inputs
            if self.show_fps:
                frequency = 1 / \
                    (self.bd.t - self.last_t) if self.last_t else self.fps
                # moving average formula
                self.fps = self.FPS_AV_FACTOR * frequency + self.FPS_AV_FACTOR_INV * self.fps
                input = cv2.putText(input, "%d FPS" % int(self.fps), (0, 16),
                                    cv2.FONT_HERSHEY_PLAIN, 1,
                                    self.FPS_COLOR if len(input.shape) == 3 else 255)  # use white if it's grayscale
                self.last_t = self.bd.t

            # just quick and dirty for now
            if self.web_stream_host:
                _ret, jpg = cv2.imencode('.jpg', input)
                self.new_frame = jpg

                # let mjpeg stream clients know that a new frame is available
                for lock in self.new_frame_locks:
                    if lock.locked():
                        lock.release()
            else:
                cv2.imshow(self.name, input)
                # cv2 needs this to actually show. this blocking maybe matplotlib could do it instead.
                cv2.waitKey(1)

        def stop(self):
            if not self.web_stream_host:
                # TODO: Check if overkill to ensure that self.name never changes?
                cv2.destroyWindow(self.name)

    @block
    class DrawKeypoints(FunctionBlock):

        type = "drawkeypoints"

        def __init__(self, image, keypoints, color=(0, 0, 255), **kwargs):
            super().__init__(inputs=[image, keypoints],
                             nin=2, nout=1, **kwargs)
            self.color = color

        def output(self, _t=None):
            [image, keypoints] = self.inputs
            drawn = cv2.drawKeypoints(image, keypoints, np.array([]), self.color,
                                      cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
            return [drawn]

except ImportError:
    logging.warning(
        "OpenCV not installed. Vision blocks will not be available")
