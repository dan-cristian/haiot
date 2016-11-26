#!/bin/bash

LOG=/mnt/log/mpd.log

declare -a NAME=("living" 	"bucatarie" 	"dormitor" 	"baie" 		"beci" 	"pod" 	"headset")
declare -a CARD=("DAC" 		"PCH" 		"DGX" 		"Device" 	"DGX"	)
declare -a DEV=("pcm0p" 	"pcm0p" 	"pcm1p" 	"pcm0p" 	"pcm0p")


function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
echo [`date +%T.%N`] $1 $2 $3 $4 $5
}


# 0 [Loopback       ]: Loopback - Loopback
# 1 [PCH            ]: HDA-Intel - HDA Intel PCH
# 2 [DGX            ]: CMI8786 - Xonar DGX
# 3 [Device         ]: USB-Audio - USB Sound Device
# 4 [DAC            ]: USB-Audio - USB Audio DAC
# 5 [C525           ]: USB-Audio - HD Webcam C525
function get_hw(){
local card_name=$1
echo2 "Looking for hw number card $card_name"
cat /proc/asound/cards | grep -q "]:"
while read -r line;
do
	dev=${line% [*} #before
	dev=${dev##* } #after
	name=${line%]:*}
	name=${name##* [}
	name=$(echo $name | xargs ) #remove trailing spaces
	if [ "$card_name" == "$name" ]; then
		echo2 "Found dev=[$dev] name=[$name] target=[$card_name]"
		return $dev
	fi
done < <(cat /proc/asound/cards | grep "]:")
return -1
}

function update_shairport(){
local zone_name=$1
local card=$2
echo2 "Updating shairport config file zone=$zone_name card=$card"
/bin/systemctl stop shairport-sync@$zone_name

#http://www.grymoire.com/Unix/Sed.html#uh-29
sed 's/output_device = .*; /output_device = '$card'; /' "/etc/shairport-sync_"$zone_name".conf"

/bin/systemctl start shairport-sync@$zone_name
}


function get_card_name(){
local zone_name=$1
local i
for i in ${!NAME[*]}; do
	if [ "${NAME[$i]}" == "$zone_name" ]; then
		CARD_NAME=${CARD[$i]}
		echo2 "Found card $CARD_NAME in zone $zone_name"
		return 0
	fi
done
return 1
}


function do_shairport(){
local zone_name=$1
get_card_name $zone_name
get_hw $CARD_NAME
hw=$?
if [ $hw -ne -1 ]; then
	hw_full="hw:$hw,0"
	update_shairport "$zone_name" "$hw_full"
else
	echo2 "Unable to find hw card zone $zone_name"
fi
}


if [ "$1" == "shairport" ]; then
	for i in ${!NAME[*]}; do
		echo2 "Updating zone ${NAME[$i]}"
		do_shairport ${NAME[$i]}
	done
else
	get_card_name $1
	get_hw $CARD_NAME
	hw=$?
	echo $hw
	exit $hw
fi
