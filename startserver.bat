@echo off

goto :start
:run_app
    python run_all.py model_auto_update %~1
    set exit_code=%ERRORLEVEL%
    echo Program exit with code %exit_code%
    echo ---------------------------------
goto :app_stop

:start
    goto :run_app %1
:app_stop
    echo Processing exit code %exit_code%
    if %exit_code% EQU 131 echo "Restarting app"

    if %exit_code% EQU 132 (
        echo Upgrading app
        git pull --no-edit
    )

    if %exit_code% EQU 133 (
        echo Shutdown app
        goto :end
    )

    if %exit_code% EQU 143 (
        echo App was killed
        goto :end
    )
    if %exit_code% EQU 137 (
        echo App was killed with -9
        goto :end
    )
    if %exit_code% EQU 1 echo App was interrupted with CTRL-C

goto :start

:end