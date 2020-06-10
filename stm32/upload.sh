#!/bin/bash

echo Running: $0 $@

echo Waiting for device

while ! lsusb -d 1209:db42
do
  echo .
  sleep 1
done

dfu-util -D $1
