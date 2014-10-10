PiMotion
========

This is a set of programs for recording video continuously from Raspberry Pi camera, and extracting
stills whenever there is motion detected.  It is intended to run using two computers on the same LAN.

"PiMotion.py" runs on the Pi, recording 30-second segments of 1080p 8 fps video as .h264 from the camera to ramdisk.
For each .h264 file, it also writes a .txt file recording the amount of motion detected every 2 frames (1/4 sec).

Separately, the shell script "push.sh" also runs on the Pi, copying each set of .h264 and .txt files on the ramdisc
over ethernet to a remote host, then deleting them to make room for more files. Doing this on the SD memory card 
would be a little slower, and also eventually wear out the flash due to the amount data flushed through over time.
This is running about 1 MB/sec on average, which is 86 GB per day (actually less in practice, during the night the
camera bitrate drops).

To make the 128MB ramdisk (on a 512MB Pi) I added this line to /etc/fstab:
'tmpfs           /ram            tmpfs   rw,size=128M      0       0'


"proc.sh" and "batchjpeg.py" run together on the remote host, converting the raw .h264 files to .mp4
with MP4Box, and then using the 'avconv' program to extract
the still frames with motion (marked out in the *.txt logfiles) and saving them as jpegs.  
MP4Box is easily installed by 'sudo apt-get install gpac' on any Debian-based system, but I had to 
compile avconv from the current github source, the standard apt-get version
does not do frame-accurate seeking, which is needed for this application.

The remote host is preferably something faster than a R-Pi. 
I am using a Acer C720 Chromebook running chrubuntu, plus external USB HDD and TU2-ET100 (Asix AX88772) 
USB-Ethernet adaptor. This system has plenty of performance in this application.

I originally tried this with the Pi simply writing to a remote folder via NFS, but that was not reliable.
It may have been delays or buffering issues through the NFS system but the PiMotion video writer would frequently lock up.
Writing from the camera to the ramdisk, where a separate process reads them off, works more reliably.

This code is "alpha". It has only been tested in one configuration on one system so far.  
If you install it, you will need to configure the code to suit your setup.

-J. Beale 9 October 2014
