SET T=c:\development\python\main_app
cd ..
mklink /J  alarm %T%\alarm
mklink /J  common %T%\common
mklink /J  graph_plotly %T%\graph_plotly
mklink /J  health_monitor %T%\health_monitor
mklink /J  heat %T%\heat
mklink /J  io_bbb %T%\io_bbb
mklink /J  main %T%\main
mklink /J  mqtt_io %T%\mqtt_io
mklink /J  node %T%\node
mklink /J  relay %T%\relay
mklink /J  sensor %T%\sensor
mklink /J  template %T%\template
mklink /J  transport %T%\transport
mklink /J  test %T%\test
mklink /J  webui %T%\webui
mklink /J  scripts %T%\scripts
mklink /J  ddns %T%\ddns
mklink /J  cloud %T%\cloud
mklink /J  sysutils %T%\sysutils
mklink /J  rule %T%\rule

del LICENSE
mklink /H LICENSE %T%\LICENSE
del README.md
mklink /H README.md %T%\README.md
del haiot.py
mklink /H haiot.py %T%\haiot.py
del startserver.sh
mklink /H startserver.sh %T%\startserver.sh
del startserver_mem.sh
mklink /H startserver_mem.sh  %T%\startserver_mem.sh
del startserver_mem_nosyslog.sh
mklink /H startserver_mem_nosyslog.sh  %T%\startserver_mem_nosyslog.sh
del startserver_disk.sh
mklink /H startserver_disk.sh  %T%\startserver_disk.sh
del startserver_daemon.sh
mklink /H startserver_daemon.sh  %T%\startserver_daemon.sh
del startserver.bat
mklink /H startserver.bat  %T%\startserver.bat
del .gitignore
mklink /H .gitignore %T%\.gitignore
del requirements.txt
mklink /H requirements.txt %T%\requirements.txt

rem mklink /J   %T%\

call scripts/push.bat