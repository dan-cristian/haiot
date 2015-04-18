#!/usr/bin/env bash

OUT_FILE=/tmp/iot-nohup.out
mv -f -v $OUT_FILE $OUT_FILE.last
./startserver.sh db_mem model_auto_update log=$OUT_FILE
