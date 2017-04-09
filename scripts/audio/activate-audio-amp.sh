#!/bin/bash

AMP_URL='http://192.168.0.13:8080/apiv1/db_update/model_name=ZoneCustomRelay&filter_name=relay_pin_name&field_name=relay_is_on'
LOG=/mnt/log/mpd.log

declare -A REMOTE_STATUS
declare -A LOCAL_STATUS
REFRESHED=0

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/../common/include_cards.sh"

#show current status, assume card names start with uppercase to avoid duplicates
tail /proc/asound/[[:upper:]]*/pcm*p/sub0/hw_params
echo Started with parameter [$1]
while :
do
  #execute close command only every 5 minutes
  MIN=`date +"%M"`
  MOD=`expr $MIN % 2`
  LOCAL_STATUS=()

  for i in ${!RELAY_NAME[*]}; do
	cat /proc/asound/${CARD_OUT[$i]}/${DEV_OUT[$i]}/sub0/hw_params | grep -q closed
	state=$?
	if [ "${LOCAL_STATUS[${RELAY_NAME[$i]}]}" == "1" ]; then
		#echo2 "Relay ${RELAY_NAME[$i]} already on, not changing"
		:
	else
		LOCAL_STATUS[${RELAY_NAME[$i]}]=$state #0 for closed, 1 for open
	fi
  done

  #refresh
  if [[ ($MOD -eq 0) && ($REFRESHED -eq 0) ]]; then
  	for i in ${!RELAY_NAME[*]}; do
                state=${LOCAL_STATUS[${RELAY_NAME[$i]}]}
                wget --timeout=10 --tries=1 -O - $AMP_URL'&filter_value='${RELAY_NAME[$i]}'&field_value='$state
                REMOTE_STATUS["${RELAY_NAME[$i]}"]=$state
		REFRESHED=1
  	done
  else
	#changed state
  	for i in ${!RELAY_NAME[*]}; do
        	if [ "${LOCAL_STATUS[${RELAY_NAME[$i]}]}" != "${REMOTE_STATUS[${RELAY_NAME[$i]}]}" ]; then
                	state=${LOCAL_STATUS[${RELAY_NAME[$i]}]}
                	wget --timeout=10 --tries=1 -O - $AMP_URL'&filter_value='${RELAY_NAME[$i]}'&field_value='$state
                	REMOTE_STATUS["${RELAY_NAME[$i]}"]=$state
        	fi
  	done
  fi


  if [ $MOD -eq 0 ]; then
  	REFRESHED=1
  else
	REFRESHED=0
  fi

  if [ "$1" != "loop" ]; then
	echo "Exiting loop as param=[$1]"
	exit
  fi

  sleep 2
done
