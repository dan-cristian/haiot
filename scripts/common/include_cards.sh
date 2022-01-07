#!/bin/bash

#sound output
declare -a CARD_NAME=("living" "living_sub" "bucatarie" "headset" "dormitor" "baie" "beci" "pod")
# living zone is mentioned twice to power on both amp and sub relays
declare -a RELAY_NAME=("living_music_relay" "living_sub_relay" "living_music_relay" "none" "dormitor_music_relay" "living_music_relay" "living_music_relay" "pod_music_relay")
#amplifier zone if amp supports multiple zones. 0 if n/a
declare -a RELAY_AMP_ZONE=("0" "0" "1" "0" "0" "3" "2" "0")
declare -a CARD_OUT=("PCH" "PCH" "Loopback" "PCH" "DGX" "Device" "DGX" "DAC")
	# 1 is usualy digital, 0 is analog
declare -a DEV_OUT=("pcm8p" "pcm8p" "pcm1p" "pcm1p" "pcm1p" "pcm0p" "pcm0p" "pcm0p")

#sound capture
declare -a RECORD_SOURCE_LIST=("hol" "cast")
declare -a RECORD_DEVICE_LIST=("C525,0,0" "Device,0,0")
declare -a DEV_CAPT=("pcm0c" "" "" "pcm0c" "pcm1c" "pcm0c" "pcm0c" "")
declare -a CARD_CAPT=("Loopback" "" "" "PCH" "DGX" "Device" "DGX" "")

# device used to redirect input to loopback
loop_input_device='Device'

#MPD settings
declare -a MPD_PORT_LIST=(6600 6600 6600 6601 6603 6604 6602 6605)
declare -a MPD_OUTPUT=("Onboard-PCH HDMI2 (living)" "Onboard-PCH HDMI2 (living)" "Loop (bucatarie)" "Onboard-PCH Optical (headset)" "PCI-DGX Optical (dormitor)" "Onboard-PCH Analog (baie)" "PCI-DGX Analog (beci)" "SmallUsb-DAC Optical (pod)")

function echo2(){
echo [`date +%T.%N`] $1 $2 $3 $4 $5 >> $LOG 2>&1
echo [`date +%T.%N`] $1 $2 $3 $4 $5
}

function get_card_index_by_name(){
local zone_name=$1
local i
for i in ${!CARD_NAME[*]}; do
	if [ "${CARD_NAME[$i]}" == "$zone_name" ]; then
		return $i
	fi
done
return -1
}
