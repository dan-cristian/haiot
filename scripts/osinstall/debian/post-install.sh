#!/usr/bin/env bash

function check_err {
    if [ "$2" == "0" ]; then
        echo "$1 completed OK"
    else
        echo "$1 FAILED with code $2, stopping script"
        exit
    fi
}

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
OP="Installing additional packages"; echo ${OP}
# 1-wire support needs owfs
apt-get -y install dialog sudo apt-utils mc nano python wget owfs git inotify-tools mc ca-certificates unzip
check_err "${OP}" $?

cd /root
OP="Installing python pip"; echo ${OP}
wget --no-check-certificate https://bootstrap.pypa.io/get-pip.py
python get-pip.py
check_err "${OP}" $?
rm get-pip.py
OP="Installing python virtualenv"; echo ${OP}
pip install --no-cache-dir virtualenv
check_err "${OP}" $?

OP="Creating user $USERNAME with password=$USERPASS"; echo ${OP}
useradd ${USERNAME} -m
echo "$USERNAME:$USERPASS" | chpasswd
adduser ${USERNAME} sudo
chsh -s /bin/bash ${USERNAME}
check_err "${OP}" $?

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
rm -f /etc/apt/sources.list.d/unstable.list
apt-get update
echo "Installing pyrax prerequisite for hubic support"
pip install --no-cache-dir --index-url=http://pypi.python.org/simple/ --trusted-host pypi.python.org  setuptools-scm
apt-get -y install build-essential python-dev
pip install --no-cache-dir pyrax
echo "[hubic]
email = <hubicemailaddress>
password = <hubicpassword>
client_id = <hubicclientid>
client_secret = <hubicclientsecret>
redirect_uri = http://localhost/" > /home/${USERNAME}/.hubic_credentials
chown ${USERNAME} /home/${USERNAME}/.hubic_credentials
chmod 700 /home/${USERNAME}/.hubic_credentials


echo "Installing webmin"
echo "deb http://download.webmin.com/download/repository sarge contrib
deb http://webmin.mirror.somersettechsolutions.co.uk/repository sarge contrib" > /etc/apt/sources.list.d/webmin.list
wget http://www.webmin.com/jcameron-key.asc
apt-key add jcameron-key.asc
rm jcameron-key.asc
apt-get update
apt-get -y install webmin
apt-get -f install

echo "Installing mdd"
# http://zackreed.me/articles/84-snapraid-with-mhddfs?view=comments
apt-get install -y mhddfs

echo "Installing hubicfuse"
# https://github.com/TurboGit/hubicfuse
# make sure you apply this fix: https://github.com/TurboGit/hubicfuse/issues/86
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
cd ..
rm -rf hubicfuse
echo "run hubic_token script to create $HOME/.hubicfuse file"

echo "Getting HAIOT application from github"
cd /home/${USERNAME}
git clone http://192.168.0.9:888/PYC.git
if [ "$?" == "0" ]; then
    echo "Dowloaded haiot from local repository"
    HAIOT_DIR=PYC
else
    echo "Downloading haiot from github"
    git clone https://github.com/dan-cristian/haiot.git
    HAIOT_DIR=haiot
fi

echo "Configuring HAIOT application"
cd /home/${USERNAME}/${HAIOT_DIR}
chmod +x scripts/*sh*
chmod +x *.sh
scripts/setup.sh.bat
chown -R ${USERNAME}:${USERNAME} .

echo "Downloading haiot init service"
cd /root
wget --no-check-certificate https://raw.githubusercontent.com/dan-cristian/userspaceServices/master/userspaceServices
chmod +x userspaceServices
echo "Installing init service"
mv userspaceServices /etc/init.d/
update-rc.d userspaceServices defaults

echo "Testing init service, create working directories for all defined linux users incl. haiot"
/etc/init.d/userspaceServices start
/etc/init.d/userspaceServices stop

echo "Creating start links for haiot to be picked up by userspaceServices"
rm -f /home/${USERNAME}/.startUp/start_daemon_userspaces.sh
rm -f /home/${USERNAME}/.shutDown/start_daemon_userspaces.sh
ln -s /home/${USERNAME}/${HAIOT_DIR}/start_daemon_userspaces.sh /home/${USERNAME}/.startUp/
ln -s /home/${USERNAME}/${HAIOT_DIR}/start_daemon_userspaces.sh /home/${USERNAME}/.shutDown/
chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}/

echo "Starting haiot via userspaceServices"
/etc/init.d/userspaceServices restart

echo "Removing not needed files and cleaning apt files"
apt-get -y remove build-essential python-dev
rm /usr/share/doc -r
rm /usr/share/man -r
apt-get -y autoremove
apt-get clean

cat /root/.profile | grep "echo haiot setup"
if [ "$?" == "0" ]; then
    cat /root/.profile | grep "#echo haiot setup"
    if [ "$?" == "0" ]; then
        echo "Post-install haiot script already executed"
    else
        echo "Disabling post install script automatic execution"
        sed -i 's|'"echo haiot setup"'|#echo haiot setup|g' /root/.profile
    fi
fi
