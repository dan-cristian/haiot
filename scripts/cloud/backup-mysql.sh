#!/bin/bash
DATE=`date +%Y%m%d-%H%M%S`
OUT_FILE=/mnt/backup/mysql-haiot-backup-$DATE.sql.gz
mysqldump  --host=localhost --protocol=tcp --port=3306 --default-character-set=utf8 --complete-insert=TRUE --single-transaction=TRUE --routines --events "haiot-reporting" | gzip >  $OUT_FILE


OUT_FILE=/mnt/backup/mysql-nextcloud-backup-$DATE.sql.gz
mysqldump  --host=localhost --protocol=tcp --port=3306 --default-character-set=utf8 --complete-insert=TRUE --single-transaction=TRUE --routines --events "nextcloud" | gzip >  $OUT_FILE
