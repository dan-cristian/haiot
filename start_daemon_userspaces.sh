#!/usr/bin/env bash

function run_app {
    $DIR/scripts/stopserver.sh
    sleep 2
    echo Starting app with parameter $1 $2 $3 $4 $5 $6 $7 $8 $9
    source $DIR/venv/bin/activate
    python $DIR/haiot.py $1 $2 $3 $4 $5 $6 $7 $8 $9 2>&1
    exit_code=$?
    echo "Program exit with code $exit_code"
    echo "---------------------------------"
}

function start {
git config --global user.email "dan.cristian@gmail.com"
git config --global user.name "Dan Cristian"
must_run=true
echo Setting dir to haiot root directory $DIR
cd $DIR
echo "Getting latest haiot version from git"
git pull --no-edit
exit_code=$?
if [ $exit_code == 128 ]; then
        echo "Git pull failed with code $exit_code, exiting"
        must_run=false
    fi

while $must_run; do
    if [[ "$@" == "standalone" ]]; then
        echo "Standalone mode, deleting db"
        rm /var/ram/database.db
    fi
    run_app db_mem model_auto_update sysloglocal $1 $2 $3 $4 $5 $6
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
}

stop() {
	me=`basename $0`
	echo "Stopping script $me"
    cd $DIR
    scripts/stopserver.sh
}

START_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
echo "Current dir on start is $START_DIR, script start parameters are: " $1 $2 $3 $4 $5 $6 $7 $8 $9
DIR=~/PYC
echo "Base dir is $DIR"



if [ "$1" = "stop" ]; then
        stop
else
        start $1 $2 $3 $4 $5 $6 $7 $8 $9
fi