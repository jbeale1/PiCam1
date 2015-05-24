#!/usr/bin/python

# houskeeping script to remove no-motion video segments older than LAG1 days
# and all video segments older than LAG2 days

from __future__ import print_function
from subprocess import call
import time

eventpre = "/media/sdb1/events/e" # start of JPEG img directory
dirpre = "/media/sdb1/v"  # start of video directory to operate on
cleanb = "/home/john/dev/PiCam1/util/cleanblank.py"  # location of video thinning script

LAG1 = 9  # how many days of full video records to keep
LAG2 = 40 # how many days of any video records to keep
LAGEVENT = 110 # how many days of still frames to keep

def t2(days):

    SECDAY = 60*60*24 # seconds in one day (normally anyway)

    nowTime = time.time()  # current time in seconds since Jan 1 1970
    nowDate = time.strftime("%y%m%d", time.localtime(nowTime))
    oldDate = time.strftime("%y%m%d", time.localtime(nowTime-(SECDAY*days)))
    print(" %s " % oldDate)
    return oldDate
    

print("Thin out video: ", end="")    
day1 = t2(LAG1)
# print("%s days ago was %s" % (LAG1,day1))
cleanpath = dirpre + day1 + "/"  # full pathname of directory to thin out
call([cleanb,cleanpath]) # clean out video files without detected motion

print("Remove video: ", end="")    
day2 = t2(LAG2)
# print("%s days ago was %s" % (LAG2,day2))
deldir = dirpre + day2 + "/"  # full pathname of directory to delete
call(["rm","-rf",deldir]) # remove directory with all contents

# LAGEVENT and eventpre
print("Remove stills: ", end="")    
day3 = t2(LAGEVENT)
# print("%s days ago was %s" % (LAGEVENT,day3))
del2dir = eventpre + day3 + "/"  # full pathname of directory to delete
call(["rm","-rf",del2dir]) # remove directory with all contents

# print("rm -rf %s" % del2dir) # show command as it would be called

# ---------

