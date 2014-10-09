#!/bin/bash

# batch-convert .h264 format files into .mp4 files using MP4Box
# by J.Beale 8-Oct-20
# do not process files younger than 'alimit', they might still be open / being transferred
alimit=120

# nominal frame rate of video
FPS=8

# minimum amount that mp4 file size of this length should be greater than raw .h264
mp4add=1900

while [ 1 ]; do
 for fname in $( ls *.h264 ); do
  mtime="$(stat -c %Y $fname)"
  now=$(date +"%s")
  age="$(($now - $mtime))"
  if [ $age -gt $alimit ]; then
     fbase="${fname%.*}"
     echo "writing $fbase.mp4"
     fmp4="$fbase.mp4"
     nice -n 20 MP4Box -fps $FPS -add $fname $fmp4
     mp4size="$(stat -c %s $fmp4)"
     h264size="$(stat -c %s $fname)"
     diff="$(($mp4size - $h264size))"
     if [ $diff -gt $mp4add ]; then
	echo "$fmp4 OK"
	rm -f $fname
     fi
  fi
 done
 sleep 15
done
