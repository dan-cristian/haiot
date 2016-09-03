#!/bin/bash
LOG=/mnt/log/backup-amazon.log

function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
echo [`date +%T.%N`] $1 $2 $3 $4 $5
}

echo2 Starting backup to amazon drive

rclone -v sync /mnt/backup remote:backup
rclone  sync /mnt/videos remote:videos
rclone  sync /mnt/photos remote:photos
rclone  sync /mnt/private remote:private
rclone  sync /mnt/media/ebooks remote:ebooks

echo2 Completed backup to amazon drive
