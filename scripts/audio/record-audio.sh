#!/bin/bash

declare -a NAME=("living" "bucatarie" "dormitor" "baie" "beci")
declare -a PORT_LIST=(6600 6601 6603 6604 6602)
declare -a STATUS_OPEN=(0 0 0 0 0)
declare -a CARD_OUT=("DAC" "PCH" "DGX" "Device" "DGX")
declare -a CARD_CAPT=("Loopback" "PCH" "DGX" "Device" "DGX")
RECORD_DEVICE="Loopback,1,0"
# 1 is usualy digital, 0 is analog
declare -a DEV_CAPT=("pcm0c" "pcm0c" "pcm1c" "pcm0c" "pcm0c")
declare -a DEV_OUT=("pcm0p" "pcm0p" "pcm1p" "pcm0p" "pcm0p")
MPD_LOOP_OUTPUT_NAME="Record"
LOG=/mnt/log/record-audio.log
RECORD_PATH=/mnt/music/_recorded

function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
echo [`date +%T.%N`] $1 $2 $3 $4 $5
}

function stop_arecord(){
while :
do
	ps ax | grep "arecord" | grep -q $RECORD_DEVICE
	if [ $? -eq 0 ]; then
		ps -ef | grep "arecord" | grep "$RECORD_DEVICE" | grep -v grep | awk '{print $2}' | xargs kill
	else
		return
	fi
	# echo "Looping until recording process is completed"
done
}

function is_output_enabled(){
port=$1
#echo check output port $port
mpc_output_list=`mpc -p $port outputs`
output_status=${mpc_output_list##*$MPD_LOOP_OUTPUT_NAME) is }
#echo Loopback output status is [$output_status]
if [ "$output_status" == "enabled" ]; then
	return 1
else
	return 0
fi
}

function set_loopback_mpd_port(){
# find card/mpd instance running with loopback
for i in ${!CARD_OUT[*]}; do
	#echo "Iterate $i"
	#cat /proc/asound/${CARD_OUT[$i]}/${DEV_OUT[$i]}/sub0/hw_params
	cat /proc/asound/${CARD_OUT[$i]}/${DEV_OUT[$i]}/sub0/hw_params | grep -q closed
	loop_in_is_closed=$?
	if [ "$loop_in_is_closed" == "1" ]; then
		#device is open
		mpd_port=${PORT_LIST[$i]}
		#echo "Found sound on card ${NAME[$i]} port=$mpd_port"
		mpc_output=`mpc -p $mpd_port status`
		readarray -t mpc_array <<<"$mpc_output"
		status_line=${mpc_array[1]}
		status=${status_line%]*}  # retain the part before the]
		status=${status##*[}  # retain the part after the last[
		#echo "Status =[$status]"
		if [ "$status" == "playing" ]; then
			is_output_enabled $mpd_port
			if [ $? -eq 1 ]; then
				# echo "MPD port with loopback enabled is $mpd_port"
				export MPD_PORT=$mpd_port
				export ZONE_NAME=${NAME[$i]}
				return 0
			fi
		fi
	fi
done
# echo2 "Could not find running MPD instance with loopback enabled"
MPC_PORT=""
return 1
}

#show current status, assume card names start with uppercase to avoid duplicates
#echo "List outputs"
#tail /proc/asound/[[:upper:]]*/pcm*p/sub0/hw_params
#echo "List inputs"
#tail /proc/asound/[[:upper:]]*/pcm*c/sub0/hw_params

timeout=1
echo2 Started with parameter [$1] [$2]
lock=/tmp/.record-audio.exclusivelock
(
	# Wait for lock on /var/lock/..exclusivelock (fd 200) for 1 seconds
	if flock -x -w 1 200 ; then
	while :
	do
		date_now=`date`
		seconds_lapsed=`printf "%s\n" $(( $(date -d "$date_now" "+%s") - $(date -d "$date_last_on" "+%s") ))`
		if [ $seconds_lapsed -le 300 ]; then
			# echo "Reusing cached MPD port, lapsed=$seconds_lapsed"
			ok_to_record=0
		else
			set_loopback_mpd_port
			ok_to_record=$?
		fi
		if [ $ok_to_record -eq 0 ]; then
			echo2 "MPD port with loopback enabled = $MPD_PORT in zone $ZONE_NAME"
			date_last_on=`date`
			mpc_event=`mpc -q -p $MPD_PORT idle`
			if [ "$mpc_event" == "player" ]; then
				mpc_output=`mpc -p $MPD_PORT status`
				readarray -t mpc_array <<<"$mpc_output"
				song_name=${mpc_array[0]}
				song_ext=".wav"
				song_path=$RECORD_PATH/$song_name$song_ext
				song_tmp_path=$RECORD_PATH/tmp/$song_name$song_ext
				#echo $song_name
				status_line=${mpc_array[1]}
				status=${status_line%]*}  # retain the part before the]
				status=${status##*[}  # retain the part after the last[
				#echo Status is $status
				if [ "$status" == "playing" ]; then
					i=0
					cat /proc/asound/${CARD_CAPT[$i]}/${DEV_CAPT[$i]}/sub0/hw_params | grep -q closed
					loop_in_is_closed=$?
					if [ -f "$song_tmp_path" ]; then
						echo2 "$song_tmp_path found."
						song_tmp_path="$RECORD_PATH/tmp/$song_name(`date +%s`)$song_ext"
						#ffmpeg -y -ffmpeg -y -f alsa -ac 2 -ar 44100 -i hw:$RECORD_DEVICE "$song_tmp_path" &
						#ps -ef | grep "American Foo" | grep -v grep | awk '{print $2}' | xargs kill
					fi
					echo2 "Recording $song_tmp_path"
					# echo "Check if input is busy"
					if [ "$loop_in_is_closed" == "0" ]; then
						#device is open
						echo2 "Closing previous recording"
						stop_arecord
					else
						echo2 "No previous recordings"
					fi
					cat /proc/asound/${CARD_CAPT[$i]}/${DEV_OUT[$i]}/sub0/hw_params | grep -q closed
					loop_out_is_open=$?
					if [ "$loop_out_is_open" == "1" ]; then
						arecord -c 2 -f S16_LE -r 44100 -t wav -D hw:$RECORD_DEVICE "$song_tmp_path" >> $LOG 2>&1 &
					fi
				else
					if [ "$status" == "" ] || [ "$status" == "paused" ]; then
						echo2 "Playback stopped. Terminating recording and deleting incomplete song."
						stop_arecord
						if [ "$status" == "paused" ]; then
							echo2 "Deleting incomplete song on PAUSE, "
							rm -v "$song_tmp_path" >> $LOG 2>&1
						fi
					fi
				fi
			else
				if [ "$mpc_event" == "output" ]; then			
					is_output_enabled $MPD_PORT
					if [ $? -eq 0 ]; then
						echo2 "Output disabled, stopping record"
						export MPC_PORT=$mpd_port
						stop_arecord
						date_last_on=""
					fi
				else
					# echo "Ignoring event $mpc_event"
					:
				fi
			fi	
		else
			sleep 1
			((timeout+=1))
			if [ $timeout -gt 30 ]; then
				timeout=1
				echo2 "No loop instance active, sleep $timeout"
			fi
		#loop port
		fi 
	#while
	done
else
	echo2 "Already recording, exit"
	exit 1
fi #lock
) 200>$lock
rm $lock
