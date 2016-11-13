#!/bin/bash

DATE=`date +%Y%m%d-%H%M%S`
HOST=`cat /etc/hostname`
BACKUP_DIR=/mnt/backup
FILE_BACKUP_GIT=$BACKUP_DIR/$HOST-GIT-Backup$DATE.tar.gz

echo backing up $FILE_BACKUP_GIT

tar -pczf $FILE_BACKUP_GIT /mnt/git -v
chmod 666 $FILE_BACKUP_GIT
