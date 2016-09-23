#!/bin/bash
DATE=`date +%Y%m%d-%H%M%S`
OUT_FILE=/mnt/backup/mysql-haiot-backup-$DATE.sql
OUT_FILE_GZ="$OUT_FILE".gz
mysqldump  --user=haiot --password=haiot --host=localhost --protocol=tcp --port=3306 --default-character-set=utf8 --complete-insert=TRUE --single-transaction=TRUE --routines --events "haiot-reporting" | gzip >  $OUT_FILE_GZ
chmod 777 $OUT_FILE_GZ
