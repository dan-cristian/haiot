#!/bin/bash

DATE=`date +%Y%m%d-%H%M%S`
HOST=`cat /etc/hostname`
BACKUP_DIR=/mnt/backup/system
BACKUP_DIFF_DIR=/mnt/backup_rdiff
FILE_BACKUP=$BACKUP_DIR/$HOST-Backup$DATE.tar.gz

echo Backing up personal data with rdiff
sleep 5
echo Backup photos
rdiff-backup --print-statistics /mnt/data/hdd-wdr-vsfn/photos $BACKUP_DIFF_DIR/photos.backup
echo Backup private
rdiff-backup --print-statistics /mnt/data/hdd-wdr-vsfn/private $BACKUP_DIFF_DIR/private.backup
echo Backup backup
rdiff-backup --print-statistics /mnt/data/hdd-wdr-vsfn/ebooks $BACKUP_DIFF_DIR/ebooks.backup
echo Backup videos
rdiff-backup --print-statistics /mnt/data/hdd-wdr-vsfn/videos $BACKUP_DIFF_DIR/videos.backup
echo Backup db
rdiff-backup --print-statistics /mnt/data/hdd-wdr-vsfn/db $BACKUP_DIFF_DIR/db.backup

# echo Backing up system to $FILE_BACKUP
# sleep 5

#tar -pczfv $FILE_BACKUP /  --exclude-from=/home/scripts/cloud/backup-exclude.txt
#chmod 666 $FILE_BACKUP
