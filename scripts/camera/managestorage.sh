#!/bin/bash

DIRSRV=/mnt/motion/
MAX_REPO_SIZE="1100100100"
FILE_AGE=30

function clean() {
echo "Cleaning oldest files"
#ls -1 -ltd -1 $PWD $DIRSRV/**/* | awk ' /^-/ { print $9}' | tail -10 | xargs rm
#ls -1 -ltd -1 $PWD $DIRSRV/** | awk ' /^-/ { print $9}' | tail -10 | xargs rm -r
#find $DIRSRV -type f -printf "%t %p\n" | sort -nr | tail -10 | xargs rm -v

#remove files x days older, then remove empty dirs
find $DIRSRV -type f -mtime +$FILE_AGE | xargs rm -v >> /dev/null 2>&1
echo "Clean done"
}

function checkandclean() {
current=$(du -s $DIRSRV)
echo "Checking space on storage, current=$current maxtarget=$MAX_REPO_SIZE units=bytes"
if (( $(echo "$current > $MAX_REPO_SIZE" | bc -l) )); then
	echo "Max size reached on storage, cleaning files older than $FILE_AGE"
	clean
	echo 0
else
	echo "Space left on storage, clean not needed"
	echo 1
fi
}

#no need to loop as only files of certain age will be removed
while [ $FILE_AGE -ne 0 ]; do
	echo "Starting cleanup"
	#result=$( checkandclean )
	checkandclean
	if [ $? == 0 ] ; then
		echo Clean empty folders
		find $DIRSRV -type d -empty | xargs rmdir -v >> /dev/null 2>&1
		((FILE_AGE--))
	else
		echo "Nothing found with age $FILE_AGE"
		break
	fi
done
