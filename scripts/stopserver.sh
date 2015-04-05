#!/usr/bin/env bash
proc_pid=$(ps w | grep '[p]ython run_all.py' | awk '{print $1}')
echo Killing proc id [$proc_pid]
kill $proc_pid
