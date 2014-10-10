#!/usr/bin/python

# Batch-convert video frames with motion, to JPEG
# works through all '123456_xxxxxx.txt' type files in directory)

# Read CSV type text file describing motion in video frames
# use 'avconv' to extract high-motion frames as JPEG stills
# from corresponding .mp4 file
# J.Beale 10-October-2014

from __future__ import print_function
import csv, os, sys, time
from subprocess import call  # execute commands in OS shell

picDir = "./events/" # where to save JPEG still frames
pThresh = 120 # pixel-count threshold for review
aThresh = 1200 # average-novel-value threshold for review

# ==================================================
def saveFile(fin,fout,otime):
  fout = picDir + fout # add output directory to filename
  if os.path.isfile(fout): # check if we've already saved it previously
    print("%s already exists" % fout)
  else:
    print("saving to: %s" % fout)  
#    time.sleep(4)
    call(["avconv","-ss",otime,"-i",fin,"-frames:v","1","-q:v","2",fout])
#    time.sleep(4)

# -----------------------------------------------------

# scan '123456_*.txt' input filenames and extract JPEGs from same-basename .mp4 file
def scanFiles(fname):
  if fname.endswith(".txt") and fname[0:6].isdigit():
    print("file: %s" % fname)
    vidfile = fname[:-3] + "mp4" # construct video filename from index file
    with open(fname, 'rb') as csvfile:
      freader = csv.reader(csvfile, delimiter=',', quotechar='"')
      for row in freader:
        try:
          v1 = int(row[0])
          sec = float(row[1])
          avg = float(row[2])
          if (v1 > pThresh) and (avg > aThresh):
            spos = "+%05.2f" % sec
            fout = fname[:-4] + spos + ".jpg"
	    timestr = "%5.3f" % sec
            saveFile(vidfile,fout,timestr) # extract still from this frame
        except ValueError:
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

