#!/bin/bash

AMP_URL='http://192.168.0.12:8080/apiv1/db_update/model_name=ZoneCustomRelay&filter_name=relay_pin_name&field_name=relay_is_on'
AMP_URL_V2='http://192.168.0.12:8080/apiv1/amp_power/state=<power_state>&relay_name=<relay_name>&amp_zone_index=<amp_zone_index>'
LOG=/mnt/log/activate-amp.log

declare -A REMOTE_STATUS
declare -A LOCAL_STATUS
declare -A LOCAL_ZONE_STATUS
REFRESHED=0

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/../common/include_cards.sh"

# $1=action $2=relay_name $3=card_name $4=state $5=zone_index
function do_url {
echo2 "$1 relay $2 in $3 index $5 to state=$4"
NEW_URL="${AMP_URL_V2/<power_state>/$4}"
NEW_URL="${NEW_URL/<relay_name>/$2}"
NEW_URL="${NEW_URL/<amp_zone_index>/$5}"
wget --timeout=10 --tries=1 -nv -O - $NEW_URL
REMOTE_STATUS["$2$5"]=$4
}


#show current status, assume card names start with uppercase to avoid duplicates
tail /proc/asound/[[:upper:]]*/pcm*p/sub0/hw_params
echo Started with parameter [$1]
while :
do
  #execute close command only every 5 minutes
  MIN=`date +"%M"`
  if [ "$1" != "loop" ]; then
	# force a refresh if script is run once
	MOD=0
  else
  	MOD=`expr $MIN % 5`
  fi

  LOCAL_STATUS=()
  LOCAL_ZONE_STATUS=()

  for i in ${!RELAY_NAME[*]}; do
	cat /proc/asound/${CARD_OUT[$i]}/${DEV_OUT[$i]}/sub0/hw_params | grep -q closed
	state=$?
	relay_name=${RELAY_NAME[$i]}
	zone_index=${RELAY_AMP_ZONE[$i]}
	# handle amp zones differently
	if [ "$zone_index" != "0" ]; then
		LOCAL_ZONE_STATUS[$relay_name$zone_index]=$state #0 for closed, 1 for open
	fi
	# if no amp zone
	if [ "${LOCAL_STATUS[$relay_name]}" == "1" ]; then
		#echo2 "Relay $relay_name in ${CARD_NAME[$i]} already on, ignoring"
		:
	else
		#echo2 "Relay $relay_name in ${CARD_NAME[$i]} is $state"
		LOCAL_STATUS[$relay_name]=$state #0 for closed, 1 for open
	fi
  done

  #refresh
  if [[ ($MOD -eq 0) && ($REFRESHED -eq 0) ]]; then
  	for i in ${!RELAY_NAME[*]}; do
		relay_name=${RELAY_NAME[$i]}
                zone_index=${RELAY_AMP_ZONE[$i]}
                if [ "$zone_index" == "0" ]; then
                        state=${LOCAL_STATUS[${RELAY_NAME[$i]}]}
                else
                        state=${LOCAL_ZONE_STATUS[$relay_name$zone_index]}
                fi
		# $1=action $2=relay_name $3=card_name $4=state $5=zone_index
		do_url "Refresh" "$relay_name" "${CARD_NAME[$i]}" "$state" "$zone_index"
		#wget --timeout=10 --tries=1 -O - $AMP_URL'&filter_value='${RELAY_NAME[$i]}'&field_value='$state
		REFRESHED=1
  	done
  else
	#changed state. run on power on, delayed off at refresh
  	for i in ${!RELAY_NAME[*]}; do
		relay_name=${RELAY_NAME[$i]}
		zone_index=${RELAY_AMP_ZONE[$i]}
		if [ "$zone_index" == "0" ]; then
                	state=${LOCAL_STATUS[${RELAY_NAME[$i]}]}
		else
			state=${LOCAL_ZONE_STATUS[$relay_name$zone_index]}
		fi
        	if [[ (("$state" == "1") || ("$zone_index" != "0"))  && ("$state" != "${REMOTE_STATUS[$relay_name$zone_index]}") ]]; then
			# $1=action $2=relay_name $3=card_name $4=state $5=zone_index
			do_url "Set" "$relay_name" "${CARD_NAME[$i]}" "$state" "$zone_index"
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
