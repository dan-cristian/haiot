#!/bin/bash

LOG=/mnt/log/mpd.log

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/../common/include_cards.sh"

function init_output() {
echo2 Initialise all outputs using script in [$DIR]
$DIR/mpc-play.sh living init
$DIR/mpc-play.sh pod init
$DIR/mpc-play.sh beci init
$DIR/mpc-play.sh dormitor init
$DIR/mpc-play.sh baie init
}

init_output
