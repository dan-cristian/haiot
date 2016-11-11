#!/bin/bash

USERNAME=haiot
USERPASS=haiot
ENABLE_WEBMIN=0
ENABLE_OPTIONAL=0
ENABLE_HAIOT=0
ENABLE_RAMRUN=0
ENABLE_MEDIA=1
ENABLE_SNAPRAID=1
DATA_DISK1=/mnt/data/hdd-wdg-6297
DATA_DISK2=/mnt/data/hdd-wdr-evhk
PARITY_DISK=/mnt/parity/hdd-wdg-2130
ENABLE_GIT=1
GIT_ROOT=/mnt/data/hdd-wdg-6297/git
ENABLE_CAMERA=1
LOG_ROOT=/mnt/data/hdd-wdr-evhk/log

echo "Setting timezone ..."
echo "Europe/Bucharest" > /etc/timezone
dpkg-reconfigure -f noninteractive tzdata

echo "Updating apt-get"
apt-get -y update
apt-get -y upgrade
echo "Installing additional packages"
apt-get -y install dialog sudo nano wget runit git ssmtp mailutils psmisc smartmontools localepurge mosquitto
if [ "$ENABLE_RAMRUN" == "1" ]; then
    # run in ram needs busybox for ramfs copy operations, see "local" script sample
    apt-get -y install busybox
fi

if [ "$ENABLE_OPTIONAL" == "1" ]; then
	apt-get -y install htop mc
	# inotify-tools dosfstools apt-utils
fi

cat /etc/apt/sources.list | grep "webmin"
if [ "$?" == "1" ]; then
    echo "Installing webmin"
    echo "deb http://download.webmin.com/download/repository sarge contrib" >> /etc/apt/sources.list
    wget http://www.webmin.com/jcameron-key.asc
    apt-key add jcameron-key.asc
    apt-get update
    apt-get install webmin
fi

echo "Creating user $USERNAME with password=$USERPASS"
useradd ${USERNAME} -m
echo "$USERNAME:$USERPASS" | chpasswd
adduser ${USERNAME} sudo
adduser ${USERNAME} audio
chsh -s /bin/bash ${USERNAME}


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


echo "Getting HAIOT application from git"
cd /home/${USERNAME}
rm -r PYC
rm -r haiot
git clone git://192.168.0.9/PYC.git
if [ "$?" == "0" ]; then
    echo "Dowloaded haiot from local repository"
    export HAIOT_DIR=/home/$USERNAME/PYC
else
    echo "Downloading haiot from github"
    git clone https://github.com/dan-cristian/haiot.git
    export HAIOT_DIR=/home/$USERNAME/haiot
fi
echo 'HAIOT_DIR=$HAIOT_DIR' > /etc/profile.d/haiot.sh
chmod +x /etc/profile.d/haiot.sh

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
    echo "Installing media - sound + mpd + kodi"
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

    apt-get install mpd mpc triggerhappy
    cp $HAIOT_DIR/scripts/osinstall/ubuntu/etc/triggerhappy/triggers.conf /etc/triggerhappy/
    ln -s $LOG_ROOT /mnt/log

    apt-get install i3 xinit xterm

fi

if [ "$ENABLE_CAMERA" == "1" ]; then
    apt-get install motion
fi

if [ "$ENABLE_HAIOT" == "1" ]; then
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

    if [ "$ENABLE_PIGPIO" == "1" ]; then
        echo "Downloading pigpio library for gpio access"
        wget abyz.co.uk/rpi/pigpio/pigpio.zip
        unzip pigpio.zip
        apt-get -y install build-essential
        echo "Compiling pigpio"
        cd PIGPIO
        make
        echo "Installing pigpio"
        make install
        cp /home/${USERNAME}/${HAIOT_DIR}/scripts/pigpio_daemon /etc/init.d
        chmod +x /etc/init.d/pigpio_daemon
        update-rc.d pigpio_daemon defaults
        rm -r /home/${USERNAME}/PIGPIO
        rm /home/${USERNAME}/pigpio.zip
        #python setup.py install
        #todo install pigpiod init script
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
        # stty rows 30 cols 40
        # setfont -f Uni2-VGA8
        apt-get -y install gpm
    fi

    echo "Configuring HAIOT application"
    cd /home/${USERNAME}/${HAIOT_DIR}
    chmod +x scripts/*sh*
    chmod +x *.sh
    scripts/setup.sh
    chown -R ${USERNAME}:${USERNAME} .
fi



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
    echo "This is a test" | mail -s "Test" dan.cristian@gmail.com
fi

echo "Removing not needed files and cleaning apt files"
apt-get -y remove build-essential
rm /usr/share/doc -r
rm /usr/share/man -r
apt-get -y autoremove
apt-get clean

