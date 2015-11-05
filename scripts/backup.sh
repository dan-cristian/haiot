#!/usr/bin/env bash
mount.cifs //192.168.0.9/temp  /mnt/server

DATE=`date +%Y%m%d-%H%M%S`
echo backing up $HOSTNAME-Backup${DATE}.tar.gz
sleep 5
tar -pczf /mnt/server/backup/$HOSTNAME-Backup-${DATE}.tar.gz -X /home/dcristian/haiot/scripts/backup-exclude.txt -v /

umount /mnt/server
