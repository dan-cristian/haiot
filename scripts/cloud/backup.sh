#!/bin/bash

DATE=`date +%Y%m%d-%H%M%S`
HOST=`cat /etc/hostname`
BACKUP_DIR=/mnt/backup
FILE_BACKUP=$BACKUP_DIR/$HOST-Backup$DATE.tar.gz
FILE_BACKUP_GIT=$BACKUP_DIR/$HOST-GIT-Backup$DATE.tar.gz

echo backing up $FILE_BACKUP
sleep 5

tar -pczf $FILE_BACKUP /  --exclude-from=/home/dcristian/OMV/backup-exclude.txt -v
chmod 666 $FILE_BACKUP

echo backing up $FILE_BACKUP_GIT

tar -pczf $FILE_BACKUP_GIT /mnt/data/hdd-wdg-6297/git -v
chmod 666 $FILE_BACKUP_GIT
