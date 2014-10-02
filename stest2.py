#!/usr/bin/python

from __future__ import print_function
import io
import picamera, time
from datetime import datetime  # for 'daytime' string

global picDir

picDir = "/run/shm/"
vidDir = "/run/shm/"

# saveFrame(): save a JPEG file
def saveFrame(camera):
  fname = picDir + daytime + ".jpg"
  camera.capture(fname, format='jpeg', resize = (1280, 720), use_video_port=True)

class MyCustomOutput(object):

    def __init__(self, camera, filename):
        self.camera = camera
        self._file = io.open(filename, 'wb')

    def write(self, buf):
        global fnumOld
        global daytime
        global tStart
	global tInterval
	global lastFrac
	global lastFrame
	global trueFrameNumber

	fnum = self.camera.frame.index
	ftype = self.camera.frame.frame_type
	if (fnum != fnumOld) and (ftype != 2):  # ignore continuation of a previous frame, and SPS headers
	  trueFrameNumber = trueFrameNumber + 1
          fnumOld = fnum
          daytime = datetime.now().strftime("%H:%M:%S.%f")  
          daytime = daytime[:-3] # lose the microseconds, leave milliseconds
          self.camera.annotate_text = str(trueFrameNumber+2) + " " + daytime  # set the in-frame text to time/date
	  tFrame = time.time()
	  fps = 1.0 / (tFrame - lastFrame)
	  print("%d, %d, %s ft:%d fps=%5.3f" % (trueFrameNumber, fnum, daytime, ftype, fps))
	  lastFrame = tFrame
	  tElapsed = tFrame - tStart  # seconds since program start
	  outFrac = tElapsed / tInterval
#	  if int(outFrac) != lastFrac:  # time for another image output?
#            print("  PIC: %d %5.3f %s" % (fnum, outFrac, daytime))
#	    lastFrac = int(outFrac)
#            saveFrame(self.camera)
        return self._file.write(buf)

    def flush(self):
        self._file.flush()

    def close(self):
        self._file.close()


with picamera.PiCamera() as camera:
    global fnumOld   # previous value of camera.frame.index
    global daytime   # current time & date
    global tStart    # time routine starts
    global lastFrac
    global tInterval
    global lastFrame
    global trueFrameNumber

    trueFrameNumber = 0  # actual video image frame count, not just packets or whatnot
    lastFrac = 0
    fnumOld = -1
    tInterval = 2.0  # how many seconds between JPEG output
    tStart = time.time() # seconds since Jan.1 1970
    lastFrame = tStart
    daytime = datetime.now().strftime("%y%m%d_%H%M%S.%f")
    daytime = "Start: " + daytime[:-3] # loose the microseconds, leave milliseconds
    print("%s" % daytime)

    camera.resolution = (1920, 1080)
    camera.framerate = 8
    camera.annotate_background = True # black rectangle behind white text for readibility
    camera.annotate_text = daytime
    output = MyCustomOutput(camera, vidDir + 'foo.h264')
    camera.start_recording(output, format='h264')
    camera.wait_recording(20)
    camera.stop_recording()
    output.close()
