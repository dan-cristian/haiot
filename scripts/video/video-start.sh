#!/bin/bash
LOG=/mnt/log/video.log
export HAIOT_USER=haiot
export DISPLAY=":0.0"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/../common/functions.sh"

function stop_kodi(){
echo2 "Stopping kodi"
kill_proc "[k]odi/kodi.bin"
}

function stop_browser(){
echo2 "Stopping browser"
kill_proc "[c]hrome"
}


function exit_if_kodi_run(){
ps ax | grep -q [k]odi.bin
kodi_code=$?
if [ $kodi_code -eq 0 ]; then
        echo2 "Kodi is running, exit"
        exit
fi
}

function exit_if_browser_run(){
ps ax | grep -q [/]opt/google/chrome/chrome
browser_code=$?
if [ $browser_code -eq 0 ]; then
        echo2 "Browser is running, exit"
        exit
fi
}

function startx_once(){
local result=`ps ax | grep [/]usr/bin/startx`
#local result=$?
#echo2 "got ps result [$result]"
if [ "$result" != "" ]; then
	tty=`cat /sys/class/tty/tty0/active`
	# echo2 "startx running, not starting again, res=[$result], console=$tty"
	con=`ps ax|grep [X]org | awk '{print $2}'`
	if [ "$con" != "$tty" ]; then
		con=${con##*tty}
		/bin/chvt $con
		echo2 "Switching to startx console $con"
	fi
	return
else
	echo2 "Starting startx with user $HAIOT_USER, res=$result"
	# https://bugs.launchpad.net/ubuntu/+source/xinit/+bug/1562219
	#chmod 0660 /dev/tty*
	#/sbin/runuser -l $HAIOT_USER -c
	"/usr/bin/startx" & >> $LOG 2>&1
	echo2 "Started X"
	while :
	do
		ps ax | grep -q [i]3blocks
		res=$?
		if [ $res -eq 1 ]; then
			#echo2 "Waiting for startx process $res"
			sleep 0.1
		else
			#default actions after x is started
			xrandr --output HDMI1 --primary
			xset +dpms
			#duplicate screens
			xrandr --output HDMI3 --auto --output HDMI1 --auto --same-as HDMI3
			#set individual screens
			#xrandr --output HDMI1 --auto --left-of HDMI3
			/usr/bin/easystroke &
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

function start_kodi_once(){
echo2 "Starting kodi display $DISPLAY"
/usr/bin/xdotool key --clearmodifiers alt+3  >> $LOG 2>&1
exit_if_kodi_run
#/sbin/runuser -l $HAIOT_USER -c "/usr/bin/kodi" >> $LOG 2>&1 &
$DIR/../audio/mpc-play.sh living stop
/usr/bin/kodi & >> $LOG 2>&1
}

function start_kodi(){
echo2 "Starting kodi display $DISPLAY"
/usr/bin/xdotool key --clearmodifiers alt+3  >> $LOG 2>&1
#/sbin/runuser -l $HAIOT_USER -c "/usr/bin/kodi" >> $LOG 2>&1 &
$DIR/../audio/mpc-play.sh living stop
/usr/bin/kodi & >> $LOG 2>&1
}

function start_browser(){
echo2 "Starting browser display $DISPLAY"
/usr/bin/xdotool key --clearmodifiers alt+2  >> $LOG 2>&1
#/sbin/runuser -l $HAIOT_USER -c "/usr/bin/kodi" >> $LOG 2>&1 &
exit_if_browser_run
/usr/bin/google-chrome --user-data-dir="/home/$HAIOT_USER/.chrome" >> $LOG 2>&1
}

function presence(){
echo2 "Detected presence"
startx_once
exit_if_kodi_run
is_monitor_on
if [ $? -ne 0 ]; then
	xset dpms force on
	$DIR/slideshow.sh
fi
}


# http://unix.stackexchange.com/questions/118811/why-cant-i-run-gui-apps-from-root-no-protocol-specified
# http://kodi.wiki/view/HOW-TO:Autostart_Kodi_for_Linux

#echo2 "Kodi cmd=$1 target_user=$HAIOT_USER whoami=`whoami`"
if [ "$1" == "start-kodi" ]; then
	stop_kodi
	startx_once
	start_kodi
	#increase_prio
elif [ "$1" == "stop" ]; then
	stop_kodi
elif [ "$1" == "start-kodi-once" ]; then
	startx_once
	start_kodi_once
	#increase_prio
elif [ "$1" == "start-browser" ]; then
        startx_once
        stop_browser
	start_browser
        #increase_prio
elif [ "$1" == "startx" ]; then
        startx_once
elif [ "$1" == "presence" ]; then
        presence
elif [ "$1" == "touch" ]; then
        presence
else
	echo2 "Action not mapped for command=[$1]"
fi
