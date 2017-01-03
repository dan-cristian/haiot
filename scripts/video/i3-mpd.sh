#!/bin/bash
# shell script to prepend i3status with more stuff
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/../common/include_cards.sh"
source "$DIR/../common/params.sh"

get_card_index_by_name $1
ind=$?
port=${MPD_PORT_LIST[$ind]}
mpc -p $port status | grep -q playing
if [ $? -eq 0 ]; then
	echo "$1: "$(mpc -p $port current)
fi

