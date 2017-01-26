#!/bin/bash
# shell script to prepend i3status with more stuff
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/../common/params.sh"

remaining=$(($FEH_SLIDESHOW_DELAY - $(expr $(date +%s) - $(date +%s -r "$FEH_CURRENT_FILE"))))
if [ $remaining -gt 10 ]; then
	color="green"
else
	color="red"
fi
echo "<span font_desc='FontAwesome'>&#xf1c0;</span><span color='$color'>$remaining</span>"
