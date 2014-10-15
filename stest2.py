#!/usr/bin/python

# Record video from Raspberry Pi camera in .h264 with in-frame text
# showing time/date, and count emitted video frames using a custom output
# which is called when buffers for each frame is ready. 

# The output class may  be called more than once per frame,
# if the picture data is larger than one buffer, \
# so need to check if camera.frame.index has changed, and
# also some buffers are not I/P image frames, so need to ignore those.
#
# Recommend to increase priority with 'sudo chrt -r -p 99 <pid>' 
# to reduce variability of process scheduling delays
#
# 15 October 2014  J.Beale

# To install needed Python components do:
# sudo apt-get install python-picamera python-numpy python-scipy 

from __future__ import print_function
import io
import picamera, time
from datetime import datetime  # for 'daytime' string
import numpy as np  # for number-crunching on arrays
from scipy import ndimage  # for array center-of-mass (location of new object)
from PIL import Image # to export debug array as bitmap image

global running  # have we done the initial array processing yet?
global vPause   # true when we should stop grabbing frames
global nGOPs    # how many GOPs to record in one segment
global mCount   # how many motion events detected in this segment
global framesLead # lead time allowed before end-of-GOP to stop sampling YUV


picDir = "/ram/"   # where to store still frames
videoDir = "/ram/"   # where to store video files
tmpDir = "/run/shm/" # where to store YUV frame buffer
frameRate = 8   # how many frames per second to record in video
sampleRate = 2 # run motion algorithm every N frames
sizeGOP = 60 # number of I+P frames in one GOP
nGOPs = 4  # (nGOPs * sizeGOP) frames will be in one H264 video segment
framesLead = 1 # how many frames before end-of-GOP we need to stop analyzing
mCalcInterval = 2.0/frameRate # seconds in between motion calculations
settleTime = 10.0 # how many seconds to do averaging before motion detect is valid
debugMap = False # set 'True' to generate debug motion-bitmap .png files in picDir

cXRes = 1920   # camera capture X resolution (video file res)
cYRes = 1080    # camera capture Y resolution
dFactor = 2.5  # how many sigma above st.dev for diff value to qualify as motion pixel
stg = 160       # groupsize for rolling statistics
pixThresh = 8  # how many novel pixels counts as an event
# --------------------------------------------------
sti = (1.0/stg) # inverse of statistics groupsize
sti1 = 1.0 - sti # 1 - inverse of statistics groupsize


running = False  # have we done the initial array processing yet?

# --------------------------------------------------------------------------------------
# xsize and ysize are used in the internal motion algorithm, not in the .h264 video output
xsize = 96 # YUV matrix output horizontal size will be multiple of 32
ysize = 32 # YUV matrix output vertical size will be multiple of 16
pixvalScaleFactor = 65535/255.0  # multiply single-byte values by this factor

# --------------------------------------------------
def date_gen(camera):
  global segTime
  global segName
  global segDate
  global segFrameNumber
  while True:

    segTime = time.time()  # current time in seconds since Jan 1 1970
    segDate = time.strftime("%y%m%d_%H%M%S.%f", time.localtime(segTime))
    segDate = segDate[:-3] # loose the microseconds, leave milliseconds
    segFrameNumber = 0 # reset in-segment frame number for start of new segment
    segName = videoDir + segDate + ".h264"
    # print("this file = %s" % segName)
    yield MyCustomOutput(camera, segName)


# initMaps(): initialize pixel maps with correct size and data type
def initMaps():
    global newmap, difmap, avgdif, mtStart, lastTime, stsum, sqsum, stdev
    global avgNovel, xcent, ycent
    global fnum # count of debug images output
    global settled  # True when initial scene averaging has settled out

    newmap = np.zeros((ysize,xsize),dtype=np.float32) # new image
    difmap = np.zeros((ysize,xsize),dtype=np.float32) # difference between new & avg
    stsum  = np.zeros((ysize,xsize),dtype=np.int32) # rolling average sum of pix values
    sqsum  = np.zeros((ysize,xsize),dtype=np.int32) # rolling average sum of squared pix values
    stdev  = np.zeros((ysize,xsize),dtype=np.int32) # rolling average standard deviation
    avgdif  = np.zeros((ysize,xsize),dtype=np.int32) # rolling average difference

    mtStart = time.time()  # time that program starts
    lastTime = mtStart  # last time event detected
    avgNovel = 0  # average of all "novel" pixels
    xcent = 0 # average x,y location of new object(s)
    ycent = 0 #
    fnum = 0 # count of debug bitmaps output
    settled = False # have not yet settled out averaging

# saveFrame(): save a JPEG file
def saveFrame(camera):
  if (not vPause):
    fname = picDir + daytime + ".jpg"
    camera.capture(fname, format='jpeg', resize = (1280, 720), use_video_port=True)

# getFrame(): returns Y intensity pixelmap (xsize x ysize) as np.array type
def getFrame(camera):
    global frameIndex  # some kind of index number, but maybe not the exact frame count

    stream=open(tmpDir + 'picamtemp.dat','w+b')
    camera.capture(stream, format='yuv', resize=(xsize,ysize), use_video_port=True)
    frameIndex = camera.frame.index
    stream.seek(0)
    return np.fromfile(stream, dtype=np.uint8, count=xsize*ysize).reshape((ysize, xsize))
  
# processImage(): do some computations on low-res version of current image
def processImage(camera):
    global running  # have we done initial array processing yet?
    global settled  # True when initial scene averaging has settled out
    global stsum # (matrix) rolling average sum of pixvals
    global sqsum # (matrix) rolling average sum of squared pixvals
    global stdev # (matrix) rolling average standard deviation of pixels
    global initPass # how many initial passes we're doing
    global countPixels # how many pixels show novelty value this frame
    global avgNovel # average value of all 'novel' pixels > 0    
    global xcent, ycent # average location of detected object
    global fnum # count of debug images output

    newmap = pixvalScaleFactor * getFrame(camera)  # current pixmap  

    if not running:  # first time ever through this function?
      stsum = stg * newmap         # call the sum over 'stg' elements just stg * initial frame
      sqsum = stg * np.power(newmap, 2) # initialze sum of squares
      running = True                    # ok, now we're running
      return False

						   # avgmap = [stsum] / stg
    difmap = newmap - np.divide(stsum, stg)        # difference pixmap (amount of per-pixel change)
    difmap = abs(difmap)                 # take absolute value (brightness may increase or decrease)
    magMax = np.amax(difmap)               # peak magnitude of change

    stsum = (stsum * sti1) + newmap           # rolling sum of most recent 'stg' images (approximately)
    sqsum = (sqsum * sti1) + np.power(newmap, 2) # rolling sum-of-squares of 'stg' images (approx)

    if not settled:
      runTime = time.time() - mtStart # how many seconds we have been running
      if (runTime > settleTime):
        settled = True
      return # stop right here, don't need to preceed before settling for valid motion detect

    devsq = (stg * sqsum) - np.power(stsum, 2)  # variance, had better not be negative
    np.clip(devsq, 0.1, 1E15, out=devsq)  # force all elements to have minimum value = 0.1
	# adding 1.0 * pixvalScaleFactor is just saying every pixel has at least one count of std.dev
    stdev = pixvalScaleFactor + (1.0/stg) * np.power(devsq, 0.5)    # matrix holding rolling-average element-wise std.deviation
    novel = difmap - (dFactor * stdev)   # novel pixels have difference exceeding (dFactor * standard.deviation)

    condition = novel > 0   # boolean array, 1 where pixel with positive novelty value exists
    changedPixels = np.extract(condition, novel)  # make a list containing only changed pixels
    countPixels = changedPixels.size
    if (countPixels > 0):  # found something! (at least one pixel's worth of something)
      avgNovel = int( np.average(changedPixels)) # clipping to integer still leaves plenty of precision
      np.clip(novel, 0.0, 1.0, out=novel) # force negative values to 0, and clip positive values to 1
      moMap = ndimage.binary_dilation(novel)
      novel = ndimage.binary_erosion(moMap, iterations=2)
      countPixels = np.count_nonzero(novel) # recount how many 'novel' pixels there are after dilation + erosion

    if (countPixels > 0):
      (ycent, xcent) = ndimage.measurements.center_of_mass(novel.astype(int)) # (x,y) center of motion. x is horizontal axis on image
      if (debugMap):  # generate bitmaps showing location of novel pixels?
        novel = novel * 65535 # rescale 0-1 to fullscale for black/white display
        img = Image.fromarray(novel.astype(int))
        fnumstr = "%03d" % fnum
        novMapName = picDir + "A" + fnumstr + ".png"
        img.save(novMapName)  # save as image for visual analysis
        fnum = fnum + 1
    else:
      avgNovel = 0
      (xcent, ycent) = (0, 0)  # nothing to see here, apparently

# -- END processImage()    
  
# -------------------------------------------------------------------------
# the 'write()' member of this class is called whenever a buffer of image data is ready

class MyCustomOutput(object):

    def __init__(self, camera, filename):
        self.camera = camera
        self._file = io.open(filename, 'wb')

    def write(self, buf):
      global fnumOld
      global daytime # time-of-day when 1st buffer of latest video frame started
      global tStart
      global tInterval
      global lastFrac
      global lastFrame
      global trueFrameNumber # how many video frames since camera started
      global segFrameNumber # how many video frames since this .h264 file segment
      global iString
      global firstTime  # True on the very first call, False all subsequent times
      global vPause # True => no motion detect
      global okGo  # False when we should turn off motion detect
      global nGOP  # how many (I,P,P,P...) H264 stream frame sets we have seen
      global firstType2 # first buffer of 'type 2' in a row
      global mCount # how many motion events detected

      if (firstTime == True):
        tStart = time.time() # seconds since Jan.1 1970
        firstTime = False    

      fnum = self.camera.frame.index
      ftype = self.camera.frame.frame_type

      if (ftype == 2):  # end of GOP?
        if (okGo == False):
          # print("End GOP marker: %d" % nGOP)
	  vPause = True
	if (firstType2 == True):
	  nGOP = nGOP + 1    # ok, first 'type 2' buffer => completed another GOP
	  firstType2 = False
      else:
	firstType2 = True

      if (ftype != 2) and (okGo == True):  # ok to re-enable event detection
	vPause = False
      if (fnum != fnumOld) and (ftype != 2):  # ignore continuation of a previous frame, and SPS headers
        
        trueFrameNumber = trueFrameNumber + 1
	segFrameNumber = segFrameNumber + 1  # how many frames since start of this H264 segment (file)
        fnumOld = fnum

        daytime = datetime.now().strftime("%y%m%d_%H:%M:%S.%f")  
        daytime = daytime[:-3] # lose the microseconds, leave milliseconds
        
	if (countPixels < pixThresh):
	  iString = "  "
	else:
	  iString = "* "
	  mCount = mCount + 1
        # set the in-frame text to time/date
#        self.camera.annotate_text = iString + str(segFrameNumber+2) + " " + daytime 
        self.camera.annotate_text = iString + " " + daytime 

	if ((trueFrameNumber + framesLead) % (nGOPs * sizeGOP)) == 0:
	  okGo = False  # we are about to end this video segment; halt event processing

      return self._file.write(buf)

    def flush(self):
        self._file.flush()

    def close(self):
        self._file.close()

        
# ===================================================
# == MAIN program begins here ==


initMaps() # set up pixelmap arrays

with picamera.PiCamera() as camera:
    global fnumOld   # previous value of camera.frame.index
    global daytime   # current time & date
    global tStart    # time routine starts
    global lastFrac
    global tInterval
    global lastFrame
    global trueFrameNumber
    global segFrameNumber # how many video frames since this .h264 file segment
    global iString
    global firstTime  # True on the very first call, False all subsequent times
    global vPause
    global okGo  # end of video segment is not imminent, so normal processing is OK
    global nGOP
    global firstType2 # if this is a 'type 2' frame, is it the first one in a row?
    global mCount     # count of motion events
    global countPixels # how many new pixels
    global eventRelTime
    global segTime

    mCount = 0        # how many motion events detected
    countPixels = 0   # how many pixels show novelty, this frame
    lastCP = 0        # previous reported countPixels value
    nGOP = 0	      # have not yet encoded any H264 GOPs yet
    okGo = True       # OK to grab frames
    vPause = False    # OK to grab frames
    firstTime = True  # have not run yet    
    firstType2 = True # previous frame was not 'type 2'
    segFrameNumber = 0 # no frames saved yet
    iString = " "  # no "event" flag yet
    trueFrameNumber = 1  # actual video image frame count, not just packets or whatnot
    lastFrac = 0
    fnumOld = -1
    tInterval = 2.0  # how many seconds between JPEG output
#    tStart = time.time() # seconds since Jan.1 1970
    lastFrame = time.time()
    daytime = datetime.now().strftime("%y%m%d_%H%M%S.%f")
    daytime = daytime[:-3] # loose the microseconds, leave milliseconds
    print("# PiMotion Start: %s" % daytime)
    log = open(videoDir+"PiMotionStart.log", 'w')       # dummy file with program start-time
    log.close()
	
    camera.resolution = (cXRes, cYRes)
    camera.framerate = frameRate
    camera.exposure_mode = 'sports'  # faster shuttter reduces blur
    camera.exposure_compensation = -5 # slightly darker than default
    camera.annotate_background = True # black rectangle behind white text for readibility
    camera.annotate_text = daytime

    for vidFile in camera.record_sequence( date_gen(camera), format='h264'):
      frameTotal = nGOPs * sizeGOP
      recSec = (1.0 * frameTotal) / frameRate
#      print("Motion events: %d" % mCount)
      mCount = 0
#      print("# Recording for %4.1f sec (%d frames) to %s" % (recSec, frameTotal, segName))
      logFileName = segName[:-4] + "txt"
#      print("logfile = %s" % logFileName)
      if not log.closed:
	log.close()
      log = open(logFileName, 'w')       # open logfile for new video file

      okGo = True # ok to start analyzing again
      while (okGo == True):  # write callback turns off 'okGo' near end of final GOP
	tLoop = time.time()

	if not vPause:
          processImage(camera)  # do the number-crunching
          if (countPixels >= pixThresh):
	    eventRelTime = time.time() - segTime  # number of seconds since start of current H264 segment
	tRemain = mCalcInterval - (time.time() - tLoop)
	if (tRemain < 0) or (lastCP >= 1):
          print("%d, %5.3f, %d, %5.3f, %4.1f,%4.1f, %s" % \
		(countPixels, (1.0*segFrameNumber)/frameRate, avgNovel, tRemain, xcent, ycent, daytime))
	if (not log.closed) and ( (tRemain < 0) or (lastCP >= 1)):
          log.write("%d, %5.3f, %d, %5.3f, %4.1f,%4.1f, %s\n" % \
		(countPixels, (1.0*segFrameNumber)/frameRate, avgNovel, tRemain, xcent, ycent, daytime))
        lastCP = countPixels # remember the previous countPixels value
	if (tRemain > 0):
          time.sleep(tRemain) # delay in between motion calculations


#   as currently written, we never actually reach here    
    camera.stop_recording()
    output.close()
    print("# Now done.")
