#!/bin/bash
LOG=/mnt/log/kodi.log

function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
echo [`date +%T.%N`] $1 $2 $3 $4 $5
}

function kill_proc(){
pid_str=`ps ax | grep "$1"`
echo2 "Looking for kodi [$1] pid returned: [$pid_str]"
if [[ -n "$pid_str" ]]; then
	pid_array=($pid_str)
	pid=${pid_array[0]}
	echo2 "Kill existing instance $pid"
	kill $pid
	sleep 2
	kill -9 $pid
	sleep 1
fi
}

function stop_kodi(){
echo2 "Stopping kodi"
kill_proc "[x]init /usr/bin/kodi"
kill_proc "[/]usr/lib/kodi/kodi.bin"
}

function exit_if_kodi_run(){
ps ax | grep -q [k]odi.bin
code=$?
if [ $code == '0' ]; then
        echo2 "Kodi is running, exit"
        exit
fi
}

# does not work when launched from thd
function increase_prio(){
while :
do
	ps -ef | grep -q "kodi.bin"
	if [ $? -eq 0 ]; then
		sleep 5
		ps -ef | grep "kodi.bin" | grep -v grep | awk '{print $2}' | xargs renice -12 -p 
		echo "Reniced!"
		return 0
	fi
echo "Looping"
sleep 1
done
}

# http://unix.stackexchange.com/questions/118811/why-cant-i-run-gui-apps-from-root-no-protocol-specified
# http://kodi.wiki/view/HOW-TO:Autostart_Kodi_for_Linux

echo2 "Kodi cmd=$1"
if [ "$1" == "start" ]; then
	stop_kodi
	echo2 "Starting kodi"
	/usr/bin/startx /usr/bin/kodi >> $LOG 2>&1 &
	#increase_prio
elif [ "$1" == "stop" ]; then
	stop_kodi
elif [ "$1" == "start_once" ]; then
	exit_if_kodi_run
	echo2 "Starting kodi once"
	/usr/bin/startx /usr/bin/kodi >> $LOG 2>&1 &
	#increase_prio
else
	echo2 "Action not mapped for command=[$1]"
fi
