#!/bin/bash

# https://unix.stackexchange.com/questions/190513/shell-scripting-proper-way-to-check-for-internet-connectivity

GW=`/sbin/ip route | awk '/default/ { print $3 }'`
checkdns=`cat /etc/resolv.conf | awk '/nameserver/ {print $2}' | awk 'NR == 1 {print; exit}'`
pppdns=`cat /etc/ppp/resolv.conf | awk '/nameserver/ {print $2}' | awk 'NR == 1 {print; exit}'`
checkdomain=google.com
pcount=2
timeout=4
ENABLE_WIFI=1
ENABLE_3G=1
IF_3G=ppp0
IF_WIFI=wlan0
TOUCH_HAVE_INTERNET=/tmp/haveinternet
TOUCH_HAVE_WLAN=/tmp/havewlan
TOUCH_HAVE_3G=/tmp/have3g
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
  echo "Pinging $1 to check for internet connection." && echo
  ping $1 -c ${pcount} -W ${timeout}

  if [ $? -eq 0 ]
    then
      echo && echo "$1 pingable. Internet connection is most probably available."&& echo
      #Insert any command you like here
      return 0
    else
      echo && echo "Could not establish internet connection in pingnet. Something may be wrong here." >&2
      return 1
      #Insert any command you like here
#      exit 1
  fi
}

function pingdns
{
  #Grab first DNS server from /etc/resolv.conf
  echo "Pinging first DNS server in resolv.conf ($checkdns) to check name resolution" && echo
  ping $checkdns -c ${pcount} -W ${timeout}
    if [ $? -eq 0 ]
    then
      echo && echo "$checkdns pingable. Proceeding with domain check."
      #Insert any command you like here
    else
      echo && echo "Could not establish internet connection to DNS. Something may be wrong here." >&2
      #Insert any command you like here
#     exit 1
  fi
}

function httpreq
{
  echo && echo "Checking for HTTP Connectivity"
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
    echo "Pinging gateway ($GW) to check for LAN connectivity" && echo;
    if [ "$GW" = "" ]; then
        echo "There is no gateway. Probably disconnected..."
    #    exit 1
    fi
    ping ${GW} -c ${pcount} -W ${timeout}
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
      pingdns
      pingnet $checkdomain
      portscan $checkdomain 80
      httpreq
      echo > /tmp/haveinternet
      return 0
    else
      echo && echo "Something is wrong with LAN (Gateway unreachable)"
      pingdns
      pingnet $checkdomain
      portscan $checkdomain 80
      httpreq
      #  exit 1
    fi

}

# test internet connectivity without making traffic (via interface status etc)
function have_internet_no_traffic
{
    return 0
}

function have_if {
    IF=$1
    TOUCH=$2
    out=`ifconfig ${IF} | grep "inet "`
    if [ $? == 0 ]; then
        arr=(`echo ${out}`)
        echo "I have ${IF}, ip is " ${arr[1]}
        if [ ${arr[4]} == "destination" ]; then
            gw=${arr[5]}
            dns=${pppdns}
        else
            out=`route -n | grep ${IF} | grep U`
            if [ $? == 0 ]; then
                arr=(`echo ${out}`)
                gw=${arr[1]}
            else
                echo "Unexpected empty outcome"
            fi
        fi
        echo "${IF} gateway is " ${gw}
        pingnet ${gw}
        if [ $? == 0 ]; then
            touch ${TOUCH}
            chmod 777 ${TOUCH}
            return 0
        else
            echo "Gateway ${gw} not responding to ping, trying DNS scan ${dns}"
            portscan ${dns} 53
            if [ $? == 0 ]; then
                echo "DNS ${dns} responded to scan"
                touch ${TOUCH}
                chmod 777 ${TOUCH}
                return 0
            else
                echo "DNS not responding as well, no internet connectivity via interface ${IF}"
            fi
        fi
    fi
    if [ -f ${TOUCH} ]; then
        rm ${TOUCH}
    fi
    return 1
}


function restart_wifi {
    echo "Restarting wifi"
    ifconfig ${IF_WIFI} up
}

function restart_3g {
    echo "Restarting ppp"
    killall -q -v pppd
    killall -q -v wvdial
    /usr/bin/wvdial &
}


function loop
{
while :
do
    have_internet
    have_if ${IF_WIFI} ${TOUCH_HAVE_WLAN}
    have_if ${IF_3G} ${TOUCH_HAVE_3G}

    if [ ${ENABLE_WIFI} == 1 ] && [ ! -f ${TOUCH_HAVE_WLAN} ]; then
        restart_wifi
    fi

    if [ ${ENABLE_3G} == 1 ] && [ ! -f ${TOUCH_HAVE_3G} ]; then
        restart_3g
    fi

    sleep 5
done
}

echo "Keep_internet service started with params=${@}"
loop

