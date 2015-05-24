#!/usr/bin/python

# Remove name.mp4 & name.txt file pair when .txt file has 0 filesize
# works through all '123456_xxxxxx.txt' type files in directory)
# J.Beale 2-Nov-2014

from __future__ import print_function
import csv, os, sys, time
import numpy as np  # linear fit
from subprocess import call  # execute commands in OS shell


# ==================================================

# -----------------------------------------------------
# test if name looks like '123456_*.txt' if os, extract JPEGs from same-basename .mp4 file
def scanFiles(workDir, fname):

  if fname.endswith(".txt") and fname[0:6].isdigit():
    ffname = workDir + fname
    fsize = os.path.getsize(ffname)
    vidfile = workDir + fname[:-3] + "mp4" # construct video filename from index file
    if (fsize == 0):
      # delete fname, vidfile
      # print("   remove %s and %s" % (ffname, vidfile))
      os.remove(ffname)
      os.remove(vidfile)
#    else:
#      print("file: %s size: %d" % (ffname,fsize), end="")

# -----------------------------------------------------
# == MAIN program here ==
# -----------------------------------------------------
global fname # name of input text file

# how many arguments passed
argCnt = len(sys.argv)

# Print it
if (argCnt > 1):  # work in specified directory
  workDir = str(sys.argv[1])
  print ("Working in %s" % workDir)
else:  # work in current directory
  workDir = os.getcwd()
  print("No arguments given, working in %s" % workDir)

for fname in sorted(os.listdir(workDir)):
  scanFiles(workDir,fname)

# ===========================================================
