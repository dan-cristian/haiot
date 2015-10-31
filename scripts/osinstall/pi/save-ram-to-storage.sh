#!/bin/bash

#http://reboot.pro/topic/14547-linux-load-your-root-partition-to-ram-and-boot-it/
#https://developers.shopware.com/blog/2015/07/16/create-delta-updates-using-rsync/

MNT_DIR=/mnt/persistent-root
OVERLAY_DIR=ram-changes-overlay
USERNAME=haiot
LOG=/var/log/save-ram-to-storage.log

echo "Starting to save ram to disk (in overlay folder), press CTRL+C to cancel this now"
sleep 1
echo -ne "4\r"
sleep 1
echo -ne "3\r"
sleep 1
echo -ne "2\r"
sleep 1
echo -ne "1\r"
sleep 1

mkdir -p $MNT_DIR
mount /dev/mmcblk0p2 $MNT_DIR
mkdir -p $MNT_DIR/$OVERLAY_DIR
rsync --dry-run --delete-delay --exclude-from=/home/$USERNAME/PYC/scripts/osinstall/pi/rsync-ram-overlay-exclude.txt --log-file=$LOG -rlHpEAXogtv --compare-dest=/ $MNT_DIR / $MNT_DIR/$OVERLAY_DIR
find $MNT_DIR/$OVERLAY_DIR -type d -empty -delete >> $LOG
umount $MNT_DIR

