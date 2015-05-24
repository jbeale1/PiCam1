#!/usr/bin/python

from __future__ import print_function
from subprocess import call
import time

arcmd = "/media/sdb1/arch1.sh"   # location of shell script to do archiving

def t1():

    SECDAY = 60*60*24 # seconds in one day (normally anyway)

    nowTime = time.time()  # current time in seconds since Jan 1 1970
    nowDate = time.strftime("%y%m%d", time.localtime(nowTime))
    yestDate = time.strftime("%y%m%d", time.localtime(nowTime-SECDAY))
    # print("Today: %s  Yesterday: %s " %(nowDate,yestDate))
    return yestDate
    
    
yesterday = t1()
print("Yesterday was %s" % yesterday)  # print yesterdays date in the form YYMMDD
call([arcmd,yesterday])  # call shell script to execute archiving process for yesterday's files

# ---------

