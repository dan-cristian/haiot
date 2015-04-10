#!/usr/bin/env bash
proc_pid=$(ps w | grep '[p]ython run_all.py' | awk '{print $1}')
if [ -e "$proc_pid" ]; then
    proc_pid=$(ps wx | grep '[p]ython run_all.py' | awk '{print $1}')
fi
if [ -n "$proc_pid" ]; then
    echo Killing proc id [$proc_pid]
    kill $proc_pid
else
    echo Program is not running, nothing to stop
fi