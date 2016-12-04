#!/bin/bash

LOG=/mnt/log/mpd.log

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/../common/include_cards.sh"

function init_output() {
echo2 Initialise all outputs using script in [$DIR]
$DIR/mpc-play.sh 6600 init
$DIR/mpc-play.sh 6601 init
$DIR/mpc-play.sh 6602 init
$DIR/mpc-play.sh 6603 init
$DIR/mpc-play.sh 6604 init
}

init_output
