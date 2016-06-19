#!/bin/bash
LOG=/mnt/log/motion.log
HUBIC_FUSE_ROOT=/mnt/hubic
HUBIC_DIR=$HUBIC_FUSE_ROOT/default/motion/
SRC_DIR=/mnt/motion/tmp/
OLD_COUNT=100

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

#upload to hubic
function upload(){
fstype=`stat --file-system --format=%T $HUBIC_FUSE_ROOT`
echo2 "Cloud mount fstype=[$fstype]"
if [ "$fstype" != "fuseblk" ]; then
  echo2 "Cloud destination is not fuse, but $fstype, aborting!"
  return 1
fi
if [ $# -ne 0 ]; then
  echo2 "Upload file $1"
  source=$1
  src_parent=`dirname $source`
  replace=''
  #replace root
  dest="${source/$SRC_DIR/$HUBIC_DIR}"
  dest_parent=`dirname $dest`
  mkdir -p $dest_parent >> $LOG 2>&1
  echo2 "Uploading to $dest"
  cp -f $source $dest >> $LOG 2>&1
  result=$?
  echo2 "Copy completed result=$result, file $source"
  #workaround to clean temp, hubicfuse bug
  #rm -fv mnt/tmp/hubicfuse/.cloudfuse* >> $LOG 2>&1
  if [ $result -eq 0 ]; then
    echo2 "Upload OK for file $source, result=[$result]"
    return 0
  else
    echo2 "Upload FAILED for file $source, result=[$result]"
    return 2
  fi
else
  echo2 "No parameters to upload a file provided"
  return 3
fi

}

#upload and if ok move file to storage
function move(){
echo2 "Starting SAVE script firstparam=$1"
if [ $# -ne 0 ]; then
  source=$1
  upload $source
  result=$?
  if [ "$result" == "0" ];then
    src_parent=`dirname $source`
    replace=''
    #strip out "tmp" folder name
    dest="${source///tmp$replace}"
    dest_parent=`dirname $dest`
    mkdir -p $dest_parent >> $LOG 2>&1
    echo2 "Move file to $dest"
    chmod -v 777 $dest_parent >> $LOG 2>&1
    mv -f $1 $dest >> $LOG 2>&1
    rm -d $src_parent
    echo2 "Change mode for $dest"
    chmod -v 777 $dest >> $LOG 2>&1
  else
    echo2 "Upload failed result=$result, not moving file from tmp"
    return 2
  fi
else
  echo2 "No parameters to move file provided, skipping this functionality"
  return 3
fi
echo2 "Move completed for $source"
return 0
}


function tune(){
#tune quality depending on day time
MOTION_URL=http://localhost:9999
h=`date +%H`
if [ $h -lt 6 ]; then
  #echo Night
  LAPSE=2
  BITRATE_OUTDOOR=20
elif [ $h -lt 21 ]; then
  #echo Day
  LAPSE=1
  BITRATE_OUTDOOR=15
else
  #echo Evening Night
  LAPSE=2
  BITRATE_OUTDOOR=20
fi
OUTDOOR_LIST=(pod-fata back front)
for thread in 1 2 3 4 5 6 7
do
  for cam in "${OUTDOOR_LIST[@]}"
  do
    #echo "Check for camera $cam in thread $thread"
    check_param $thread "text_event" $cam
    res=$?
    if [ "$res" == "0" ]; then
      	check_param $thread "ffmpeg_variable_bitrate" $BITRATE_OUTDOOR
	res=$?
	if [ "$res" == "1" ]; then
		echo2 "Setting values for outdoor $cam thread=$thread bitrate=$BITRATE_OUTDOOR"
      		wget -q -O /dev/null $MOTION_URL/$thread/config/set?ffmpeg_variable_bitrate=$BITRATE_OUTDOOR
	fi
	check_param $thread "ffmpeg_timelapse" $LAPSE
	res=$?
	if [ "$res" == "1" ]; then
      		echo2 "Setting values for outdoor $cam thread=$thread lapse=$LAPSE"
      		wget -q -O /dev/null $MOTION_URL/$thread/config/set?ffmpeg_timelapse=$LAPSE
	fi
    fi
  done
done
}

#move older files that failed to be uploaded
function move_failed(){
count=0
count_failed=0
find $SRC_DIR -type f -mtime +1 |
while read source
do
  if [ -f $source ]; then
	file_count=`find /mnt/motion/tmp -type f | wc -l`
	echo2 "FILE COUNT in tmp folder is $file_count"
  	file=`basename $source`
  	lock=/tmp/.motion.move.$file.exclusivelock
  	echo2 "Picking older file tryok #$count tryfail #$count_failed $source"
  	(
  	# Wait for lock on /var/lock/..exclusivelock (fd 200) for 1 seconds
  	if flock -x -w 1 200 ; then
        	echo2 "Moving older file $source"
        	move $source
		result=$?
		echo2 "Moved older done result=$result"
		exit $result
  	else
        	echo2 "Already processing file $source, try next"
		exit 6
  	fi
  	) 200>$lock
  	result=$?
  	rm $lock
  	echo2 "Move older file result is $result"
  	if [ $result -eq 0 ];then
		((count++))
		#move 5 files then exit
		if [ $count -eq $OLD_COUNT ];then
	  		return 0
		fi
  	else
		((count_failed++))
		if [ $count_failed -eq 50 ]; then
			return 1
		fi
	fi
  else
	echo2 "File does not exist, skipping $source"
  fi
done
}

move $1 $2
tune
#should be last one as it exits on success
if [ $# -eq 0 ]; then
  move_failed
fi
