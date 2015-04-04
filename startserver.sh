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
    scripts/stopserver.sh
    source venv/bin/activate
    python run_all.py disk
    exit_code=$?
    echo "Program exit with code $exit_code"
}

must_run=true
while $must_run; do
    run_app
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
done