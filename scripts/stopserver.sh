#!/usr/bin/env bash

kill $(ps w | grep '[p]ython run_all.py' | awk '{print $1}')
