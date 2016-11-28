#!/bin/bash

LOG=/mnt/log/mpd.log

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/include_cards.sh"

#function echo2(){
#echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
#echo [`date +%T.%N`] $1 $2 $3 $4 $5
#}


function init_output() {
#root_dir=`dirname $0`
echo2 Initialise all outputs using script in [$DIR]
$DIR/mpc-play.sh 6600 init
$DIR/mpc-play.sh 6601 init
$DIR/mpc-play.sh 6602 init
$DIR/mpc-play.sh 6603 init
$DIR/mpc-play.sh 6604 init
}

init_output
