#!/bin/bash
# batch-convert .h264 format files in a directory into .mp4 files using MP4Box
# by J.Beale 21-Jan-2015

# working directory for .h264 -> .mp4 conversion
basedir="/var/www/media"

# nominal frame rate of video
FPS=25

# do not process files younger than 'alimit' seconds
alimit=5

# how many seconds between checking for new file
looptime=2

# how many seconds before checking if filesize has changed
testtime=6

# minimum increase in # bytes that mp4 file should be over raw .h264 file
# (simple test for conversion error => file corruption)
mp4add=500

cd $basedir

while [ 1 ]; do
 sleep $looptime
 if test -n "$(find $basedir -maxdepth 1 -name '*.h264' -print -quit)"; then
  for fname in $( ls *.h264 ); do
   mtime="$(stat -c %Y $fname)"
   fsize1="$(stat -c %s $fname)"
   now=$(date +"%s")
   age="$(($now - $mtime))"
   sleep $testtime
   fsize2="$(stat -c %s $fname)"  # if file still being written, size changes
   if [ $age -gt $alimit ] && [ $fsize1 -eq $fsize2 ]; then
      fbase="${fname%.*}"
      echo "writing $fbase.mp4"
      fmp4="$fbase.mp4"
      nice -n 20 MP4Box -fps $FPS -add $fname $fmp4
      mp4size="$(stat -c %s $fmp4)"
      h264size="$(stat -c %s $fname)"
      diff="$(($mp4size - $h264size))"
      if [ $diff -gt $mp4add ]; then # does file size look OK?
         echo "$fmp4 OK"
         rm -f $fname
      else
         echo "$fmp4 size diff: $diff"  # got a problem here, save it for later
         mv -f $fname $fname.corrupt
      fi
   fi
  done
 fi
done
