#!/usr/bin/python

# PiMotion: Detect motion with Raspberry Pi camera, and save video before and after event
# 
# Based on my motion code from http://pastebin.com/1yTxtgwz  and Dave Hughes' Picamera example
# http://picamera.readthedocs.org/en/release-1.8/recipes2.html#splitting-to-from-a-circular-stream
#
# by John Beale  Sept.25 2014


import io, picamera, datetime, time
import numpy as np

preMotionBuffer = 4 # record this many seconds before motion starts
postMotionDelay = 2 # record this many seconds after motion ends
videoDir = "/mnt/video1/" # directory to record video files
logfile = "/home/pi/logs/PiMotion_log.csv"  # where to save log of motion detections

videoFPS = 6  # record video at this frame rate
cxres = 1920 # initial vertical camera resolution
cyres = 1080 # initial horizontal camera resolution
#cxres = 1280 # initial vertical camera resolution
#cyres = 720 # initial horizontal camera resolution

# xsize and ysize are used in the internal motion algorithm, not in the video output
xsize = 32 # YUV matrix output horizontal size will be multiple of 32
ysize = 16 # YUV matrix output vertical size will be multiple of 16
mThresh = 20.0 # pixel brightness change threshold that means motion
tFactor = 1.8  # threshold above max.average diff per frame, for motion detect
pcThresh = 9  # total number of changed elements which add up to "motion"
logHoldoff = 1 # don't log another motion event until this many seconds after previous event

avgmax = 3     # long-term average of maximum-pixel-change-value
running = False  # whether we have done our initial average-settling time
pixvalScaleFactor = 99.999/255.0  # multiply single-byte values by this factor
frac = 0.1  # fraction by which to update long-term average on each pass
frames = 0 # how many frames we've looked at for motion
fupdate = 100   # report debug data every this many frames
gotMotion = False # true when motion has been detected
debug = False # should we report debug data (pixmap dump)
showStatus = True # if we should print status data every pass
showStatus = False

# initMaps(): initialize pixel maps with correct size and data type
def initMaps():
    global avgmap, newmap, difmap, avgdif, tStart
    avgmap = np.zeros((ysize,xsize),dtype=np.float32) # average background image
    newmap = np.zeros((ysize,xsize),dtype=np.float32) # new image
    difmap = np.zeros((ysize,xsize),dtype=np.float32) # difference between new & avg
    avgdif = np.zeros((ysize,xsize),dtype=np.int32) # difference between new & avg
    tStart = time.time()  # time that program starts

# getFrame(): returns Y intensity pixelmap (xsize x ysize) as np.array type
def getFrame(camera):
    stream=open('/run/shm/picamtemp.dat','w+b')
    camera.capture(stream, format='yuv', resize=(xsize,ysize), use_video_port=True)
    stream.seek(0)
    return np.fromfile(stream, dtype=np.uint8, count=xsize*ysize).reshape((ysize, xsize))

# updateTS(): update video timestamp with current time, and '*' if motion detected
# the optional second argument specifies a delay in seconds, meanwhile time keeps updating
def updateTS(camera, delay = 0):
    tcount = np.float32(delay)  # remaining time as a float
    if gotMotion:
      camera.annotate_text = datetime.datetime.now().strftime('* %Y-%m-%d %H:%M:%S *')
    else:
      camera.annotate_text = datetime.datetime.now().strftime('  %Y-%m-%d %H:%M:%S  ')
    while tcount > 0:
      # print tcount
      if gotMotion:
        camera.annotate_text = datetime.datetime.now().strftime('* %Y-%m-%d %H:%M:%S *')
      else:
        camera.annotate_text = datetime.datetime.now().strftime('  %Y-%m-%d %H:%M:%S  ')
      tcount = tcount - 0.2
      time.sleep(0.2)

# Note to self:
# yuv format is YUV420(planar). Output is horizontal mult of 32, vertical mult of 16
# http://picamera.readthedocs.org/en/release-1.8/recipes2.html#unencoded-image-capture-yuv-format
#

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
 
    updateTS(camera)

    newmap = pixvalScaleFactor * getFrame(camera)  # current pixmap
    difmap = newmap - avgmap                       # difference pixmap (amount of per-pixel change)
    max = np.amax(difmap)			   # largest increase in brightness over average
    min = np.amin(difmap)                          # largest decrease in brightness
    pkDif = int((max - min)*100)                   # peak amplitude of change across pixmap
    avgmap = (avgmap * (1.0-frac)) + (newmap * frac)  # low-pass filter to form average pixmap
    difmap = abs(difmap)                 # take absolute value (brightness may increase or decrease)
    maxmag = np.amax(difmap)               # peak magnitude of change
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
      updateTS(camera)  # flag moment of detected motion in timestamp
      # print gotMotion, frames, pkDif, fps
    else:
      gotMotion = False

    if showStatus:  # print debug info
#      print gotMotion, frames, min, max, pkDif, pkAvgDif, avgmax, countPixels, fps	
      print gotMotion, pkDif, countPixels, fps	

    if gotMotion:
      tNow = time.time()
      tInterval = tNow - tStart
      if (tInterval > logHoldoff):  # only log when at least logHoldoff time has elapsed
        tStart = tNow
        daytime = datetime.datetime.now().strftime("%y%m%d-%H_%M_%S")
        tstr = ("%s,  %04.1f, %6.3f, %d\n" % (daytime,maxmag,tInterval,countPixels))
        f.write(tstr)
        f.flush()

      if showStatus:
        print '********************* MOTION **********************************'
    else:
      running = True  # 'running' set True after initial filter settles and "Motion-Detect" drops

    frames = frames + 1
    if (((frames % fupdate) == 0) and debug):
        # print ("%s,  %03d max = %5.3f, avg = %5.3f" % (str(datetime.datetime.now()),frames,max,avgmax))
        print gotMotion, frames, pkDif, pkAvgDif, fps	
        # print avgdif
        print np.int32(avgmap)

    # running = False  # DEBUG never admit to a motion detection
    if running:
      return gotMotion
    else:
      return False

def write_video(stream):
    # Write the entire content of the circular buffer to disk. No need to
    # lock the stream here as we're definitely not writing to it
    # simultaneously
    global eventTime

    fName = videoDir + eventTime + "_0.h264"  # filename of "before-event" video from buffer
    with io.open(fName, 'wb') as output:
        for frame in stream.frames:
            if frame.frame_type == picamera.PiVideoFrameType.sps_header:
                stream.seek(frame.position)
                break
        while True:
            updateTS(camera)  # maintain video timestamp
            buf = stream.read1()
            if not buf:
                break
            output.write(buf)
    # Wipe the circular stream once we're done
    stream.seek(0)
    stream.truncate()

# ===============================================
# ============= Main Program ====================

with picamera.PiCamera() as camera:
    global avgmap   # average pixelmap values

    np.set_printoptions(precision=2)
    f = open(logfile, 'a')
    f.write ("# PiMotion log v0.2 Sept. 22 2014 J.Beale\n")
    outbuf = "# Start: " +  str(datetime.datetime.now()) + "\n"
    f.write (outbuf)
    f.flush()
    daytime = datetime.datetime.now().strftime("%y%m%d-%H_%M_%S")
    print "PiMotion starting at " + str(datetime.datetime.now())

    initMaps() # set up pixelmap arrays
    camera.resolution = (cxres, cyres)
    camera.framerate = videoFPS 
    # camera.exposure_compensation = -20   # -25 to +25, larger numbers are brighter
    camera.annotate_background = True
    camera.annotate_text = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # camera.start_preview()  # turn on camera
    # updateTS(camera, 3) # allow autoexposure to settle after initial powerup
    stream = picamera.PiCameraCircularIO(camera, seconds=preMotionBuffer) # actual buffer longer than this?
    camera.start_recording(stream, format='h264')
    # camera.stop_preview() # in case we don't want the preview cluttering up the screen
    lastTime = time.time()
    avgmap = pixvalScaleFactor * getFrame(camera)  # initialize the average pixel map to the current frame

#    for i in range(0,30000):
#       detect_motion(camera)
    while True:
#            camera.wait_recording(1)
            if detect_motion(camera):
                eventTime = datetime.datetime.now().strftime("%y%m%d-%H_%M_%S")
#                eventTime = datetime.datetime.now().strftime("%y%m%d-%H_%M_%S.%f") # need microseconds?
                print(eventTime + ' Motion detected!')
                fName =  videoDir + eventTime + "_1.h264" # filename for 'after' motion part of video
                camera.split_recording(fName) # 'after' motion H264 file
                # Write the buffered "before" motion to disk as well
                write_video(stream)
                # Wait until motion is no longer detected, then split
                # recording back to the in-memory circular buffer
                while detect_motion(camera):
		    updateTS(camera, 0.2)
                print('Motion stopped!')
		updateTS(camera, postMotionDelay) # keep recording for this long after motion ends
                camera.split_recording(stream)
    camera.stop_recording()
