#!/bin/bash
LOG=/mnt/log/video.log

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/../common/functions.sh"

pause=10
params="feh --keep-zoom-vp -g1920x1080 -Bblack -Zxd -rzqY. -D$pause"

kill_proc "$params"

i3-msg workspace 5
$params '/mnt/photos' &

