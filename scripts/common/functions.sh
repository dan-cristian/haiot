#!/bin/bash

export DISPLAY=":0.0"

function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
echo [`date +%T.%N`] $1 $2 $3 $4 $5
}

function kill_proc(){
search=$1
safe_search=${search:0:0}[${search:0:1}]${search:1}
echo2 "Stopping processes containing [$safe_search]"
while :
do
ps ax | grep "$safe_search"
if ps ax | grep -q "$safe_search"; then
#if [ $? -eq 0 ]; then
	echo2 "Found process, killing"
	ps -ef | grep "$safe_search" | awk '{print $2}' | xargs kill -9 
    	sleep 0.1
else
	echo2 "No process found to stop"
	return
fi
done
}

function pause(){
read -n1 -r -p "Press any key to continue..." key
}

function set_power_save(){
xset dpms 600 600 600
}

function unset_power_save(){
xset dpms 0 0 0
}

function enable_dpms(){
if xset -q | grep "DPMS is Disabled"; then
	xset +dpms
fi
}

function is_monitor_on(){
xset -q | grep "Monitor is On"
return $?
}

function get_current_workspace(){
index=$(i3-msg -t get_workspaces | jq '.[] | select(.focused==true).name' | cut -d"\"" -f2)
return $index
}

function set_workspace(){
i3-msg workspace $1
while :
do
	get_current_workspace
	workspace=$?
	if [ $workspace == $1 ]; then
		return
	else
		echo2 "Workspace is $workspace, not yet changed to $1"
		sleep 0.1
	fi
done
}
