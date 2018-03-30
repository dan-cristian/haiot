#!/bin/bash
LOG=/mnt/log/backup-private-cloud.log
HOST_DEST=192.168.0.18
#HOST_DEST=www.dancristian.ro

function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
echo [`date +%T.%N`] $1 $2 $3 $4 $5
}


function backup(){
rsync -avrPe 'ssh -p 222 -T -c aes128-cbc -o Compression=no -x ' $1 haiot@$HOST_DEST:/media/usb/$2
}

echo2 Starting backup to private cloud

backup /mnt/backup/ backup
backup /mnt/photos/ photos
backup /mnt/videos/ videos
backup /mnt/private/ private
backup /mnt/music/ music
backup /mnt/ebooks/ ebooks


#rsync -avrPze 'ssh -p 443' /mnt/ebooks/ haiot@www.dancristian.ro:/media/usb/
#/usr/sbin/rclone -v copy /mnt/backup remote:backup
#/usr/sbin/rclone copy /mnt/videos remote:videos
#/usr/sbin/rclone --transfers 8 copy /mnt/photos remote:photos
#/usr/sbin/rclone copy /mnt/private remote:private
#/usr/sbin/rclone copy /mnt/ebooks remote:ebooks

echo2 Completed backup to private cloud
