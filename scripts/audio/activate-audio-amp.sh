#!/bin/bash

AMP_URL='http://192.168.0.13:8080/apiv1/db_update/model_name=ZoneCustomRelay&filter_name=relay_pin_name&field_name=relay_is_on'

declare -a NAME=("living" "bucatarie" "dormitor" "baie" "beci")
declare -a RELAY=("living_music_relay" "bucatarie_music_relay" "dormitor_music_relay" "baie_mare_music_relay" "beci_music_relay")
declare -a STATUS_OPEN=(0 0 0 0 0)
declare -a CARD=("DAC" "PCH" "DGX" "Device" "DGX")
# 1 is usualy digital, 0 is analog
declare -a DEV=("pcm0p" "pcm0p" "pcm1p" "pcm0p" "pcm0p")
CLOSED_DONE=0
CLOSED_DONE_LOOP=0
LOG=/mnt/log/mpd.log

function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
echo [`date +%T.%N`] $1 $2 $3 $4 $5
}

#show current status, assume card names start with uppercase to avoid duplicates
tail /proc/asound/[[:upper:]]*/pcm*p/sub0/hw_params
echo Started with parameter [$1]
while :
do
  for i in ${!RELAY[*]}; do
	#execute close command only every 5 minutes
	MIN=`date +"%M"`
	MOD=`expr $MIN % 5`
	cat /proc/asound/${CARD[$i]}/${DEV[$i]}/sub0/hw_params | grep -q closed
	if [ "$?" == "0" ]; then
		#device is closed
		#echo "Device ${NAME[$i]} ${CARD[$i]} ${DEV[$i]} is Closed"
		if [ "$MOD" == "0" ] || [ "$1" != "loop" ]; then
			if [ $CLOSED_DONE_LOOP -eq 0 ]; then
				echo2 "Closing amp ${NAME[$i]} status=${STATUS_OPEN[$i]} close_done_loop=$CLOSED_DONE_LOOP mod=$MOD"
				wget --timeout=10 --tries=1 -O - $AMP_URL'&filter_value='${RELAY[$i]}'&field_value=0'
				CLOSED_DONE=1
				STATUS_OPEN[$i]=0
			fi
		else
			#echo Skipping wget, minute=$MIN, modulus=$MOD
			CLOSED_DONE_LOOP=0
		fi
	else
		# activate only is prev value is 0 or after a period (to catch exceptions)
		if [ ${STATUS_OPEN[$i]} -eq 0 ] || [ "$MOD" == "0" ]; then
			echo2 "Device ${NAME[$i]} ${CARD[$i]} ${DEV[$i]} is Playing, status=${STATUS_OPEN[$i]} mod=$MOD"
			wget --timeout=10 --tries=1 -O - $AMP_URL'&filter_value='${RELAY[$i]}'&field_value=1'
			STATUS_OPEN[$i]=1
		fi
		#no need to loop again as we started the power
		#CLOSED_DONE=1
	fi
  done

  # sleep if close is already completed to avoid many duplicate wget
  if [ $CLOSED_DONE -eq 1 ]; then
	CLOSED_DONE_LOOP=1
  fi


  if [ "$1" != "loop" ]; then
	echo "Exiting loop as param=[$1]"
	exit
  else
	echo Pause short
	sleep 5
  fi

done

