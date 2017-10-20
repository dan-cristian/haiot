#!/bin/bash

LOG=/mnt/log/mpd.log

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/../common/params.sh"

target_dir=$MUSIC_PLAYLIST_PATH/`date +%m-%d-%H_%M`
mkdir -p $target_dir

mpc playlist -f $MUSIC_PATH/%file% |
while read -r line ; do
	file_name=$(basename "$line")
	echo2 "Processing file $file_name"
	ln -s "$line" "$target_dir/$file_name"
done
