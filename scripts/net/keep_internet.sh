#!/bin/bash

# https://unix.stackexchange.com/questions/190513/shell-scripting-proper-way-to-check-for-internet-connectivity

GW=`/sbin/ip route | awk '/default/ { print $3 }'`
checkdns=`cat /etc/resolv.conf | awk '/nameserver/ {print $2}' | awk 'NR == 1 {print; exit}'`
pppdns1=`cat /etc/ppp/resolv.conf | awk '/nameserver/ {print $2}' | awk 'NR == 1 {print; exit}'`
pppdns2=`cat /etc/ppp/resolv.conf | awk '/nameserver/ {print $2}' | awk 'NR == 2 {print; exit}'`
checkdomain=google.com
pcount=2
timeout=10
ENABLE_WIFI=1
ENABLE_3G=1
ENABLE_SSH_TUNNEL=1
SSH_USER_HOST=haiot@www.dancristian.ro
FWKNOCK_SSH_PROFILE=router
FWKNOCK_CHECK_HOST=192.168.0.1
IF_3G=ppp0
IF_WIFI=wlan0
TOUCH_HAVE_INTERNET=/tmp/haveinternet
TOUCH_HAVE_WLAN=/tmp/havewlan
TOUCH_HAVE_3G=/tmp/have3g
MODEM_3G_KEYWORD='ZTE WCDMA'
DHCP_DEBUG_FILE=/tmp/dhclient-script.debug
#some functions

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
  ping $1 -c ${pcount} -W ${timeout} -q -I ${if} > /dev/null

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

function checkgw
{
    #Ping gateway first to verify connectivity with LAN
    #echo "Pinging gateway ($GW) to check for LAN connectivity" && echo;
    if [ "$GW" = "" ]; then
        echo "There is no gateway. Probably disconnected..."
    #    exit 1
    fi
    ping ${GW} -c ${pcount} -W ${timeout} -q
    return $?
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


function debug {
    checkgw
    if [ $? -eq 0 ]
    then
      echo && echo "LAN Gateway pingable. Proceeding with internet connectivity check."
      pingnet $checkdns $IF_WIFI
      pingnet $checkdomain $IF_WIFI
      portscan $checkdomain 80
      httpreq
      echo > /tmp/haveinternet
      return 0
    else
      echo && echo "Something is wrong with LAN (Gateway unreachable)"
      pingnet $checkdns $IF_WIFI
      pingnet $checkdomain $IF_WIFI
      portscan $checkdomain 80
      httpreq
      #  exit 1
    fi

}


function have_3g_modem {
    lsusb | grep -q "${MODEM_3G_KEYWORD}"
    if [ $? == 0 ]; then
        return 0
    else
        echo "3G modem ${MODEM_3G_KEYWORD} not found"
        return 1
    fi
}

function have_if {
    IF=$1
    TOUCH=$2
    pingnet ${checkdomain} ${IF}
    if [ $? == 0 ]; then
        touch ${TOUCH}
        chmod 777 ${TOUCH}
        return 0
    else
        echo "${checkdomain} not responding to ping"
    fi

    if [ -f ${TOUCH} ]; then
        rm ${TOUCH}
    fi
    return 1
}


function restart_wifi {
    echo "Restarting wifi"
    #ifconfig ${IF_WIFI} up
}

function restart_3g {
    echo "Restarting ppp"
    killall -q -v wvdial
    killall -q -v pppd
    /usr/bin/wvdial &
    sleep 30
}


function start_ssh {
    /usr/bin/fwknop -s -n ${FWKNOCK_SSH_PROFILE} --verbose
    /usr/bin/ssh -N -R 9091:localhost:22 ${SSH_USER_HOST}
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

function set_default_route_dhcp {
    if=$1
    if [ -f ${DHCP_DEBUG_FILE} ]; then
        line=`grep -A 9 -B 1 ${if} ${DHCP_DEBUG_FILE} | tail -10 | grep new_routers`
        gw=${line##*=}
        echo "Got dhcp network ${gw} for interface ${if}"
        set_route_default ${if} ${gw}
    else
        echo "DHCP debug file not found, activate it in /etc/dhcp/debug by setting RUN=Yes"
    fi
}


function set_default_route_ppp {
    if=$1
    out=`ifconfig ${if} | grep "inet "`
    if [ $? == 0 ]; then
        arr=(`echo ${out}`)
        if [ ${arr[4]} == "destination" ]; then
            gw=${arr[5]}
            echo "Got destintion network ${gw} for interface ${if}"
            set_route_default ${if} ${gw}
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
while :
do
    if [ ${ENABLE_WIFI} == 1 ]; then
        have_if ${IF_WIFI} ${TOUCH_HAVE_WLAN}
        if [ ! -f ${TOUCH_HAVE_WLAN} ]; then
            restart_wifi
        else
            # set wlan as default gw
            set_default_route_dhcp ${IF_WIFI}
        fi
    fi

    if [ ${ENABLE_3G} == 1 ]; then
        have_3g_modem
        if [ $? == 0 ]; then
            have_if ${IF_3G} ${TOUCH_HAVE_3G}
            if [ ! -f ${TOUCH_HAVE_3G} ]; then
                restart_3g
            else
                # set 3g as default gw only if wlan is off
                if [ ! -f ${TOUCH_HAVE_WLAN} ]; then
                    set_default_route_ppp ${IF_3G}
                fi
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

