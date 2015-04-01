# haiot
Home Automation &amp; Internet of Things

System capabilities
Application is split in modules, each with a set of features. Modules can be enabled or disabled.

admin module (mandatory)
This is a mandatory module that
System configuration via a web interface, accessible usually at http://localhost:5000/admin/modules

mqtt_io module


Target Platforms:
- Linux (tested mostly with Debian)
- Windows (tested with Windows 8.1

Application was tested on
- Raspberry Pi model B
- Beaglebone Black
- Debian (Openmediavault based install)
- Windows 8.1 64 bit

How to setup the application
General prerequisites:
- python 2.7
- several python packages listed in requirements.txt

Specific prerequisites for Windows 8.1
- hdparm
- smartmoontools
Ensure hdparm.exe and smartctl.exe are added in the PATH

Specific prerequisites for Linux
- Enable sudo access for hdparm and smartctl
- virtualenv usage recommended

On Linux, grant execute rights and run setup.sh.bat.
This will install virtualenv and setup a python venv context with all required packages

How to start / stop the application
Run startserver.sh OR python run_all.py <disk or mem> <debug or warning>
Run stopserver.sh to stop the application

Startup parameters
disk or mem parameters specify where the database file will be created.
for disk option, db is created in the current path.
for mem option, db is created in /tmp folder, on constrained devices (PI, BBB) this is usually mapped to ramfs.
Note that db content will be lost at restarts if db is created in ram
