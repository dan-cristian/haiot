#!/usr/bin/env bash
export proc_pid=$(ps w | grep '[h]aiot.py' | awk '{print $1}')
echo "proc pid=$proc_pid, 1st attempt"
if [ -z "$proc_pid" ]; then
    echo "No pid found with ps w, trying now with ps wx"
    export proc_pid=$(ps wx | grep '[h]aiot.py' | awk '{print $1}')
    echo "proc pid=$proc_pid, 2nd attempt"
fi
if [ -n "$proc_pid" ]; then
    echo "Killing proc id [$proc_pid]"
    kill $proc_pid
    sleep 1
    kill -9 $proc_pid
else
    echo "Program is not running, nothing to stop"
fi