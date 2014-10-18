#!/usr/bin/python

# Batch-convert video frames with motion, to JPEG
# works through all '123456_xxxxxx.txt' type files in directory)

# Read CSV type text file describing motion in video frames
# use 'avconv' to extract high-motion frames as JPEG stills
# from corresponding .mp4 file
# 
# 11-Oct-14: Change pThresh,aThresh to extract smaller events
# 18-Oct-14: Ignore motion below a lower boundary, and below a certain L-R (x) speed
#
# J.Beale 18-October-2014

from __future__ import print_function
import csv, os, sys, time
from subprocess import call  # execute commands in OS shell

picDir = "./events/" # where to save JPEG still frames
pThresh = 12 # pixel-count threshold for review
aThresh = 500 # average-novel-value threshold for review

xScale = 1920.0 / 96.0  # scale up X by this
yScale = 1080.0 / 32.0  # scale up Y by this
xEdge = 200 # expand motion area border by this many pixels
yEdge = 150
# ==================================================
# save still frame JPEG extracted from MP4 video
def saveFile(fin,fout,otime):
  fout = picDir + fout # add output directory to filename
  if os.path.isfile(fout): # check if we've already saved it previously
    print("%s already exists" % fout)
  else:
    print("saving to: %s" % fout)  
    call(["avconv","-ss",otime,"-i",fin,"-frames:v","1","-q:v","2",fout])

# -----------------------------------------------------
# save a cropped version showing only the motion area
def saveCrop(fname,geom):
  fin = picDir + fname
  fout = picDir + "thumbs/" + fname  # output file directory
  if os.path.isfile(fout): # check if we've already saved it previously
    print("%s already exists" % fout)
  else:
    print("saving detail to: %s" % fout)  
    call(["convert","-crop",geom,"-resize","300x200",fin,fout])
  

# -----------------------------------------------------

# scan '123456_*.txt' input filenames and extract JPEGs from same-basename .mp4 file
def scanFiles(fname):
  if fname.endswith(".txt") and fname[0:6].isdigit():
    print("file: %s" % fname)
    vidfile = fname[:-3] + "mp4" # construct video filename from index file
    with open(fname, 'rb') as csvfile:
      freader = csv.reader(csvfile, delimiter=',', quotechar='"')
      xcentOld = -2 # previous frame motion coordinate
      for row in freader:
        try:
          v1 = int(row[0])
          sec = float(row[1])
          avg = float(row[2])
          xcent = float(row[4])  # x,y center of motion
          ycent = float(row[5])
          dX = xcent - xcentOld
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
          print("%s" % geom) # DEBUG check x,y size

	  sec = sec - 0.25;  # correct lag from motion detection
	  if (sec < 0):
            sec = 0
          if sec > 30.0:
            sec = sec - 30.0  # bugfix, should not ever happen
          if (v1 > pThresh) and (avg > aThresh) and (abs(dX) > 6) and (float(row[8]) < 20):
            spos = "+%05.2f" % sec
            fout = fname[:-4] + spos + ".jpg"
	    timestr = "%5.3f" % sec
            saveFile(vidfile,fout,timestr) # extract still from this frame
	    saveCrop(fout,geom) # extract motion region from still
            xcentOld = xcent # remember this xcenter for next time
        except:
	  v1 = 0

# -----------------------------------------------------

# -----------------------------------------------------
# == MAIN program here ==


# how many arguments passed
argCnt = len(sys.argv)
# Get the arguments list 
 
# Print it
if (argCnt > 1):  # work on only specified .txt file
  fname = str(sys.argv[1])
  print ("Working on %s" % fname)
  scanFiles(fname)
else:  # scan all .txt files in current directory
  workDir = os.getcwd()
  print("No arguments given, working in %s" % workDir)
  for fname in os.listdir(workDir):
    scanFiles(fname)

# ===========================================================

