#!/bin/bash

#sound output
#declare -a NAME=("living" "headset" "dormitor" "baie" "beci" "pod")
declare -a CARD_NAME=("living" "headset" "dormitor" "baie" "beci" "pod")
declare -a RELAY_NAME=("living_music_relay" "none"  "dormitor_music_relay" "baie_mare_music_relay" "beci_music_relay" "pod_music_relay")
#declare -a CARD=("DAC" "PCH" "DGX" "Device" "DGX" "none")
declare -a CARD_OUT=("PCH" "PCH" "DGX" "Device" "DGX" "DAC")
	# 1 is usualy digital, 0 is analog
#declare -a DEV=("pcm0p" "pcm0p" "pcm1p" "pcm0p" "pcm0p" "")
declare -a DEV_OUT=("pcm8p" "pcm0p" "pcm1p" "pcm0p" "pcm0p" "pcm0p")

#sound capture
declare -a RECORD_SOURCE_LIST=("hol" "cast")
declare -a RECORD_DEVICE_LIST=("C525,0,0" "Device,0,0")
declare -a DEV_CAPT=("pcm0c" "pcm0c" "pcm1c" "pcm0c" "pcm0c" "")
declare -a CARD_CAPT=("Loopback" "PCH" "DGX" "Device" "DGX" "")

#MPD settings
#declare -a PORT=(6600 6601 6603 6604 6602 6605)
#declare -a PORT_LIST=(6600 6601 6603 6604 6602 6605)
declare -a MPD_PORT_LIST=(6600 6601 6603 6604 6602 6605)

#declare -a OUTPUT=("Digital Small USB (living2)" "Digital Onboard (Bluetooth)" "Digital DGX PCIe (dormitor)" "Digital Box USB (baie)" "Analog DGX PCIe (beci)" "")
declare -a MPD_OUTPUT=("Onboard-PCH HDMI2 (living)" "Onboard-PCH Optical (headset)" "PCI-DGX Optical (dormitor)" "MediumUsb-Device Optical (baie)" "PCI-DGX Analog (beci)" "SmallUsb-DAC Optical (pod)")

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
