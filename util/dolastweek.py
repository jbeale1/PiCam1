#!/usr/bin/python

# houskeeping script to remove no-motion video segments older than LAG1 days
# and all video segments older than LAG2 days

from __future__ import print_function
from subprocess import call
import time

dirpre = "/media/sdb1/v"  # start of full directory to operate on
cleanb = "/home/john/dev/PiCam1/util/cleanblank.py"  # location of video thinning script

LAG1 = 10  # how many days of full video records to keep
LAG2 = 52 # how many days of any video records to keep

def t2(days):

    SECDAY = 60*60*24 # seconds in one day (normally anyway)

    nowTime = time.time()  # current time in seconds since Jan 1 1970
    nowDate = time.strftime("%y%m%d", time.localtime(nowTime))
    oldDate = time.strftime("%y%m%d", time.localtime(nowTime-(SECDAY*days)))
    print("Today: %s  Old Day: %s " %(nowDate,oldDate))
    return oldDate
    
    
day1 = t2(LAG1)
# print("%s days ago was %s" % (LAG1,day1))
cleanpath = dirpre + day1 + "/"  # full pathname of directory to thin out

day2 = t2(LAG2)
# print("%s days ago was %s" % (LAG2,day2))
deldir = dirpre + day2 + "/"  # full pathname of directory to delete

# print("rm -rf %s" % deldir) # command to remove directory & all contents
# print("%s %s" % (cleanb, cleanpath)) # command to remove directory & all contents

call(["rm","-rf",deldir]) # remove directory with all contents
call([cleanb,cleanpath]) # clean out video files without detected motion

# ---------

