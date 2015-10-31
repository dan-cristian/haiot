#!/bin/bash

USERNAME=haiot
USERPASS=haiot
ENABLE_PIFACE=1

echo "Setting timezone ..."
echo "Europe/Bucharest" > /etc/timezone
dpkg-reconfigure -f noninteractive tzdata

echo "Updating apt-get"
apt-get upgrade
apt-get update
echo "Installing additional packages"
# 1-wire support needs owfs
apt-get -y install dialog sudo apt-utils mc nano locales python wget owfs git python-rpi.gpio inotify-tools


echo "Installing python pip and virtualenv"
wget --no-check-certificate https://bootstrap.pypa.io/get-pip.py
python get-pip.py
rm get-pip.py
pip install virtualenv

echo Creating user $USERNAME with password=$USERPASS
useradd $USERNAME -m
echo "$USERNAME:$USERPASS" | chpasswd
adduser $USERNAME sudo
chsh -s /bin/bash $USERNAME

if [ "$ENABLE_PIFACE" == "1" ]; then
    # needed for piface
    apt-get -y install raspi-config python-pifacedigitalio
    #enable spi
    # safest method is to use raspi-config manuallt, and enable SPI in advanced option menu
    cat /boot/config.txt | grep spi=
    if [ "$?" == "0" ]; then
        sed -i 's/spi=off/spi=on/g' /boot/config.txt
    else
        echo "dtparam=spi=on" >> /boot/config.txt
    fi
    # access rights for piface, by default python-pifacedigitalio assumes username as being = pi
    gpasswd -a $USERNAME spi
    # needed to get write access to /sys/class/gpio/
    gpasswd -a $USERNAME gpio
fi



echo Getting HAIOT application from github
cd /home/$USERNAME
git clone http://192.168.0.9:888/PYC.git

echo Downloading pigpio library for gpio access
wget abyz.co.uk/rpi/pigpio/pigpio.zip
unzip pigpio.zip
cd PIGPIO
echo Compiling pigpio
apt-get -y install build-essential
make
echo Installing pigpio
make install
cp /home/$USERNAME/PYC/scripts/pigpio_daemon.sh /etc/init.d
chmod +x /etc/init.d/pigpio_daemon.sh
#python setup.py install
#todo install pigpiod init script

echo Configuring HAIOT application
cd /home/$USERNAME/PYC
chmod +x scripts/*sh*
chmod +x *.sh
scripts/setup.sh.bat
chown -R $USERNAME:$USERNAME .

echo Downloading init service
cd ~
wget https://raw.githubusercontent.com/dan-cristian/userspaceServices/master/userspaceServices
chmod +x userspaceServices
echo Installing init service
mv userspaceServices /etc/init.d/
update-rc.d userspaceServices defaults

echo Testing init service, create working directories for all defined linux users incl. haiot
/etc/init.d/userspaceServices start
/etc/init.d/userspaceServices stop

echo Creating start links for haiot to be picked up by userspaceServices
ln -s /home/$USERNAME/PYC/start_daemon_userspaces.sh /home/$USERNAME/.startUp/
ln -s /home/$USERNAME/PYC/start_daemon_userspaces.sh /home/$USERNAME/.shutDown/
chown -R $USERNAME:$USERNAME /home/$USERNAME/

echo Starting haiot via userspaceServices
/etc/init.d/userspaceServices restart

echo "Removing not needed files and cleaning apt files"
rm /usr/share/doc -r
rm /usr/share/man -r
apt-get -y autoremove
apt-get clean


