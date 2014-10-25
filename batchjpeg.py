#!/usr/bin/python

# Batch-convert video frames with motion, to JPEG
# works through all '123456_xxxxxx.txt' type files in directory)

# Read CSV type text file describing motion in video frames
# use 'avconv' to extract high-motion frames as JPEG stills
# from corresponding .mp4 file
# Generate log file describing motion events
# 
# 11-Oct-14: Change pThresh,aThresh to extract smaller events
# 18-Oct-14: Ignore motion below a lower boundary, and below a certain L-R (x) speed
#
# J.Beale 20-October-2014

from __future__ import print_function
import csv, os, sys, time
import numpy as np  # linear fit
from subprocess import call  # execute commands in OS shell

picDir = "./events/" # where to save extracted JPEG still frames
logFileName = "./logs/eLog.csv" # event log file to append to

pThresh = 12 # pixel-count threshold for review
aThresh = 500 # average-novel-value threshold for review

xScale = 1920.0 / 96.0  # scale up X by this
yScale = 1080.0 / 32.0  # scale up Y by this
xEdge = 200 # expand motion area border by this many pixels
yEdge = 150

# ==================================================

# -----------------------------------------------------
# save still frame JPEG extracted from MP4 video
def saveJPEG(fin,fout,otime):
  fout = picDir + fout # add output directory to filename
  if not os.path.isfile(fout): # check if we've already saved it previously
#    print("%s already exists" % fout)
#  else:
    print("saving to: %s" % fout)  
    call(["avconv","-ss",otime,"-i",fin,"-frames:v","1","-q:v","2",fout])

# -----------------------------------------------------
# save a cropped version showing only the motion area
def saveCrop(fname,geom):
  fin = picDir + fname
  fout = picDir + "thumbs/" + fname  # output file directory
  if not os.path.isfile(fout): # check if we've already saved it previously
#    print("%s already exists" % fout)
#  else:
    print("saving detail to: %s" % fout)  
    call(["convert","-crop",geom,"-resize","300x200",fin,fout])

# -----------------------------------------------------
# Save data for an event
def saveEvent():
  global eventNow # true when this line part of an event
  global xVec,yVec # x,y matrices for linear fit
  global avgY # average Y position of event motion center

  duration = sec - tStart  # how many seconds long this event was
  if (eFrame > 0):
    avgLength = sumLength / eFrame
    avgY = sumY / eFrame
  else:
    avgLength = 0
    avgY = 0

  if (eFrame > 1):
    xVec = xVec[0:(eFrame-1)]
    yVec = yVec[0:(eFrame-1)]
    (slope,offset),fit,c,d,e = np.polyfit(xVec,yVec,1,full=True)
  else:
    slope = 0

  try:
    fit0 = fit[0]
  except:
    fit0 = 0

  if (avgLength > 0):
    print("%s, %5.1f sec, %5.1f px, %4.1f Y, %5.1f slope (%4.2f), %d frames" % \
      (dStart, duration, avgLength, avgY, slope, fit0, eFrame))
    log.write("%s, %6.1f, %6.1f, %5.1f, %6.1f, %6.1f, %4d\n" % \
      (dStart, duration, avgLength, avgY, slope, fit0, eFrame))
  eventNow = False
  xVec = np.zeros(120,dtype=np.float32)
  yVec = np.zeros(120,dtype=np.float32)
  
# -----------------------------------------------------
# process one row in file
def doRow(row):
  global xcentOld # previous frame motion coordinate
  global eventNow # true when this line part of an event
  global tOld # previous time offset
  global tStart # start time of current event
  global dStart # start date/time of current event
  global eFrame # frame number from start of this event
  global sec # seconds offset of current row
  global sumLength # sum of x size of motion
  global xVec  # x,y matrices for linear fit
  global yVec
  global sumY # sum of Y locations of event motion center

  try:
    pxls = int(row[0])  # how many motion pixels detected
    sec = float(row[1])
    avg = float(row[2])
    xcent = float(row[4])  # x,y center of motion
    ycent = float(row[5])
    dX = xcent - xcentOld
    deltaT = sec - tOld  # time difference between this line and previous one
    if (eventNow) and ((deltaT > 1.0) or (pxls == 0)):  # end of event
      saveEvent()

    if (not eventNow) and (pxls >= pThresh):  # start of an event?
      tStart = sec
      eFrame = -1   # this will be the first frame
      sumLength = 0 # no length yet
      sumY = 0 # no Y sum yet
      eventNow = True
      try:
	dStart = row[13]
      except:
        dStart = row[12]

    if (eventNow) and (pxls >= pThresh):  # this frame is in event, and has valid pixel count
      eFrame = eFrame + 1
      sumLength = sumLength + (float(row[9]) - float(row[7]))
      sumY = sumY + ycent
      xVec[eFrame] = float(row[1]) # time in seconds (offset from t=0 of 30)
      yVec[eFrame] = float(row[4]) # horiz. center position in pixels, 0..96

    # upper-left corner of motion box
    x1 = int(xScale * float(row[7]))-xEdge
    y1 = int(yScale * float(row[8]))-yEdge
    # lower-right corner of motion box
    x2 = int(xScale * float(row[9]))+xEdge
    y2 = int(yScale * float(row[10]))+yEdge
    x1 = max(x1,0) # clamp values to image border
    y1 = max(y1,0)
    x2 = min(x2,1919)
    y2 = min(y2,1079)

    xsize = (x2 - x1)   # width of bounding box
    ysize = (y2 - y1)   # height of bounding box
    geom = "%dx%d+%d+%d" % (xsize, ysize, x1, y1)
 #   print("%s" % geom) # DEBUG check x,y size

    sec = sec - 0.25;  # correct lag from motion detection
    sec = max(sec, 0)  # make sure it's not negative 
    if sec > 30.0:
      sec = sec - 30.0  # bugfix, should not ever happen
    tOld = sec   # remember this time offset for next line
    if (pxls > pThresh) and (avg > aThresh) and (abs(dX) > 6) and (float(row[8]) < 20):
      spos = "+%05.2f" % sec
      fout = fname[:-4] + spos + ".jpg"
      timestr = "%5.3f" % sec
      saveJPEG(vidfile,fout,timestr) # extract still from this frame
      saveCrop(fout,geom) # extract motion region from still
      xcentOld = xcent # remember this xcenter for next time
  except:
    pxls = 0

# -----------------------------------------------------
# test if name looks like '123456_*.txt' if os, extract JPEGs from same-basename .mp4 file
def scanFiles(fname):
  global xcentOld # previous frame motion coordinate
  global vidfile # name of video file
  global eventNow # true when this line part of an event
  global tOld # previous time offset
  global tStart # start time of current event
  global dStart # start date/time of current event
  global eFrame # frame number from start of this event
  global xVec  # x,y matrices for linear fit
  global yVec

  eventNow = False # not yet found an event
  tOld = -2 # force previous time offset to be invalid
  tStart = 0 # actually, should not be needed
  eFrame = 0 # not needed?
  xVec = np.zeros(120,dtype=np.float32)
  yVec = np.zeros(120,dtype=np.float32)

  dStart = " " # should not be needed
  if fname.endswith(".txt") and fname[0:6].isdigit():
#    print("file: %s" % fname)
    vidfile = fname[:-3] + "mp4" # construct video filename from index file
    with open(fname, 'rb') as csvfile:
      freader = csv.reader(csvfile, delimiter=',', quotechar='"')
      xcentOld = -2 # previous frame motion coordinate
      for row in freader:
        doRow(row) # process data in this row
      if (eventNow):  # if event was still open, this is the end of it
        saveEvent()

# -----------------------------------------------------
# == MAIN program here ==
# -----------------------------------------------------
global fname # name of input text file

# how many arguments passed
argCnt = len(sys.argv)

log = open(logFileName, 'a')       # open logfile
 
# Print it
if (argCnt > 1):  # work on only specified .txt file
  fname = str(sys.argv[1])
  print ("Working on %s" % fname)
  scanFiles(fname)
else:  # scan all .txt files in current directory
  workDir = os.getcwd()
  print("No arguments given, working in %s" % workDir)
  for fname in sorted(os.listdir(workDir)):
    scanFiles(fname)

log.close()  # close log file when finished
# ===========================================================
