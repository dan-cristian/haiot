#!/bin/bash
LOG=/mnt/log/backup-private-cloud.log
source /home/haiot/PYC/.credentials/.general.credentials

function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
echo [`date +%T.%N`] $1 $2 $3 $4 $5
}

function backup(){
# rsync -avrPe 'ssh -p 222 -T -c aes128-cbc -o Compression=no -x ' $1 haiot@$HOST_DEST:/media/usb/$2
rsync -avrPe 'ssh -T -p '${HAIOT_SSH_PORT}' -c '${HAIOT_SSH_CIPHER}' -o Compression=no -x' $1 ${HAIOT_SSH_SERVER}:/mnt/sdd1/$2 >> $LOG 2>&1
}

echo2 'Starting backup to private cloud '${HAIOT_SSH_SERVER}' '${HAIOT_SSH_PORT}' '${HAIOT_SSH_CIPHER}

backup /mnt/backup/ backup
backup /mnt/photos/ photos
backup /mnt/videos/ videos
backup /mnt/private/ private
backup /mnt/music/ music
backup /mnt/ebooks/ ebooks

echo2 Completed backup to private cloud
