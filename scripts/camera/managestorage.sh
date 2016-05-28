#!/bin/bash

DIRSRV=/mnt/motion
CONFFILE=/home/dcristian/OMV/conf/storagecontrol.conf
LOG=/var/log/dvr.log

function getdirsize(){
	USEDS=(`du -sh $DIRSRV`)
	unit=${USEDS: -1}
	#echo "(Unit $unit)"
	if [ "$unit" == "G" ] ; then
		valwithunit=${USEDS[0]}
		valnounit=${valwithunit::-1}
		#replace , with . to become numeric
		valnounit="${valnounit/,/.}"
		echo $valnounit
	else
		echo 0
	fi
}

function getmaxsize(){
source $CONFFILE
#conffilepath=$CONFFILE
#confline=$(cat $conffilepath)
#confval=($confline)
#confresult=${confval[1]}
#echo $confresult
echo $maxrepositorysize
}

function clean() {
echo "Cleaning oldest files" >> $LOG
#ls -1 -ltd -1 $PWD $DIRSRV/**/* | awk ' /^-/ { print $9}' | tail -10 | xargs rm
#ls -1 -ltd -1 $PWD $DIRSRV/** | awk ' /^-/ { print $9}' | tail -10 | xargs rm -r
#find $DIRSRV -type f -printf "%t %p\n" | sort -nr | tail -10 | xargs rm -v

#remove files 30 days older
find $DIRSRV -maxdepth 4 -type f -mtime +10 | xargs rm -v >> $LOG 2>&1
echo "Clean done" >> $LOG
}

function checkandclean() {
current=$(getdirsize)
max=$(getmaxsize)
echo "Checking space on storage, current=$current maxtarget=$max units=GB" >> $LOG
if (( $(echo "$current > $max" | bc -l) )); then
	echo "Max size reached on storage" >> $LOG
	clean
	echo FULL >> $LOG
else
	#echo "Space left on storage, clean not needed"
	echo EMPTY >> $LOG
fi
}

#no need to loop as only files of certain age will be removed
#while true; do
	result=$(checkandclean)
	if [ "$result" == "EMPTY" ] ; then
		break
	fi
#done

