#!/bin/bash

LOG=/mnt/log/mpd.log

function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
echo [`date +%T.%N`] $1 $2 $3 $4 $5
}


function init_output() {
root_dir=`dirname $0`
echo2 Initialise all outputs using script in [$root_dir]
$root_dir/mpc-play.sh 6600 init
$root_dir/mpc-play.sh 6601 init
$root_dir/mpc-play.sh 6602 init
$root_dir/mpc-play.sh 6603 init
$root_dir/mpc-play.sh 6604 init
}

init_output
