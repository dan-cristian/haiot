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
if [ $be_quiet == "0" ]; then
	echo [`date +%T.%N`] $1 $2 $3 $4 $5
fi
}

path=$1
event=$2
echo2 "Event: Ending record movie=$1 event=$2 path="`pwd`
#$DIR/../audio/detect-record-sound.sh end "$event" "$path" >> $LOG 2>&1
# http://stackoverflow.com/questions/11779490/how-to-add-a-new-audio-not-mixing-into-a-video-using-ffmpeg
#echo2 Mixing sound with video
#todo
$DIR/upload-amazondrive.sh $1 $2 >> $LOG 2>&1
$DIR/upload-private-cloud.sh $1 $2 >> $LOG 2>&1
