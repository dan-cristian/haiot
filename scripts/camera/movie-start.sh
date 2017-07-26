#!/bin/bash
LOG=/mnt/log/motion.log
SRC_DIR=/mnt/motion/tmp/
OLD_COUNT=1000
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

#1=thread, 2=param, 3=value
function check_param(){
  #echo "Testing $1 $2 $3"
  wget_out="`wget -qO- $MOTION_URL/$1/config/get?query=$2`"
  #echo "Got $wget_out"
  if [[ $wget_out == *"$2 = $3"* ]]
  then
    #echo FOUND
    return 0
  fi
return 1
}

function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
echo [`date +%T.%N`] $1 $2 $3 $4 $5
}

path=$1
event=$2
# echo2 "Event: Starting record movie=$1 event=$2 path=["`pwd`"] root=$DIR"
# $DIR/../audio/detect-record-sound.sh start "$event" "$path" & >> $LOG 2>&1
