#!/bin/bash
while [ 1 ]; do
  echo `date` "," `/home/pi/get-temp`
  sleep 300
done
