#!/bin/bash

DATE=`date +%Y%m%d-%H%M%S`
HOST=`cat /etc/hostname`
BACKUP_DIR=/mnt/backup
BACKUP_DIFF_DIR=/mnt/backup_rdiff
FILE_BACKUP=$BACKUP_DIR/$HOST-Backup$DATE.tar.gz

echo Backing up personal data with rdiff
sleep 5

rdiff-backup /mnt/data/hdd-wdg-6297/photos $BACKUP_DIFF_DIR/photos.backup
rdiff-backup /mnt/data/hdd-wdg-6297/private $BACKUP_DIFF_DIR/private.backup
rdiff-backup /mnt/data/hdd-wdg-6297/ebooks $BACKUP_DIFF_DIR/ebooks.backup
rdiff-backup /mnt/data/hdd-wdr-evhk/videos $BACKUP_DIFF_DIR/videos.backup

echo Backing up system to $FILE_BACKUP
sleep 5

tar -pczf $FILE_BACKUP /  --exclude-from=/home/scripts/cloud/backup-exclude.txt
chmod 666 $FILE_BACKUP
