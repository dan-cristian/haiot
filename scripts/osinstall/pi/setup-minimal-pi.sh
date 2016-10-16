#!/usr/bin/env bash
#script to remove unnecesary packages from a raspbian minimal install

#https://wiki.debian.org/ReduceDebian
#http://www.cnx-software.com/2012/07/31/84-mb-minimal-raspbian-armhf-image-for-raspberry-pi/

dpkg-query -Wf '${Installed-Size}\t${Package}\n' | sort -n

apt-get -y remove oracle-java8-jdk wolfram-engine sonic-pi scratch libraspberrypi-doc nuscratch python3.2 python3 python3-minimal lightdm x11-common libopencv-* python2.7-dev libgtk2.0-common libgtk-3-common vim-runtime gnome-* desktop-base apache2 freepats libgl1-mesa-dri nodejs python2.6 midori lxde ppp manpages avahi-daemon omxplayer epiphany-browser-data libjavascriptcoregtk-3.0-0 python3.2-minimal minecraft-pi penguinspuzzle tcl8.5 tcl8.4 fonts-droid lxde-icon-theme ttf-dejavu-core poppler-data fonts-freefont-ttf libatlas3-base bluez winbind gdb wpasupplicant --purge

rm -rf /usr/lib/chromium/
rm /usr/share/doc -r
rm -r /usr/share/icons
#python2.6-minimal python2.7-minimal libasound2 libcaca0 libgphoto2-port0 aspell-en  x11-xserver-utils libx11-xcb1 vim-common libruby1.9.1 libwebkitgtk-1.0-0 libgphoto2-2 ruby ruby-dev geoip-database   xscreensaver-data apache2.2-common  apache2-utils


apt-get -y install localepurge  
localepurge
apt-get -y remove winbind --purge
apt-get -y autoremove
apt-get clean
