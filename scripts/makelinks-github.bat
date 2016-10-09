SET T=c:\development\python\main_app
cd ..
mklink /J  alarm %T%\alarm
mklink /J  cloud %T%\cloud
mklink /J  common %T%\common
mklink /J  ddns %T%\ddns
mklink /J  gpio %T%\gpio
mklink /J  health_monitor %T%\health_monitor
mklink /J  heat %T%\heat
mklink /J  main %T%\main
mklink /J  music %T%\music
mklink /J  node %T%\node
mklink /J  presence %T%\presence
mklink /J  rule %T%\rule
mklink /J  scripts %T%\scripts
mklink /J  sensor %T%\sensor
mklink /J  sysutils %T%\sysutils
mklink /J  template %T%\template
mklink /J  test %T%\test
mklink /J  transport %T%\transport
mklink /J  utility %T%\utility
mklink /J  webui %T%\webui

del LICENSE
mklink /H LICENSE %T%\LICENSE
del README.md
mklink /H README.md %T%\README.md

del haiot.py
mklink /H haiot.py %T%\haiot.py

del start_daemon_userspaces.sh
mklink /H start_daemon_userspaces.sh  %T%\start_daemon_userspaces.sh
del startserver.bat
mklink /H startserver.bat  %T%\startserver.bat

del .gitignore
mklink /H .gitignore %T%\.gitignore
del requirements.txt
mklink /H requirements.txt %T%\requirements.txt
del requirements-beaglebone.txt
mklink /H requirements-beaglebone.txt %T%\requirements-beaglebone.txt
del requirements-rpi.txt
mklink /H requirements-rpi.txt %T%\requirements-rpi.txt
del requirements-win.txt
mklink /H requirements-win.txt %T%\requirements-win.txt

rem mklink /J   %T%\

call scripts/push.bat