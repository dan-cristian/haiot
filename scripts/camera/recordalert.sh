#!/bin/bash

#parameters 1:zoneid, 2:message
source ${HAIOT_DIR}/.credentials/.general.credentials
#ignore very fast requests, allow just one every 30 seconds
savefile=/tmp/lastalertdate$1.txt
touch $savefile
datenow=$(date +"%s")
lastdate=$(cat $savefile)
diff=$(($datenow-lastdate))
diffsec=$(($diff % 60))
#echo "Passed $diffsec"
#echo "Passed $(($diff / 60)) $(($diff % 60))"
if [ $diffsec -le 30 ] ; then
	#logger "Alert received too soon seconds passed=$diffsec"
	#echo "too soon"
	:
else
	echo $datenow > $savefile
	logger "Motion alerting cam $1 $2 $3"
	wget -q --output-document=/dev/null --timeout=1 --tries=1 ${HAIOT_API_URL}"/apiv1/camera_alert/zone_name=$1&cam_name=$2&has_move=$3"
fi
