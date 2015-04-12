#!/usr/bin/env bash

OUT_FILE = /tmp/iot-nohup.out
nohup ./startserver.sh db_mem model_auto_update > $OUT_FILE &

mv $OUT_FILE $OUT_FILE.last