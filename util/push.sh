#!/bin/bash

# Continually push oldest .h264 and .txt files in 'fDir' directory to remote host
# delete files locally after sending

# flim = number of files in directory, when exceeded, causes a file to be moved
flim=2

# fDir = local directory, source of files
fDir="/ram/"

# toDir = directory on remote host, destination of files
toDir="/media/sdb1/"

# user and name of remote host
# must change this to match your setup, like "pi@192.168.10.50"
host="pi@192.168.1.56"


while [ 1 ]; do
  fnum=$(ls /ram/*.h264 | wc -l)
  if [ "$fnum" -gt "$flim" ]; then
    oldFileFull=$(ls -rt "$fDir"*.h264 | head -1)
    # oldFileFull = [full pathname of oldest file]
    oldFile="${oldFileFull##*/}"
    fBase="${oldFile%.*}"
    fLog="$fBase.txt"
    echo "files = $fnum  So, should move $fDir$oldFile and $fDir$fLog to $toDir"
    nice -n 20 scp -c blowfish "$fDir$oldFile" "$host":\""$toDir$oldFile"\"
    nice -n 20 scp -c blowfish "$fDir$fLog" "$host":\""$toDir$fLog"\"
    rm "$fDir$oldFile"
    rm "$fDir$fLog" 
  fi  
  sleep 1
done
