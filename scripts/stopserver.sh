#!/usr/bin/env bash
proc_pid=$(ps w | grep '[h]aiot.py' | awk '{print $1}')
# echo "proc pid=$proc_pid, 1st attempt"
if [ -z "$proc_pid" ]; then
    # echo "No pid found with ps w, trying now with ps wx"
    proc_pid=$(ps wxa | grep '[h]aiot.py' | awk '{print $1}')
    # echo "proc pid=$proc_pid, 2nd attempt"
fi
if [ -n "$proc_pid" ]; then
    echo "Killing proc id [$proc_pid]"
    kill $proc_pid
    sleep 2
    kill -9 $proc_pid
else
    echo "Program is not running, nothing to stop"
fi