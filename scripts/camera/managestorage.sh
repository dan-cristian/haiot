#!/bin/bash

DIRSRV=/mnt/motion/
maxrepositorysize="750" #GBytes
MAX_REPO_SIZE="1234567890"
LOG=/mnt/log/dvr.log
FILE_AGE=30

function clean() {
#echo "Cleaning oldest files" >> $LOG
#ls -1 -ltd -1 $PWD $DIRSRV/**/* | awk ' /^-/ { print $9}' | tail -10 | xargs rm
#ls -1 -ltd -1 $PWD $DIRSRV/** | awk ' /^-/ { print $9}' | tail -10 | xargs rm -r
#find $DIRSRV -type f -printf "%t %p\n" | sort -nr | tail -10 | xargs rm -v

#remove files x days older
find $DIRSRV -type f -mtime +$FILE_AGE | xargs rm -v >> $LOG 2>&1
echo "Clean done" >> $LOG
}

function checkandclean() {
current=(`du -s $DIRSRV`)
echo "Checking space on storage, current=$current maxtarget=$MAX_REPO_SIZE units=bytes" >> $LOG
if (( $(echo "$current > $MAX_REPO_SIZE" | bc -l) )); then
	echo "Max size reached on storage, cleaning files older than $FILE_AGE" >> $LOG
	clean
	echo FULL
else
	#echo "Space left on storage, clean not needed"
	echo EMPTY
fi
}

#no need to loop as only files of certain age will be removed
while true; do
	result=$(checkandclean)
	if [ "$result" == "EMPTY" ] ; then
		break
	else
		((FILE_AGE--))
	fi
done
