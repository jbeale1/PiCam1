#!/usr/bin/python

# Read a set of text files. Each file is a video directory list from a "PiKrellCam"
# and is a single column of file names, such as "motion_2015-12-20_11.10.58_1061.mp4"

# Group together items starting within 'eventGap' seconds of each other and
# consider those as relating to the same event
# For each such 'event', generate a list of which RPi cameras saw that event

# 21 DEC 2015  J.Beale

in1 = 18  # character string element with first digit of 'hours'
eventGap = 8  # seconds between separate events
camThresh = 3 # how many cameras must detect a valid event

# list of data files from different RPi camera devices
fnames = ["rp22.txt", "rp2.txt", "rp30.txt", "rp23.txt", "rp27.txt", "rp21.txt", "rp3.txt"]
events = []     # empty list to hold event data tuples

 # returns a fixed-format version of a list of items from 0..n
def pPrint ( list ):
  s = "" # empty string
  # print (list)
  for x in range(len(fnames)):
    if x in list:
     s = s[:x] + str(x) + s[x:]  # replace xth char in string
    else:
     s = s[:x] + " " + s[x:]
    # print (s)
  return s

def readFile( fi, fn, eList ):
 with open(fn, "rw+") as fp:  # close file when done
  for l in fp:
    line = l.strip()            # remove leading and trailing whitespace
    hh = line[in1:in1+2]        # hour digits
    mm = line[in1+3:in1+5]      # minute digits
    ss = line[in1+6:in1+8]      # minute digits
    sec = (3600 * int(hh)) + (60 * int(mm)) + int(ss)  # seconds past midnight
    eList.append( (fi, fn, line, sec) )
    # print("%s %s %s %s %s") % (fi, hh,mm,ss,sec)

# =========================================================================


for fname in fnames:
  print (fname[:-4])
  fidx = fnames.index(fname)  # list index of this particular name
  readFile( fidx, fname, events )

sList = sorted(events, key=lambda x: x[3])  # generate a sorted list
tLast = 0  # second index of previous event in storted list
startTime = -1  # reset event start time
eventCount = 0 # how many overall events
gList = []  # initialize grouped event list to nul
tList = []  # temporary list of cameras seeing this event

for e in sList:  # do this for each separate event detect
  tNow = e[3]  # time index (seconds) of this event

  newEvent = False
  if ((int(tNow) - int(tLast)) > eventGap):
    newEvent = True  # just detected a new event

  if ( e[0] in tList ):  # has this camera already seen this event?
    newEvent = True  # if so, this is something new

  if (newEvent):       # current item is start of new event
    if ( eventCount != 0 ): # if not 1st one, save the previous event
      gList.append( (eventCount, startTime, tList, efCam, efName) )
    eventCount += 1
    startTime = tNow  # remember start time of new event
    # print ( startTime )
    efCam = e[1]       # camera name of this record
    efName = e[2]      # filename of this particular camera record
    # print(" ")   # line break between events when time > eventGap
    tList = []   # clear out list of cameras active on this event

  tList.append( e[0] )  # add this camera number to those seeing this event

  # print (e)
  tLast = tNow

if ( eventCount != 0 ):
      gList.append( (eventCount, startTime, tList, efCam, efName) ) # save the previous event

print " =================================== "
print
count = 0  # count of "signficant" events
for g in gList:  # iterate over grouped event detects
  cams = len(g[2])  # how many cameras captured this event?
  if (2 in g[2]):    cam2 = True
  else:    cam2 = False
  s1 = pPrint( g[2])
  cam2 = False  # DEBUG force print
  if (cams >= camThresh) and (cam2 == False):
    count += 1
    print "%4s [%s]  %4s  %s" % (count, s1, g[3][:-4], g[4])
