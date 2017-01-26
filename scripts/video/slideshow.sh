#!/bin/bash
LOG=/mnt/log/video.log

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/../common/functions.sh"
source "$DIR/../common/params.sh"

params="feh --keep-zoom-vp -g1920x1080 -Bblack -Zxd -rzqY. -D$FEH_SLIDESHOW_DELAY"
kill_proc "$params"

i3-msg workspace 5

#cmd="echo %f > $FEH_CURRENT_FILE; exiv2 -pt %f | grep Exif.Photo.UserComment | grep -q $PICTURE_TAG_PRIVATE; if [ $? -eq 0 ]; then echo skip; kill -SIGUSR1 %V; else echo ok; fi"
cmd="echo '%f' > '$FEH_CURRENT_FILE'; echo %V > $FEH_SLIDESHOW_PID; echo 'Feh analyse %f' >> $LOG; if exiv2 -pt '%f' | grep 'Exif.Photo.UserComment' | grep  -q '$PICTURE_TAG_PRIVATE'; then echo 'Skipping private picture %f' >> $LOG; kill -SIGUSR1 %V; fi"
#echo Launching $params --info \"$cmd\" /mnt/photos/Poze Proprii/
$params --info "$cmd" /mnt/photos/Poze\ Proprii/ &

