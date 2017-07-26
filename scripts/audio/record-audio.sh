#!/bin/bash
declare -a STATUS_OPEN=(0 0 0 0 0)
RECORD_DEVICE="Loopback,1,0"
MPD_LOOP_OUTPUT_NAME="Record"
LOG=/mnt/log/record-audio.log
RECORD_PATH=/mnt/music/_recorded

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/../common/include_cards.sh"

function compress_set_tag(){
local src_file=$rec_song_tmp_path
local dst_file=$rec_song_path
echo2 "Processing song=[$rec_song_name] from [$src_file] to [$dst_file]"
if [ -f "$src_file" ]; then
	if [ -f "$dst_file" ]; then
		local duration_ondisk=$(metaflac --show-total-samples --show-sample-rate "$dst_file" | tr '\n' ' ' | awk '{print $1/$2}' -)
		duration_ondisk=${duration_ondisk%.*}
		# check if what we have on disk is shorter than current record
		if [ $rec_song_duration -le $duration_ondisk ]; then
			echo2 "Destination [$dst_file] exists with duration=$duration_ondisk, is shorter ($rec_song_duration), skipping"
			return
		fi
	echo2 "Destination [$dst_file] exists with duration=$duration_ondisk, song is longer ($rec_song_duration), overwriting"
	fi

	#check if play was stopped earlier or skipped. add 2 seconds loss
	local duration_ondisk=$(mediainfo --Inform="Audio;%Duration%" "$src_file")
	duration_ondisk=$(( 2 + $duration_ondisk / 1000))
	echo2 "Song actual duration=$duration_ondisk, forecasted duration=$rec_song_duration"
	if [ $duration_ondisk -lt $rec_song_duration ]; then
		echo2 "Song not completely played, target=$rec_song_duration actual=$duration_ondisk, ignoring"
		rm -vf "$src_file"
		return
	fi
	local artist=${rec_song_name% - *}  # retain the part before the " - "
	local title=${rec_song_name##* - }  # retain the part after the " - "
	#flac -f -0 "$src_file" -o "$dst_file"
	sox "$src_file" -b16 "$dst_file"
	echo2 "Setting ID3 TAGS, artist=$artist title=$title"
	id3v2 -a "$artist" -t "$title" "$dst_file"
	if [ $? -eq 0 ]; then
		echo2 "Compress OK, removing source wav $src_file"
		rm -vf "$src_file"
	else
		echo2 "Error, file not compressed and tagged"
	fi
else
	echo2 "Source file [$src_file] not on disk, skip compressing"
fi
}

function record_song(){
#local song_tmp_path=$1
local mpc_search=`mpc -p $MPD_PORT search artist "$song_artist" title "$song_title"`
if [ -z "$mpc_search" ]; then
	record_duration=$(($song_duration + 5))
	record_duration=$(($record_duration<=7200?$record_duration:7200))
	echo2 "Recording channels=$sound_channels format=$sound_format rate=$sound_rate $song_tmp_path, safe duration=$record_duration sec"
	arecord -d $record_duration -c $sound_channels -f $sound_format -r $sound_rate -t wav -D hw:$RECORD_DEVICE "$song_tmp_path" & >> $LOG 2>&1
	rec_song_name="$song_name"
	rec_song_tmp_path="$song_tmp_path"
	rec_song_path="$song_path"
	rec_song_duration="$song_duration"
	echo2 "Started recording $rec_sound_name to file $rec_song_tmp_path"
	#arecord -q -c 2 -f S16_LE -r 44100 -t wav -D hw:$RECORD_DEVICE | flac -0 -o "$_song_tmp_path" >> $LOG 2>&1 &
else
	echo2 "Song already in library at [$mpc_search], not recording"
fi
}

function stop_arecord(){
echo2 "Closing previous recording song=[$rec_sound_name]"
while :
do
	ps ax | grep "arecord" | grep -q $RECORD_DEVICE
	if [ $? -eq 0 ]; then
		ps -ef | grep "arecord" | grep "$RECORD_DEVICE" | grep -v grep | awk '{print $2}' | xargs kill -s SIGINT
	else
		return
	fi
	# echo "Looping until recording process is completed"
done
}

function is_output_enabled(){
local port=$1
#echo check output port $port
local mpc_output_list=`mpc -p $port outputs`
local output_status=${mpc_output_list##*$MPD_LOOP_OUTPUT_NAME) is }
#echo "Loopback output status for $port:$MPD_LOOP_OUTPUT_NAME is [$output_status]"
#http://stackoverflow.com/questions/229551/string-contains-in-bash
if [[ "$output_status" == "enabled"* ]]; then
	echo2 "Output enabled"
	return 1
else
	return 0
fi
}

#access: RW_INTERLEAVED
#format: S32_LE
#subformat: STD
#channels: 2
#rate: 44100 (44100/1)
#period_size: 5512
#buffer_size: 22052

get_loopback_meta(){
echo2 "Get loopback for card $CARD_INDEX"
local output=`cat /proc/asound/${CARD_OUT[$CARD_INDEX]}/${DEV_OUT[$CARD_INDEX]}/sub0/hw_params`
readarray -t sound_array <<<"$output"
local format=${sound_array[1]}
sound_format=${format##*: }  # retain the part after the last :
format=${sound_array[3]}
sound_channels=${format##*: }
format=${sound_array[4]}
format=${format##*: }
sound_rate=${format% (*}
echo2 "Loopback sound meta i=$i format=$sound_format channels=$sound_channels rate=$sound_rate"
}

function set_loopback_mpd_port(){
# find card/mpd instance running with loopback
local i
for i in ${!CARD_OUT[*]}; do
	#cat /proc/asound/${CARD_OUT[$i]}/${DEV_OUT[$i]}/sub0/hw_params
	cat /proc/asound/${CARD_OUT[$i]}/${DEV_OUT[$i]}/sub0/hw_params | grep -q closed
	local loop_in_is_closed=$?
	if [ "$loop_in_is_closed" == "1" ]; then
		#device is open
		local mpd_port=${MPD_PORT_LIST[$i]}
		#echo "Found sound on card ${NAME[$i]} port=$mpd_port"
		mpc_output=`mpc -p $mpd_port status`
		readarray -t mpc_array <<<"$mpc_output"
		local status_line=${mpc_array[1]}
		local status=${status_line%]*}  # retain the part before the]
		status=${status##*[}  # retain the part after the last[
		#echo "Status=[$status]"
		if [ "$status" == "playing" ]; then
			is_output_enabled $mpd_port
			if [ $? -eq 1 ]; then
				# echo "MPD port with loopback enabled is $mpd_port"
				MPD_PORT=$mpd_port
				ZONE_NAME=${CARD_NAME[$i]}
        CARD_INDEX=$i
				return 0
			fi
		fi
	fi
done
# echo2 "Could not find running MPD instance with loopback enabled"
export MPD_PORT=""
return 1
}


#Galantis - Gold Dust
#[playing] #2/39   0:46/3:54 (19%)
#volume: 57%   repeat: off   random: off   single: off   consume: off

function get_song_meta(){
local mpc_output=`mpc -p $MPD_PORT status`
readarray -t mpc_array <<<"$mpc_output"
song_name=${mpc_array[0]}
song_title=${song_name##*- }
song_artist=${song_name% -*}
#fix for (AlbumArtist) issue
#Estiva, Estiva (AlbumArtist) - Foreverland (Original Mix)
echo $song_artist | grep -q ' (AlbumArtist)'
if [ $? -eq 0 ]; then
	echo2 "Found bad artist title, fixing=[$song_artist]"
	song_artist=${song_artist%,*}
	echo2 "Fixed bad artist title, fixed=[$song_artist]"
	song_name="$song_artist - $song_title"
	echo2 "Fixed song name=[$song_name]"
fi
#end fix
sanitized_song_name=${song_name////_}
song_path=$RECORD_PATH/$sanitized_song_name$song_ext
song_tmp_path=$RECORD_PATH/tmp/$sanitized_song_name$song_tmp_ext
local status_line=${mpc_array[1]}
local status=${status_line%]*}  # retain the part before the]
player_status=${status##*[}  # retain the part after the last[
local duration_line=${status_line##*   }
duration_line=${duration_line##*/}
duration_line=${duration_line% (*}
if [ "$duration_line" != "" ]; then
	local min=${duration_line%:*}
	local sec=${duration_line##*:}
	echo2 "Duration [$min] [$sec] [$duration_line]" 
	#trim leading 0
	sec=$(echo $sec | sed 's/^0*//')
  if [ "$sec" == "" ]; then
    sec="0"
  fi
  song_duration=$(($min * 60 + $sec))
else
	song_duration=0
fi
echo2 "Song=$song_name Artist=$song_artist Title=$song_title status=$player_status duration=$song_duration"
}

function finish(){
rm -f /tmp/.record-audio.exclusivelock
}

#show current status, assume card names start with uppercase to avoid duplicates
#echo "List outputs"
#tail /proc/asound/[[:upper:]]*/pcm*p/sub0/hw_params
#echo "List inputs"
#tail /proc/asound/[[:upper:]]*/pcm*c/sub0/hw_params

timeout=1
song_tmp_ext=".wav"
song_ext=".flac"

trap finish EXIT
echo2 "Started with parameter [$1] [$2] in dir=$DIR"
lock=/tmp/.record-audio.exclusivelock
(
	# Wait for lock on /var/lock/..exclusivelock (fd 200) for 1 seconds
	if flock -x -w 1 200 ; then
	while :
	do
		date_now=`date`
		seconds_lapsed=`printf "%s\n" $(( $(date -d "$date_now" "+%s") - $(date -d "$date_last_on" "+%s") ))`
		if [ $seconds_lapsed -le 300 ] && [ "$MPD_PORT" != "" ]; then
			echo2 "Reusing cached MPD port=$MPD_PORT, lapsed=$seconds_lapsed"
			ok_to_record=0
		else
			set_loopback_mpd_port
			ok_to_record=$?
		fi
		if [ $ok_to_record -eq 0 ] && [ "$MPD_PORT" != "" ]; then
			echo2 "MPD port with loopback enabled = $MPD_PORT in zone $ZONE_NAME"
			if [ "$MPD_PORT" == "" ]; then
				echo2 "MPD port is empty?"
			fi
			date_last_on=`date`
			mpc_event=`mpc -q -p $MPD_PORT idle`
			if [ "$mpc_event" == "player" ]; then
				get_song_meta
				if [ "$player_status" == "playing" ]; then
					i=0
          echo2 "Checking ${CARD_CAPT[$i]}-${DEV_CAPT[$i]}"
					cat /proc/asound/${CARD_CAPT[$i]}/${DEV_CAPT[$i]}/sub0/hw_params | grep -q closed
					loop_in_is_closed=$?
					if [ -f "$song_tmp_path" ]; then
						echo2 "$song_tmp_path found. deleting"
						rm -vf "$song_tmp_path"
						#song_tmp_path="$RECORD_PATH/tmp/$song_name(`date +%s`)$song_tmp_ext"
					fi
					# echo "Check if input is busy"
					if [ "$loop_in_is_closed" == "0" ]; then
						#device is open
						stop_arecord
						# put it in background to avoid delay for next record
						compress_set_tag &
					else
						echo2 "No previous recordings"
					fi
					cat /proc/asound/${CARD_CAPT[$i]}/${DEV_OUT[$i]}/sub0/hw_params | grep -q closed
					loop_out_is_open=$?
					if [ "$loop_out_is_open" == "1" ]; then
						get_loopback_meta
						record_song
					else
            echo2 "Not recording $song_name as out=$loop_out_is_open"
          fi
				else
					if [ "$player_status" == "" ] || [ "$player_status" == "paused" ]; then
						echo2 "Playback stopped. Terminating recording and deleting incomplete song."
						stop_arecord
						if [ "$player_status" == "paused" ]; then
							echo2 "Deleting incomplete song on PAUSE, $song_tmp_path"
							rm -v "$song_tmp_path" >> $LOG 2>&1
						fi
					fi
				fi
			else
				if [ "$mpc_event" == "output" ]; then
					is_output_enabled $MPD_PORT
					if [ $? -eq 0 ]; then
						echo2 "Output disabled, stopping record"
						MPD_PORT=$mpd_port
						stop_arecord
						date_last_on=""
					fi
				else
					# echo "Ignoring event $mpc_event"
					:
				fi
			fi
		else
			sleep 5
			((timeout+=1))
			if [ $timeout -gt 30 ]; then
				timeout=1
				echo2 "No loop instance active, sleep $timeout, dir=$DIR"
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

