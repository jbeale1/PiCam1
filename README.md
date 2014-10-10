PiMotion
========

This is a set of programs for recording video continuously from Raspberry Pi camera, and extracting
stills whenever there is motion detected.  It is intended to run using two computers.

"PiMotion.py" runs on the Pi, recording 30-second segments video as .h264 from the camera to ramdisk.
For each .h264 file, it also writes a .txt file recording the amount of motion in each frame.

"push.sh" also runs on the Pi, copying each set of .h264, .txt files to a remote host

To make the ramdisk (on a 512MB Pi) I added this line to /etc/fstab:
tmpfs           /ram            tmpfs   rw,size=128M      0       0


"proc.sh" and "batchjpeg.py" run together on the remote host, using the 'avconv' program to extract
the still frames with motion (marked out in the *.txt logfiles) and saving them as jpegs.  
Note I had to compile avconv from the current github source, the standard Debian apt-get version
does not do frame-accurate seeking, which is needed for this application.

The remote host is preferably something faster than a R-Pi. 
I am using a Acer C720 Chromebook running chrubuntu, plus external USB HDD.
This system has plenty of performance in this application.

This code is "alpha". It has only been tested on one system so far.

-J. Beale 9 October 2014
