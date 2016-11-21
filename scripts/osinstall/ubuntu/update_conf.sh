#!/bin/bash

echo "Copying relevant conf files from system to GIT repo. Press CTRL+C if you are unsure."
sleep 10
CONF=$HAIOT_DIR/scripts/osinstall/ubuntu/etc

cp -vi /etc/motion/*.conf $CONF/motion/
cp -vi /etc/triggerhappy/triggers.conf $CONF/triggerhappy/
cp -vi /etc/mpd.conf $CONF/
cp -vi /etc/upmpdcli*.conf $CONF/
