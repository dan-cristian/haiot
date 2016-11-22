#!/bin/bash
LOG=/mnt/log/video.log
export HAIOT_USER=haiot
export DISPLAY=":0.0"

function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
echo [`date +%T.%N`] $1 $2 $3 $4 $5
}

function kill_proc(){
pid_str=`ps ax | grep "$1"`
echo2 "Looking for proc [$1] pid returned: [$pid_str]"
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

function stop_browser(){
echo2 "Stopping browser"
kill_proc "[c]hrome"
}


function exit_if_video_run(){
ps ax | grep -q [k]odi.bin
kodi_code=$?
ps ax | grep -q [c]hrome
browser_code=$?
if [ $kodi_code -eq 0 ] || [ $browser_code -eq 0 ]; then
        echo2 "Kodi or Browser is running, exit"
        exit
fi
}

function startx_once(){
ps ax | grep -q [s]tartx
if [ $? == '0' ]; then
	echo2 "startx running, not starting again"
	return
else
	echo2 "Starting startx with user $HAIOT_USER"
	# https://bugs.launchpad.net/ubuntu/+source/xinit/+bug/1562219
	#chmod 0660 /dev/tty*
	#/sbin/runuser -l $HAIOT_USER -c
	"/usr/bin/startx" & >> $LOG 2>&1
	echo2 "Started X"
	while :
	do
		ps ax | grep -q [i]3status
		res=$?
		if [ $res -eq 1 ]; then
			echo2 "Waiting for startx process $res"
			sleep 0.1
		else
			return
		fi
	done
	echo2 "Exit startx"
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

function start_kodi(){
echo2 "Starting kodi display $DISPLAY"
/usr/bin/xdotool key --clearmodifiers alt+1  >> $LOG 2>&1
#/sbin/runuser -l $HAIOT_USER -c "/usr/bin/kodi" >> $LOG 2>&1 &
/usr/bin/kodi & >> $LOG 2>&1
}

function start_browser(){
echo2 "Starting browser display $DISPLAY"
/usr/bin/xdotool key --clearmodifiers alt+2  >> $LOG 2>&1
#/sbin/runuser -l $HAIOT_USER -c "/usr/bin/kodi" >> $LOG 2>&1 &
/usr/bin/google-chrome --user-data-dir="/home/$HAIOT_USER/.chrome" >> $LOG 2>&1
}


# http://unix.stackexchange.com/questions/118811/why-cant-i-run-gui-apps-from-root-no-protocol-specified
# http://kodi.wiki/view/HOW-TO:Autostart_Kodi_for_Linux

echo2 "Kodi cmd=$1 target_user=$HAIOT_USER whoami=`whoami`"
if [ "$1" == "start-kodi" ]; then
	stop_kodi
	startx_once
	start_kodi
	#increase_prio
elif [ "$1" == "stop" ]; then
	stop_kodi
elif [ "$1" == "start-kodi-once" ]; then
	exit_if_video_run
	startx_once
	start_kodi
	#increase_prio
elif [ "$1" == "start-browser" ]; then
        startx_once
        stop_browser
	start_browser
        #increase_prio
else
	echo2 "Action not mapped for command=[$1]"
fi
