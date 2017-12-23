#!/usr/bin/env bash

/home/haiot/PYC/scripts/common/haveinternet.sh

if [ ! -f /tmp/haveinternet ]; then
    ifconfig | grep ppp0
    if [ $? -eq 1 ]; then
        wvdial &
    else
        echo "Restarting ppp"
        killall pppd
        wvdial &
    fi
fi