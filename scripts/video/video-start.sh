#!/bin/bash
LOG=/mnt/log/video.log
export HAIOT_USER=haiot
export DISPLAY=":0.0"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/../common/functions.sh"
source "$DIR/../common/params.sh"

function stop_kodi(){
echo2 "Stopping kodi"
kill_proc "kodi/kodi.bin"
}

function stop_browser(){
echo2 "Stopping browser"
kill_proc "midori"
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
ps ax | grep -q [/]usr/bin/midori
browser_code=$?
if [ $browser_code -eq 0 ]; then
        echo2 "Browser is running, exit"
        exit
fi
}

function gesture-config(){
	killall easystroke
	echo2 "Starting easystroke show with HOME=$HOME"
	if [ -z $HOME ]; then
        	export HOME="/root"
	fi
	/usr/bin/easystroke show >> $LOG
}

function start_gesture_once(){
ps ax | grep -q [e]asystroke
if [ $? -eq 0 ]; then
        echo2 "Easystroke is running"
        return
fi
echo2 "Starting easystroke with HOME=$HOME"
if [ -z $HOME ]; then
	export HOME="/root"
fi
/usr/bin/easystroke hide >> $LOG 2>&1 &
}

# http://askubuntu.com/questions/371261/display-monitor-info-via-command-line
# http://unix.stackexchange.com/questions/13619/how-do-i-prevent-xorg-using-my-linux-laptops-display-panel
function configure_ignored_hdmi_amp(){
local amp_name=$1
for dir in /sys/class/drm/*HDMI*; do
	if cat $dir/edid | parse-edid | grep $amp_name | grep -vq grep; then
		id=${dir: -1}
		echo2 "Found monitor $amp_name as HDMI$id"
		x_conf=/etc/X11/xorg.conf.d/haiot-amp-ignore.conf
		echo 'Section "Monitor"' > $x_conf
        	echo 'Identifier      "HDMI'$id'"' >> $x_conf
        	echo 'Option  "ignore"        "true"' >> $x_conf
		echo 'EndSection' >> $x_conf
		return
	fi
done
echo2 "Warning, could not find monitor $amp_name"
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
	configure_ignored_hdmi_amp "$AMP_HDMI_X11_IGNORE"
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
			# https://wiki.archlinux.org/index.php/Display_Power_Management_Signaling
			# http://ptspts.blogspot.ro/2009/10/screen-blanking-dpms-screen-saver.html
			enable_dpms
			set_power_save
			#duplicate screens, needed for pointer calibration
			xrandr --output HDMI2 --auto --output HDMI1 --auto --same-as HDMI2
			#xrandr --output HDMI3 --auto --output HDMI1 --auto --same-as HDMI3
			#xrandr --output HDMI3 --auto --output HDMI2 --auto --same-as HDMI3
			#set individual screens
			#xrandr --output HDMI1 --auto --left-of HDMI3
			start_gesture_once
			# SONY BD mode change
			#xrandr --output HDMI3 --mode 1920x1080
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
set_workspace $I3_WORKSPACE_KODI
exit_if_kodi_run
#/sbin/runuser -l $HAIOT_USER -c "/usr/bin/kodi" >> $LOG 2>&1 &
$DIR/../audio/mpc-play.sh living stop
/usr/bin/kodi & >> $LOG 2>&1
}

function start_kodi(){
echo2 "Starting kodi display $DISPLAY"
set_workspace $I3_WORKSPACE_KODI
#/sbin/runuser -l $HAIOT_USER -c "/usr/bin/kodi" >> $LOG 2>&1 &
$DIR/../audio/mpc-play.sh living stop
/usr/bin/kodi & >> $LOG 2>&1
}

function start_browser(){
echo2 "Starting browser display $DISPLAY"
set_workspace $I3_WORKSPACE_BROWSER
echo2 "Workspace set for browser"
exit_if_browser_run
echo2 "Launch midori"
rm -R ~/.config/midori/
midori -e Fullscreen http://localhost:8080 >> $LOG 2>&1 &
}

function presence(){
echo2 "Detected presence"
startx_once
start_gesture_once
#xdotool key Shift
# awake receiver HDMI sound if screen was off
#xrandr --output HDMI2 --auto
#xrandr --output HDMI3 --auto
#force resolution on sony amp
#xrandr --output HDMI3 --mode 1920x1080
exit_if_kodi_run
enable_dpms
is_monitor_on
if [ $? -ne 0 ]; then
	#xdotool key Shift
	xset dpms force on
	#extending screen close timeout?
	xset s reset
	#unset_power_save
	#set_power_save
	$DIR/slideshow.sh
fi
}


function get_picture_path(){
tmp_current_file=`cat $FEH_CURRENT_FILE`
tmp_file_parent=$(dirname "$tmp_current_file")
echo2 "Parent is $tmp_file_parent"
}

function gesture-picture-delete(){
get_picture_path
echo2 "Deleting file $tmp_current_file"
echo2 "Creating parent $PICTURE_DELETE_PATH/$tmp_file_parent"
mkdir -pv "$PICTURE_DELETE_PATH/$tmp_file_parent"
mv -v "$tmp_current_file" "$PICTURE_DELETE_PATH/$tmp_file_parent"
kill -SIGUSR1 $(cat $FEH_SLIDESHOW_PID)
}

function gesture-picture-exclude(){
get_picture_path
echo2 "Excluding file $tmp_current_file"
echo2 "Creating parent $PICTURE_DELETE_PATH/$tmp_file_parent"
mkdir -pv "$PICTURE_EXCLUDE_PATH/$tmp_file_parent"
mv -v "$tmp_current_file" "$PICTURE_EXCLUDE_PATH/$tmp_file_parent"
kill -SIGUSR1 $(cat $FEH_SLIDESHOW_PID)
}

function gesture-picture-private(){
get_picture_path
echo2 "Set Private file $tmp_current_file"
exiv2 -M "add Exif.Photo.UserComment $PICTURE_TAG_PRIVATE $tmp_current_file"
kill -SIGUSR1 $(cat $FEH_SLIDESHOW_PID)
}

function gesture-picture-favorite(){
get_picture_path
echo2 "Set favorite file $tmp_current_file"
exiv2 -M "add Exif.Photo.UserComment $PICTURE_TAG_FAVORITE $tmp_current_file"
}


# http://unix.stackexchange.com/questions/118811/why-cant-i-run-gui-apps-from-root-no-protocol-specified
# http://kodi.wiki/view/HOW-TO:Autostart_Kodi_for_Linux

#echo2 "Kodi cmd=$1 target_user=$HAIOT_USER whoami=`whoami`"
lock=/tmp/.video-start.exclusivelock
(
# Wait for lock on /var/lock/..exclusivelock (fd 200) for 1 seconds
if flock -x -w 1 200 ; then

echo2 "Executing video command $1"
if [ "$1" == "start-kodi" ]; then
	stop_kodi
	startx_once
	start_kodi
	#increase_prio
elif [ "$1" == "stop" ]; then
	stop_kodi
elif [ "$1" == "start-kodi-once" ]; then
	startx_once
	#start_kodi_once
	stop_kodi
	start_kodi
	#increase_prio
elif [ "$1" == "start-browser" ]; then
        #startx_once
        stop_browser
	start_browser
        #increase_prio
elif [ "$1" == "startx" ]; then
        startx_once
elif [ "$1" == "presence" ]; then
        presence
elif [ "$1" == "touch" ]; then
        presence
elif [ "$1" == "gesture-config" ]; then
        gesture-config
else
	echo2 "Action not mapped for command=[$1], try to run anyways"
	$1
fi

fi #lock
) 200>$lock
rm $lock
