#!/bin/bash
LOG=/mnt/log/mpd.log
MPD_MUSIC=/mnt/music
MPD_DELETED=/mnt/music_deleted

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/../common/include_cards.sh"

function delete(){
prefix="file: "
id="Pos: "
file=`echo "currentsong" | nc localhost $1 | grep "$prefix"`
file_path="${file/$prefix/$MPD_MUSIC/}"
song=`echo "currentsong" | nc localhost $1 | grep "$id"`
song_pos="${song/$id/''}"
echo2 "Preparing to delete file $file_path pos=$song_pos"
delete_status=`echo "delete $song_pos" | nc localhost $1`
echo2 "Delete song from playlist returned:$delete_status"
dest="${file_path/$MPD_MUSIC/$MPD_DELETED}"
echo2 "Moving to $dest"
parent_dest=`dirname "$dest"`
mkdir -p "$parent_dest"
mv -f "$file_path" "$dest"
}

# https://www.musicpd.org/doc/protocol/command_reference.html
function add_fav(){
id="Id: "
prefix="file: "
file=`echo "currentsong" | nc localhost $1 | grep "$prefix"`
file_path="${file/$prefix/''}" #$MPD_MUSIC/}"
song=`echo "currentsong" | nc localhost $1 | grep "$id"`
song_id="${song/$id/''}"
echo2 "Marking favorite song $song_id $file_path"
add_status=`echo playlistadd 9 \"$file_path\" | nc localhost $1`
echo2 "Marking returned $add_status"
}

function un_fav(){
id="Id: "
prefix="file: "
file=`echo "currentsong" | nc localhost $1 | grep "$prefix"`
file_path="${file/$prefix/''}" #$MPD_MUSIC/}"
song=`echo "currentsong" | nc localhost $1 | grep "$id"`
song_id="${song/$id/''}"
echo2 "Removing favorite song $song_id $file_path from playlist"
status=`echo deleteid \"$song_id\" | nc localhost $1`
echo2 "Marking returned $status"
}

function exit_if_kodi_run(){
ps ax | grep -q [k]odi.bin
code=$?
if [ $code == '0' ]; then
	echo2 "Kodi is running, exit"
	exit
fi
}

PORT=0
echo2 "Using MPC zone=$1 type=$2 extra=$3"
for i in ${!CARD_NAME[*]}; do  
	if [ "${CARD_NAME[$i]}" == "$1" ]; then
		PORT=${MPD_PORT_LIST[$i]}
		if [ "$2" == "init" ]; then
			echo2 "Init output in zone ${CARD_NAME[$i]}, output=[${MPD_OUTPUT[$i]}]"
			mpc -vp $PORT enable only "${MPD_OUTPUT[$i]}"
			mpc -vp $PORT volume 25
			mpc -vp $PORT status
			mpc -vp $PORT outputs
		elif [ "$2" == "music" ]; then
			echo2 "Starting MUSIC play in zone ${CARD_NAME[$i]}, output=[${MPD_OUTPUT[$i]}]"
			mpc -vp $PORT enable only "${MPD_OUTPUT[$i]}" >> $LOG 2>&1
			mpc -vp $PORT clear >> $LOG 2>&1
			mpc -vp $PORT ls | mpc -p $PORT add >> $LOG 2>&1
			mpc -vp $PORT random on >> $LOG 2>&1
			mpc -vp $PORT repeat on >> $LOG 2>&1
			mpc -vp $PORT volume 25 >> $LOG 2>&1
			mpc -vp $PORT play >> $LOG 2>&1
			#start amp if needed
			`dirname $0`/activate-audio-amp.sh
			break
		elif [ "$2" == "radio" ]; then
			echo2 "Starting RADIO play in zone ${CARD_NAME[$i]}, output=[${MPD_OUTPUT[$i]}]"
			mpc -vp $PORT clear >> $LOG 2>&1
			mpc -vp $PORT load radios >> $LOG 2>&1
			mpc -vp $PORT volume 25 >> $LOG 2>&1
			mpc -vp $PORT play >> $LOG 2>&1
			#start amp if needed
      `dirname $0`/activate-audio-amp.sh
		elif [ "$2" == "list" ]; then
			echo2 "Starting PLAYLIST=$3 in zone ${CARD_NAME[$i]}, output=[${MPD_OUTPUT[$i]}]"
			mpc -vp $PORT clear >> $LOG 2>&1
			mpc -vp $PORT load $3 >> $LOG 2>&1
			mpc -vp $PORT random on >> $LOG 2>&1
			mpc -vp $PORT repeat on >> $LOG 2>&1
			mpc -vp $PORT volume 25 >> $LOG 2>&1
			mpc -vp $PORT play >> $LOG 2>&1
			#start amp if needed
		  `dirname $0`/activate-audio-amp.sh
		elif [ "$2" == "next" ]; then
			mpc -vp $PORT next >> $LOG 2>&1
		elif [ "$2" == "prev" ]; then
			mpc -vp $PORT prev >> $LOG 2>&1
		elif [ "$2" == "toggle" ]; then
			exit_if_kodi_run
			mpc -vp $PORT toggle >> $LOG 2>&1
		elif [ "$2" == "stop" ]; then
			mpc -vp $PORT stop >> $LOG 2>&1
		elif [ "$2" == "volumeup" ]; then
			mpc -vp $PORT volume +1 >> $LOG 2>&1
		elif [ "$2" == "volumedown" ]; then
			mpc -vp $PORT volume -2 >> $LOG 2>&1
		elif [ "$2" == "delete" ]; then
			delete $PORT
			mpc -vp $PORT next >> $LOG 2>&1
		elif [ "$2" == "fav" ]; then
			add_fav $PORT
			#introduce a pause to indicate add to fav happened
			mpc -vp $PORT toggle >> $LOG 2>&1
			sleep 1
			mpc -vp $PORT toggle >> $LOG 2>&1
		elif [ "$2" == "unfav" ]; then
      un_fav $PORT
      #introduce a pause to indicate add to fav happened
      mpc -vp $PORT toggle >> $LOG 2>&1
      sleep 1
      mpc -vp $PORT toggle >> $LOG 2>&1
		else
			echo2 "Action not mapped for command=[$2]"
		fi
	fi
done
if [ "$PORT" -eq "0" ]; then
	echo2 "Warning, zone=[$1] not found in config list, no action executed"
fi
