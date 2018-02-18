#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   return 1
fi

COUNTRY_CODE=RO
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

ENABLE_BACKUP_SERVER=0
ENABLE_BACKUP_CLIENT=0
ENABLE_VPN_SERVER=0
ENABLE_SECURE_SSH=0

ENABLE_ROUTER=0

ENABLE_DASHCAM_PI=1
ENABLE_DASHCAM_PI_LCD_DF=1
ENABLE_DASHCAM_MOTION=0
ENABLE_3G_MODEM=1
ENABLE_LOG_RAM=0

set_config_var() {
  lua - "$1" "$2" "$3" <<EOF > "$3.bak"
local key=assert(arg[1])
local value=assert(arg[2])
local fn=assert(arg[3])
local file=assert(io.open(fn))
local made_change=false
for line in file:lines() do
  if line:match("^#?%s*"..key.."=.*$") then
    line=key.."="..value
    made_change=true
  end
  print(line)
end

if not made_change then
  print(key.."="..value)
end
EOF
mv "$3.bak" "$3"
}

clear_config_var() {
  lua - "$1" "$2" <<EOF > "$2.bak"
local key=assert(arg[1])
local fn=assert(arg[2])
local file=assert(io.open(fn))
for line in file:lines() do
  if line:match("^%s*"..key.."=.*$") then
    line="#"..line
  end
  print(line)
end
EOF
mv "$2.bak" "$2"
}

get_config_var() {
  lua - "$1" "$2" <<EOF
local key=assert(arg[1])
local fn=assert(arg[2])
local file=assert(io.open(fn))
local found=false
for line in file:lines() do
  local val = line:match("^%s*"..key.."=(.*)$")
  if (val ~= nil) then
    print(val)
    found=true
    break
  end
end
if not found then
   print(0)
end
EOF
}



SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Script directory is $SCRIPT_DIR, make sure script is placed in proper haiot GIT folder structure to find conf files"
echo "Setting timezone ..."
echo "Europe/Bucharest" > /etc/timezone
dpkg-reconfigure -f noninteractive tzdata


# give internet connectivity via WIFI first
if [ "$ENABLE_DASHCAM_PI" == "1" ]; then
	#http://pidashcam.blogspot.ro/2013/09/install.html#front
	cat /etc/network/interfaces | grep "auto wlan0"
    if [ "$?" == "1" ]; then
		#https://www.raspberrypi.org/documentation/configuration/wireless/wireless-cli.md
		iwlist wlan0 scan
		TMP_WIFI="/etc/wpa_supplicant/wpa_supplicant.conf"
        read -sp "Enter wifi password:" wifipass
		echo 'network={' 	>> $TMP_WIFI
		echo 'ssid="home2"'	>> $TMP_WIFI
		echo 'psk="'$wifipass'"'	>> $TMP_WIFI
		echo 'priority=1'	>> $TMP_WIFI
		echo "}"			>> $TMP_WIFI
		set_config_var country $COUNTRY_CODE $TMP_WIFI
		wpa_cli -i wlan0 reconfigure
		echo "auto wlan0" >> /etc/network/interfaces
        echo "Change password for pi user as SSH will be enabled"
		passwd pi
        systemctl enable ssh
		systemctl start ssh
	fi
fi

if [ `cat /etc/hostname` == "raspberrypi" ]; then
    read -sp "Enter host name:" new_host_name
    echo $new_host_name > /etc/hostname
    echo "127.0.0.1" $new_host_name > /etc/hosts
fi


echo "Testing internet connectivity"
while true;do
    ping -c 1 www.google.com && break
    sleep 1
done

echo "Starting update & auto install in 10 seconds"
sleep 10

echo "Updating apt-get and upgrade"
if [ ! -f /tmp/updated ]; then
    apt-get -y update
    apt-get -y upgrade
    #echo "Ignore following error if you are not running on a PI"
    #rpi-update
    touch /tmp/updated
else
    echo "Skipping update & upgrade, already done!"
fi

echo "Installing additional generic packages"
apt-get -y install ssh dialog sudo nano wget runit git ssmtp mailutils psmisc smartmontools localepurge sshpass dos2unix


echo "Creating user $USERNAME with password=$USERPASS"
useradd ${USERNAME} -m
echo "$USERNAME:$USERPASS" | chpasswd
adduser ${USERNAME} sudo
adduser ${USERNAME} audio
adduser ${USERNAME} video
adduser ${USERNAME} tty
adduser ${USERNAME} dialout
adduser ${USERNAME} i2c
adduser ${USERNAME} spi
adduser ${USERNAME} gpio
adduser ${USERNAME} netdev # for wpa_cli access as non-root
echo "${USERNAME} ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers.d/010_pi-nopasswd
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

    apt-get -y install mosquitto owfs ow-shell

    echo "Installing I2C for owfs"
    #https://gist.github.com/kmpm/4445289
    apt install -y i2c-tools libi2c-dev python-smbus
    #python-smbus is needed for realtime clock
    if ! grep -q "^i2c[-_]dev" /etc/modules; then printf "i2c-dev\n" >> /etc/modules; fi
    if ! grep -q "^i2c[-_]bcm2708" /etc/modules; then printf "i2c-bcm2708\n" >> /etc/modules; fi
    set_config_var dtparam i2c_arm=on /boot/config.txt

    echo "Instaling bluetooth modules"
    apt install -y bluez python-bluez
    apt-get -y build-dep python-bluez

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
    ln -s $HAIOT_DIR/scripts /home/scripts
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
   apt install easystroke gpm

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

    echo "Compiling ffmpeg with HW"
    # https://gist.github.com/Brainiarc7/eb45d2e22afec7534f4a117d15fe6d89
    apt-get -y install autoconf automake build-essential libass-dev libtool pkg-config texinfo zlib1g-dev libdrm-dev libva-dev vainfo libogg-dev
    mkdir ffmpeg-hw
    cd ffmpeg-hw
    git clone https://github.com/01org/cmrt
    cd cmrt
    ./autogen.sh
    ./configure
    time make -j$(nproc) VERBOSE=1
    make -j$(nproc) install
    ldconfig -vvvv

    cd ..
    git clone https://github.com/01org/libva
    cd libva
    ./autogen.sh
    ./configure
    time make -j$(nproc) VERBOSE=1
    make -j$(nproc) install


    cd ..
    cd intel-hybrid-driver
    ./autogen.sh
    ./configure
    time make -j$(nproc) VERBOSE=1
    make -j$(nproc) install
    ldconfig -vvv

    cd ./post-install.shgit clone https://github.com/01org/intel-vaapi-driver
    cd intel-vaapi-driver
    ./autogen.sh
    ./configure --enable-hybrid-codec
    time make -j$(nproc) VERBOSE=1
    make -j$(nproc) install
    ldconfig -vvvv


    mkdir -p $HOME/bin
    chown -Rc $USER:$USER $HOME/bin
    mkdir -p ~/ffmpeg_sources
    cd ~/ffmpeg_sources
    wget wget http://www.nasm.us/pub/nasm/releasebuilds/2.14rc0/nasm-2.14rc0.tar.gz
    tar xzvf nasm-2.14rc0.tar.gz
    cd nasm-2.14rc0
    ./configure --prefix="$HOME/bin" --bindir="$HOME/bin"
    make -j$(nproc) VERBOSE=1
    make -j$(nproc) install
    make -j$(nproc) distclean

    cd ~/ffmpeg_sources
    wget http://download.videolan.org/pub/x264/snapshots/last_stable_x264.tar.bz2
    tar xjvf last_stable_x264.tar.bz2
    cd x264-snapshot*
    PATH="$HOME/bin:$PATH" ./configure --prefix="$HOME/bin" --bindir="$HOME/bin" --enable-static --disable-opencl
    PATH="$HOME/bin:$PATH" make -j$(nproc) VERBOSE=1
    make -j$(nproc) install VERBOSE=1
    make -j$(nproc) distclean

    apt-get install cmake mercurial
    cd ~/ffmpeg_sources
    hg clone https://bitbucket.org/multicoreware/x265
    cd ~/ffmpeg_sources/x265/build/linux
    PATH="$HOME/bin:$PATH" cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="$HOME/bin" -DENABLE_SHARED:bool=off ../../source
    make -j$(nproc) VERBOSE=1
    make -j$(nproc) install VERBOSE=1
    make -j$(nproc) clean VERBOSE=1

    cd ~/ffmpeg_sources
    wget -O fdk-aac.tar.gz https://github.com/mstorsjo/fdk-aac/tarball/master
    tar xzvf fdk-aac.tar.gz
    cd mstorsjo-fdk-aac*
    autoreconf -fiv
    ./configure --prefix="$HOME/bin" --disable-shared
    make -j$(nproc)
    make -j$(nproc) install
    make -j$(nproc) distclean

    cd ~/ffmpeg_sources
    git clone https://github.com/webmproject/libvpx/
    cd libvpx
    ./configure --prefix="$HOME/bin" --enable-runtime-cpu-detect --enable-vp9 --enable-vp8 \
    --enable-postproc --enable-vp9-postproc --enable-multi-res-encoding --enable-webm-io --enable-vp9-highbitdepth --enable-onthefly-bitpacking --enable-realtime-only \
    --cpu=native --as=yasm
    time make -j$(nproc)
    time make -j$(nproc) install
    time make clean -j$(nproc)
    time make distclean

    cd ~/ffmpeg_sources
    wget -c -v http://downloads.xiph.org/releases/vorbis/libvorbis-1.3.5.tar.xz
    tar -xvf libvorbis-1.3.5.tar.xz
    cd libvorbis-1.3.5
    ./configure --enable-static --prefix="$HOME/bin"
    time make -j$(nproc)
    time make -j$(nproc) install
    time make clean -j$(nproc)
    time make distclean

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

    #https://stackoverflow.com/questions/9293042/how-to-perform-a-mysqldump-without-a-password-prompt
    echo "Set default user for mysqldump operations in ~/.my.cnf"
    sleep 5
fi

if [ "$ENABLE_BACKUP_SERVER" == "1" ]; then
    echo "Installing cloud backup tools"
    apt-get install -y fuse ntfs-3g davfs2

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
    apt install -y apache2 mariadb-server
    #apt install libapache2-mod-php5 php5-cli php5-mysql php5-curl php5-mysql php5-gd php5-json php5-intl php5-mcrypt php5-imagick
    apt install -y libapache2-mod-php php-cli php-mysql php-curl php-mysql php-gd php-json php-intl php-mcrypt php-imagick
    apt install -y php-zip php-xml php-mbstring php-dompdf
    cd /var/www/
    tar -xjf /tmp/nextcloud-12.0.2.tar.bz2
    #https://docs.nextcloud.com/server/12/admin_manual/installation/source_installation.html#prerequisites-for-manual-installation
    #https://bayton.org/docs/nextcloud/installing-nextcloud-on-ubuntu-16-04-lts-with-redis-apcu-ssl-apache/
    cp $SCRIPT_DIR/etc/nextcloud.conf /etc/apache2/sites-available/nextcloud.conf
    ln -s /etc/apache2/sites-available/nextcloud.conf /etc/apache2/sites-enabled/nextcloud.conf
    a2enmod rewrite headers env dir mime
    a2enmod ssl
    a2ensite default-ssl
    chown www-data:www-data -R nextcloud

    mysql -u root -p
    #CREATE DATABASE nextcloud;
    #GRANT ALL ON nextcloud.* to 'nextcloud'@'localhost' IDENTIFIED BY 'cba';
    #FLUSH PRIVILEGES;
    #quit;

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

if [ "$ENABLE_BACKUP_CLIENT" == "1" ]; then
    echo "Installing backup client tools"
    # https://www.digitalocean.com/community/tutorials/how-to-configure-ssh-key-based-authentication-on-a-linux-server

fi

if [ "$ENABLE_ROUTER" == "1" ]; then
   #https://www.ostechnix.com/sslh-share-port-https-ssh/
   apt install -y nginx sslh

fi

if [ "$ENABLE_SECURE_SSH" == "1" ]; then
    apt install -y fail2ban

    #Beaglebone black optimisation
    #https://datko.net/2013/10/03/howto_crypto_beaglebone_black/
    #https://superuser.com/questions/881404/beaglebone-black-openssl-crypto-acceleration
    cd ~
    apt install -y linux-headers-4.4.54-ti-r93
    wget http://nwl.cc/pub/cryptodev-linux/cryptodev-linux-1.9.tar.gz
    tar zxf cryptodev-linux-1.7.tar.gz
    cd cryptodev-linux-1.9
    make
    make install
    depmod -a
    modprobe cryptodev
    echo cryptodev >> /etc/modules

    # http://mgalgs.github.io/2014/10/22/enable-arcfour-and-other-fast-ciphers-on-recent-versions-of-openssh.html
    echo "ciphers arcfour,arcfour128,arcfour256" >> /etc/ssh/sshd_config
    # https://www.daveperrett.com/articles/2010/09/14/ssh-authentication-refused/

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

if [ "$ENABLE_DASHCAM_PI" == "1" ]; then
    cd /home/${USERNAME}
	ln -s $HAIOT_DIR/scripts /home/scripts

    cp $HAIOT_DIR/scripts/osinstall/ubuntu/etc/systemd/system/haiot_standalone.service /lib/systemd/system/
    systemctl enable haiot_standalone.service
    #systemctl start keep_internet.service

	#http://pidashcam.blogspot.ro/2013/09/install.html#front
    if ! grep -q "gpu_mem" /boot/config.txt; then
        #enable camera
		# https://raspberrypi.stackexchange.com/questions/14229/how-can-i-enable-the-camera-without-using-raspi-config
        echo "Enabling PI camera"
        set_config_var enable_uart 0 /boot/config.txt
		set_config_var start_x 1 /boot/config.txt
		CUR_GPU_MEM=$(get_config_var gpu_mem /boot/config.txt)
		if [ -z "$CUR_GPU_MEM" ] || [ "$CUR_GPU_MEM" -lt 128 ]; then
		  set_config_var gpu_mem 128 /boot/config.txt
		fi
		sed /boot/config.txt -i -e "s/^startx/#startx/"
		sed /boot/config.txt -i -e "s/^fixup_file/#fixup_file/"
	fi
	echo "Disabling not needed services"
	systemctl disable dhcpcd

	#https://raspberrypi.stackexchange.com/questions/169/how-can-i-extend-the-life-of-my-sd-card
	apt-get remove dphys-swapfile
	#https://github.com/waveform80/picamera/issues/288#issuecomment-222636171
	apt install -y python-picamera

	#http://www.richardmudhar.com/blog/2015/02/raspberry-pi-camera-and-motion-out-of-the-box-sparrowcam/
	#modprobe bcm2835-v4l2
	#if ! grep -q "^bcm2835[-_]v4l2" /etc/modules; then printf "bcm2835-v4l2\n" >> /etc/modules; fi

    # https://unix.stackexchange.com/questions/91027/how-to-disable-usb-autosuspend-on-kernel-3-7-10-or-above
	if ! grep -q "usbcore[._]autosuspend" /boot/cmdline.txt; then echo -n " usbcore.autosuspend=-1" >> /boot/cmdline.txt; fi
	if ! grep -q "panic[=_]" /boot/cmdline.txt; then echo -n " panic=3" >> /boot/cmdline.txt; fi
	#remove new line
	tr -d '\n' < /boot/cmdline.txt > /boot/cmdline.new
	mv /boot/cmdline.new /boot/cmdline.txt

	#https://github.com/legotheboss/YouTube-files/wiki/(RPi)-Compile-FFmpeg-with-the-OpenMAX-H.264-GPU-acceleration
    #might need more disk space, resize SSD
    #https://askubuntu.com/questions/386420/how-to-open-gparted-terminal
    #https://unix.stackexchange.com/questions/67095/how-can-i-expand-ext4-partition-size-on-debian
    apt install -y git libomxil-bellagio-dev libx264-dev libx265-dev libmp3lame-dev libfontconfig-dev libasound2-dev

    if [ ! -f FFmpeg/ffmpeg ]; then
        git clone https://github.com/FFmpeg/FFmpeg.git
        cd FFmpeg
        #./configure --arch=armel --target-os=linux --enable-libmp3lame --enable-gpl --enable-omx --enable-omx-rpi --enable-nonfree --prefix=/usr --extra-version='1~deb9u1' --toolchain=hardened --libdir=/usr/lib/arm-linux-gnueabihf --incdir=/usr/include/arm-linux-gnueabihf
        ./configure --arch=armel --target-os=linux --enable-indev=alsa --enable-outdev=alsa --enable-libfreetype --enable-libfontconfig --enable-libmp3lame --enable-gpl --enable-omx --enable-omx-rpi --enable-nonfree --prefix=/usr --toolchain=hardened --libdir=/usr/lib/arm-linux-gnueabihf --incdir=/usr/include/arm-linux-gnueabihf
        make -j4
        cd ..
    fi
    #https://www.raspberrypi.org/documentation/raspbian/applications/camera.md
    #http://www.bogotobogo.com/VideoStreaming/ffmpeg_AdaptiveLiveStreaming_SmoothStreaming.php
    # https://superuser.com/questions/908280/what-is-the-correct-way-to-fix-keyframes-in-ffmpeg-for-dash
    #pi cam v1
    #raspivid -o -  -t 0 -ex night -br 50 -n -w 1296 -h    -fps 8 | ./ffmpeg -r 8 -i - -y -frag_duration 1000 -an -c:v h264_omx -b:v 3000k -vf "drawtext=text='%{localtime\:%c}': fontcolor=white@0.8: fontsize=32: x=10: y=10" record0.mp4
    #usb webcam 5mp
    #./ffmpeg -r 8 -f video4linux2 -i /dev/video1 -vf "drawtext=text='%{localtime\:%c}': fontcolor=white@0.8: fontsize=32: x=10: y=10" -s 1600x1200 -an -c:v h264_omx -b:v 3000k -y -frag_duration 1000 record1.mp4
    #./ffmpeg -y -f alsa -thread_queue_size 512 -ac 1 -i hw:1 -ar 16000 -acodec mp3 -f video4linux2 -r 8 -i /dev/video1 -vf "drawtext=text='%{localtime\:%c}': fontcolor=white@0.8: fontsize=32: x=10: y=10" -s 1280x720 -c:v h264_omx -b:v 3000k -frag_duration 1000 record2.mp4

    echo "Fix USB issue"
    #https://github.com/raspberrypi/linux/issues/623

    #usb web cam logitech c310
    #./ffmpeg -y -f alsa -thread_queue_size 16384 -ac 1 -i hw:1 -r 8 -f video4linux2 -thread_queue_size 8192 -i /dev/video0 -vf "drawtext=text='%{localtime\:%c}': fontcolor=white@0.8: fontsize=32: x=10: y=10" -s 1280x720 -c:v h264_omx -b:v 3000k -frag_duration 1000 -f segment -segment_time 3600 -segment_format mp4 -reset_timestamps 1  -force_key_frames "expr:gte(t,n_forced*2)" /mnt/tmp/record2_%03d.mp4
    #windows
    #https://stackoverflow.com/questions/44347991/how-to-grab-laptop-webcam-video-with-ffmpeg-in-windows
    #ffmpeg -y -f dshow -i video="Integrated Camera" -r 8 -c:v libx264 -b:v 2000k -frag_duration 1000 record1.mp4

    echo "Installing I2C sensor packages"
    apt install -y i2c-tools libi2c-dev python-smbus
    #python-smbus is needed for realtime clock
    if ! grep -q "^i2c[-_]dev" /etc/modules; then printf "i2c-dev\n" >> /etc/modules; fi
    if ! grep -q "^i2c[-_]bcm2708" /etc/modules; then printf "i2c-bcm2708\n" >> /etc/modules; fi

    set_config_var dtparam i2c_arm=on /boot/config.txt
    #echo "Installing accel + gyro lib"
    #pip install mpu6050-raspberrypi

    echo "Disable UART console for GPS use"
    sed -i -e "s/console=serial0,115200//g" /boot/cmdline.txt

    echo "Installing GPS"
    apt install -y gpsd gpsd-clients
    systemctl stop gpsd.socket
    systemctl disable gpsd.socket

    gpsd /dev/ttyS0 -F /var/run/gpsd.sock
    cgps -s
    # https://gitlab.com/eneiluj/phonetrack-oc
    echo "gpsd /dev/ttyS0 -F /var/run/gpsd.sock" >> /etc/rc.local

    echo "Configuring fwknop"
    apt install -y fwknop-client

    echo "Set proper network gw order"
    # https://unix.stackexchange.com/questions/292940/how-to-set-a-routing-table-that-prefers-wlan-dhcp-interface-as-default-route

    echo "Install USB power control app"
    sudo apt install -y libusb-dev
    https://raw.githubusercontent.com/codazoda/hub-ctrl.c/master/hub-ctrl.c
    gcc -o hub-ctrl hub-ctrl.c -lusb

    echo "Enable RTC"
    #https://www.raspberrypi-spy.co.uk/2015/05/adding-a-ds3231-real-time-clock-to-the-raspberry-pi/
    if ! grep -q "^rtc[-_]ds1307" /etc/modules; then printf "rtc-ds1307\n" >> /etc/modules; fi
    echo 'echo ds1307 0x68 > /sys/class/i2c-adapter/i2c-1/new_device' >> /etc/rc.local

    echo "move exit 0 to the end in rc.local to allow scripts to run"
    nano /etc/rc.local
fi


if [ "$ENABLE_DASHCAM_MOTION" == "1" ]; then
    apt install -y motion
    cam1_conf=/etc/motion/camera1.conf
    cam2_conf=/etc/motion/camera2.conf
    motion_conf=/etc/motion/motion.conf
	cp /etc/motion/camera1-dist.conf $cam1_conf
    cp /etc/motion/camera2-dist.conf $cam2_conf
    sed -i -re '/camera1.conf/ s/^; //' $motion_conf
    sed -i -re '/camera2.conf/ s/^; //' $motion_conf

echo "
target_dir /home/${USERNAME}/motion/records
movie_filename front-%v-%Y%m%d%H%M%S
width 640
height 480
framerate 8
output_pictures off
ffmpeg_timelapse_mode hourly
ffmpeg_video_codec mpeg4
stream_localhost off
stream_maxrate 8
webcontrol_localhost off
" >> $cam1_conf

echo "
target_dir /home/${USERNAME}/motion/records
movie_filename rear-%v-%Y%m%d%H%M%S
input -1
width 640
height 480
framerate 8
output_pictures off
ffmpeg_timelapse_mode hourly
ffmpeg_video_codec mpeg4
stream_localhost off
stream_maxrate 8
webcontrol_localhost off
" >> $cam2_conf
fi

fi

if [ "$ENABLE_DASHCAM_PI_LCD_DF" == "1" ]; then
    modprobe rp_usbdisplay
    if [ "$?" == "1" ]; then
        echo "Installing dfrobot tft screen"
        #https://github.com/pimoroni/rp_usbdisplay/tree/master/dkms
        #http://docs.robopeak.net/doku.php?id=rpusbdisp_faq#q12
        wget https://github.com/pimoroni/rp_usbdisplay/raw/master/dkms/rp-usbdisplay-dkms_1.0_all.deb
        # https://askubuntu.com/questions/714874/how-to-point-dkms-to-kernel-headers
        #ln -s /usr/src/linux-headers-$(uname -r)  /lib/modules/$(uname -r)/build
        #http://virtual.4my.eu/RP_USBDisplay/Ubuntu%20ARMv7hf/readme.txt
        apt install -y dkms raspberrypi-kernel-headers python-pip 
        #https://askubuntu.com/questions/299950/how-do-i-install-pygame-in-virtualenv/299965#299965
        apt build-dep -y python-pygame
        apt install -y libsdl-dev python-pygame
        dpkg -i rp-usbdisplay-dkms_1.0_all.deb
        echo "Probing module"
        modprobe rp_usbdisplay

        if ! grep -q "fbcon[=_]map:1" /boot/cmdline.txt; then echo -n " fbcon=font:ProFont6x11 fbcon=map:1" >> /boot/cmdline.txt; fi
        #remove new line
        tr -d '\n' < /boot/cmdline.txt > /boot/cmdline.new
        mv /boot/cmdline.new /boot/cmdline.txt
        #https://stackoverflow.com/questions/24147026/display-gui-on-raspberry-pi-without-startx
        #https://unix.stackexchange.com/questions/58961/how-do-i-let-an-sdl-app-not-running-as-root-use-the-console/387144#387144

        #https://pythonprogramming.net/pygame-button-function-events/
        #calibrate tft pointer
        #https://stackoverflow.com/questions/26092441/pygame-mousebuttondown-coordinates-are-off-unless-im-in-xwindows
        #not working -- https://learn.adafruit.com/adafruit-pitft-28-inch-resistive-touchscreen-display-raspberry-pi/resistive-touchscreen-manual-install-calibrate
	fi
	if ! grep -q "^rp_[u_]sbdisplay" /etc/modules; then printf "rp_usbdisplay\n" >> /etc/modules; fi
fi

if [ "$ENABLE_3G_MODEM" == "1" ]; then
    # https://linux-romania.com/ro/raspberry-pi-project/23-zte-mf-110-digi-net-mobile-.html
    # http://myhowtosandprojects.blogspot.ro/2013/12/how-to-setup-usb-3g-modem-linux.html
    if ! grep -q "ttyUSB2" /etc/wvdial.conf; then
        echo "Enabling 3G modem"
        apt install -y ppp wvdial usb-modeswitch
        echo "
[Dialer Defaults]
Modem Type = Analog Modem
Phone = *99***1#
ISDN = 0
Baud = 9600
Modem = /dev/ttyUSB2
Init1 = ATZ
Init2 = at+cgdcont=1,"ip","internet"
Stupid Mode = 1
Password = { }
Username = { }
Abort on No Dialtone = 0
Dial Attempts = 0
        " > /etc/wvdial.conf
        dos2unix /etc/wvdial.conf
        echo "Testing connectivity, press CTRL+C if OK"
        wvdial
        #improve this as removes wanted line
        sed -i '/exit 0/d' /etc/rc.local
        echo "
echo Waiting 20s for USB modem to connect
sleep 20
wvdial &
exit 0
        " >> /etc/rc.local
    fi

    #https://www.raspberrypi.org/forums/viewtopic.php?t=41056
    #https://ubuntuforums.org/showthread.php?t=1648939
    # https://askubuntu.com/questions/667922/udev-script-doesnt-run-in-the-background
    #echo 'ACTION=="add",SUBSYSTEMS=="usb",ATTRS{manufacturer}=="ZTE,Incorporated",RUN+="/usr/bin/wvdial & disown"' > /etc/udev/rules.d/10-3gstick.rules

    # https://unix.stackexchange.com/questions/296347/crontab-never-running-while-in-etc-cron-d
    #cat ${HAIOT_DIR}/apps/dashcam/scripts/cron.d.3gdial >> /etc/crontab

    ln -s $HAIOT_DIR/scripts /home/scripts

    cp $HAIOT_DIR/scripts/osinstall/ubuntu/etc/systemd/system/keep_internet.service /lib/systemd/system/
    systemctl enable keep_internet.service
    systemctl start keep_internet.service

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
	if [ "$ENABLE_LOG_RAM" == "1" ]; then
        echo "tmpfs           /var/log        tmpfs   defaults,noatime        0       0" >> /etc/fstab
	fi
    echo "tmpfs           /tmp            tmpfs   defaults,noatime        0       0" >> /etc/fstab
	mount -a
else
	echo "Ram folder for sqlite db storage exists already"
fi

# https://www.cyberciti.biz/tips/linux-use-gmail-as-a-smarthost.html
# http://iqjar.com/jar/sending-emails-from-the-raspberry-pi/
cat /etc/ssmtp/ssmtp.conf | grep "smtp.gmail.com"
if [ "$?" == "1" ]; then
    apt install -y ssmtp mailutils
    echo "Setting email"
    read -sp "Enter email password:" emailpass
    echo "AuthUser=antonio.gaudi33@gmail.com" >> /etc/ssmtp/ssmtp.conf
    echo "AuthPass=$emailpass" >> /etc/ssmtp/ssmtp.conf
    echo "FromLineOverride=YES" >> /etc/ssmtp/ssmtp.conf
    echo "mailhub=smtp.gmail.com:587" >> /etc/ssmtp/ssmtp.conf
    echo "UseSTARTTLS=YES" >> /etc/ssmtp/ssmtp.conf
    #echo "Now enter your password in email conf and save with CTRL+x"
    #sleep 3
    #nano /etc/ssmtp/ssmtp.conf
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