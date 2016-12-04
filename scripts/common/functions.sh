#!/bin/bash

export DISPLAY=":0.0"

function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
echo [`date +%T.%N`] $1 $2 $3 $4 $5
}

function kill_proc(){
search=$1
echo2 "Stopping processes containing [$1]"
while :
do
ps ax | grep -q '$search' | grep -v grep
if [ $? -eq 0 ]; then
	#echo2 Stopping process `ps -ef | grep "$1" | grep -v grep | awk '{print $2}'`
	ps -ef | grep "$1" | grep -v grep | awk '{print $2}' | xargs kill -9
    	sleep 0.1
else
	return
fi
done
}

function pause(){
read -n1 -r -p "Press any key to continue..." key
}

function is_monitor_on(){
xset -q | grep "Monitor is On"
return $?
}
