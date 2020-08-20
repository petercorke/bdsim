import logging

try:
    from ..components import SourceBlock, block

    @block
    class VideoStreamBlock():
        pass

    @block
    class CvtColorBlock():
        pass

    @block
    class ThresholdBlock():
        pass

    @block
    class SimpleBlobDetectorBlock():
        pass

except ModuleNotFoundError:
    logging.warn("OpenCV not installed. OpenCV Blocks will not be available")
