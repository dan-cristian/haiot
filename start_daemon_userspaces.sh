#!/usr/bin/env bash

function run_app {
    $DIR/scripts/stopserver.sh
    sleep 2
    echo Starting app with parameter $1 $2 $3 $4 $5 $6 $7 $8 $9 $10
    source $DIR/venv/bin/activate
    python $DIR/haiot.py $1 $2 $3 $4 $5 $6 $7 $8 $9 $10
    exit_code=$?
    echo "Program exit with code $exit_code"
    echo "---------------------------------"
}

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
echo "Current dir on start is $DIR, script start parameters are: " $1 $2 $3 $4 $5
must_run=true
echo "Getting latest haiot version from git"
git pull --no-edit
while $must_run; do
    run_app db_mem model_auto_update syslog=logs2.papertrailapp.com:30445 $1 $2 $3 $4 $5
    if [ $exit_code == 131 ]; then
        echo "Restarting app"
    fi
    if [ $exit_code == 132 ]; then
        echo "Upgrading app"
        cd $DIR
        git pull --no-edit
    fi
    if [ $exit_code == 133 ]; then
        echo "Shutdown app"
        must_run=false
    fi
    if [ $exit_code == 143 ]; then
        echo "App was killed"
        must_run=false
    fi
    if [ $exit_code == 137 ]; then
        echo "App was killed with -9"
        must_run=false
    fi
    if [ $exit_code == 1 ]; then
        echo "App was interrupted with CTRL-C or by exception code [$exit_code]"
        must_run=false
    fi
done