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
mklink /J  test %T%\test
mklink /J  webui %T%\webui
mklink /J  scripts %T%\scripts
mklink /H LICENSE %T%\LICENSE
mklink /H README.md %T%\README.md
mklink /H run_all.py %T%\run_all.py
mklink /H startserver.sh %T%\startserver.sh
mklink /H startserver_mem.sh  %T%\startserver_mem.sh
mklink /H startserver.bat  %T%\startserver.bat
mklink /H .gitignore %T%\.gitignore
rem mklink /J   %T%\