#!/usr/bin/env bash
function log(){
	logger -t haiot $1
	echo $1
}

start(){
#OUT_FILE=/tmp/iot-nohup.out
#mv -f -v $OUT_FILE $OUT_FILE.last
#$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
log "Current dir for haiot daemon is $DIR. Pause for 10 seconds to allow network interfaces to start."
sleep 10
cd $DIR
./startserver.sh db_mem model_auto_update syslog=logs2.papertrailapp.com:30445 $1 $2 $3 $4 $5  2>&1 | logger -t haiot
log "Haiot startserver daemon exit" # >> $OUT_FILE
}

stop() {
	me=`basename $0`
	log "Stopping script $me"
    cd $DIR
    ./scripts/stopserver.sh 2>&1 | logger -t haiot
}

log "Executing script with parameter $1 $2 $3"
DIR="$(dirname "$(readlink -f "$0")")"
if [ "$1" = "stop" ]; then
        stop
else
        start
fi

