 # haiot
<h1>Home Automation &amp; Internet of Things</h1>
<h2>Overview</h2>
With Haiot you can control a huge number of sensors and devices in your house (and not only), setup automation rules and visualise sensors and control the system via Web and Mobile interfaces. It integrates with Openhab via Mqtt.
The application currently covers the following automation scripts in my house:
<br>- Heating control (with multiple sources: gas, solar)
<br>- Ventilation systems (Interface with Atrea Duplex)
<br>- Alarm sensors (PIR)
<br>- Motion sensors (IP cameras via motion)
<br>- Watering system
<br>- Audio control via MPD (Interface with Yamaha RX-Vx700 via RS232)
<br>- Gates opening/close control
<br>- Electricity usage monitoring and grid export control function (Qubino, Shelly3M)
<br>- Presence monitoring (wifi, bluetooth)
<br>- Location tracking
<br>- Solar production tracking (APS Microinverters / ECU, Sonoff POW)
<br>- Solar excess export divert to water heater (via ESP8266 PWM and SSR relay)
<br>- Solar excess divert to battery charger (via DROK 720W Buck Converter)
<br>- Battery BMS monitoring integration via bluetooth (SmartBMS)
<br>- TV control (LG RS232)
<br>- Air quality monitoring (PM2.5, CO2, VOC, O3 sensors)
<br>- Dashboards and UI control with OpenHab and Grafana/Influxdb
<br>- and many more

<h2>System modules</h2>
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
Heat control

<h3>relay</h3>
Turns on and off relays

<h2>Target Platforms</h2>
- Linux (tested mostly with Debian)
- Windows (tested with Windows 8.1

<h3>Application was tested on:</h3>
- Raspberry Pi  (all versions)
- Beaglebone Black
- Debian (Openmediavault based install)
- OpenWrt/Linaro GCC 4.8-2014.04 r42625 (
- Windows 8.1 64 bit

<h3> Supported sensors</h3>
ESP8266 with Tasmota: Sonoff, Wemos D1 Mini
zWave (Qubino and other power meters)
1wire (temperature, humidity, etc)


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

<h1>Other packages used</h1>
https://github.com/woudt/pyRFXtrx

<p><p>
<b>
Many thanks @Jetbrains for providing a full license for PyCharm Professional!
