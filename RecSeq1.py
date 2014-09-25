#!/usr/bin/python

# Record a set of time-stamped video files from RPi camera
# each file is one minute long, and named with the date & time
# J.Beale  24 Sept 2014

from __future__ import print_function
from datetime import datetime, time
from time import sleep
import picamera

def date_gen():
  while True:
    dstr = "/var/www/pics/a" + datetime.now().strftime("%y%m%d_%H%M%S") + ".h264"
    yield dstr

# updateTS(): update video timestamp with current time
# the optional second argument specifies a delay in seconds, meanwhile time keeps updating
def updateTS(camera, delay = 0):
    tcount = float(delay)  # remaining time as a float
    camera.annotate_text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    while tcount > 0:
      #print("%5.3f " % tcount)
      camera.annotate_text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
      tcount = tcount - 0.25
      sleep(0.249)


zx = 0.0  # normalized horizontal image offset
#zy = 0.5 # normalized vertical image offset (0 = top of frame)
zy = 0.0 # normalized vertical image offset (0 = top of frame)
zw = 1.0 # normalized horizontal scale factor (1.0 = full size)
zh = 0.5 # normalized vertical scale factor (1.0 = full size)

with picamera.PiCamera() as camera:
    #camera.resolution = (1920, 1080)  # sensor res = 2592 x 1944
    camera.resolution = camera.MAX_RESOLUTION
    camera.framerate = 3  # how many frames per second to record
    camera.annotate_background = True # black rectangle behind white text for readibility
    camera.zoom = (zx, zy, zw, zh) # set image offset and scale factor (default 0,0,1,1 )
    camera.exposure_mode = 'night'
#    for filename in camera.record_sequence( date_gen(), format='h264', resize=(1920, 720), bitrate=4000000 ):
    for filename in camera.record_sequence( date_gen(), format='h264', resize=(1920, 720)):
        utcnow = datetime.utcnow()
        midnight_utc = datetime.combine(utcnow.date(), time(0))
        delta = datetime.utcnow() - midnight_utc
        ts = delta.total_seconds()  # seconds since midnight (Python 2.7)
        waitTime = 60.0 - (ts % 60)
        # print("Recording for %d to %s" % (waitTime,filename))
        # camera.wait_recording(waitTime)
        updateTS(camera, waitTime)
