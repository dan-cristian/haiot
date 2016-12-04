#!/bin/bash
##########################
# MQTT Shell Listen & Exec

LOG=/mnt/log/video.log

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/functions.sh"

screen_on(){
   $DIR/../video/video-start.sh presence
}

listen(){
rm -f $p
([ ! -p "$p" ]) && mkfifo $p
(mosquitto_sub -h $host -t $topic >$p 2>/dev/null) &
#echo "$!" > pidfile
while read line <$p
do
  echo $line | grep -q "$search_screen_on"
  res=$?
  if [ $res -eq 0 ]; then
    #(rm -f $p;rm $clean;kill $pid) 2>/dev/null
    #break
   #echo $line
	screen_on
  else
    #echo "No action res=$res for [$line]"
    :
  fi
done
}

p="/tmp/mqtt_pipe"

host=192.168.0.12
topic=iot/main
search_screen_on='"Presence", "sensor_name": "living"'

while :
do
echo2 "Starting mqtt listener"
listen >> $LOG 2>&1
sleep 10
done
