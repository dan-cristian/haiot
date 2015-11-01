#!/bin/bash

echo "Starting haiot post-install script, press CTRL+C to abort"
sleep 5
USERNAME=haiot
USERPASS=haiot

#http://linuxconfig.org/enable-ssh-root-login-on-debian-linux-server
#how to avoid ssl cert errors!
#pip install --index-url=http://pypi.python.org/simple/ --trusted-host pypi.python.org  pythonPackage

echo "Updating apt-get"
apt-get -y upgrade
apt-get -y update
echo "Installing additional packages"
# 1-wire support needs owfs
apt-get -y install dialog sudo apt-utils mc nano python wget owfs git inotify-tools mc ca-certificates


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

echo "Installing duplicity and hubic"
# http://www.yvangodard.me/hubic-backup-duplicity-backend-pyrax/
# https://www.tiernanotoole.ie/2015/04/01/Duplicity_Hubic.html
apt-get -y purge duplicity
apt-get -y install fuse
# http://serverfault.com/questions/22414/how-can-i-run-debian-stable-but-install-some-packages-from-testing
echo "Package: *
Pin: release a=unstable
Pin-Priority: 50" > /etc/apt/preferences.d/unstable.pref
echo "deb     http://ftp.us.debian.org/debian/    unstable main contrib non-free" > /etc/apt/sources.list.d/unstable.list
apt-get update
apt-get -y -t unstable install duplicity
echo "Installing pyrax prerequisite for hubic support"
pip install --no-cache-dir --index-url=http://pypi.python.org/simple/ --trusted-host pypi.python.org  setuptools-scm
apt-get -y install build-essential python-dev
pip install --no-cache-dir pyrax
echo "[hubic]
email = <hubicemailaddress>
password = <hubicpassword>
client_id = <hubicclientid>
client_secret = <hubicclientsecret>
redirect_uri = http://localhost/" > /home/$USERNAME/.hubic_credentials
chown $USERNAME /home/$USERNAME/.hubic_credentials
chmod 700 /home/$USERNAME/.hubic_credentials


echo "Installing webmin"
echo "deb http://download.webmin.com/download/repository sarge contrib
deb http://webmin.mirror.somersettechsolutions.co.uk/repository sarge contrib" > /etc/apt/sources.list.d/webmin.list
wget http://www.webmin.com/jcameron-key.asc
apt-key add jcameron-key.asc
apt-get update
apt-get -y install webmin
apt-get -f install

echo "Installing mdd"
# http://zackreed.me/articles/84-snapraid-with-mhddfs?view=comments
apt-get install -y mhddfs

echo "Installing hubicfuse"
# https://github.com/TurboGit/hubicfuse
cd /root
git clone https://github.com/TurboGit/hubicfuse.git
apt-get install -y gcc make curl libfuse-dev pkg-config \
            libcurl4-openssl-dev libxml2-dev libssl-dev libjson-c-dev \
            libmagic-dev
cd hubicfuse
./configure
make
make install
apt-get remove -y gcc make curl libfuse-dev pkg-config \
            libcurl4-openssl-dev libxml2-dev libssl-dev libjson-c-dev \
            libmagic-dev
echo "run hubic_token script to create $HOME/.hubicfuse file"

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
apt-get -y remove build-essential python-dev
rm /usr/share/doc -r
rm /usr/share/man -r
apt-get -y autoremove
apt-get clean
