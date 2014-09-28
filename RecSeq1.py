#!/usr/bin/python

# Record a set of time-stamped video files from RPi camera
# At the same time, do motion detection and generate log of motion events
# Saving stills when motion is detected is possible, but interrupts the video.
# J.Beale  v0.2 27 Sept 2014

from __future__ import print_function
from datetime import datetime
import picamera, time
import numpy as np
from PIL import Image  # for converting array back to a JPEG for export (debug only)

# --------------------------------------------------
videoDir = "/mnt/video1/" # directory to record video files 
picDir = "/mnt/video1/" # directory to record still images
logfile = "/home/pi/logs/RecSeq_log.csv" # where to save log of motion detections
recFPS = 8  # how many frames per second to record
cxsize = 1920 # camera video X size
cysize = 1080 # camera video Y size
segTime = 3600 # how many seconds long each video file should be 

# xsize and ysize are used in the internal motion algorithm, not in the .h264 video output
xsize = 64 # YUV matrix output horizontal size will be multiple of 32
ysize = 32 # YUV matrix output vertical size will be multiple of 16
dFactor = 3.0  # how many sigma above st.dev for diff value to qualify as motion pixel
pcThresh = 30  # total number of changed elements which add up to "motion"
novMaxThresh = 200 # peak "novel" pixmap value required to qualify "motion event"

logHoldoff = 0.4 # don't log another motion event until this many seconds after previous event

avgmax = 3     # long-term average of maximum-pixel-change-value
stg = 10       # groupsize for rolling statistics

timeMin = 1.0/6  # minimum time between motion computation (seconds)
running = False  # whether we have done our initial average-settling time
initPass = 5     # how many initial passes to do
pixvalScaleFactor = 65535/255.0  # multiply single-byte values by this factor
frames = 0 # how many frames we've looked at for motion
fupdate = 1   # report debug data every this many frames
gotMotion = False # true when motion has been detected
debug = False # should we report debug data (pixmap dump to PNG files)
showStatus = True # if we should print status data every pass?
showStatus = False

# Image crop / zoom parameters (can change image aspect ratio)
zx = 0.0  # normalized horizontal image offset
zy = 0.0 # normalized vertical image offset (0 = top of frame)
zw = 1.0 # normalized horizontal scale factor (1.0 = full size)
zh = 0.5 # normalized vertical scale factor (1.0 = full size)
resX = 1920  # rescaled X resolution (video / still)
resY = 540  # rescaled Y resolutio (video / still)

# --------------------------------------------------
sti = (1.0/stg) # inverse of statistics groupsize
sti1 = 1.0 - sti # 1 - inverse of statistics groupsize

# --------------------------------------------------
def date_gen():
  while True:
    dstr = videoDir + datetime.now().strftime("%y%m%d_%H%M%S") + ".h264"
    yield dstr

# initMaps(): initialize pixel maps with correct size and data type
def initMaps():
    global newmap, difmap, avgdif, tStart, lastTime, stsum, sqsum, stdev
    newmap = np.zeros((ysize,xsize),dtype=np.float32) # new image
    difmap = np.zeros((ysize,xsize),dtype=np.float32) # difference between new & avg
    stsum  = np.zeros((ysize,xsize),dtype=np.int32) # rolling average sum of pix values
    sqsum  = np.zeros((ysize,xsize),dtype=np.int32) # rolling average sum of squared pix values
    stdev  = np.zeros((ysize,xsize),dtype=np.int32) # rolling average standard deviation
    avgdif  = np.zeros((ysize,xsize),dtype=np.int32) # rolling average difference

    tStart = time.time()  # time that program starts
    lastTime = tStart  # last time event detected

# getFrame(): returns Y intensity pixelmap (xsize x ysize) as np.array type
def getFrame(camera):
    stream=open('/run/shm/picamtemp.dat','w+b')
    camera.capture(stream, format='yuv', resize=(xsize,ysize), use_video_port=True)
    stream.seek(0)
    return np.fromfile(stream, dtype=np.uint8, count=xsize*ysize).reshape((ysize, xsize))

# saveFrame(): save a JPEG file
def saveFrame(camera):
    fname = picDir + daytime + ".jpg"
    camera.capture(fname, format='jpeg', use_video_port=True)


# updateTS1(): update video timestamp with current time, and '*' if motion detected
# the optional second argument specifies a delay in seconds, meanwhile time keeps updating
def updateTS1(camera, delay = 0):
  tStart = time.time() # actual value is raw seconds since Jan.1 1970
  while True: 
    detect_motion(camera) # one pass through the motion-detect algorithm
    if gotMotion:
      camera.annotate_text = datetime.now().strftime('* %Y-%m-%d %H:%M:%S *')
    else:
      camera.annotate_text = datetime.now().strftime('  %Y-%m-%d %H:%M:%S  ')
    tElapsed = time.time() - tStart  # seconds since this function started
    if (tElapsed >= delay): # quit when elapsed time reaches the delay requested
      break

# =============================================== 

# detect_motion() is where the low-res version of the image is compared with an average of
# past images, and a recent standard-deviation pixel map, to detect 'novel' pixels.
# Enough novel pixels, with a large enough peak amplitude, generates a motion event.

def detect_motion(camera):
    global running # true if algorithm has passed through initial startup settling
    global xsize, ysize  # dimensions of pixmap for motion calculations
    global newmap, avgdif # pixmap data arrays
    global avgmax # (scalar) running average of maximum magnitude of pixel change
    global frames  # how many frames we've examined for motion
    global gotMotion # boolean True if motion has been detected
    global tStart  # time of last event
    global lastTime # time this function was last run
    global daytime # current time of day when motion event detected
    global stsum # (matrix) rolling average sum of pixvals
    global sqsum # (matrix) rolling average sum of squared pixvals
    global stdev # (matrix) rolling average standard deviation of pixels
    global initPass # how many initial passes we're doing

     
    newTime = time.time()
    elapsedTime = newTime - lastTime
    if (elapsedTime < timeMin):  # don't recompute motion data too rapidly (eg. on same frame)
      time.sleep(timeMin - elapsedTime)

    lastTime = newTime
    fps = int(1/elapsedTime)

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

# note: stdev ~8000, difmap ~500 for 32x16 matrix, pixvalScaleFactor = 100/255, stg = 15

    stsum = (stsum * sti1) + newmap           # rolling sum of most recent 'stg' images (approximately)
    sqsum = (sqsum * sti1) + np.power(newmap, 2) # rolling sum-of-squares of 'stg' images (approx)
    devsq = 0.1 + (stg * sqsum) - np.power(stsum, 2)  # variance, had better not be negative
    stdev = (1.0/stg) * np.power(devsq, 0.5)    # matrix holding rolling-average element-wise std.deviation
    novel = difmap - (dFactor * stdev)   # novel pixels have difference exceeding (dFactor * standard.deviation)

    novMax = np.amax(novel)  # largest value in 'novel' array: greatest unusual brightness change 
    novMin = np.amin(novel)  # smallest value; very close to zero unless recent big brightness change

    dAvg = np.average(difmap)  # average of all elements of array (pixmap)
    sAvg = np.average(stdev)

    if initPass > 0:             # are we still initializing array averages?
      initPass = initPass - 1
      return False		# if so, quit now before making any event-detections

    condition = novel > 0  # boolean array of pixels showing positive 'novelty' value
    changedPixels = np.extract(condition, novel)
    countPixels = changedPixels.size  # how many pixels are considered unusual / novel in this frame

    novel = novel - novMin  # force minimum to zero

    if (countPixels > pcThresh) and (novMax > novMaxThresh):  # found enough changed pixels to qualify as motion?
      gotMotion = True
    else:
      gotMotion = False

    if showStatus:  # print debug info
      print ("%d %f %d %f" % (gotMotion, magMax, countPixels, fps))

    if gotMotion:
      tNow = time.time()
      tInterval = tNow - tStart
      if (tInterval > logHoldoff):  # only log when at least logHoldoff time has elapsed
        tStart = tNow
        daytime = datetime.now().strftime("%y%m%d_%H%M%S")
	# saveFrame(camera)  # save a still image - unfortunately makes the video recording skip frames
        tstr = ("%s,  dM:%4.1f, nM:%4.1f, dT:%6.3f, px:%d\n" % (daytime,magMax,novMax,tInterval,countPixels))
        f.write(tstr)
        f.flush()

      if showStatus:
        print("********************* MOTION **********************************")
    else:
      running = True  # 'running' set True after initial filter settles and "Motion-Detect" drops

    frames = frames + 1
    if (((frames % fupdate) == 0) and debug):
        print ("cPx:%d nM:%5.1f d:%5.2f s:%5.2f fps=%3.0f" %\
               (countPixels, novMax, dAvg, sAvg, fps))
        
	# np.set_printoptions(precision=1)
	# print(difmap)
	# print(sqsum) # show all elements of array 
	# print(stdev) # show all elements of array 

#        fstr = '%04d' % (frames)  # convert integer to formatted string with leading zeros
#        img = Image.fromarray(stsum.astype(int))
#        avgMapName = "A" + fstr + ".png"
#        img.save(avgMapName)  # save as image for visual analysis

    # running = False  # DEBUG never admit to a motion detection
    if running:
      return gotMotion
    else:
      return False

# ============= Main Program ====================

with picamera.PiCamera() as camera:

    np.set_printoptions(precision=1)
    daytime = datetime.now().strftime("%y%m%d_%H:%M:%S")
    f = open(logfile, 'a')
    f.write ("# RecSeq log v0.2 Sept. 27 2014 J.Beale\n")
    outbuf = "# Start: " + daytime  + "\n"
    f.write (outbuf)
    f.flush()
    print ("PiMotion starting at %s" % daytime)

    initMaps() # set up pixelmap arrays
#    camera.resolution = camera.MAX_RESOLUTION  # sensor res = 2592 x 1944
    camera.resolution = (cxsize, cysize)
    camera.framerate = recFPS  # how many frames per second to record
    camera.annotate_background = True # black rectangle behind white text for readibility
    camera.zoom = (zx, zy, zw, zh) # set image offset and scale factor (default 0,0,1,1 )
    camera.exposure_mode = 'night'
    for filename in camera.record_sequence( date_gen(), format='h264', resize=(resX, resY)):
        waitTime = segTime-(time.time()%segTime)
        print("Recording for %d to %s" % (waitTime,filename))
        updateTS1(camera, waitTime)

# ================================================
