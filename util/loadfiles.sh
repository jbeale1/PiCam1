#!/bin/bash
ssh rp2  "cd /home/pi/pikrellcam/media/videos && ls -1f *.mp4 " | sort > rp2.txt
echo rp2
ssh rp22 "cd /home/pi/pikrellcam/media/videos && ls -1f *.mp4 " | sort > rp22.txt
echo rp22
ssh rp23 "cd /home/pi/pikrellcam/media/videos && ls -1f *.mp4 " | sort > rp23.txt
echo rp23
ssh rp27 "cd /home/pi/pikrellcam/media/videos && ls -1f *.mp4 " | sort > rp27.txt
echo rp27
ssh rp30 "cd /home/pi/pikrellcam/media/videos && ls -1f *.mp4 " | sort > rp30.txt
echo rp30
ssh rp21 "cd /home/pi/pikrellcam/media/stills && ls -1f *.jpg " | sort > rp21.txt
echo rp21
ssh rp3 "cd /home/pi/pikrellcam/media/videos && ls -1f *.mp4 " | sort > rp3.txt
echo rp3
