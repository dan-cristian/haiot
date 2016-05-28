#!/bin/bash
LOG=/mnt/log/hubicfuse.log
HUBIC_FUSE_ROOT=/mnt/hubic
HUBIC_DIR=$HUBIC_FUSE_ROOT/default/motion/

function echo2(){
echo $1 $2 $3 $4 $5 >> $LOG 2>&1
echo $1 $2 $3 $4 $5
}

echo2 Starting script with params=$# firstparam=$1
#check if hubic is mounted, if not mount it

fstype=`stat --file-system --format=%T $HUBIC_FUSE_ROOT`
if [ "$fstype" != "fuseblk" ]; then
  echo2 Hubic not mounted, force unmount and remount
  umount -l  $HUBIC_FUSE_ROOT
  #gdb --eval-command=run handle SIGPIPE nostop noprint pass --args \
  hubicfuse $HUBIC_FUSE_ROOT \
	-o noatime,noauto_cache,sync_read,allow_other,big_writes,large_read,max_write=131072,max_read=131072 -f #>> $LOG 2>&1
  if [ $? -eq 0]; then
    echo2 Hubic mounted
    else
    echo2 Hubic mount error
  fi
else
  echo2 Hubic already mounted
fi
