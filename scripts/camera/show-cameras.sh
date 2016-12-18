#!/bin/bash
LOG=/mnt/log/video.log

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/../common/functions.sh"

rel=5

param="feh -Z.x -R$rel --keep-zoom-vp -Bblack"
kill_proc $param
kill_proc midori
if [ "$1" != "stop" ]; then
i3-msg workspace 4, layout splith
sleep 1
$param 'http://v:vabcd1234@192.168.0.23/Streaming/channels/1/picture' &
sleep 2
# https://wiki.xfce.org/midori/faq#kiosk_mode
#midori -e Navigationbar -e Statusbar  -e Menubar -a "http://192.168.0.12:8080/dashboard" & >> $LOG
midori -e Menubar -a "http://192.168.0.12:8080/dashboard" & >> $LOG
sleep 4
i3-msg splitv
$param 'http://admin:Abcd!234@192.168.0.28/Streaming/channels/1/picture' &
sleep 4
i3-msg focus left, splitv
$param 'http://192.168.0.26/cgi-bin/CGIProxy.fcgi?cmd=snapPicture2&usr=v&pwd=a' &
$param 'http://v:vabcd1234@192.168.0.22/Streaming/channels/1/picture' &
sleep 4
i3-msg focus right, splitv
$param 'http://admin:Abcd!234@192.168.0.21/Streaming/channels/1/picture' &
fi
