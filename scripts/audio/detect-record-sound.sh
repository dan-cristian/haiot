#!/bin/bash

LOG=/mnt/log/motion.log
RECORD_PATH=/mnt/motion/tmp/sound

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/../common/include_cards.sh"

function record_if_noise(){
mkdir -p $RECORD_PATH/$SOURCE
#local level=`arecord -f S16_LE -r 16000 -D  hw:$RECORD_DEVICE -d 1 /dev/shm/tmp_rec.wav ; sox -t .wav /dev/shm/tmp_rec.wav -n stat 2>&1 | grep "Maximum amplitude" | cut -d ':' -f 2 | xargs`
#rm -f /dev/shm/tmp_rec.wav
#if (( $(echo "$level > 0.02" |bc -l) )); then
	echo2 ALARM $level device=$RECORD_DEVICE
	#local SOUND_FILE=$RECORD_PATH/$SOURCE"/sound_"`date +%F_%H-%m-%S`.mp3
	local SOUND_FILE="$RECORD_PATH/$SOURCE/$DST_FILE.mp3"
	#arecord -f S16_LE -r 16000 -D  hw:$RECORD_DEVICE -d 120 $FILE
	arecord -f S16_LE -r 16000 -D  hw:$RECORD_DEVICE -d 1800 | lame -m m -s 16000 -r -V 0 - $SOUND_FILE >> $LOG 2>&1
#else
	echo2 SILENCE $level device=$RECORD_DEVICE
#fi
}

function get_record_device(){
for i in ${!RECORD_SOURCE_LIST[*]}; do
	if [ ${RECORD_SOURCE_LIST[$i]} == "$SOURCE" ]; then
		RECORD_DEVICE=${RECORD_DEVICE_LIST[$i]}
		return 0
	fi
done
echo2 "No device for source $SOURCE"
return 1
}

function stop_arecord(){
echo2 "Closing previous recording dev=$RECORD_DEVICE"
while :
do
        ps ax | grep "arecord" | grep -q $RECORD_DEVICE
        if [ $? -eq 0 ]; then
		echo2 "Stopping arecord process"
                ps -ef | grep "arecord" | grep "$RECORD_DEVICE" | grep -v grep | awk '{print $2}' | xargs kill -s SIGINT
        else
                return
        fi
        # echo "Looping until recording process is completed"
done
}


function record_sound(){
get_record_device
if [ $? -eq 0 ]; then
	record_if_noise
else
	echo2 "Unknown record source at start for event=$SOURCE"
fi
}

function stop_record_sound(){
get_record_device
if [ $? -eq 0 ]; then
	stop_arecord
else
	echo2 "Unknown record source at end for event=$SOURCE"
fi
}

ACTION=$1
SOURCE=$2
FILE=$3

DST_FILE=`basename $FILE`
DST_FILE="${DST_FILE%.*}"

if [ "$ACTION" == "start" ]; then
	record_sound
else
	if [ "$ACTION" == "end" ]; then
		stop_record_sound
	fi
fi

