#!/bin/bash

AMP_URL='http://192.168.0.13:8080/apiv1/db_update/model_name=ZoneCustomRelay&filter_name=relay_pin_name&field_name=relay_is_on'

declare -a NAME=("living" "bucatarie" "dormitor" "baie" "beci")
declare -a RELAY=("living_music_relay" "bucatarie_music_relay" "dormitor_music_relay" "baie_mare_music_relay" "beci_music_relay")
declare -a CARD=("DAC" "PCH" "DGX" "Device" "DGX")
# 1 is usualy digital, 0 is analog
declare -a DEV=("pcm0p" "pcm0p" "pcm1p" "pcm0p" "pcm0p")
CLOSED_DONE=0
LOG=/mnt/log/mpd.log

function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
echo [`date +%T.%N`] $1 $2 $3 $4 $5
}

#show current status, assume card names start with uppercase to avoid duplicates
tail /proc/asound/[[:upper:]]*/pcm*p/sub0/hw_params

#25 times x 2 secons
while [ True ]
do

echo === Try $times ===
  for i in ${!RELAY[*]}; do
	cat /proc/asound/${CARD[$i]}/${DEV[$i]}/sub0/hw_params | grep -q closed
	if [ "$?" == "0" ]; then
		#device is closed
		echo "Device ${NAME[$i]} ${CARD[$i]} ${DEV[$i]} is Closed"
		#execute close command only every 5 minutes
		MIN=`date +"%M"`
		MOD=`expr $MIN % 5`
		if [ "$MOD" == "0" ]; then
			echo2 "Closing amp, running wget, minute=$MIN, modulus=$MOD"
			wget --timeout=10 --tries=1 -O - $AMP_URL'&filter_value='${RELAY[$i]}'&field_value=0'
			CLOSED_DONE=1
		else
			echo Skipping wget, minute=$MIN, modulus=$MOD
		fi
	else
		echo2 "Device ${NAME[$i]} ${CARD[$i]} ${DEV[$i]} is Playing"
		wget --timeout=10 --tries=1 -O - $AMP_URL'&filter_value='${RELAY[$i]}'&field_value=1'
		#no need to loop again as we started the power
		CLOSED_DONE=1
	fi
  echo ""
  done

  if [ "$CLOSED_DONE" == "1" ]; then
	break
  fi
  sleep 2

if [ $1 -ne "loop" ]; then
    exit
fi

done

