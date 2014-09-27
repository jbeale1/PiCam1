#!/usr/bin/python

# Record a set of time-stamped video files from RPi camera
# each file is one minute long, and named with the date & time
# J.Beale  26 Sept 2014

from __future__ import print_function
from datetime import datetime
import picamera, time
import numpy as np
from PIL import Image  # for converting array back to a JPEG for export (debug only)

# --------------------------------------------------
videoDir = "/mnt/video1/" # directory to record video files 
#videoDir = "./" # directory to record video files 
picDir = "/mnt/video1/" # directory to record still images
logfile = "/home/pi/logs/RecSeq_log.csv" # where to save log of motion detections
recFPS = 12  # how many frames per second to record
cxsize = 1920 # camera video X size
cysize = 1080 # camera video Y size
# xsize and ysize are used in the internal motion algorithm, not in the video output
xsize = 128 # YUV matrix output horizontal size will be multiple of 32
ysize = 64 # YUV matrix output vertical size will be multiple of 16
mThresh = 20.0 # pixel brightness change threshold that means motion
tFactor = 2.5  # threshold above max.average diff per frame, for motion detect
pcThresh = 15  # total number of changed elements which add up to "motion"
logHoldoff = 0.4 # don't log another motion event until this many seconds after previous event

avgmax = 3     # long-term average of maximum-pixel-change-value
running = False  # whether we have done our initial average-settling time
pixvalScaleFactor = 65535/255.0  # multiply single-byte values by this factor
frac = 0.2  # fraction by which to update long-term average on each pass
frames = 0 # how many frames we've looked at for motion
fupdate = 10   # report debug data every this many frames
gotMotion = False # true when motion has been detected
debug = True # should we report debug data (pixmap dump to PNG files)
showStatus = True # if we should print status data every pass
#showStatus = False

zx = 0.0  # normalized horizontal image offset
#zy = 0.5 # normalized vertical image offset (0 = top of frame)
zy = 0.0 # normalized vertical image offset (0 = top of frame)
zw = 1.0 # normalized horizontal scale factor (1.0 = full size)
zh = 0.5 # normalized vertical scale factor (1.0 = full size)

# --------------------------------------------------
def date_gen():
  while True:
    dstr = videoDir + datetime.now().strftime("%y%m%d_%H%M%S") + ".h264"
    yield dstr

# initMaps(): initialize pixel maps with correct size and data type
def initMaps():
    global avgmap, newmap, difmap, avgdif, tStart, lastTime, stsum, sqsum, stdev
    avgmap = np.zeros((ysize,xsize),dtype=np.float32) # average background image
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


# updateTS(): update video timestamp with current time, and '*' if motion detected
# the optional second argument specifies a delay in seconds, meanwhile time keeps updating
def updateTS1(camera, delay = 0):
    tcount = np.float32(delay)  # remaining time as a float
    if gotMotion:
      camera.annotate_text = datetime.now().strftime('* %Y-%m-%d %H:%M:%S *')
    else:
      camera.annotate_text = datetime.now().strftime('  %Y-%m-%d %H:%M:%S  ')
    while tcount > 0:
      detect_motion(camera)   # run the motion-detect algorithm
      # print tcount
      if gotMotion:
        camera.annotate_text = datetime.now().strftime('* %Y-%m-%d %H:%M:%S *')
      else:
        camera.annotate_text = datetime.now().strftime('  %Y-%m-%d %H:%M:%S  ')
      tcount = tcount - 0.1
      # time.sleep(0.1)  # enough delay from motion detect alg.


# updateTS(): update video timestamp with current time
# the optional second argument specifies a delay in seconds, meanwhile time keeps updating
def updateTS(camera, delay = 0):
    tcount = float(delay)  # remaining time as a float
    camera.annotate_text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    while tcount > 0:
      #print("%5.3f " % tcount)
      camera.annotate_text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
      tcount = tcount - 0.25
      time.sleep(0.249)

# =============================================== 

# detect_motion() is where the low-res version of the image is compared with an average of
# past images to detect motion.

def detect_motion(camera):
    global running # true if algorithm has passed through initial startup settling
    global xsize, ysize  # dimensions of pixmap for motion calculations
    global avgmap, newmap, avgdif # pixmap data arrays
    global avgmax # (scalar) running average of maximum magnitude of pixel change
    global frames  # how many frames we've examined for motion
    global gotMotion # boolean True if motion has been detected
    global tStart  # time of last event
    global lastTime # time this function was last run
    global daytime # current time of day when motion event detected
    global stsum # (matrix) rolling average sum of pixvals
    global sqsum # (matrix) rolling average sum of squared pixvals
    global stdev # (matrix) rolling average standard deviation of pixels

    stg = 30.0 # statistics (rolling standard-deviation) averaging group size (sort of)
    sti = 1.0 - (1.0/stg) # 1 - inverse of statistics groupsize
     

    # updateTS(camera)

    newmap = pixvalScaleFactor * getFrame(camera)  # current pixmap
    difmap = newmap - avgmap                       # difference pixmap (amount of per-pixel change)
    max = np.amax(difmap)			   # largest increase in brightness over average
    min = np.amin(difmap)                          # largest decrease in brightness
    pkDif = int((max - min)*100)                   # peak amplitude of change across pixmap
    avgmap = (avgmap * (1.0-frac)) + (newmap * frac)  # low-pass filter to form average pixmap
    difmap = abs(difmap)                 # take absolute value (brightness may increase or decrease)
    maxmag = np.amax(difmap)               # peak magnitude of change

# each stsum element on order of 1E6
# each sqsum element on order of  3E10
    stsum = (stsum * sti) + newmap           # rolling sum of most recent 'stg' images (approximately)
    sqsum = (sqsum * sti) + np.power(newmap, 2) # rolling sum-of-squares of 'stg' images (approx)
    devsq = (stg * sqsum) - np.power(stsum, 2)  
    stdev = (1.0/10) * np.power(devsq, 0.5)    # matrix holding rolling-average element-wise std.deviation

    avgdif = np.int32(((1 - frac)*avgdif) + (frac * 100 * difmap))  # long-term average difference
    pkAvgDif = np.amax(avgdif)           # largest value in long-term average difference
    avgmax = ((1 - frac)*avgmax) + (maxmag * frac)  # (scalar) averaged peak magnitude pixel change

    # tFactor = 2  # threshold above max.average diff per frame for motion detect

    aThresh = tFactor * avgmax  # adaptive amplitude-of-change threshold
    condition = difmap > aThresh  # boolean array of pixels exceeding threshold 'aThresh'
    changedPixels = np.extract(condition, difmap)
    countPixels = changedPixels.size

    newTime = time.time()
    elapsedTime = newTime - lastTime
    lastTime = newTime
    fps = int(1/elapsedTime)

    if (countPixels > pcThresh):  # found enough changed pixels to qualify as motion?
      gotMotion = True
      # updateTS(camera)  # flag moment of detected motion in timestamp
      # print gotMotion, frames, pkDif, fps
    else:
      gotMotion = False

    if showStatus:  # print debug info
#      print gotMotion, frames, min, max, pkDif, pkAvgDif, avgmax, countPixels, fps	
      print ("%d %f %d %f" % (gotMotion, pkDif, countPixels, fps))

    if gotMotion:
      tNow = time.time()
      tInterval = tNow - tStart
      if (tInterval > logHoldoff):  # only log when at least logHoldoff time has elapsed
        tStart = tNow
        daytime = datetime.now().strftime("%y%m%d-%H_%M_%S")
	saveFrame(camera)  # save a still image
        tstr = ("%s,  %04.1f, %6.3f, %d\n" % (daytime,maxmag,tInterval,countPixels))
        f.write(tstr)
        f.flush()

      if showStatus:
        print("********************* MOTION **********************************")
    else:
      running = True  # 'running' set True after initial filter settles and "Motion-Detect" drops

    frames = frames + 1
    if (((frames % fupdate) == 0) and debug):
        print ("%s,  %03d max = %5.3f, avg = %5.3f" % (str(datetime.now()),frames,max,avgmax))
        print ("%d %f %d %f" % (gotMotion, pkDif, countPixels, fps))
	fstr = '%04d' % (frames)  # convert integer to formatted string with leading zeros
        
	np.set_printoptions(precision=2)
	# print(sqsum) # show all elements of array 
	# print(stdev) # show all elements of array 
#        img = Image.fromarray(stsum.astype(int))
#        avgMapName = "A" + fstr + ".png"
#	img.save(avgMapName)
        img = Image.fromarray(stdev.astype(int))
        dMapName = "STD" + fstr + ".png"
	img.save(dMapName)
        # print avgdif
        # print np.int32(avgmap)

    # running = False  # DEBUG never admit to a motion detection
    if running:
      return gotMotion
    else:
      return False

# ============= Main Program ====================

with picamera.PiCamera() as camera:
    # global avgmap   # average pixelmap values

    np.set_printoptions(precision=2)
    daytime = datetime.now().strftime("%y%m%d-%H_%M_%S")
    f = open(logfile, 'a')
    f.write ("# RecSeq log v0.1 Sept. 26 2014 J.Beale\n")
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
#    for filename in camera.record_sequence( date_gen(), format='h264', resize=(1920, 720), bitrate=4000000 ):
    for filename in camera.record_sequence( date_gen(), format='h264', resize=(1280,720)):
        waitTime = 60-(time.time()%60)
        print("Recording for %d to %s" % (waitTime,filename))
        # camera.wait_recording(waitTime)
        updateTS1(camera, waitTime)
