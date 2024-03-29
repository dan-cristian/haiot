#!/bin/bash

USERNAME=haiot
USERPASS=haiot
ENABLE_PIFACE=1
ENABLE_DFROBOT=0
ENABLE_PIGPIO=0
ENABLE_WEBMIN=0
ENABLE_OPTIONAL=0
ENABLE_BACKUP=1
ENABLE_HAIOT=1
ENABLE_RUN_IN_RAM=0

echo "Setting timezone ..."
echo "Europe/Bucharest" > /etc/timezone
dpkg-reconfigure -f noninteractive tzdata

echo "Updating apt-get"
apt-get -y update
apt-get -y upgrade

echo "Installing additional packages"
# 1-wire support needs owfs
apt-get -y install dialog sudo nano locales python wget owfs git python-rpi.gpio python-dev rpi-update wiringpi ssmtp mailutils mosquitto

if [ "$ENABLE_HAIOT" == "1" ]; then
    apt-get -y install dialog sudo nano locales python wget git python-rpi.gpio python-dev rpi-update ssmtp mailutils
fi

if [ "$ENABLE_RUN_IN_RAM" == "1" ]; then
    # run in ram needs busybox for ramfs copy operations, see "local" script sample
    apt-get -y install busybox
fi

if [ "$ENABLE_OPTIONAL" == "1" ]; then
	apt-get -y install htop apt-utils mc inotify-tools dosfstools
fi

pip -V
if [ "$?" != "0" ]; then
	echo "Installing python pip"
	wget --no-check-certificate https://bootstrap.pypa.io/get-pip.py
	python get-pip.py
	rm get-pip.py
fi
virtualenv  --version
if [ "$?" != "0" ]; then
	echo "Installing virtualenv"
	pip install --no-cache-dir virtualenv
fi

echo "Creating user $USERNAME with password=$USERPASS"
useradd ${USERNAME} -m
echo "$USERNAME:$USERPASS" | chpasswd
adduser ${USERNAME} sudo
adduser ${USERNAME} audio
chsh -s /bin/bash ${USERNAME}

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
    gpasswd -a ${USERNAME} spi
fi



echo "Getting HAIOT application from github"
cd /home/${USERNAME}
rm -r PYC
git clone git://192.168.0.9/PYC.git
if [ "$?" == "0" ]; then
    echo "Dowloaded haiot from local repository"
    HAIOT_DIR=PYC
else
    echo "Downloading haiot from github"
    git clone https://github.com/dan-cristian/haiot.git
    HAIOT_DIR=haiot
fi

if [ "$ENABLE_DFROBOT" == "1" ]; then
    echo "Configuring DFRobot screen"
	# http://unix.stackexchange.com/questions/72320/how-can-i-hook-on-to-one-terminals-output-from-another-terminal
	# script -f /dev/tty1
	# cmdline.txt=dwc_otg.lpm_enable=0 console=ttyAMA0,115200 console=tty1 root=/dev/mmcblk0p2 rootfstype=ext4
	#   cgroup_enable=memory elevator=deadline rootwait fbcon=font:ProFont6x11 fbcon=map:1 consoleblank=0
	# http://docs.robopeak.net/doku.php?id=rpusbdisp_faq#q12
	# https://www.kernel.org/doc/Documentation/fb/fbcon.txt
	# page 19: http://www.robopeak.com/data/doc/rpusbdisp/RPUD02-rpusbdisp_usermanual-enUS.1.1.pdf
	# https://learn.adafruit.com/adafruit-pitft-28-inch-resistive-touchscreen-display-raspberry-pi/using-the-console
	# ABOVE NOT WORKING for PIZEROW, try DKMS below
	# https://github.com/pimoroni/rp_usbdisplay/tree/master/dkms
	# stty rows 30 cols 40
	# setfont -f Uni2-VGA8
    apt-get -y install gpm
fi

if [ "$ENABLE_WEBMIN" == "1" ]; then
	echo "Installing minimal webmin"
	wget http://prdownloads.sourceforge.net/webadmin/webmin-1.791-minimal.tar.gz
	tar -xvzf webmin-1.791-minimal.tar.gz
	mv webmin-1.791 /opt/
	echo "Configure webmin"
	/opt/webmin-1.791/setup.sh <<EOF




admin
admin123
admin123
y
EOF
fi

#echo "Installing kivy prerequisites"
# http://kivy.org/docs/installation/installation-linux.html
#apt-get install -y libsdl2-dev

echo "Configuring HAIOT application"
cd /home/${USERNAME}/${HAIOT_DIR}
chmod +x scripts/*sh*
chmod +x *.sh
scripts/setup.sh
chown -R ${USERNAME}:${USERNAME} .

echo "Downloading haiot init service"
cd ~
wget --no-check-certificate https://raw.githubusercontent.com/dan-cristian/userspaceServices/master/userspaceServices
chmod +x userspaceServices
echo "Installing init service"
mv userspaceServices /etc/init.d/
update-rc.d userspaceServices defaults

echo "Testing init service, create working directories for all defined linux users incl. haiot"
/etc/init.d/userspaceServices start
/etc/init.d/userspaceServices stop

echo "Creating start links for haiot to be picked up by userspaceServices"
ln -s /home/${USERNAME}/${HAIOT_DIR}/start_daemon_userspaces.sh /home/${USERNAME}/.startUp/
ln -s /home/${USERNAME}/${HAIOT_DIR}/start_daemon_userspaces.sh /home/${USERNAME}/.shutDown/
#set proper owner on all user homedir files (as they were created by root)
chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}/

echo "Create tmpfs"
# http://www.zdnet.com/article/raspberry-pi-extending-the-life-of-the-sd-card/
sudo mkdir /var/ram
sudo chmod 777 /var/ram/

echo "Enable sound test via console"
sudo chmod 777 /dev/snd/*

echo "Enable SPI via raspi-config if you have a PI-FACE card"
sleep 5
sudo raspi-config

cat /etc/fstab | grep "/var/ram"
if [ "$?" == "1" ]; then
	echo "Add ram folder for sqlite db storage and logs"
	sudo echo "tmpfs           /var/ram        tmpfs   defaults,noatime        0       0" >> /etc/fstab
	sudo echo "tmpfs           /var/log        tmpfs   defaults,noatime        0       0" >> /etc/fstab
	sudo echo "tmpfs           /tmp            tmpfs   defaults,noatime        0       0" >> /etc/fstab
	sudo mount -a
else
	echo "Ram folder for sqlite db storage exists already"
fi

# https://www.cyberciti.biz/tips/linux-use-gmail-as-a-smarthost.html
# http://iqjar.com/jar/sending-emails-from-the-raspberry-pi/
cat /etc/ssmtp/ssmtp.conf | grep "smtp.gmail.com"
if [ "$?" == "1" ]; then
    echo "Setting email"
    echo "AuthUser=antonio.gaudi33@gmail.com" >> /etc/ssmtp/ssmtp.conf
    echo "AuthPass=<your_password>" >> /etc/ssmtp/ssmtp.conf
    echo "FromLineOverride=YES" >> /etc/ssmtp/ssmtp.conf
    echo "mailhub=smtp.gmail.com:587" >> /etc/ssmtp/ssmtp.conf
    echo "UseSTARTTLS=YES" >> /etc/ssmtp/ssmtp.conf
    echo "Now enter your password in email conf and save with CTRL+x"
    sleep 3
    nano /etc/ssmtp/ssmtp.conf
    echo "Sending test email"
    echo "This is a test" | mail -s "Test" dan.cristian@gmail.com
fi

echo "Enable gpio access"
sudo gpasswd -a $USERNAME gpio
echo "Allow mail access"
sudo gpasswd -a $USERNAME mail

echo "Starting haiot via userspaceServices"
/etc/init.d/userspaceServices restart

echo "Removing not needed files and cleaning apt files"
apt-get -y remove build-essential
rm /usr/share/doc -r
rm /usr/share/man -r
apt-get -y autoremove
apt-get clean

echo "Consider running also rpi-update"
#sudo rpi-update
