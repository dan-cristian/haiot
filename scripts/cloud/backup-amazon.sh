#!/bin/bash
LOG=/mnt/log/backup-amazon.log

function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
echo [`date +%T.%N`] $1 $2 $3 $4 $5
}

echo2 Starting backup to amazon drive

/usr/sbin/rclone -v sync /mnt/backup remote:backup
/usr/sbin/rclone sync /mnt/media/videos remote:videos
/usr/sbin/rclone --transfers 8 sync /mnt/media/photos remote:photos
/usr/sbin/rclone sync /mnt/media/private remote:private
/usr/sbin/rclone sync /mnt/media/ebooks remote:ebooks

echo2 Completed backup to amazon drive
