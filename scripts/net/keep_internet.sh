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
      echo && echo "Could not establish internet connection in pingnet. Something may be wrong here." >&2
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
    out=`ifconfig ${IF} | grep "inet "`
    if [ $? == 0 ]; then
        arr=(`echo ${out}`)
        #echo "I have ${IF}, ip is " ${arr[1]}
        if [ ${arr[4]} == "destination" ]; then
            gw=${arr[5]}
            #dns1=${pppdns1}
            #dns2=${pppdns2}
        else
            out=`route -n | grep ${IF} | grep U`
            if [ $? == 0 ]; then
                arr=(`echo ${out}`)
                gw=${arr[1]}
                #dns1=${checkdns}
                #dns2=""
            else
                echo "Unexpected empty outcome"
            fi
        fi
        #echo "${IF} gateway is " ${gw}
        pingnet ${checkdomain} ${IF}
        if [ $? == 0 ]; then
            touch ${TOUCH}
            chmod 777 ${TOUCH}
            return 0
        else
            echo "${checkdomain} not responding to ping"
            #portscan ${dns1} 53
            #res=$?
            #if [ ${res} != 0 ]; then
            #    echo "First DNS not responding to scan, trying 2nd DNS scan ${dns2}"
            #    portscan ${dns2} 53
            #    res=$?
            #fi

            #if [ ${res} == 0 ]; then
            #    echo "DNS responded to scan"
            #    touch ${TOUCH}
            #    chmod 777 ${TOUCH}
            #    return 0
            #else
            #    echo "DNS not responding as well, no internet connectivity via interface ${IF}"
            #fi
        fi
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


function set_default_route {
    if=$1
    if [ -f ${DHCP_DEBUG_FILE} ]; then
        line=`grep -A 9 -B 1 ${if} ${DHCP_DEBUG_FILE} | tail -10 | grep new_routers`
        gw=${line##*=}
        echo "Got dhcp gateway ${gw} for interface ${if}"
        #check if default gw not already set
        out=`route -n | grep UG`
        if [ $? == 0 ]; then
            arr=(`echo ${out}`)
            if [ "${gw}" != "${arr[1]}" ]; then
                echo "Setting default gw to ${gw} for interface ${if}"
                ip route del default
                ip route add default via ${gw} dev ${if}
            fi
        fi
    else
        echo "DHCP debug file not found, activate it in /etc/dhcp/debug by setting RUN=Yes"
    fi
}


function loop
{
while :
do
    set_default_route ${IF_WIFI}

    if [ ${ENABLE_WIFI} == 1 ]; then
        have_if ${IF_WIFI} ${TOUCH_HAVE_WLAN}
        if [ ! -f ${TOUCH_HAVE_WLAN} ]; then
            restart_wifi
        else
            # set wlan as default gw
            set_default_route ${IF_WIFI}
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
                    set_default_route ${IF_3G}
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

