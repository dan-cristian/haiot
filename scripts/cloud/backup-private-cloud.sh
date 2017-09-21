#!/bin/bash
LOG=/mnt/log/backup-private-cloud.log

function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
echo [`date +%T.%N`] $1 $2 $3 $4 $5
}


function backup(){
rsync -avrPze 'ssh -p 443' $1 haiot@www.dancristian.ro:/media/usb/$2
}

echo2 Starting backup to private cloud

backup /mnt/music/ music
backup /mnt/ebooks/ ebooks
backup /mnt/backup/ backup


#rsync -avrPze 'ssh -p 443' /mnt/ebooks/ haiot@www.dancristian.ro:/media/usb/

#/usr/sbin/rclone -v copy /mnt/backup remote:backup
#/usr/sbin/rclone copy /mnt/videos remote:videos
#/usr/sbin/rclone --transfers 8 copy /mnt/photos remote:photos
#/usr/sbin/rclone copy /mnt/private remote:private
#/usr/sbin/rclone copy /mnt/ebooks remote:ebooks

echo2 Completed backup to private cloud
