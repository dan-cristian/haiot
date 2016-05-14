#!/bin/bash

AMP_URL='http://192.168.0.113:8080/apiv1/db_update/model_name=ZoneCustomRelay&filter_name=zone_id&field_name=relay_is_on'

declare -a NAME=("living" "bucatarie" "dormitor" "baie" "beci")
declare -a ZONE=(2 1 4 5 3)
declare -a CARD=("PCH" "PCH" "DGX" "Device" "DGX")
# 1 is usualy digital, 0 is analog
declare -a DEV=("pcm1p" "pcm0p" "pcm1p" "pcm0p" "pcm0p")
CLOSED_DONE=0

for times in 1 2 3 4 5 6 7 8 9 10; do
echo === Try $times ===
  for i in ${!ZONE[*]}; do
	cat /proc/asound/${CARD[$i]}/${DEV[$i]}/sub0/hw_params | grep closed
	if [ "$?" == "0" ]; then
		#device is closed
		echo Device ${NAME[$i]} is Closed
		#execute close command only every 5 minutes
		MIN=`date +"%M"`
		MOD=`expr $MIN % 5`
		if [ "$MOD" == "0" ]; then
			echo Running wget, minute=$MIN, modulus=$MOD
			wget --timeout=10 --tries=1 -O - $AMP_URL'&filter_value='${ZONE[$i]}'&field_value=0'
		else
			echo Skipping wget, minute=$MIN, modulus=$MOD
		fi
	else
		echo Device ${NAME[$i]} is Playing
		wget --timeout=10 --tries=1 -O - $AMP_URL'&filter_value='${ZONE[$i]}'&field_value=1'
		#no need to loop again as we started the power
		CLOSED_DONE=1
	fi
  done

  if [ "$CLOSED_DONE" == "1" ]; then
	break
  fi
  sleep 5
done
