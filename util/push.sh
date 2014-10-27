#!/bin/bash

# push oldest .h264 and .txt files in 'fDir' directory to remote host

# flim = number of files in directory, when exceeded, causes a file to be moved
flim=1

# fDir = local directory, source of files
fDir="/ram/"

# toDir = directory on remote host, destination of files
toDir="/media/sdb1/"

while [ 1 ]; do
  fnum=$(ls /ram/*.h264 | wc -l)
  if [ "$fnum" -gt "$flim" ]; then
    sleep 4
    oldFileFull=$(ls -rt "$fDir"*.h264 | head -1)
    # oldFileFull = [full pathname of oldest file]
    oldFile="${oldFileFull##*/}"
    fBase="${oldFile%.*}"
    fLog="$fBase.txt"
    # echo "files = $fnum  So, should move $fDir$oldFile and $fDir$fLog to $toDir"
    nice -n 20 scp -c blowfish "$fDir$oldFile" pi@192.168.1.56:\""$toDir$oldFile"\"
    nice -n 20 scp -c blowfish "$fDir$fLog" pi@192.168.1.56:\""$toDir$fLog"\"
    rm "$fDir$oldFile"
    rm "$fDir$fLog" 
  fi  
  sleep 1
done
