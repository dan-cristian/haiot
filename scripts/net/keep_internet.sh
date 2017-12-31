#!/bin/bash

# https://unix.stackexchange.com/questions/190513/shell-scripting-proper-way-to-check-for-internet-connectivity
GW=`/sbin/ip route | awk '/default/ { print $3 }'`
checkdns=`cat /etc/resolv.conf | awk '/nameserver/ {print $2}' | awk 'NR == 1 {print; exit}'`
pppdns1=`cat /etc/ppp/resolv.conf | awk '/nameserver/ {print $2}' | awk 'NR == 1 {print; exit}'`
pppdns2=`cat /etc/ppp/resolv.conf | awk '/nameserver/ {print $2}' | awk 'NR == 2 {print; exit}'`
checkdomain=google.com
pcount=3
timeout=10
ENABLE_WIFI=1
ENABLE_3G=1
ENABLE_ETH=0
ENABLE_SSH_TUNNEL=1
SSH_HOST=www.dancristian.ro
SSH_USER=haiot
SSH_REMOTE_PORT=60000
SSH_CHECK_REMOTE_HOST=192.168.0.9
SSH_LOG=/tmp/ssh.log
FWKNOCK_PORT=62222
FWKNOCK_SSH_PROFILE=nas
MY_IP_HOST=67.20.100.192
MY_IP_URL=https://${MY_IP_HOST}/cgi-bin/myip
IF_3G=ppp0
IF_WIFI=wlan0
TOUCH_HAVE_INTERNET=/tmp/haveinternet
TOUCH_HAVE_WLAN=/tmp/havewlan
TOUCH_HAVE_3G=/tmp/have3g
MODEM_3G_KEYWORD='ZTE WCDMA'
MODEM_CONF_FILE=/etc/wvdial.conf
MODEM_DEV_1=/dev/gsmmodem
MODEM_DEV_2=/dev/ttyUSB2
DHCP_DEBUG_FILE=/tmp/dhclient-script.debug
GW_WLAN=""
GW_3G="" # gateway for 3g link
EXT_IP_3G="" # external ip via 3g
SSH_EXT_IP_CONNECTED="" # ip to which ssh connected succesfully last time
#some functions


function shut_usb_eth {
    echo "Turn off eth usb port"
    /usr/local/bin/hub-ctrl -h 0 -P 1 -p 0
}

# https://www.raspberrypi.org/forums/viewtopic.php?t=196827
function cycle_usb_ports {
    /usr/local/bin/hub-ctrl -h 0 -P 2 -p 0
    sleep 5
    /usr/local/bin/hub-ctrl -h 0 -P 2 -p 1
}

# https://unix.stackexchange.com/questions/242546/how-to-get-bus-id-of-an-usb-device
function reset_3g_port {
    out=`tail /sys/bus/usb/devices/*/product | grep -B 1 "${MODEM_3G_KEYWORD}" | head -1`
    #==> /sys/bus/usb/devices/1-1.2/product <==
    bus_id=`echo $out | cut -d/ -f 6`
    echo -n "${bus_id}" > /sys/bus/usb/drivers/usb/unbind
    sleep 3
    echo -n "${bus_id}" > /sys/bus/usb/drivers/usb/bind
}


function portscan
{
  host=$1
  port=$2
  #echo "Starting port scan of $checkdomain port 80"
  if nc -zw1 -w ${timeout} ${host} ${port}; then
    #echo "Port scan good, $checkdomain port 80 available"
    return 0
  else
    echo "Port scan of ${host}:${port} failed."
    return 1
  fi
}

function pingnet
{
  #Google has the most reliable host name. Feel free to change it.
  #echo "Pinging $1 to check for internet connection." && echo
  host=$1
  if=$2
  ping ${host} -c ${pcount} -W ${timeout} -q -I ${if} > /dev/null

  if [ $? -eq 0 ]
    then
      #echo && echo "$1 pingable. Internet connection is most probably available."&& echo
      #Insert any command you like here
      return 0
    else
      echo && echo "Could not establish internet connection in pingnet for ${if}." >&2
      return 1
      #Insert any command you like here
#      exit 1
  fi
}

function ping_via_gw {
    if=$1
    gw=$2
    line=`getent ahostsv4 ${checkdomain} | head -1`
    host=${line%  *}
    route add -host ${host} gw ${gw}
    ping ${host} -c ${pcount} -W ${timeout} -q -I ${if} > /dev/null
    res=$?
    route del -host ${host}
    if [ ${res} -eq 0 ]; then
        return 0
    else
        echo && echo "Could not establish internet connection in ping ${host} via gw ${gw} on ${if}" >&2
        return 1
    fi
}

function httpreq
{
  #echo && echo "Checking for HTTP Connectivity"
  case "$(curl -s --max-time 2 -I $checkdomain | sed 's/^[^ ]*  *\([0-9]\).*/\1/; 1q')" in
    [23]) echo "HTTP connectivity is up";;
    5) echo "The web proxy won't let us through";exit 1;;
    *) echo "Something is wrong with HTTP connections. Go check it."; exit 1;;
  esac
#  exit 0
}


function have_internet
{
    #echo "Fast check for HTTPS connectivity" && echo
    if portscan ${checkdomain} 80; then
        touch ${TOUCH_HAVE_INTERNET}
        chmod 777 ${TOUCH_HAVE_INTERNET}
        return 0;
    fi
    if [ -f ${TOUCH_HAVE_INTERNET} ]; then
        rm ${TOUCH_HAVE_INTERNET}
    fi
    return 1
}

function have_lan_connected {
    if=$1
    touch=$2
    out=`ifconfig ${if} | grep "inet "`
    if [ $? == 0 ]; then
        return 0
    else
        echo "${if} is not connected"
    fi
    if [ -f ${touch} ]; then
        rm ${touch}
    fi
    return 1
}


function have_3g_modem {
    lsusb | grep -q "${MODEM_3G_KEYWORD}"
    if [ $? == 0 ]; then
        return 0
    else
        echo "3G modem ${MODEM_3G_KEYWORD} not found"
    fi
    if [ -f ${TOUCH_HAVE_3G} ]; then
        rm ${TOUCH_HAVE_3G}
    fi
    return 1
}

function have_if {
    if=$1
    touch=$2
    gw=$3
    #pingnet ${checkdomain} ${IF}
    ping_via_gw ${if} ${gw}
    if [ $? == 0 ]; then
        touch ${touch}
        chmod 777 ${touch}
        return 0
    else
        echo "${checkdomain} not responding to ping"
    fi

    if [ -f ${touch} ]; then
        rm ${touch}
    fi
    return 1
}


function restart_wifi {
    echo "Restarting wifi"
    ifconfig ${IF_WIFI} down
    ifconfig ${IF_WIFI} up
    sleep 10
}

function restart_3g {
    next_step=0
    while :
    do
        have_if ${IF_3G} ${TOUCH_HAVE_3G} ${GW_3G}
        if [ ! -f ${TOUCH_HAVE_3G} ] && [ ${next_step} == 0 ]; then
            echo "Restarting ppp daemon"
            killall -q -v wvdial
            killall -q -v pppd
            /usr/bin/wvdial &
            sleep 30
            next_step=1
        fi
        if [ ! -f ${TOUCH_HAVE_3G} ] && [ ${next_step} == 1 ]; then
            reset_3g_port
            next_step=2
        fi
        if [ ! -f ${TOUCH_HAVE_3G} ] && [ ${next_step} == 2 ]; then
            cycle_usb_ports
            next_step=3
        fi
        if [ ! -f ${TOUCH_HAVE_3G} ] && [ ${next_step} == 3 ]; then
            echo "Unable to recover 3G link"
            break
        fi
        if [ -f ${TOUCH_HAVE_3G} ]; then
            echo "3G link recovery succesfull"
            return 0
        fi
    done
    return 1
}


#Kernel IP routing table
#Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
#192.168.0.0     0.0.0.0         255.255.255.0   U     0      0        0 wlan0

#Kernel IP routing table
#Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
#0.0.0.0         0.0.0.0         0.0.0.0         U     0      0        0 ppp0
#10.64.64.64     0.0.0.0         255.255.255.255 UH    0      0        0 ppp0
#192.168.0.0     0.0.0.0         255.255.255.0   U     0      0        0 wlan0

function set_route_default {
    if=$1
    gw=$2
    #check if default gw not already set
    out=`route -n | grep 0.0.0.0 | head -1`
    if [ $? == 0 ]; then
        arr=(`echo ${out}`)
        if [ "${gw}" != "${arr[1]}" ]; then
            echo "Setting default gw to ${gw} for interface ${if}"
            ip route del default
            ip route add default via ${gw} dev ${if}
        fi
    fi
}


function get_3g_ext_ip {
    route add -host ${MY_IP_HOST} gw ${GW_3G}
    #set ppp as default interface
    #set_route_default ${if} ${gw}
    EXT_IP_3G=`curl --interface ${IF_3G} -k -s ${MY_IP_URL} | tr -d '[:cntrl:]'` # clean string
}

function check_ssh {
    ps ax | grep -q ${SSH_LOG} | head -1
    if [ $? == 0 ]; then
        grep -q "remote forward success" ${SSH_LOG}
        if [ $? == 0 ]; then
            LAST_EXT_IP=${EXT_IP_3G}
            get_3g_ext_ip
            if [ "${LAST_EXT_IP}" != "${EXT_IP_3G}" ]; then
                echo "SSH is probably freezed as 3G ip changed since got connected"
            else
                return 0
            fi
        else
            echo "SSH failed to start"
        fi
    else
        echo "SSH not started ok"
    fi
    out=`ps ax | grep ${SSH_LOG} | head -1`
    arr=(`echo ${out}`)
    pid=${arr[0]}
    echo "Killing instance ${pid}"
    kill ${pid}
    return 1
}

# http://www.thirdway.ch/En/projects/raspberry_pi_3g/index.php
function start_ssh {
    if=$1
    gw=$2
    get_3g_ext_ip
    route add -host ${SSH_HOST} gw ${gw} #  force route for fwknop and ssh via ppp
    su -lc "/usr/bin/fwknop -a ${EXT_IP_3G} -n ${FWKNOCK_SSH_PROFILE}" ${SSH_USER}
    if [ $? -eq 0 ]; then
        su -lc "/usr/bin/ssh -t ${SSH_USER}@${SSH_HOST} -p ${FWKNOCK_PORT} 'sudo netstat -anlp | grep 127.0.0.1:60000'"
        su -lc "/usr/bin/ssh -v -N -E ${SSH_LOG} -R ${SSH_REMOTE_PORT}:127.0.0.1:22 ${SSH_USER}@${SSH_HOST} -p ${FWKNOCK_PORT} &" ${SSH_USER}
        sleep 10
        check_ssh
        code=$?
        if [ ${code} == 0 ]; then
            echo "Started SSH succesfully"
            SSH_EXT_IP_CONNECTED=${EXT_IP_3G}
            if [ "${LAST_EXT_IP}" == "" ]; then
                LAST_EXT_IP=${EXT_IP_3G} # init if empty
            fi
        fi
    else
        echo && echo "Could not ssh connect to ${host} via gw ${gw} on ${if}" >&2
        code=1
    fi
    return ${code}
}



function get_gw_wlan {
    if=$1
    if [ -f ${DHCP_DEBUG_FILE} ]; then
        line=`grep -A 9 -B 1 ${if} ${DHCP_DEBUG_FILE} | tail -10 | grep new_routers`
        gw=${line##*=}
        GW_WLAN=${gw//\'} #strip quotes
        echo "Got dhcp network ${GW_WLAN} for interface ${if}"
        return 0
    else
        echo "DHCP debug file not found, activate it in /etc/dhcp/debug by setting RUN=Yes"
    fi
    return 1
}

function get_gw_3g {
    if=$1
    out=`ifconfig ${if} | grep "inet "`
    if [ $? == 0 ]; then
        arr=(`echo ${out}`)
        if [ ${arr[4]} == "destination" ]; then
            gw=${arr[5]}
            GW_3G=${gw}
            echo "Got destination network ${GW_3G} for interface ${if}"
            return 0
        else
            echo "Could not find destination ip for ${if}"
        fi
    else
        echo "Could not find interface ${if}, is it active?"
    fi
    return 1
}


function loop
{
if [ ${ENABLE_ETH} == 0 ]; then
    ifconfig eth0 down
    shut_usb_eth
fi

while :
do
    if [ ${ENABLE_WIFI} == 1 ]; then
        have_lan_connected ${IF_WIFI} ${TOUCH_HAVE_WLAN}
        if [ $? != 0 ]; then
            restart_wifi
        fi
        have_lan_connected ${IF_WIFI} ${TOUCH_HAVE_WLAN}
        if [ $? == 0 ]; then
            get_gw_wlan ${IF_WIFI}
            res=$?
            if [ ${res} != 0 ]; then
                restart_wifi
                get_gw_wlan ${IF_WIFI}
                res=$?
            fi
            if [ ${res} == 0 ]; then
                have_if ${IF_WIFI} ${TOUCH_HAVE_WLAN} ${GW_WLAN}
                if [ ! -f ${TOUCH_HAVE_WLAN} ]; then
                    restart_wifi
                else
                    # set wlan as default gw
                    set_route_default ${IF_WIFI} ${GW_WLAN}
                fi
            else
                echo "Unable to check WLAN link"
            fi
        else
            echo "WLAN is down, skip checking link"
        fi
    fi

    if [ ${ENABLE_3G} == 1 ]; then
        have_3g_modem
        if [ $? == 0 ]; then
            get_gw_3g ${IF_3G}
            res=$?
            if [ ${res} != 0 ]; then
                restart_3g
                get_gw_3g ${IF_3G}
                res=$?
            fi
            if [ ${res} == 0 ]; then
                have_if ${IF_3G} ${TOUCH_HAVE_3G} ${GW_3G}
                if [ ! -f ${TOUCH_HAVE_3G} ]; then
                    restart_3g
                else
                    check_ssh
                    if [ $? != 0 ]; then
                        start_ssh ${IF_3G} ${GW_3G}
                    fi
                    # set 3g as default gw only if wlan is off
                    if [ ! -f ${TOUCH_HAVE_WLAN} ]; then
                        set_route_default ${IF_3G} ${GW_3G}
                    fi
                fi
            else
                echo "Unable to check 3G link"
            fi
        else
            # restart 3G usb port?
            echo "3G modem not detected"
        fi
    fi

    have_internet

    sleep 30
done
}

echo "Keep_internet service started with params=${@}"
loop

