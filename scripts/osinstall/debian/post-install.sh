#!/bin/bash

USERNAME=haiot
USERPASS=haiot

#http://linuxconfig.org/enable-ssh-root-login-on-debian-linux-server

echo "Updating apt-get"
apt-get -y upgrade
apt-get -y update
echo "Installing additional packages"
# 1-wire support needs owfs
apt-get -y install dialog sudo apt-utils mc nano python wget owfs git inotify-tools localepurge

cd /root
echo "Installing python pip and virtualenv"
wget --no-check-certificate https://bootstrap.pypa.io/get-pip.py
python get-pip.py
rm get-pip.py
pip install --no-cache-dir virtualenv

echo "Creating user $USERNAME with password=$USERPASS"
useradd $USERNAME -m
echo "$USERNAME:$USERPASS" | chpasswd
adduser $USERNAME sudo
chsh -s /bin/bash $USERNAME

echo "Getting HAIOT application from github"
cd /home/$USERNAME
git clone http://192.168.0.9:888/PYC.git


echo "Configuring HAIOT application"
cd /home/$USERNAME/PYC
chmod +x scripts/*sh*
chmod +x *.sh
scripts/setup.sh.bat
chown -R $USERNAME:$USERNAME .

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
ln -s /home/$USERNAME/PYC/start_daemon_userspaces.sh /home/$USERNAME/.startUp/
ln -s /home/$USERNAME/PYC/start_daemon_userspaces.sh /home/$USERNAME/.shutDown/
chown -R $USERNAME:$USERNAME /home/$USERNAME/

echo "Starting haiot via userspaceServices"
/etc/init.d/userspaceServices restart

echo "Removing not needed files and cleaning apt files"
apt-get -y remove build-essential
rm /usr/share/doc -r
rm /usr/share/man -r
apt-get -y autoremove
apt-get clean
