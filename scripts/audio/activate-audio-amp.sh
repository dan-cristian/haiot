#!/bin/bash

AMP_URL='http://192.168.0.13:8080/apiv1/db_update/model_name=ZoneCustomRelay&filter_name=relay_pin_name&field_name=relay_is_on'
CLOSED_DONE=0
CLOSED_DONE_LOOP=0
LOG=/mnt/log/mpd.log

REMOTE_STATUS=()
LOCAL_STATUS=()
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
  MOD=`expr $MIN % 5`

  for i in ${!RELAY[*]}; do
	cat /proc/asound/${CARD[$i]}/${DEV[$i]}/sub0/hw_params | grep -q closed
	LOCAL_STATUS[$i]=$? #0 for closed, 1 for open
	if [ "${LOCAL_STATUS[$i]}" != "${REMOTE_STATUS[$i]}" ] || [ $MOD -eq 0 ] && [ "$REFRESHED" == "0" ]; then
		if [ "${LOCAL_STATUS[$i]}" == "0" ] && [ $MOD -ne 0 ]; then
			DO_REMOTE=0
		else
			DO_REMOTE=1
		fi
		if [ $DO_REMOTE -eq 1 ]; then
			echo2 "Set amp relay to ${LOCAL_STATUS[$i]} for ${NAME[$i]}"
			wget --timeout=10 --tries=1 -S -O - $AMP_URL'&filter_value='${RELAY[$i]}'&field_value='${LOCAL_STATUS[$i]}
			REMOTE_STATUS[$i]=${LOCAL_STATUS[$i]}
			REFRESHED=1
		fi
	fi
  done

  if [ $MOD -ne 0 ]; then
  	REFRESHED=0
  fi

  if [ "$1" != "loop" ]; then
	echo "Exiting loop as param=[$1]"
	exit
  fi

  sleep 2
done
