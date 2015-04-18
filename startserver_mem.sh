#!/usr/bin/env bash

OUT_FILE=/tmp/iot-nohup.out
mv -f -v $OUT_FILE $OUT_FILE.last
nohup ./startserver.sh db_mem model_auto_update log=$OUT_FILE > $OUT_FILE &
sleep 2
echo Tailing log file $OUT_FILE you can exit safely with CTRL+C, program will continue to run
tail -f $OUT_FILE
