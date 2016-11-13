#!/bin/bash

#declare -a NAME=("living" "bucatarie" "dormitor" "baie" "beci")
declare -a STATUS_OPEN=(0 0 0 0 0)
declare -a CARD_CAPT=("Loopback" "PCH" "DGX" "Device" "DGX")
RECORD_DEVICE="Loopback,1,0"
# 1 is usualy digital, 0 is analog
declare -a DEV_CAPT=("pcm0c" "pcm0c" "pcm1c" "pcm0c" "pcm0c")
declare -a DEV_OUT=("pcm0p" "pcm0p" "pcm1p" "pcm0p" "pcm0p")
LOG=/mnt/log/record-audio.log
RECORD_PATH=/mnt/music/_recorded

function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
echo [`date +%T.%N`] $1 $2 $3 $4 $5
}

#show current status, assume card names start with uppercase to avoid duplicates
echo "List outputs"
tail /proc/asound/[[:upper:]]*/pcm*p/sub0/hw_params
echo "List inputs"
tail /proc/asound/[[:upper:]]*/pcm*c/sub0/hw_params


echo2 Started with parameter [$1] [$2]

lock=/tmp/.record-audio.exclusivelock
(
# Wait for lock on /var/lock/..exclusivelock (fd 200) for 1 seconds
if flock -x -w 1 200 ; then

while :
	do
	mpc_event=`mpc idle`
	if [ "$mpc_event" == "player" ]; then
		mpc_output=`mpc status`
		readarray -t mpc_array <<<"$mpc_output"
		song_name=${mpc_array[0]}.wav
		song_path=$RECORD_PATH/$song_name
		song_tmp_path=$RECORD_PATH/tmp/$song_name
		echo $song_name
		status_line=${mpc_array[1]}
		status=${status_line%]*}  # retain the part before the]
		status=${status##*[}  # retain the part after the last[
		echo Status is $status
		if [ "$status" == "playing" ]; then
			i=0
                        cat /proc/asound/${CARD_CAPT[$i]}/${DEV_CAPT[$i]}/sub0/hw_params | grep -q closed
			loop_in_is_closed=$?
			if [ -f "$song_tmp_path" ]; then
				echo "$song_tmp_path found."
				#ffmpeg -y -ffmpeg -y -f alsa -ac 2 -ar 44100 -i hw:$RECORD_DEVICE "$song_tmp_path" &
				#ps -ef | grep "American Foo" | grep -v grep | awk '{print $2}' | xargs kill
			else
				echo "$song_tmp_path not found. recording."
				echo "Check if input is busy"
			        if [ "$loop_in_is_closed" == "0" ]; then
                			#device is open
					echo "Closing previous recording"
					ps ax | grep "arecord"
					ps -ef | grep "arecord" | grep -v grep | awk '{print $2}' | xargs kill
					sleep 0.2
				else
					echo "No previous recordings"
				fi
				cat /proc/asound/${CARD_CAPT[$i]}/${DEV_OUT[$i]}/sub0/hw_params | grep -q closed
                        	loop_out_is_open=$?
				if [ "$loop_out_is_open" == "1" ]; then
					arecord -c 2 -f S16_LE -r 44100 -t wav -D hw:$RECORD_DEVICE "$song_tmp_path" &
				fi
			fi
		else
			echo 2
		fi

	else
		echo "Ignoring event $mpc_event"
	fi
	done
else
	echo2 "Already recording, exit"
	exit 1
fi
) 200>$lock
rm $lock
