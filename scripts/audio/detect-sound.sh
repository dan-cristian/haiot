#!/bin/bash

LOG=/mnt/log/mpd.log
RECORD_DEVICE="C525,0,0"
RECORD_PATH=/tmp/sound_record

function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
echo [`date +%T.%N`] $1 $2 $3 $4 $5
}


mkdir -p $RECORD_PATH
level=`arecord -f S16_LE -r 16000 -D  hw:$RECORD_DEVICE -d 1 /dev/shm/tmp_rec.wav ; sox -t .wav /dev/shm/tmp_rec.wav -n stat 2>&1 | grep "Maximum amplitude" | cut -d ':' -f 2 | xargs`
if (( $(echo "$level > 0.02" |bc -l) )); then
	echo ALARM $level
	FILE=$RECORD_PATH"/sound_record_hol"`date +%F_%T`.mp3
	#arecord -f S16_LE -r 16000 -D  hw:$RECORD_DEVICE -d 120 $FILE
	arecord -f S16_LE -r 16000 -D  hw:$RECORD_DEVICE -d 30 | lame -m m -s 16000 -r -V 0 - $FILE
else
	echo SILENCE $level
fi
