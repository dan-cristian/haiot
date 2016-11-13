#!/bin/bash

DATE=`date +%Y%m%d-%H%M%S`
HOST=`cat /etc/hostname`
BACKUP_DIR=/mnt/backup
FILE_BACKUP=$BACKUP_DIR/$HOST-Backup$DATE.tar.gz

echo backing up $FILE_BACKUP
sleep 5

tar -pczf $FILE_BACKUP /  --exclude-from=/home/haiot/PYC/scripts/cloud/backup-exclude.txt -v
chmod 666 $FILE_BACKUP

