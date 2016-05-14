#!/bin/bash
#kill $(cat /var/run/thd.pid)
killall thd
thd --triggers /etc/triggerhappy/triggers.conf --socket /var/run/thd.socket  --pidfile /var/run/thd.pid  --daemon
th-cmd  --socket /var/run/thd.socket --tag living --add  /dev/input/by-id/usb-Microsoft_Microsoft®_2.4GHz_Transceiver_v8.0-event-kbd
th-cmd  --socket /var/run/thd.socket --tag bucatarie --add /dev/input/by-id/usb-CHESEN_USB_Keyboard-event-kbd
th-cmd  --socket /var/run/thd.socket --tag baie --add /dev/input/by-id/usb-Cyp_Se_WitheHome-event-mouse
