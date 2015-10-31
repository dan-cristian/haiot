#! /bin/bash
chmod +x startserver*.sh
chmod +x scripts/stopserver.sh
sudo pip install --upgrade pip
sudo pip install virtualenv
virtualenv venv
source venv/bin/activate
echo Ensure pip latest version
pip install --upgrade pip
#latest needed for apscheduler
pip install --upgrade setuptools
echo Install mandatory requirements
pip install -r requirements.txt
echo Install optional requirements, you can ignore errors
pip install -r requirements-beaglebone.txt
pip install -r requirements-rpi.txt
pip install -r requirements-win.txt

echo Installing mysql connector
wget http://dev.mysql.com/get/Downloads/Connector-Python/mysql-connector-python-2.1.3.zip
unzip mysql-connector-python-2.1.3.zip
cd mysql-connector-python-2.1.3/
python setup.py install
cd ..
rm mysql-connector-python-2.1.3.zip
rm -r mysql-connector-python-2.1.3

echo Installing pigpio python module, assuming is installed in user home folder
cd ../PIGPIO
python setup.py install
cd ../PYC