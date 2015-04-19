#!/usr/bin/env bash
#echo Enter mem[Enter] to run db in memory. Default is from disk
#read -t 3 answer
#if [ $? == 0 ]; then
#    echo "Selected"
#else
#    echo "Can't wait anymore!"
#answer=disk
#fi
#echo "Your answer is: $answer"

function run_app {
    $DIR/scripts/stopserver.sh
    sleep 2
    echo Starting app with parameter $1 $2 $3 $4 $5 $6 $7 $8 $9 $10
    source $DIR/venv/bin/activate
    python $DIR/run_all.py $1 $2 $3 $4 $5 $6 $7 $8 $9 $10
    exit_code=$?
    echo "Program exit with code $exit_code"
    echo "---------------------------------"
}
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
must_run=true
while $must_run; do
    run_app $1 $2 $3 $4 $5 $6 $7 $8 $9 $10
    if [ $exit_code == 131 ]; then
        echo "Restarting app"
    fi
    if [ $exit_code == 132 ]; then
        echo "Upgrading app"
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
        echo "App was interrupted with CTRL-C or by exception"
        must_run=false
    fi
done