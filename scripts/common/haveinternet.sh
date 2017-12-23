#!/bin/bash

GW=`/sbin/ip route | awk '/default/ { print $3 }'`
checkdns=`cat /etc/resolv.conf | awk '/nameserver/ {print $2}' | awk 'NR == 1 {print; exit}'`
checkdomain=google.com
pcount=2
#some functions

function portscan
{
  tput setaf 6; echo "Starting port scan of $checkdomain port 80"; tput sgr0;
  if nc -zw1 $checkdomain 80; then
    tput setaf 2; echo "Port scan good, $checkdomain port 80 available"; tput sgr0;
    return 0
  else
    tput setaf 1; echo "Port scan of $checkdomain port 80 failed."
    return 1
  fi
}

function pingnet
{
  #Google has the most reliable host name. Feel free to change it.
  tput setaf 6; echo "Pinging $checkdomain to check for internet connection." && echo; tput sgr0;
  ping $checkdomain -c $pcount

  if [ $? -eq 0 ]
    then
      tput setaf 2; echo && echo "$checkdomain pingable. Internet connection is most probably available."&& echo ; tput sgr0;
      #Insert any command you like here
    else
      tput setaf 1; echo && echo "Could not establish internet connection. Something may be wrong here." >&2
      #Insert any command you like here
#      exit 1
  fi
}

function pingdns
{
  #Grab first DNS server from /etc/resolv.conf
  tput setaf 6; echo "Pinging first DNS server in resolv.conf ($checkdns) to check name resolution" && echo; tput sgr0;
  ping $checkdns -c $pcount
    if [ $? -eq 0 ]
    then
      tput setaf 6; echo && echo "$checkdns pingable. Proceeding with domain check."; tput sgr0;
      #Insert any command you like here
    else
      tput setaf 1; echo && echo "Could not establish internet connection to DNS. Something may be wrong here." >&2
      #Insert any command you like here
#     exit 1
  fi
}

function httpreq
{
  tput setaf 6; echo && echo "Checking for HTTP Connectivity"; tput sgr0;
  case "$(curl -s --max-time 2 -I $checkdomain | sed 's/^[^ ]*  *\([0-9]\).*/\1/; 1q')" in
    [23]) tput setaf 2; echo "HTTP connectivity is up"; tput sgr0;;
    5) echo "The web proxy won't let us through";exit 1;;
    *) tput setaf 1; echo "Something is wrong with HTTP connections. Go check it."; tput sgr0; exit 1;;
  esac
#  exit 0
}

function checkgw
{
    #Ping gateway first to verify connectivity with LAN
    tput setaf 6; echo "Pinging gateway ($GW) to check for LAN connectivity" && echo; tput sgr0;
    if [ "$GW" = "" ]; then
        tput setaf 1;echo "There is no gateway. Probably disconnected..."; tput sgr0;
    #    exit 1
    fi
    ping $GW -c $pcount
    return $?
}

tput setaf 6; echo "Fast check for HTTPS connectivity" && echo; tput sgr0;
if portscan; then exit 0; fi

checkgw
if [ $? -eq 0 ]
then
  tput setaf 6; echo && echo "LAN Gateway pingable. Proceeding with internet connectivity check."; tput sgr0;
  pingdns
  pingnet
  portscan
  httpreq
  exit 0
else
  echo && echo "Something is wrong with LAN (Gateway unreachable)"
  pingdns
  pingnet
  portscan
  httpreq
  #  exit 1
fi