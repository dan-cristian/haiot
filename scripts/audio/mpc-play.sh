#!/bin/bash
LOG=/mnt/log/mpd.log
MPD_MUSIC=/mnt/music
MPD_DELETED=/mnt/music_deleted

function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
echo [`date +%T.%N`] $1 $2 $3 $4 $5
}

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

echo2 "Using MPC port=$1 type=$2 extra=$3"

declare -a NAME=("living" "bucatarie" "beci" "dormitor" "baie")
declare -a PORT=(6600 6601 6602 6603 6604)
declare -a OUTPUT=("Digital Small USB (living2)" "Analog Onboard (bucatarie)" "Analog DGX PCIe (beci)" "Digital DGX PCIe (dormitor)" "Digital Box USB (baie)")
PORT_MATCH=0

for i in ${!PORT[*]}; do
	if [ "${PORT[$i]}" == "$1" ]; then
		PORT_MATCH=$1
		if [ "$2" == "init" ]; then
			echo2 "Init output in zone ${NAME[$i]}, output=[${OUTPUT[$i]}]"
			mpc -vp $1 enable only "${OUTPUT[$i]}" >> $LOG 2>&1
			mpc -vp $1 volume 25 >> $LOG 2>&1
		elif [ "$2" == "music" ]; then
			echo2 "Starting MUSIC play in zone ${NAME[$i]}, output=[${OUTPUT[$i]}]"
			mpc -vp $1 enable only "${OUTPUT[$i]}" >> $LOG 2>&1
			mpc -vp $1 clear >> $LOG 2>&1
			mpc -vp $1 ls | mpc -p $1 add >> $LOG 2>&1
			mpc -vp $1 random on >> $LOG 2>&1
			mpc -vp $1 repeat on >> $LOG 2>&1
			mpc -vp $1 volume 25 >> $LOG 2>&1
			mpc -vp $1 play >> $LOG 2>&1
			#start amp if needed
			`dirname $0`/activate-audio-amp.sh
			break
		elif [ "$2" == "radio" ]; then
			echo2 "Starting RADIO play in zone ${NAME[$i]}, output=[${OUTPUT[$i]}]"
			mpc -vp $1 clear >> $LOG 2>&1
			mpc -vp $1 load radios >> $LOG 2>&1
			mpc -vp $1 volume 25 >> $LOG 2>&1
			mpc -vp $1 play >> $LOG 2>&1
			#start amp if needed
                        `dirname $0`/activate-audio-amp.sh
		elif [ "$2" == "list" ]; then
			echo2 "Starting PLAYLIST=$3 in zone ${NAME[$i]}, output=[${OUTPUT[$i]}]"
			mpc -vp $1 clear >> $LOG 2>&1
			mpc -vp $1 load $3 >> $LOG 2>&1
			mpc -vp $1 random on >> $LOG 2>&1
			mpc -vp $1 repeat on >> $LOG 2>&1
			mpc -vp $1 volume 25 >> $LOG 2>&1
			mpc -vp $1 play >> $LOG 2>&1
			#start amp if needed
                        `dirname $0`/activate-audio-amp.sh
		elif [ "$2" == "next" ]; then
			mpc -vp $1 next >> $LOG 2>&1
		elif [ "$2" == "prev" ]; then
			mpc -vp $1 prev >> $LOG 2>&1
		elif [ "$2" == "toggle" ]; then
			exit_if_kodi_run
			mpc -vp $1 toggle >> $LOG 2>&1
		elif [ "$2" == "stop" ]; then
			mpc -vp $1 stop >> $LOG 2>&1
		elif [ "$2" == "volumeup" ]; then
			mpc -vp $1 volume +1 >> $LOG 2>&1
		elif [ "$2" == "volumedown" ]; then
			mpc -vp $1 volume -2 >> $LOG 2>&1
		elif [ "$2" == "delete" ]; then
			delete $1
			mpc -vp $1 next >> $LOG 2>&1
		elif [ "$2" == "fav" ]; then
			add_fav $1
			#introduce a pause to indicate add to fav happened
			mpc -vp $1 toggle >> $LOG 2>&1
			sleep 1
			mpc -vp $1 toggle >> $LOG 2>&1
		elif [ "$2" == "unfav" ]; then
                        un_fav $1
                        #introduce a pause to indicate add to fav happened
                        mpc -vp $1 toggle >> $LOG 2>&1
                        sleep 1
                        mpc -vp $1 toggle >> $LOG 2>&1
		else
			echo2 "Action not mapped for command=[$2]"
		fi
	fi
done
if [ "$PORT_MATCH" -eq "0" ]; then
	echo2 "Warning, port=[$1] not found in config list, no action executed"
fi
