#!/bin/bash

# script to archive files from working directory into sub-directories
# J.Beale 28 December 2014

# first argument is $1, second is $2  all args: $@, arg count is $#

if [[ $# -ne 1 ]]; then
  echo "Oops: must supply file basename, such as $0 141225"
  exit 1
fi

# input must be just six digits
base=$(echo $1 | grep -Eo '[0-9]{6}')

# count number of characters in variable
chars=${#base}

if [[ $chars -ne 6 ]]; then
  echo "Oops: argument must have exactly 6 digits, like 141225"
  exit 1
fi

echo "Working on $base"
# list files of this type
#ls -al $from*.txt

# fD = source directory of files

fD="/media/sdb1"
fDE="$fD/events"
fDEN="$fDE/e$base"
fDENT="$fDEN/thumbs"
from=$fD/$base

#echo "mkdir $fD/v$base"
#echo "mkdir $fDEN"
#echo "mkdir $fDENT"
#echo "mv $from* $fD/v$base/."
#echo "mv $fDE/$base*.jpg $fDEN/."
#echo "mv $fDE/thumbs/$base*.jpg $fDENT/."

# Thumbs directory example: /media/sdb1/events/e141021/thumbs

mkdir $fD/v$base
mkdir $fDEN
mkdir $fDENT
mv $from* $fD/v$base/.
mv $fDE/$base*.jpg $fDEN/.
mv $fDE/thumbs/$base*.jpg $fDENT/.
