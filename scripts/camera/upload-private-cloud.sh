#!/bin/bash
source /home/haiot/private_config/.credentials/.general.credentials
LOG=/mnt/log/motion.log
SRC_DIR=/mnt/motion/tmp/
OLD_COUNT=1000

function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
}

#upload to cloud
function upload(){
if [ $# -ne 0 ]; then
  echo2 "Upload file $1"
  source=$1
  src_parent=`dirname "$source"`
  replace=''
  #replace root
  dest="${source/$SRC_DIR/$BACKUP_PATH}"
  dest_parent=`dirname "$dest"`
  #mkdir -p $dest_parent >> $LOG 2>&1
  echo2 "Uploading $source to $dest"
  if [ -z ${HOME+x} ]; then export HOME="/home/motion"; fi
  
  #/usr/sbin/rclone copy $source $dest_parent >> $LOG 2>&1
  echo2 "Creating remote parent folder $dest_parent"
  #echo2 ssh -T -p ${HAIOT_SSH_PORT} -c ${HAIOT_SSH_CIPHER} -o Compression=no ${HAIOT_SSH_SERVER} "mkdir -p $dest_parent"
  ssh -T -p ${BACKUP_SSH_PORT} -c ${BACKUP_SSH_CIPHER} -o Compression=no ${BACKUP_SSH_SERVER} "mkdir -p $dest_parent" >> $LOG 2>&1
  echo2 "Now uploading"
  #echo2 rsync -avPe 'ssh -T -p '${HAIOT_SSH_PORT}' -c '${HAIOT_SSH_CIPHER}' -o Compression=no -x' ${source} ${HAIOT_SSH_SERVER}:${dest_parent}/
  rsync -avPe 'ssh -T -p '${BACKUP_SSH_PORT}' -c '${BACKUP_SSH_CIPHER}' -o Compression=no -x' ${source} ${BACKUP_SSH_SERVER}:${dest_parent}/ >> $LOG 2>&1

  #cp -f $source $dest >> $LOG 2>&1
  result=$?
  #echo2 "Copy completed result=$result, file $source"
  if [ $result -eq 0 ]; then
    echo2 "Upload OK for file $source, result=[$result]"
    return 0
  else
    echo2 "Upload FAILED for file $source, result=[$result], HOME=$HOME, user=`whoami`"
    return 2
  fi
else
  echo2 "No parameters to upload a file provided"
  return 3
fi
}

#upload and if ok move file to storage
function move(){
#echo2 "Starting SAVE script firstparam=$1"
if [ $# -ne 0 ]; then
  source="$1"
  upload "$source"
  result=$?
  if [ "$result" == "0" ];then
    src_parent=`dirname "$source"`
    replace=''
    #strip out "tmp" folder name
    dest="${source///tmp$replace}"
    dest_parent=`dirname "$dest"`
    mkdir -p "$dest_parent" >> $LOG 2>&1
    if [ $? -eq 1 ]; then
	echo2 "Create parent folder failed"
	return 2
    fi
    #echo2 "Move file to $dest"
    chmod -v 777 "$dest_parent" >> $LOG 2>&1
    mv -f $1 "$dest" >> $LOG 2>&1
    rm -d "$src_parent" >> $LOG 2>&1
    if [ $? -eq 0 ]; then
    	src_parent_2=`dirname $src_parent`
    	rm -d "$src_parent_2" >> $LOG 2>&1
	if [ $? -eq 0 ]; then
		src_parent_3=`dirname "$src_parent_2"`
        	rm -d "$src_parent_3" >> $LOG 2>&1
	fi
    fi
    #echo2 "Change mode for $dest"
    chmod -v 777 "$dest" >> $LOG 2>&1
  else
    echo2 "Upload failed result=$result, not moving file from tmp"
    return 2
  fi
else
  # echo2 "No parameters to move file provided, skipping this functionality"
  return 3
fi
echo2 "Move OK for $source"
return 0
}


#move older files that failed to be uploaded
function move_failed(){
count=0
count_failed=0
be_quiet=1
#find $SRC_DIR -type f -mtime +1 |
find ${SRC_DIR} -type f  |
while read source
do
  echo2 "Processing old file ["${source}"]"
  if [[ -f "${source}" ]]; then
	file_count=`find /mnt/motion/tmp -type f | wc -l`
	if [[ ${file_count} -le "154000" ]]; then
		be_quiet=1
	fi
  	file=`basename "${source}"`
	# check if file is in use with lsof
	filename=$(basename "${file}")
	lsof -w | grep -q "${filename}"
	if [[ $? = 1 ]]; then
		echo2 "FILE COUNT in tmp folder is $file_count"
  		lock=/tmp/.motion.move.$file.exclusivelock
  		echo2 "Picking older file tryok #$count tryfail #$count_failed $source"
  		(
  		# Wait for lock on /var/lock/..exclusivelock (fd 200) for 1 seconds
  		if flock -x -w 1 200 ; then
        		echo2 "Moving older file ${source}"
        		move "${source}"
			result=$?
			#echo2 "Moved older done result=$result"
			return ${result}
  		else
        		echo2 "Already processing file $source, try next"
			return 6
  		fi
  		) 200>${lock}
  		result=$?
  		rm ${lock}
  		#echo2 "Move older file result is $result"
		if [[ ${result} -eq 0 ]];then
			count=$((count+1))
			#move x files then exit
			if [[ ${count} -eq ${OLD_COUNT} ]];then
				echo2 "Exiting as I moved $count files out of $OLD_COUNT"
	  			return 0
			fi
  		else
			count_failed=$((count_failed+1))
			if [[ ${count_failed} -eq 10 ]]; then
				echo2 "Exiting as I failed to move $count_failed files"
				return 1
			fi
		fi
	fi
  else
	echo2 "File does not exist, skipping $source"
  fi
done
}

be_quiet=0
move $1 $2
#tune
#should be last one as it exits on success
if [[ $# -eq 0 ]]; then
  	lock2=/tmp/.motion.move-history.$file.exclusivelock
	(
		if flock -x -w 1 200 ; then
			move_failed
		else
			echo2 "Move history already in progress, skipping"
		fi
	) 200>${lock2}
	rm ${lock2}
fi
