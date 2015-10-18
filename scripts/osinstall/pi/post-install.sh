#!/bin/bash

echo "Setting timezone ..."
echo "Europe/Bucharest" > /etc/timezone 
dpkg-reconfigure -f noninteractive tzdata

echo "Updating apt-get"
apt-get upgrade
apt-get update
echo "Installing additional packages"
apt-get -y install sudo apt-utils mc nano locales rsync python wget owfs git python-rpi.gpio inotify-tools

echo "Installing python pip and virtualenv"
wget --no-check-certificate https://bootstrap.pypa.io/get-pip.py
python get-pip.py
rm get-pip.py
pip install virtualenv

echo Creating user haiot with password=haiot
useradd haiot -m
echo "haiot:haiot" | chpasswd
#passwd haiot

echo Getting HAIOT application
cd /home/haiot
git clone http://192.168.0.9:888/PYC.git

echo Configuring HAIOT application
cd PYC 
chmod +x scripts/*sh*
scripts/setup.sh.bat
chown -R haiot:haiot .
#todo init scripts

echo "Removing not needed files and cleaning apt files"
rm /usr/share/doc -r
rm /usr/share/man -r
apt-get -y autoremove
apt-get clean


