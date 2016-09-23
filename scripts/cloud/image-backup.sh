#!/bin/bash

DATE=`date +%Y%m%d-%H%M%S`
HOST=`cat /etc/hostname`
BACKUP_DIR=/mnt/backup
FILE_BACKUP=$BACKUP_DIR/$HOST-BackupImage$DATE.img.gz
echo backing up image $FILE_BACKUP
sleep 5
dd if=/dev/sdd conv=sync,noerror bs=512K | gzip -c > $FILE_BACKUP
chmod 666 $FILE_BACKUP
