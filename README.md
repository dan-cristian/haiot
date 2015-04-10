# haiot
<h1>Home Automation &amp; Internet of Things</h1>

<h2>System capabilities</h2>
Application is split in modules, each with a set of features. Modules can be enabled or disabled.

<h3>admin (mandatory)</h3>
This is a mandatory module that includes db setup, thread pool and events processing
System configuration via a web interface, accessible usually at http://localhost:5000/admin/modules

<h3>mqtt_io (mandatory)</h3>
Module used for communication with other application modules

<h3>health_monitor</h3>
Monitors CPU , memory usage, hard drives temperature, disk health

<h3>webui</h3>
Web interface to manage the application

<h3>node</h3>
Cluster capability, multiple nodes can run at the same time with failover capability enabled

<h3>sensor</h3>
Monitors 1-wire sensors based on owserver and RFXCOM compatible sensors.
RFXCOM device tested is RFXtrx433.

<h3>alarm</h3>

<h3>heat</h3>
<h3>io_bbb</h3>
IO input capability for beaglebone, detects contact states, used as a basis for alarm system

<h3>graph_plotly</h3>
Automatically creates graphics online using free plot.ly service. 
Check some samples <a  href="https://plot.ly/~dancri77">here</a>.

<h3>relay</h3>
Turns on and off relays

<h2>Target Platforms</h2>
- Linux (tested mostly with Debian)
- Windows (tested with Windows 8.1

<h3>Application was tested on:</h3>
- Raspberry Pi model B
- Beaglebone Black
- Debian (Openmediavault based install)
- OpenWrt/Linaro GCC 4.8-2014.04 r42625 (
- Windows 8.1 64 bit

<h2>How to setup the application</h2>
General prerequisites:<br>
- python 2.7
- several python packages listed in requirements.txt
- connection to a mqtt server, tested with mosquitto

Specific prerequisites for Windows 8.1<br>
- hdparm
- smartmoontools
- bash, nohup, sudo
Ensure hdparm.exe and smartctl.exe are added in the PATH

Specific prerequisites for Linux<br>
- Enable sudo access for hdparm and smartctl
- virtualenv usage recommended
- for pyserial, set access rights to open /dev/ttyUSBx device: sudo usermod -a -G dialout $USER

On Linux, grant execute rights and run setup.sh.bat.
This will install virtualenv and setup a python venv context with all required packages

<h2>How to start / stop the application</h2>
Run startserver.sh OR python run_all.py <disk or mem> <debug or warning>
Run stopserver.sh to stop the application

<h3>Startup parameters</h3>
- db_disk or db_mem parameters specify where the database file will be created.
for db_disk option, db is created in the current path.
for db_mem option, db is created in /tmp folder, on constrained devices (PI, BBB) this is usually mapped to ramfs.
Note that db content will be lost at restarts if db is created in ram
- model_auto_update, automatically updates db schema if changes are detected (implies drop tables and default values)