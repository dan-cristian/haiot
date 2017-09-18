#!/bin/bash

echo "Run this script with root account"

USERNAME=haiot
USERPASS=haiot
ENABLE_WEBMIN=0
ENABLE_OPTIONAL=0
ENABLE_HAIOT=0
ENABLE_RAMRUN=0
ENABLE_MEDIA=0
MUSIC_ROOT=/mnt/data/hdd-wdr-evhk/music

ENABLE_SNAPRAID=0
DATA_DISK1=/mnt/data/hdd-wdg-6297
DATA_DISK2=/mnt/data/hdd-wdr-evhk
PARITY_DISK=/mnt/parity/hdd-wdg-2130

VIDEOS_ROOT=/mnt/data/hdd-wdr-evhk/videos
PHOTOS_ROOT=/mnt/data/hdd-wdg-6297/photos
PRIVATE_ROOT=/mnt/data/hdd-wdg-6297/private
EBOOKS_ROOT=/mnt/data/hdd-wdg-6297/ebooks

ENABLE_GIT=0
GIT_ROOT=/mnt/data/hdd-wdg-6297/git

ENABLE_CAMERA=0
ENABLE_CAMERA_SHINOBI=0
MOTION_ROOT=/mnt/data/hdd-wdr-evhk/motion
LOG_ROOT=/mnt/data/hdd-wdr-evhk/log

ENABLE_TORRENT=0
#ENABLE_SAMBA=1
ENABLE_CLOUD_AMAZON=0

ENABLE_MYSQL_SERVER=0
MYSQL_DATA_ROOT=/mnt/data/hdd-wdr-evhk/mysql

ENABLE_DASHBOARD=0
ENABLE_ALEXA=0

ENABLE_BACKUP=0
ENABLE_VPN_SERVER=0
ENABLE_SECURE_SSH=0

ENABLE_ROUTER=0

echo "Setting timezone ..."
echo "Europe/Bucharest" > /etc/timezone
dpkg-reconfigure -f noninteractive tzdata

echo "Updating apt-get and upgrade"
if [ ! -f /tmp/updated ]; then
    apt-get -y update
    apt-get -y upgrade
    touch /tmp/updated
else
    echo "Skipping update & upgrade, already done!"
fi

echo "Installing additional generic packages"
apt-get -y install ssh dialog sudo nano wget runit git ssmtp mailutils psmisc smartmontools localepurge gpm davfs2


echo "Creating user $USERNAME with password=$USERPASS"
useradd ${USERNAME} -m
echo "$USERNAME:$USERPASS" | chpasswd
adduser ${USERNAME} sudo
adduser ${USERNAME} audio
adduser ${USERNAME} video
adduser ${USERNAME} tty
chsh -s /bin/bash ${USERNAME}


if [ "$ENABLE_RAMRUN" == "1" ]; then
    # run in ram needs busybox for ramfs copy operations, see "local" script sample
    apt-get -y install busybox
fi

if [ "$ENABLE_OPTIONAL" == "1" ]; then
	apt-get -y install htop mc
	# inotify-tools dosfstools apt-utils
fi

if [ "$ENABLE_WEBMIN" == "1" ]; then
    cat /etc/apt/sources.list | grep "webmin"
    if [ "$?" == "1" ]; then
        echo "Installing webmin"
        echo "deb http://download.webmin.com/download/repository sarge contrib" >> /etc/apt/sources.list
        wget http://www.webmin.com/jcameron-key.asc
        apt-key add jcameron-key.asc
        apt-get update
        apt-get install webmin
    fi
fi


if [ "$ENABLE_SNAPRAID" == "1" ]; then
    echo "Installing backup clients"
    apt install -y openvpn

    cat /etc/fstab | grep "/mnt/data"
    if [ "$?" == "1" ]; then
        echo "Setting up hard drives in fstab. This is custom setup for each install."
        mkdir -p $DATA_DISK1
        mkdir -p $DATA_DISK2
        mkdir -p $PARITY_DISK
        echo "# Added by postinstall script" >> /etc/fstab
        echo "UUID=f6283955-9310-4ff2-8525-a48dbcdf61e3       $DATA_DISK1          ext4    nofail,noatime,journal_async_commit,data=writeback,barrier=0,errors=remount-ro    1       1" >> /etc/fstab
        echo "UUID=1bc8e1b1-da57-4e66-9b4a-4b35fa555f15       $PARITY_DISK        ext4    nofail,noatime,journal_async_commit,data=writeback,barrier=0,errors=remount-ro    1       1" >> /etc/fstab
        echo "UUID=615e4b68-905a-43e0-81f2-5c0a66d632ba       $DATA_DISK2          ext4    nofail,noatime,journal_async_commit,data=writeback,barrier=0,errors=remount-ro    1       1" >> /etc/fstab
        echo "#/mnt/data/*                                     /mnt/media      fuse.mergerfs   defaults,allow_other,big_writes,direct_io,fsname=mergerfs,minfreespace=50G         0       0" >> /etc/fstab
        mount -a
        ln -s $VIDEOS_ROOT /mnt/videos
        ln -s $PHOTOS_ROOT /mnt/photos
        ln -s $PRIVATE_ROOT /mnt/private
        ln -s $EBOOKS_ROOT /mnt/ebooks
    fi
fi

if [ "$ENABLE_GIT" == "1" ]; then
    echo "Setting up git"
    ln -s $GIT_ROOT /mnt/git
    git config --global user.name "Dan Cristian"
    git config --global user.email "dan.cristian@gmail.com"
    git config --global push.default simple
    useradd gitdaemon -m
    mkdir -p /etc/sv/git-daemon
    echo '#!/bin/sh' >> /etc/sv/git-daemon/run
    echo "exec 2>&1" >> /etc/sv/git-daemon/run
    echo "echo git-daemon starting" >> /etc/sv/git-daemon/run
    echo "exec chpst -ugitdaemon "$(git --exec-path)"/git-daemon --verbose --reuseaddr --syslog --informative-errors --base-path=/mnt/git --enable=receive-pack" >> /etc/sv/git-daemon/run
    chmod +x /etc/sv/git-daemon/run
    sv start git-daemon
fi

if [ "$ENABLE_HAIOT" == "1" ]; then
    echo "Getting HAIOT application from git"
    cd /home/${USERNAME}
    if [ -d PYC ]; then
        echo "PYC exists, remove? y/[n]"
        read -t 30 remove
        if [ "$remove" == "y" ]; then
            rm -r PYC
        fi
    fi

    if [ -d PYC ]; then
        cd PYC
        git pull
        cd ..
    else
        git clone git://192.168.0.9/PYC.git
    fi
    if [ "$?" == "0" ]; then
        echo "Downloaded haiot from local repository"
        export HAIOT_DIR=/home/$USERNAME/PYC
    else
        echo "Downloading haiot from github"
        rm -r haiot
        git clone https://github.com/dan-cristian/haiot.git
        export HAIOT_DIR=/home/$USERNAME/haiot
    fi
    echo "export HAIOT_DIR=$HAIOT_DIR" > /etc/profile.d/haiot.sh
    echo "export DISPLAY=:0.0" >> /etc/profile.d/haiot.sh
    echo "export HAIOT_USER=haiot" >> /etc/profile.d/haiot.sh
    chmod +x /etc/profile.d/haiot.sh
    cp /etc/profile.d/haiot.sh /etc/profile.d/root.sh

    apt-get install mosquitto owfs
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

    echo "Configuring HAIOT application in dir ${HAIOT_DIR}"
    cd ${HAIOT_DIR}
    chmod +x scripts/*sh*
    chmod +x *.sh

    source venv/bin/activate
    if [ "$?" != "0" ]; then
        #sudo pip install --upgrade pip
        sudo pip install virtualenv
        virtualenv venv
        source venv/bin/activate
    fi

    echo "Installing mysql connector"
    wget http://dev.mysql.com/get/Downloads/Connector-Python/mysql-connector-python-2.1.3.zip
    unzip mysql-connector-python-2.1.3.zip
    cd mysql-connector-python-2.1.3/
    python setup.py install
    echo "Installing done for mysql connector"
    cd ..
    rm mysql-connector-python-2.1.3.zip
    rm -r mysql-connector-python-2.1.3

    #setuptools latest needed for apscheduler
    echo "Updating pip etc."
    if [ ! -f /tmp/updated_pip ]; then
        pip install --no-cache-dir --upgrade pip
        pip install --no-cache-dir --upgrade setuptools
        touch /tmp/updated_pip
    fi

    echo Install mandatory requirements
    pip install --no-cache-dir -r requirements.txt

    echo Install optional requirements, you can ignore errors
    res=`cat /etc/os-release | grep raspbian -q ; echo $?`
    if [ "$res" == "0" ]; then
        pip install --no-cache-dir -r requirements-rpi.txt
    else
        pip install --no-cache-dir -r requirements-beaglebone.txt
    fi

    echo "Setup python done"

    #source scripts/setup.sh

    chown -R ${USERNAME}:${USERNAME} .
fi


if [ "$ENABLE_SNAPRAID" == "1" ]; then
    echo "Setup snapraid"
    apt-get install gcc git make -y
    cd
    wget https://github.com/amadvance/snapraid/releases/download/v10.0/snapraid-10.0.tar.gz
    tar xzvf snapraid-10.0.tar.gz
    cd snapraid-10.0/
    ./configure
    make
    # make check
    make install
    cd ..
    #cp ~/snapraid-10.0/snapraid.conf.example /etc/snapraid.conf
    #cd ..
    rm -rf snapraid*
    cp $HAIOT_DIR/scripts/osinstall/ubuntu/etc/snapraid.conf /etc/snapraid.conf
fi


if [ "$ENABLE_MEDIA" == "1" ]; then
    echo "Installing bluetooth BLE for polar7"
   #http://installfights.blogspot.ro/2016/08/fix-set-scan-parameters-failed.html


    echo "Installing media - sound + mpd + kodi + mp3 tagger"
    apt-get install alsa-utils bluez pulseaudio-module-bluetooth python-gobject python-gobject-2
    # https://www.raspberrypi.org/forums/viewtopic.php?t=68779
    # https://jimshaver.net/2015/03/31/going-a2dp-only-on-linux/
    usermod -a -G lp $USERNAME
    echo 'Enable=Source,Sink,Media,Socket' >> /etc/bluetooth/audio.conf
    echo '[General]' >> /etc/bluetooth/audio.conf
    echo 'Disable=Headset' >> /etc/bluetooth/audio.conf
    echo 'resample-method = trivial' >> /etc/pulse/daemon.conf
    echo 'PULSEAUDIO_SYSTEM_START=1' >> /etc/default/pulseaudio
    echo 'DISALLOW_MODULE_LOADING=0' >> /etc/default/pulseaudio
    adduser $USERNAME pulse-access
    echo 'autospawn = no' >> /etc/pulse/client.conf
    echo 'allow-module-loading = yes' >> /etc/pulse/daemon.conf
    echo 'load-default-script-file = yes' >> /etc/pulse/daemon.conf
    echo 'default-script-file = /etc/pulse/default.pa' >> /etc/pulse/daemon.conf

    echo 'Add these two lines in /etc/dbus-1/system.d/pulseaudio-system.conf before </policy>'
    echo '<allow send_destination="org.bluez"/>'
    echo '<allow send_interface="org.bluez.Manager"/>'
    sleep 5
    nano /etc/dbus-1/system.d/pulseaudio-system.conf


    echo '
    bluetoothctl
    power on
    agent on
    default-agent
    connect 00:02:5B:00:2B:8D
    '

    echo '
    rfkill unblock bluetooth
    bluetoothctl
    agent KeyboardDisplay
    default-agent
    scan on
    pair <Device Address>
    connect <Device Address>
    exit the bluetooth utility
    pactl list sinks
    pactl set-default-sink <Device name coming in the sinks>
    e.g. pactl set-default-sink bluez_sink.00_ 18_6B_4e_A4_B8
    mplayer <audio file>
    '
    echo 'Installing music tools'

    apt-get install mpd mpc triggerhappy avahi-daemon shairport-sync sox lame metaflac mpdscribble id3v2 flac mediainfo
    git clone https://github.com/wertarbyte/triggerhappy.git
    cd triggerhappy/
    make
    make install
    cp $HAIOT_DIR/scripts/osinstall/ubuntu/etc/triggerhappy/triggers.conf /etc/triggerhappy/
    cd ..
    rm -r triggerhappy
    ln -s $LOG_ROOT /mnt/log
    ln -s $MUSIC_ROOT /mnt/music
    cp $HAIOT_DIR/scripts/osinstall/ubuntu/etc/mpd.conf /etc/
    cp $HAIOT_DIR/scripts/osinstall/ubuntu/etc/systemd/system/mpd@.service /lib/systemd/system/
    cp $HAIOT_DIR/scripts/osinstall/ubuntu/etc/systemd/system/mpd@*.socket /lib/systemd/system/
    systemctl enable mpd@living.service
    systemctl enable mpd@pod.service
    systemctl enable mpd@beci.service
    systemctl enable mpd@dormitor.service
    systemctl enable mpd@baie.service
    systemctl enable mpd@headset.service

    systemctl enable mpd@living.socket
    systemctl enable mpd@pod.socket
    systemctl enable mpd@beci.socket
    systemctl enable mpd@dormitor.socket
    systemctl enable mpd@baie.socket
    systemctl enable mpd@headset.socket

    systemctl start mpd@living.socket
    systemctl start mpd@pod.socket
    systemctl start mpd@beci.socket
    systemctl start mpd@dormitor.socket
    systemctl start mpd@baie.socket
    systemctl start mpd@headset.socket

    # http://www.lesbonscomptes.com/upmpdcli/upmpdcli.html
    # https://www.lesbonscomptes.com/upmpdcli/downloads.html#ubuntu
    add-apt-repository ppa:jean-francois-dockes/upnpp1
    apt-get update
    apt-get install upmpdcli
    # will start manually with cron
    systemctl stop upmpdcli
    systemctl disable upmpdcli
    cp $HAIOT_DIR/scripts/osinstall/ubuntu/etc/upmpdcli*.conf /etc
    cp $HAIOT_DIR/scripts/osinstall/ubuntu/etc/systemd/system/upmpdcli@.service /lib/systemd/system/
    systemctl enable upmpdcli@living
    systemctl start upmpdcli@living
    systemctl enable upmpdcli@beci
    systemctl start upmpdcli@beci
    systemctl enable upmpdcli@dormitor
    systemctl start upmpdcli@dormitor
    systemctl enable upmpdcli@headset
    systemctl start upmpdcli@headset

    # https://trac.ffmpeg.org/wiki/Capture/ALSA#Recordaudiofromanapplicationwhilealsoroutingtheaudiotoanoutputdevice
    echo "snd_aloop" >> /etc/modules
    # this is loaded with index 0
    echo "options snd_aloop pcm_substreams=1" >> /etc/modprobe.d/alsa-base.conf
    echo "Setting sound card order - useful for kodi if default is busy with audio chose the next one"
    # set here the next one (in a safe zone, kodi picks this one if others are busy)
    # http://superuser.com/questions/626606/how-to-make-alsa-pick-a-preferred-sound-device-automatically
    echo "options snd_oxygen index=1" >> /etc/modprobe.d/alsa-base.conf

    echo 'Installing video tools'
    #http://blog.endpoint.com/2012/11/using-cec-client-to-control-hdmi-devices.html
    # http://www.semicomplete.com/projects/xdotool/#idp2912
    # http://askubuntu.com/questions/371261/display-monitor-info-via-command-line
    apt-get install i3 xinit xterm kodi xdotool i3blocks jq read-edid
    
    #dependencies for chrome
    #apt-get install gconf-service

    echo "Set default card for X"
    echo '
    pcm.!default {
    type hw
    card DAC
    }

    ctl.!default {
    type hw
    card DAC
    }' > /root/.asoundrc

    #echo "Configure kodi socket activation"
    #cp $HAIOT_DIR/scripts/osinstall/ubuntu/etc/systemd/system/kodi* /lib/systemd/system/
    #systemctl enable kodi@root.socket
    #systemctl start kodi@root.socket

    # https://github.com/mikebrady/shairport-sync
    echo "Configure AirPlay default sound card"
    sleep 5
    nano /etc/default/shairport-sync
    cp $HAIOT_DIR/scripts/osinstall/ubuntu/etc/shairport-sync*.conf /etc/
    cp $HAIOT_DIR/scripts/osinstall/ubuntu/etc/systemd/system/shairport-sync@.service /lib/systemd/system/
    # disable default instance
    systemctl disable shairport-sync
    systemctl stop shairport-sync
    systemctl enable shairport-sync@living
    systemctl enable shairport-sync@beci
    systemctl enable shairport-sync@dormitor
    systemctl start shairport-sync@living
    systemctl start shairport-sync@beci
    systemctl start shairport-sync@dormitor


    # https://wiki.archlinux.org/index.php/Music_Player_Daemon/Tips_and_tricks#Last.fm.2FLibre.fm_scrobbling
    echo "Configure mpdscribble to Last.fm"
    cp $HAIOT_DIR/scripts/osinstall/ubuntu/etc/systemd/system/mpdscribble@.service /lib/systemd/system/
    systemctl disable mpdscribble
    echo "Comment port setting in conf file"
    sleep 5
    nano /etc/mpdscribble.conf
    systemctl enable mpdscribble@6600
    systemctl enable mpdscribble@6601
    systemctl enable mpdscribble@6602
    systemctl start mpdscribble@6600
    systemctl start mpdscribble@6601
    systemctl start mpdscribble@6602

    echo "Configuring additional music scripts"
    cp $HAIOT_DIR/scripts/osinstall/ubuntu/etc/systemd/system/activate-audio-amp.service /lib/systemd/system/
    cp $HAIOT_DIR/scripts/osinstall/ubuntu/etc/systemd/system/record-audio.service /lib/systemd/system/
    cp $HAIOT_DIR/scripts/osinstall/ubuntu/etc/systemd/system/thd.service /lib/systemd/system/
    systemctl enable activate-audio-amp
    systemctl enable record-audio
    systemctl start activate-audio-amp
    systemctl start record-audio
    systemctl enable thd
    systemctl start thd

    echo "Installing screenshow"
    apt install feh exiv2

   echo "Installing gesture"
   apt install easystroke

   echo "Installing GoogleMusicProxy"
   # http://gmusicproxy.net/
   apt-get install python-virtualenv virtualenvwrapper
   cd /home/${USERNAME}
   su ${USERNAME} #<<'EOF'

   mkvirtualenv -p /usr/bin/python2 gmusicproxy
   git clone https://github.com/diraimondo/gmusicproxy.git
   cd gmusicproxy
   pip install -r requirements.txt
   workon gmusicproxy
   cp $HAIOT_DIR/scripts/osinstall/ubuntu/etc/systemd/system/gmusicproxy.service /lib/systemd/system/
   cp $HAIOT_DIR/scripts/config/gmusicproxy.cfg /home/${USERNAME}/.config/
   systemctl enable gmusicproxy
   echo "Open gmusicproxy config file to set user, pass and port"
   # systemctl start gmusicproxy
   # chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}

   echo "serial control via net for AMP setup"
   # http://techtinkering.com/2013/04/02/connecting-to-a-remote-serial-port-over-tcpip/
   apt install ser2net
   echo "update /etc/ser2net.conf, use port 2000"
   systemctl restart ser2net

fi

if [ "$ENABLE_DASHBOARD" == "1" ]; then
    echo "Installing smashing dashboard"
    adduser ${USERNAME} dialout
    # http://labrat.it/2014/01/11/dashing-dashboard/
    # https://github.com/SmashingDashboard/smashing
    apt-get install ruby nodejs
    apt-get install ruby-dev g++ libmysqlclient-dev
    gem install bundler
    gem install smashing
    git clone https://github.com/dan-cristian/dashiot.git
    cd dashiot
    bundle
    echo "Installing dashboard service"
    # https://gist.github.com/gregology/5313326

fi

if [ "$ENABLE_ALEXA" == "1" ]; then
    echo "Installing alexa control"
    apt-get install npm
fi

if [ "$ENABLE_CAMERA" == "1" ]; then
    echo 'Installing motion'
    apt-get install motion lsof
    /etc/init.d/motion stop
    cp $HAIOT_DIR/scripts/osinstall/ubuntu/etc/motion/*.conf /etc/motion/
    echo 'start_motion_daemon=yes' > /etc/default/motion
    ln -s $MOTION_ROOT /mnt/motion
    chown motion:users /mnt/log/motion.log
    # change default motion user attribs to set right perms
    adduser motion users
    adduser motion audio
    chmod -R g+w /mnt/motion/
    mkdir -p /home/motion
    chown motion:users /home/motion
    chsh -s /bin/bash motion
    usermod -m -d /home/motion motion

    echo 'Installing latest version from alternate git as default package is very old'
    git clone https://github.com/Motion-Project/motion.git
    cd motion/
    apt-get install autoconf libjpeg-dev pkgconf libavutil-dev libavformat-dev libavcodec-dev libswscale-dev
    autoreconf
    ./configure
    make
    make install
    ln -s /etc/motion/motion.conf /usr/local/etc/motion/motion.conf
    echo "Update motion daemon path and paths, usually in /local/bin rather than /bin"
    sleep 5
    nano /etc/init.d/motion
    /etc/init.d/motion restart
fi

if [ "$ENABLE_CAMERA_SHINOBI" == "1" ]; then
    echo 'Installing shinobi'
    # https://shinobi.video/docs/start
    apt-get install nodejs npm
    npm cache clean -f
    npm install -g n
    n stable

    npm install pm2 -g
fi

# CLOUD must be after CAMERA due to user creation
if [ "$ENABLE_CLOUD_AMAZON" == "1" ]; then
    # http://rclone.org/install/
    curl -O http://downloads.rclone.org/rclone-current-linux-amd64.zip
    unzip rclone-current-linux-amd64.zip
    cd rclone-*-linux-amd64
    cp rclone /usr/sbin/
    chown root:root /usr/sbin/rclone
    chmod 755 /usr/sbin/rclone
    cd ..
    rm -r rclone*
    echo "Set your cloud account"
    runuser -l $USERNAME -c '/usr/sbin/rclone config'
    cp /home/$USERNAME/.rclone.conf /home/motion
    chown motion:motion /home/motion/.rclone.conf
fi


if [ "$ENABLE_TORRENT" == "1" ]; then
    apt-get install transmission-daemon
    /etc/init.d/transmission-daemon stop
    cp -R $HAIOT_DIR/scripts/osinstall/ubuntu/etc/transmission-daemon /etc
    /etc/init.d/transmission-daemon start
fi

if [ "$ENABLE_MYSQL_SERVER" == "1" ]; then
    echo 'Installing mysql'
    apt-get install mysql-server
    /etc/init.d/mysql stop
    # http://tecadmin.net/change-default-mysql-data-directory-in-linux/
    echo "change data dir and comment listen on local interface only"
    sleep 5
    nano /etc/mysql/mysql.conf.d/mysqld.cnf
    echo "add mysql data dir in app armor to allow write"
    sleep 5
    nano /etc/apparmor.d/usr.sbin.mysqld
    chown mysql:mysql -R $MYSQL_DATA_ROOT
    /etc/init.d/mysql restart
fi

if [ "$ENABLE_BACKUP" == "1" ]; then
    echo "Installing cloud backup tools"
    apt-get install -y fuse ntfs-3g

    # not working
    #https://www.howtoforge.com/tutorial/owncloud-install-debian-8-jessie/
    #echo 'deb http://download.opensuse.org/repositories/isv:/ownCloud:/community/Debian_8.0/ /' >> /etc/apt/sources.list.d/owncloud.list
    #https://tecadmin.net/install-owncloud-on-ubuntu/#
    #http://manjaro.site/install-owncloud-10-debian-8-jessie/

    #apt-get install -y apache2 mysql-server php5-common libapache2-mod-php5 php5-cli php5-mysql php5-curl
    #owncloud
    #cd /tmp
    #wget https://download.owncloud.org/community/owncloud-10.0.2.tar.bz2
    #cd /var/www/html
    #tar xjf /tmp/owncloud-10.0.2.tar.bz2
    #chown -R www-data:www-data owncloud
    #chmod -R 755 owncloud
    #rm -f /tmp/owncloud-10.0.2.tar.bz2

    #mysql -u root -p
    #mysql> CREATE DATABASE owncloud;
    #mysql> GRANT ALL ON owncloud.* to 'owncloud'@'localhost' IDENTIFIED BY '_password_';
    #mysql> FLUSH PRIVILEGES;
    #mysql> quit
    #https://doc.owncloud.org/server/8.2/user_manual/files/access_webdav.html


    #enable high power consumption
    #https://www.reddit.com/r/raspberry_pi/comments/2x4bo4/external_hard_drive_for_rasppi_2/

    cd /tmp
    wget https://download.nextcloud.com/server/releases/nextcloud-12.0.2.tar.bz2
    apt install apache2 mariadb-server libapache2-mod-php5 php5-cli php5-mysql php5-curl php5-mysql php5-gd php5-json php5-intl php5-mcrypt php5-imagick
    cd /var/www/
    tar -xjf /tmp/nextcloud-12.0.2.tar.bz2
    #https://docs.nextcloud.com/server/12/admin_manual/installation/source_installation.html#prerequisites-for-manual-installation
    nano /etc/apache2/sites-available/nextcloud.conf
    ln -s /etc/apache2/sites-available/nextcloud.conf /etc/apache2/sites-enabled/nextcloud.conf
    a2enmod rewrite
    a2enmod headers
    a2enmod env
    a2enmod dir
    a2enmod mime
    a2enmod ssl
    a2ensite default-ssl
    chown www-data:www-data -R nextcloud

    mysql -u root -p
    #CREATE DATABASE nextcloud;
    #GRANT ALL ON nextcloud.* to 'nextcloud'@'localhost' IDENTIFIED BY 'cba';
    #FLUSH PRIVILEGES;

    service apache2 restart

    #https://www.htpcguides.com/spin-down-and-manage-hard-drive-power-on-raspberry-pi/
    apt install -y build-essential fakeroot debhelper
    cd ~
    wget http://sourceforge.net/projects/hd-idle/files/hd-idle-1.05.tgz
    tar -xvf hd-idle-1.05.tgz && cd hd-idle
    dpkg-buildpackage -rfakeroot
    dpkg -i ../hd-idle_*.deb

    cp $HAIOT_DIR/scripts/osinstall/ubuntu/etc/systemd/system/hd-idle.service /etc/systemd/system/
    systemctl enable hd-idle
    systemctl start hd-idle
fi

if [ "$ENABLE_ROUTER" == "1" ]; then
   #https://www.ostechnix.com/sslh-share-port-https-ssh/
   apt install -y nginx sslh

fi

if [ "$ENABLE_SECURE_SSH" == "1" ]; then
    apt install -y fail2ban

fi

if [ "$ENABLE_VPN_SERVER" == "1" ]; then
    #https://www.digitalocean.com/community/tutorials/how-to-set-up-an-openvpn-server-on-debian-8
    apt install -y openvpn easy-rsa ufw
    gunzip -c /usr/share/doc/openvpn/examples/sample-config-files/server.conf.gz > /etc/openvpn/server.conf
    nano /etc/openvpn/server.conf
    #dh2048.pem
    #push "redirect-gateway def1 bypass-dhcp"
    #open dns
    #user nobody
    #group nogroup
    echo 1 > /proc/sys/net/ipv4/ip_forward
    nano /etc/sysctl.conf
    #net.ipv4.ip_forward=1
    ufw allow ssh
    ufw allow 1194/udp
    nano /etc/default/ufw
    #DEFAULT_FORWARD_POLICY="ACCEPT"
    nano /etc/ufw/before.rules
    #
    cp -r /usr/share/easy-rsa/ /etc/openvpn
    mkdir /etc/openvpn/easy-rsa/keys
    nano /etc/openvpn/easy-rsa/vars
    #
    echo "This will take a lot of time"
    openssl dhparam -out /etc/openvpn/dh2048.pem 2048
    cd /etc/openvpn/easy-rsa
    . ./vars
    ./clean-all
    ./build-ca
    ./build-key-server server
    cp /etc/openvpn/easy-rsa/keys/{server.crt,server.key,ca.crt} /etc/openvpn
    ls /etc/openvpn
    service openvpn start
    service openvpn status
    echo "Build client keys"
    ./build-key client1
    cp /usr/share/doc/openvpn/examples/sample-config-files/client.conf /etc/openvpn/easy-rsa/keys/client.ovpn
    nano /etc/openvpn/easy-rsa/keys/client.ovpn
    #remote your_server_ip 1194
    #user nobody
    #group nogroup

    nano /etc/openvpn/easy-rsa/keys/client.ovpn
    #;ca ca.crt
    #;cert client.crt
    #;key client.key
    echo '<ca>' >> /etc/openvpn/easy-rsa/keys/client.ovpn
    cat /etc/openvpn/ca.crt >> /etc/openvpn/easy-rsa/keys/client.ovpn
    echo '</ca>' >> /etc/openvpn/easy-rsa/keys/client.ovpn

    echo '<cert>' >> /etc/openvpn/easy-rsa/keys/client.ovpn
    cat /etc/openvpn/easy-rsa/keys/client1.crt >> /etc/openvpn/easy-rsa/keys/client.ovpn
    echo '</cert>' >> /etc/openvpn/easy-rsa/keys/client.ovpn

    echo '<key>' >> /etc/openvpn/easy-rsa/keys/client.ovpn
    cat /etc/openvpn/easy-rsa/keys/client1.key >> /etc/openvpn/easy-rsa/keys/client.ovpn
    echo '</key>' >> /etc/openvpn/easy-rsa/keys/client.ovpn
fi

echo "Optimise for flash and ssd usage"

echo "Create tmpfs"
# http://www.zdnet.com/article/raspberry-pi-extending-the-life-of-the-sd-card/
mkdir -p /var/ram
chmod 777 /var/ram/

cat /etc/fstab | grep "/var/ram"
if [ "$?" == "1" ]; then
	echo "Add ram folder for sqlite db storage and logs"
	echo "tmpfs           /var/ram        tmpfs   defaults,noatime        0       0" >> /etc/fstab
	echo "tmpfs           /var/log        tmpfs   defaults,noatime        0       0" >> /etc/fstab
	echo "tmpfs           /tmp            tmpfs   defaults,noatime        0       0" >> /etc/fstab
	mount -a
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
    dmesg | mail -s "Test" dan.cristian@gmail.com
fi

echo "Removing not needed files and cleaning apt files"
apt-get -y remove build-essential
rm /usr/share/doc -r
rm /usr/share/man -r
apt-get -y autoremove
apt-get clean

echo "Install completed"