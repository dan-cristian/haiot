#!/bin/bash
LOG=/mnt/log/video.log

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/../common/functions.sh"

pause=5
params="feh -FrzqY. -D$pause --draw-exif"

kill_proc "$params"

i3-msg workspace 5
$params '/mnt/photos' &

