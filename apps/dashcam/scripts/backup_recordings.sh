#!/bin/bash
LOG=/home/haiot/log/backup-recordings.log
#HOST_DEST=192.168.0.18
HOST_DEST=www.dancristian.ro

function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
echo [`date +%T.%N`] $1 $2 $3 $4 $5
}


function backup(){
rsync -avrPe 'ssh -p 222 -T -c arcfour -o Compression=no -x ' $1 haiot@$HOST_DEST:/media/usb/$2
}

echo2 "Starting backup to private cloud"
mkdir -p /home/haiot/log

backup /home/haiot/recordings dashcam

echo2 "Completed backup to private cloud"
