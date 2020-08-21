'''
Class to efficiently use the picamera resource.
Uses threading to seperate the image capture and 
any other processing required.

Adapted from: https://www.pyimagesearch.com/2015/12/28/increasing-raspberry-pi-fps-with-python-and-opencv/
Sam
'''


# Import the required modules
from picamera.array import PiRGBArray
from picamera import PiCamera
from picamera.exc import PiCameraValueError
import threading
import numpy as np
import time

class PiVideoStream():
    def __init__(self, 
                resolution=(3280,2464), 
                framerate=10,
                vflip=False,
                hflip=False,
                use_video_port=True):
        # Initialize the camera and stream
        self.camera = PiCamera()
        try:
            self.camera.resolution = resolution
        # Is the picamera a V1? Try the max v1 resolution just incase.
        except PiCameraValueError:
            self.camera.resolution = (2592,1944)
        self.camera.framerate = framerate
        self.camera.vflip = vflip
        self.camera.hflip = hflip
        self.rawCapture = PiRGBArray(self.camera)
        self.stream = self.camera.capture_continuous(
                        self.rawCapture,
                        format="bgr", 
                        use_video_port=use_video_port)
        time.sleep(1) # Allow the cam to warm up

        # Initialize the frame and the variable used to indicate
        # if the thread should be stopped
        self.frame_available = False
        self.frame = None
        self.stopped = False
        print("Camera initialised")
        print("Resolution: ",self.camera.resolution)

    def start(self):
        # start the thread to read frames from the video stream
        threading.Thread(name="Camera", target=self.__update, args=(), daemon=False).start()
        return self

    def stop(self):
        # indicate that the thread should be stopped
        self.stopped = True

    def __update(self):
        # keep looping infinitely until the thread is stopped
        for f in self.stream:
            # grab the frame from the stream and clear the stream in
            # preparation for the next frame
            self.frame = f.array
            self.rawCapture.truncate(0)
            self.frame_available = True

            # if the thread indicator variable is set, stop the thread
            # and resource camera resources
            if self.stopped:
                self.stream.close()
                self.rawCapture.close()
                self.camera.close()
                return

    def read(self):
        # return the frame most recently read
        return self.frame


if __name__ == '__main__':
    '''Example program
        Needs a screen'''
    import cv2
    #import piVideoStream   # When using in a different .py file

    cam = PiVideoStream()   # `cam = piVideoStream.PiVideoStream()` when using a different .py file
    cam.start()

    # Shows 100 frames from the camera stream and exits
    frame_count = 0
    while (frame_count < 100):
        if cam.frame_available:
            im = cam.read()

            '''Do image processing here.
                im is a size[w,h,3] numpy array in the bgr format'''

            cv2.imshow("Test window", im)
            cv2.waitKey(0.01)
            cam.frame_available = False
            frame_count = frame_count + 1

    cam.stop()
    cv2.waitKey(1)
    cv2.destroyAllWindows()
