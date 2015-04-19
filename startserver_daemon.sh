#!/usr/bin/env bash

OUT_FILE=/tmp/iot-nohup.out
#mv -f -v $OUT_FILE $OUT_FILE.last
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
$DIR/startserver.sh db_mem model_auto_update syslog=logs2.papertrailapp.com:30445 log=$OUT_FILE $1 $2 $3 $4 $5 > $OUT_FILE 2>&1
